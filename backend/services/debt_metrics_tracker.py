import logging
from typing import Dict, Any
from datetime import datetime
from models.tech_debt import DebtMetricsHistory, TechDebtReport
from core.database import SessionLocal

logger = logging.getLogger(__name__)


class DebtMetricsTracker:
    """Tracks debt metrics over time for trend analysis."""
    
    def record_metrics(
        self,
        repository_id: str,
        report: TechDebtReport
    ):
        """Record current metrics to history."""
        db = SessionLocal()
        try:
            history = DebtMetricsHistory(
                id=f"{repository_id}_{datetime.utcnow().isoformat()}",
                repository_id=repository_id,
                total_debt_score=report.total_debt_score,
                debt_density=report.debt_density,
                total_items=report.total_items,
                items_by_category=report.items_by_category,
                remediation_velocity=0.0,  # Would calculate from previous records
            )
            db.add(history)
            db.commit()
            logger.info(f"Recorded debt metrics for repository: {repository_id}")
        except Exception as e:
            logger.error(f"Error recording debt metrics: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_trends(
        self,
        repository_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get debt trends over time."""
        from datetime import timedelta
        
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            history = db.query(DebtMetricsHistory).filter(
                DebtMetricsHistory.repository_id == repository_id,
                DebtMetricsHistory.recorded_at >= cutoff_date
            ).order_by(DebtMetricsHistory.recorded_at).all()
            
            return {
                "data_points": [
                    {
                        "date": h.recorded_at.isoformat() if h.recorded_at else None,
                        "debt_score": h.total_debt_score,
                        "debt_density": h.debt_density,
                        "total_items": h.total_items,
                    }
                    for h in history
                ],
                "trend": self._calculate_trend(history),
            }
        finally:
            db.close()
    
    def _calculate_trend(self, history: list) -> str:
        """Calculate overall trend (improving, stable, worsening)."""
        if len(history) < 2:
            return "insufficient_data"
        
        first_score = history[0].total_debt_score
        last_score = history[-1].total_debt_score
        
        change = last_score - first_score
        percent_change = (change / first_score * 100) if first_score > 0 else 0
        
        if percent_change < -5:
            return "improving"
        elif percent_change > 5:
            return "worsening"
        else:
            return "stable"
