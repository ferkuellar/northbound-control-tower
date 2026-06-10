"""Tests for the async AI analysis flow.

Pattern: POST /analyze → 202 (pending job) → Celery worker runs resume_pending →
GET /analyses/{id} returns current status (pending | running | completed | failed).
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ai.enums import AIAnalysisStatus, AIAnalysisType, AIProvider
from ai.errors import AIProviderConfigurationError
from ai.schemas import AIAnalysisRequest
from api.main import app
from auth.dependencies import get_current_user
from core.database import SessionLocal, get_db
from models.ai_analysis import AIAnalysis
from models.tenant import Tenant
from models.user import User, UserRole
from security.rate_limit import RateLimitDecision


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _bypass_rate_limit():
    """Skip the Redis-backed rate limiter for all tests in this module.

    The rate limit is an operational concern (tested elsewhere). Tests here
    focus on the async analysis flow and would exhaust the shared Redis quota
    when run alongside the full test suite.
    """
    decision = RateLimitDecision(allowed=True, retry_after=0)
    with patch("middleware.rate_limit.rate_limiter.check", return_value=decision):
        yield


# ── helpers ───────────────────────────────────────────────────────────────────

def _db_override():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_user(role: UserRole = UserRole.ANALYST) -> User:
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Async Tenant {suffix}", slug=f"async-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"async-{role.value.lower()}-{suffix}@northbound.local",
        full_name="Async User",
        hashed_password="not-used",
        role=role.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.expunge(user)
    db.close()
    return user


def _client_for(user: User) -> TestClient:
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


class _FakeProvider:
    provider_name = "deepseek"
    model_name = "fake-model"

    def generate_analysis(self, prompt: str, max_tokens: int, temperature: float) -> str:
        return (
            '{"executive_summary": {"summary": "no data available — limitation noted."},'
            '"limitations": ["incomplete context — data unavailable"]}'
        )


# ── POST /analyze → 202 ──────────────────────────────────────────────────────

def test_post_analyze_returns_202() -> None:
    user = _seed_user()
    client = _client_for(user)
    try:
        with patch("api.routes.ai.run_ai_analysis") as mock_task:
            mock_task.delay = MagicMock()
            response = client.post(
                "/api/v1/ai/analyze",
                json={"analysis_type": "executive_summary", "provider": "deepseek"},
            )
        assert response.status_code == 202
    finally:
        _clear_overrides()


def test_post_analyze_response_contains_analysis_id() -> None:
    user = _seed_user()
    client = _client_for(user)
    try:
        with patch("api.routes.ai.run_ai_analysis") as mock_task:
            mock_task.delay = MagicMock()
            response = client.post(
                "/api/v1/ai/analyze",
                json={"analysis_type": "executive_summary", "provider": "deepseek"},
            )
        body = response.json()
        assert "analysis_id" in body
        uuid.UUID(body["analysis_id"])  # must be a valid UUID
    finally:
        _clear_overrides()


def test_post_analyze_response_status_is_pending() -> None:
    user = _seed_user()
    client = _client_for(user)
    try:
        with patch("api.routes.ai.run_ai_analysis") as mock_task:
            mock_task.delay = MagicMock()
            response = client.post(
                "/api/v1/ai/analyze",
                json={"analysis_type": "executive_summary", "provider": "deepseek"},
            )
        assert response.json()["status"] == "pending"
    finally:
        _clear_overrides()


def test_post_analyze_enqueues_celery_task_with_string_ids() -> None:
    user = _seed_user()
    client = _client_for(user)
    try:
        with patch("api.routes.ai.run_ai_analysis") as mock_task:
            mock_task.delay = MagicMock()
            client.post(
                "/api/v1/ai/analyze",
                json={"analysis_type": "executive_summary", "provider": "deepseek"},
            )
        mock_task.delay.assert_called_once()
        # Both args must be plain strings (no ORM objects passed to Celery)
        call_args = mock_task.delay.call_args[0]
        assert isinstance(call_args[0], str)  # analysis_id
        assert isinstance(call_args[1], str)  # user_id
        assert call_args[1] == str(user.id)
        uuid.UUID(call_args[0])  # analysis_id must be a valid UUID string
    finally:
        _clear_overrides()


def test_post_analyze_does_not_call_ai_provider() -> None:
    user = _seed_user()
    client = _client_for(user)
    try:
        with patch("api.routes.ai.run_ai_analysis") as mock_task:
            mock_task.delay = MagicMock()
            with patch("ai.service.get_ai_provider") as mock_provider:
                client.post(
                    "/api/v1/ai/analyze",
                    json={"analysis_type": "executive_summary", "provider": "deepseek"},
                )
        mock_provider.assert_not_called()
    finally:
        _clear_overrides()


# ── create_pending ───────────────────────────────────────────────────────────

def test_create_pending_creates_analysis_with_pending_status() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    try:
        request = AIAnalysisRequest(
            analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY,
            provider=AIProvider.DEEPSEEK,
        )
        analysis = AIAnalysisService(db).create_pending(current_user=user, request=request)
        assert analysis.status == AIAnalysisStatus.PENDING.value
        assert analysis.id is not None
        assert analysis.tenant_id == user.tenant_id
        assert analysis.created_by_user_id == user.id
    finally:
        db.close()


def test_create_pending_does_not_call_ai_provider() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    with patch("ai.service.get_ai_provider") as mock_provider:
        try:
            request = AIAnalysisRequest(
                analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY,
                provider=AIProvider.DEEPSEEK,
            )
            AIAnalysisService(db).create_pending(current_user=user, request=request)
        finally:
            db.close()
    mock_provider.assert_not_called()


# ── resume_pending ───────────────────────────────────────────────────────────

def test_resume_pending_marks_running_before_provider_call() -> None:
    from ai.service import AIAnalysisService
    from sqlalchemy import select as _select

    captured: list[str] = []

    class _CapturingProvider:
        provider_name = "deepseek"
        model_name = "fake-model"

        def generate_analysis(self, prompt: str, max_tokens: int, temperature: float) -> str:
            snap_db = SessionLocal()
            try:
                row = snap_db.scalar(_select(AIAnalysis).where(AIAnalysis.tenant_id == _user.tenant_id))
                if row:
                    captured.append(row.status)
            finally:
                snap_db.close()
            return '{"executive_summary": {"summary": "no data available"}}'

    _user = _seed_user()
    db = SessionLocal()
    try:
        request = AIAnalysisRequest(analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY, provider=AIProvider.DEEPSEEK)
        analysis = AIAnalysisService(db).create_pending(current_user=_user, request=request)
        with patch("ai.service.get_ai_provider", return_value=_CapturingProvider()):
            AIAnalysisService(db).resume_pending(analysis_id=analysis.id, current_user=_user)
    finally:
        db.close()

    assert AIAnalysisStatus.RUNNING.value in captured


def test_resume_pending_marks_completed_on_success() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    try:
        request = AIAnalysisRequest(analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY, provider=AIProvider.DEEPSEEK)
        analysis = AIAnalysisService(db).create_pending(current_user=user, request=request)
        analysis_id = analysis.id

        with patch("ai.service.get_ai_provider", return_value=_FakeProvider()):
            AIAnalysisService(db).resume_pending(analysis_id=analysis_id, current_user=user)

        db.expire(analysis)
        db.refresh(analysis)
        assert analysis.status == AIAnalysisStatus.COMPLETED.value
        assert analysis.output != {}
        assert analysis.completed_at is not None
    finally:
        db.close()


def test_resume_pending_marks_failed_on_known_provider_error() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    try:
        request = AIAnalysisRequest(analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY, provider=AIProvider.DEEPSEEK)
        analysis = AIAnalysisService(db).create_pending(current_user=user, request=request)
        analysis_id = analysis.id

        class _FailingProvider:
            provider_name = "deepseek"
            model_name = "fake-model"

            def generate_analysis(self, *a, **kw):
                raise AIProviderConfigurationError("provider key is not configured")

        with patch("ai.service.get_ai_provider", return_value=_FailingProvider()):
            AIAnalysisService(db).resume_pending(analysis_id=analysis_id, current_user=user)

        db.expire(analysis)
        db.refresh(analysis)
        assert analysis.status == AIAnalysisStatus.FAILED.value
        assert analysis.error_message is not None
    finally:
        db.close()


def test_resume_pending_marks_failed_on_unexpected_error_with_sanitized_message() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    try:
        request = AIAnalysisRequest(analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY, provider=AIProvider.DEEPSEEK)
        analysis = AIAnalysisService(db).create_pending(current_user=user, request=request)
        analysis_id = analysis.id

        class _CrashingProvider:
            provider_name = "deepseek"
            model_name = "fake-model"

            def generate_analysis(self, *a, **kw):
                raise RuntimeError("unexpected crash with sk-secret-key-12345")

        with patch("ai.service.get_ai_provider", return_value=_CrashingProvider()):
            AIAnalysisService(db).resume_pending(analysis_id=analysis_id, current_user=user)

        db.expire(analysis)
        db.refresh(analysis)
        assert analysis.status == AIAnalysisStatus.FAILED.value
        # Raw exception text must NOT be stored — sanitized generic message is used
        assert "sk-secret-key" not in (analysis.error_message or "")
        assert analysis.error_message == "AI provider request failed"
    finally:
        db.close()


def test_resume_pending_raises_for_unknown_analysis_id() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    try:
        with pytest.raises(ValueError, match="not found"):
            AIAnalysisService(db).resume_pending(
                analysis_id=uuid.uuid4(),
                current_user=user,
            )
    finally:
        db.close()


# ── Celery task ───────────────────────────────────────────────────────────────

def test_run_ai_analysis_task_calls_resume_pending_with_correct_ids() -> None:
    from workers.tasks import run_ai_analysis

    analysis_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.UUID(user_id)

    with patch("core.database.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.get.return_value = mock_user

        with patch("ai.service.AIAnalysisService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service_cls.return_value = mock_service

            run_ai_analysis.apply(args=[analysis_id, user_id])

    mock_service.resume_pending.assert_called_once()
    call_kwargs = mock_service.resume_pending.call_args.kwargs
    assert str(call_kwargs["analysis_id"]) == analysis_id
    assert call_kwargs["current_user"] is mock_user


def test_run_ai_analysis_task_closes_db_after_success() -> None:
    from workers.tasks import run_ai_analysis

    analysis_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    with patch("core.database.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.get.return_value = MagicMock(spec=User, id=uuid.UUID(user_id))

        with patch("ai.service.AIAnalysisService"):
            run_ai_analysis.apply(args=[analysis_id, user_id])

    mock_db.close.assert_called_once()


def test_run_ai_analysis_task_closes_db_on_exception() -> None:
    # apply() runs synchronously (including retries) but stores the final
    # exception in the result object rather than re-raising it. We verify
    # that the task fails and that db.close() was called in the finally block.
    from workers.tasks import run_ai_analysis

    analysis_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    with patch("core.database.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.get.return_value = None  # user not found → ValueError → retry

        result = run_ai_analysis.apply(args=[analysis_id, user_id])

    assert result.failed()
    # db.close() must be called in the finally block on every attempt
    assert mock_db.close.call_count >= 1


# ── polling via GET /analyses/{id} ───────────────────────────────────────────

def test_polling_returns_pending_for_newly_created_analysis() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    try:
        request = AIAnalysisRequest(analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY, provider=AIProvider.DEEPSEEK)
        analysis = AIAnalysisService(db).create_pending(current_user=user, request=request)
        analysis_id = str(analysis.id)
    finally:
        db.close()

    client = _client_for(user)
    try:
        response = client.get(f"/api/v1/ai/analyses/{analysis_id}")
        assert response.status_code == 200
        assert response.json()["status"] == AIAnalysisStatus.PENDING.value
    finally:
        _clear_overrides()


def test_polling_returns_completed_after_resume_pending() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    try:
        request = AIAnalysisRequest(analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY, provider=AIProvider.DEEPSEEK)
        analysis = AIAnalysisService(db).create_pending(current_user=user, request=request)
        analysis_id = analysis.id
        with patch("ai.service.get_ai_provider", return_value=_FakeProvider()):
            AIAnalysisService(db).resume_pending(analysis_id=analysis_id, current_user=user)
    finally:
        db.close()

    client = _client_for(user)
    try:
        response = client.get(f"/api/v1/ai/analyses/{analysis_id}")
        assert response.status_code == 200
        assert response.json()["status"] == AIAnalysisStatus.COMPLETED.value
    finally:
        _clear_overrides()


def test_polling_returns_failed_after_provider_error() -> None:
    from ai.service import AIAnalysisService

    user = _seed_user()
    db = SessionLocal()
    try:
        request = AIAnalysisRequest(analysis_type=AIAnalysisType.EXECUTIVE_SUMMARY, provider=AIProvider.DEEPSEEK)
        analysis = AIAnalysisService(db).create_pending(current_user=user, request=request)
        analysis_id = analysis.id

        class _FailingProvider:
            provider_name = "deepseek"
            model_name = "fake-model"

            def generate_analysis(self, *a, **kw):
                raise AIProviderConfigurationError("not configured")

        with patch("ai.service.get_ai_provider", return_value=_FailingProvider()):
            AIAnalysisService(db).resume_pending(analysis_id=analysis_id, current_user=user)
    finally:
        db.close()

    client = _client_for(user)
    try:
        response = client.get(f"/api/v1/ai/analyses/{analysis_id}")
        assert response.status_code == 200
        assert response.json()["status"] == AIAnalysisStatus.FAILED.value
    finally:
        _clear_overrides()


def test_polling_404_for_unknown_analysis_id() -> None:
    user = _seed_user()
    client = _client_for(user)
    try:
        response = client.get(f"/api/v1/ai/analyses/{uuid.uuid4()}")
        assert response.status_code == 404
    finally:
        _clear_overrides()
