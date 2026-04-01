import re
from typing import Any, Dict, Optional

# Bare stub produced when OpenAI was unavailable: "Service: click._compat"
_STUB_RE = re.compile(r"^service:\s*\S+$", re.IGNORECASE)


def is_stub_description(text: object) -> bool:
    """Return True if *text* is empty or is a known bare auto-generated stub."""
    if not isinstance(text, str) or not text.strip():
        return True
    stripped = text.strip()
    if _STUB_RE.match(stripped):
        return True
    # Very short single-line non-markdown lines are stubs too
    if len(stripped) < 40 and "\n" not in stripped and not stripped.startswith("#"):
        return True
    return False


def build_service_summary_plain(
    *,
    service_name: str,
    language: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Short plain-text blurb for inventory cards when no LLM summary exists in the database.
    Written as natural sentences (not a rigid template), until a full analysis run stores LLM text.
    """
    meta = metadata or {}
    classification = str(meta.get("classification") or "").replace("_", " ").strip() or "general"
    ep = int(meta.get("entry_point_count") or 0)
    lang = (language or "unknown").strip() or "unknown"
    sym = meta.get("symbol_stats") if isinstance(meta.get("symbol_stats"), dict) else {}
    classes = int(sym.get("class_count") or 0) if sym else 0
    funcs = int(sym.get("function_count") or 0) if sym else 0

    parts: list[str] = []
    parts.append(
        f'"{service_name}" is part of this {lang} codebase and roughly plays a {classification} role '
        f"in the layout we detected."
    )
    if ep > 0:
        parts.append(f"It advertises {ep} entry point(s), so it is likely where execution or tooling hooks in.")
    if classes or funcs:
        parts.append(
            f"Roughly {classes} public classes and {funcs} public functions or methods showed up in static extraction—"
            f"use the detail view for a deeper pass once documentation is generated."
        )
    else:
        parts.append(
            "We did not surface many public symbols yet; it may be a thin package, re-export, or needs a fresh analysis run."
        )
    parts.append("Re-run analysis with the API configured to replace this with a full AI summary.")
    return " ".join(parts)


def build_service_description(
    *,
    service_name: str,
    language: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    path: Optional[str] = None,
) -> str:
    """Markdown for UI cards/detail. No H1–H3 title — the inventory header already shows the service name."""
    meta = metadata or {}
    classification = str(meta.get("classification") or "").replace("_", " ").strip()
    module_name = str(meta.get("module_name") or "").strip()
    entry_points = meta.get("entry_points") or []
    entry_point_count = int(meta.get("entry_point_count") or len(entry_points) or 0)
    lang = (language or "unknown").strip() or "unknown"

    lines = [
        "#### Summary",
        "",
        f"- **Language:** {lang}",
    ]
    if classification:
        lines.append(f"- **Module role:** {classification}")
    if module_name and module_name != service_name:
        lines.append(f"- **Import path / name:** `{module_name}`")
    if entry_point_count > 0:
        lines.append(f"- **Entry points:** {entry_point_count}")
    if path:
        lines.append(f"- **Source file:** `{path}`")

    lines.extend(
        [
            "",
            "_Richer prose appears when documentation generation succeeds (valid `OPENAI_MODEL` and API key)._",
            "",
            "Re-run **Analyze** after fixing `.env` if summaries stay minimal.",
        ]
    )
    return "\n".join(lines).strip()
