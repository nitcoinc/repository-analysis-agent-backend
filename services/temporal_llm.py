"""LLM layer for temporal / drift narratives."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from core.config import get_settings
from services.openai_chat import chat_completions_create

logger = logging.getLogger(__name__)
settings = get_settings()


def _client() -> Optional[OpenAI]:
    if not settings.openai_api_key:
        return None
    try:
        return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url or None)
    except Exception as exc:
        logger.warning("temporal_llm: OpenAI init failed: %s", exc)
        return None


def _merge_ai_summary_gaps(dest: Dict[str, Any], fb: Dict[str, Any]) -> None:
    """Fill empty LLM strings from rule-based fallback so the UI never shows blank sections."""
    d_ai = dict(dest.get("ai_summary") or {})
    f_ai = fb.get("ai_summary") or {}
    for k in ("drift_summary", "risky_modules", "anomalies"):
        if not str(d_ai.get(k) or "").strip():
            d_ai[k] = str(f_ai.get(k) or "").strip()
    dest["ai_summary"] = d_ai


def enrich_temporal_insights(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds: insights[], ai_summary { drift_summary, risky_modules, anomalies }.
    """
    client = _client()
    drift = payload.get("drift_metrics") or {}
    heat = payload.get("heatmap") or {}
    pr_i = payload.get("pr_insights") or {}
    dbg = payload.get("debug") or {}
    structured_insights: List[Dict[str, Any]] = list(payload.get("insights") or [])

    fallback = _fallback_insights(payload)

    churn_map = drift.get("module_churn_window") or drift.get("module_churn_30d") or {}
    compact = {
        "drift_statements": (drift.get("statements") or [])[:10],
        "module_churn_sample": dict(list(churn_map.items())[:12]) if isinstance(churn_map, dict) else {},
        "heatmap_top": (heat.get("modules") or [])[:12],
        "large_prs": (pr_i.get("large_prs") or [])[:8],
        "hotfixes": (pr_i.get("hotfix_patterns") or [])[:8],
        "repeat_files": (pr_i.get("repeat_files") or [])[:8],
        "commits_in_window": drift.get("commits_in_window") or dbg.get("commits_processed"),
    }

    if not client:
        out = dict(fallback)
        if structured_insights:
            out["insights"] = structured_insights[:10]
        _merge_ai_summary_gaps(out, fallback)
        return out

    prompt = (
        "You are analyzing code evolution over time. Identify risks, trends, and anomalies "
        "using ONLY the structured facts below. Do not invent commit hashes or authors.\n"
        "Respond with a single JSON object with keys:\n"
        '- "insights": array of { "severity": "low"|"medium"|"high", "title": string, "detail": string }, max 8\n'
        '- "drift_summary": string, 2-4 sentences\n'
        '- "risky_modules": string, list module names or themes at risk\n'
        '- "anomalies": string, unusual patterns (spikes, large PRs, hotfixes)\n'
        "Every string value must be non-empty when facts exist; if a category has no signal, write "
        '"No strong signal in this sample." rather than leaving the field blank.\n'
        f"\nFACTS:\n{json.dumps(compact, indent=2)}"
    )

    try:
        resp = chat_completions_create(
            client,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
        data = json.loads(raw)
        insights = data.get("insights") or []
        if not isinstance(insights, list):
            insights = []
        norm: List[Dict[str, Any]] = []
        for i in insights[:10]:
            if not isinstance(i, dict):
                continue
            title = str(i.get("title") or "").strip()
            detail = str(i.get("detail") or "").strip()
            if not title and detail:
                title = "Insight"
            if not title:
                continue
            norm.append(
                {
                    "severity": str(i.get("severity") or "medium").lower(),
                    "title": title[:200],
                    "detail": detail[:800],
                }
            )
        out = {
            "insights": norm,
            "ai_summary": {
                "drift_summary": str(data.get("drift_summary") or "").strip(),
                "risky_modules": str(data.get("risky_modules") or "").strip(),
                "anomalies": str(data.get("anomalies") or "").strip(),
            },
        }
        if not out["insights"] and structured_insights:
            out["insights"] = structured_insights[:10]
        _merge_ai_summary_gaps(out, fallback)
        logger.info("temporal_llm: generated %d insights", len(out["insights"]))
        return out
    except Exception as exc:
        logger.warning("temporal_llm failed: %s", exc)
        out = dict(fallback)
        if structured_insights:
            out["insights"] = structured_insights[:10]
        _merge_ai_summary_gaps(out, fallback)
        return out


def _fallback_insights(payload: Dict[str, Any]) -> Dict[str, Any]:
    drift = payload.get("drift_metrics") or {}
    statements = drift.get("statements") or []
    insights: List[Dict[str, Any]] = []
    for i, s in enumerate(statements[:6]):
        insights.append(
            {
                "severity": "medium",
                "title": f"Drift signal {i + 1}",
                "detail": s,
            }
        )
    pr_i = payload.get("pr_insights") or {}
    for lp in (pr_i.get("large_prs") or [])[:2]:
        insights.append(
            {
                "severity": "high",
                "title": f"Large PR #{lp.get('number')}",
                "detail": lp.get("title", "")[:300],
            }
        )
    return {
        "insights": insights[:10],
        "ai_summary": {
            "drift_summary": " ".join(statements[:3]) if statements else "Not enough history for a drift narrative.",
            "risky_modules": "See heatmap and impact table for modules with high churn and connectivity.",
            "anomalies": f"Hotfix-style PRs: {len(pr_i.get('hotfix_patterns') or [])}. Large PRs: {len(pr_i.get('large_prs') or [])}.",
        },
    }
