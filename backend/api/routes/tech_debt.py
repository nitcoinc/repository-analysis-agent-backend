import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from core.security import verify_api_key
from services.tech_debt_analyzer import TechDebtAnalyzer
from models.tech_debt import TechDebtItem, TechDebtReport, DebtRemediationPlan, DebtMetricsHistory
from core.database import SessionLocal
from sqlalchemy.orm import Session

router = APIRouter()


class TechDebtAnalysisRequest(BaseModel):
    repository_id: str


class RemediationPlanRequest(BaseModel):
    repository_id: str
    focus_areas: Optional[List[str]] = None


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/analyze")
async def analyze_tech_debt(
    request: TechDebtAnalysisRequest,
    api_key: bool = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Start tech debt analysis for a repository."""
    # TODO: Get repository path and code elements from database
    # For now, return a placeholder response
    return {
        "analysis_id": str(uuid.uuid4()),
        "repository_id": request.repository_id,
        "status": "queued",
        "message": "Tech debt analysis queued"
    }


@router.get("/reports/{repository_id}")
async def get_debt_report(
    repository_id: str,
    api_key: bool = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get tech debt report for a repository."""
    # Get latest report
    report = db.query(TechDebtReport).filter(
        TechDebtReport.repository_id == repository_id
    ).order_by(TechDebtReport.created_at.desc()).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tech debt report not found. Run analysis first."
        )
    
    # Get debt items
    items = db.query(TechDebtItem).filter(
        TechDebtItem.repository_id == repository_id
    ).all()
    
    return {
        "report_id": report.id,
        "repository_id": repository_id,
        "total_debt_score": report.total_debt_score,
        "debt_density": report.debt_density,
        "total_items": report.total_items,
        "category_scores": {
            "code_quality": report.code_quality_score,
            "architecture": report.architecture_score,
            "dependency": report.dependency_score,
            "documentation": report.documentation_score,
            "test_coverage": report.test_coverage_score,
        },
        "items_by_category": report.items_by_category,
        "items_by_severity": report.items_by_severity,
        "debt_items": [
            {
                "id": item.id,
                "category": item.category,
                "severity": item.severity,
                "priority": item.priority,
                "title": item.title,
                "description": item.description,
                "file_path": item.file_path,
                "line_start": item.line_start,
                "line_end": item.line_end,
                "impact_score": item.impact_score,
                "effort_estimate": item.effort_estimate,
                "status": item.status,
            }
            for item in items
        ],
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("/items")
async def list_debt_items(
    repository_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    priority: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    api_key: bool = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """List debt items with filters."""
    query = db.query(TechDebtItem)
    
    if repository_id:
        query = query.filter(TechDebtItem.repository_id == repository_id)
    if category:
        query = query.filter(TechDebtItem.category == category)
    if severity:
        query = query.filter(TechDebtItem.severity == severity)
    if priority:
        query = query.filter(TechDebtItem.priority == priority)
    if status:
        query = query.filter(TechDebtItem.status == status)
    
    items = query.all()
    
    return {
        "items": [
            {
                "id": item.id,
                "repository_id": item.repository_id,
                "service_id": item.service_id,
                "category": item.category,
                "severity": item.severity,
                "priority": item.priority,
                "title": item.title,
                "description": item.description,
                "file_path": item.file_path,
                "line_start": item.line_start,
                "line_end": item.line_end,
                "impact_score": item.impact_score,
                "effort_estimate": item.effort_estimate,
                "status": item.status,
            }
            for item in items
        ],
        "total": len(items),
    }


@router.get("/metrics/{repository_id}")
async def get_debt_metrics(
    repository_id: str,
    api_key: bool = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get debt metrics for a repository."""
    # Get latest report
    report = db.query(TechDebtReport).filter(
        TechDebtReport.repository_id == repository_id
    ).order_by(TechDebtReport.created_at.desc()).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tech debt report not found"
        )
    
    return {
        "repository_id": repository_id,
        "total_debt_score": report.total_debt_score,
        "debt_density": report.debt_density,
        "total_items": report.total_items,
        "category_scores": {
            "code_quality": report.code_quality_score,
            "architecture": report.architecture_score,
            "dependency": report.dependency_score,
            "documentation": report.documentation_score,
            "test_coverage": report.test_coverage_score,
        },
        "items_by_category": report.items_by_category,
        "items_by_severity": report.items_by_severity,
    }


@router.post("/remediation-plan")
async def generate_remediation_plan(
    request: RemediationPlanRequest,
    api_key: bool = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Generate remediation plan for a repository."""
    # Get debt items
    items = db.query(TechDebtItem).filter(
        TechDebtItem.repository_id == request.repository_id,
        TechDebtItem.status == "open"
    ).all()
    
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open debt items found"
        )
    
    # Generate plan (simplified - would use agent in production)
    debt_analyzer = TechDebtAnalyzer()
    debt_items = [
        {
            "id": item.id,
            "category": item.category,
            "severity": item.severity,
            "title": item.title,
            "description": item.description,
            "impact_score": item.impact_score,
            "effort_estimate": item.effort_estimate,
        }
        for item in items
    ]
    
    prioritized = debt_analyzer.prioritize_debt(debt_items)
    
    # Create plan
    plan_id = str(uuid.uuid4())
    plan = DebtRemediationPlan(
        id=plan_id,
        repository_id=request.repository_id,
        plan_name=f"Remediation Plan - {datetime.utcnow().strftime('%Y-%m-%d')}",
        priority_breakdown={
            "quick_wins": len([i for i in prioritized if i.get("priority") == 1]),
            "strategic": len([i for i in prioritized if i.get("priority") == 2]),
            "fill_ins": len([i for i in prioritized if i.get("priority") == 3]),
        },
        recommendations=[item["title"] for item in prioritized[:10]],
    )
    
    db.add(plan)
    db.commit()
    
    return {
        "plan_id": plan_id,
        "repository_id": request.repository_id,
        "plan_name": plan.plan_name,
        "priority_breakdown": plan.priority_breakdown,
        "recommendations": plan.recommendations,
    }


@router.get("/trends/{repository_id}")
async def get_debt_trends(
    repository_id: str,
    days: int = Query(30, ge=1, le=365),
    api_key: bool = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get debt trends over time."""
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    history = db.query(DebtMetricsHistory).filter(
        DebtMetricsHistory.repository_id == repository_id,
        DebtMetricsHistory.recorded_at >= cutoff_date
    ).order_by(DebtMetricsHistory.recorded_at).all()
    
    return {
        "repository_id": repository_id,
        "period_days": days,
        "data_points": [
            {
                "date": h.recorded_at.isoformat() if h.recorded_at else None,
                "debt_score": h.total_debt_score,
                "debt_density": h.debt_density,
                "total_items": h.total_items,
                "items_by_category": h.items_by_category,
            }
            for h in history
        ],
    }
