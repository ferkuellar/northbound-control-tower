from __future__ import annotations

import uuid

from workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    name="ai.run_analysis",
)
def run_ai_analysis(self, analysis_id: str, user_id: str) -> None:
    from core.database import SessionLocal
    from ai.service import AIAnalysisService
    from models.user import User

    db = SessionLocal()
    try:
        user = db.get(User, uuid.UUID(user_id))
        if user is None:
            raise ValueError(f"User {user_id} not found for AI analysis task")
        AIAnalysisService(db).resume_pending(
            analysis_id=uuid.UUID(analysis_id),
            current_user=user,
        )
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()
