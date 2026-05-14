# Contributing — Northbound Control Tower

> Branch conventions, commit format, and step-by-step guides for extending the platform.

---

## Table of Contents

1. [Development Setup](#1-development-setup)
2. [Branch Conventions](#2-branch-conventions)
3. [Commit Convention](#3-commit-convention)
4. [Code Style](#4-code-style)
5. [How to Add a Cloud Collector](#5-how-to-add-a-cloud-collector)
6. [How to Add a Finding Type](#6-how-to-add-a-finding-type)
7. [How to Add an AI Provider](#7-how-to-add-an-ai-provider)
8. [Testing](#8-testing)
9. [Pull Request Process](#9-pull-request-process)
10. [Documentation Updates](#10-documentation-updates)

---

## 1. Development Setup

Follow [QUICKSTART.md](./QUICKSTART.md) to get the full stack running locally. For backend development, you can run the API outside Docker for faster iteration:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start dependencies only (postgres, redis, otel)
docker compose up postgres redis otel-collector -d

# Run the API locally
uvicorn api.main:app --reload --port 8000

# Run tests locally
pytest
```

For frontend development:

```bash
cd frontend
npm install
npm run dev
```

---

## 2. Branch Conventions

All branches branch from `main`. Use the following prefix pattern:

| Prefix | Use for |
|---|---|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `security/` | Security-related changes |
| `refactor/` | Code restructuring without behavior change |
| `docs/` | Documentation only |
| `test/` | Test additions or fixes |
| `chore/` | Build, CI, dependency updates |

**Examples:**

```
feature/azure-collector
fix/findings-engine-null-metadata
security/redis-rate-limiter
docs/architecture-phase1
test/aws-collector-mocks
```

Branch names use lowercase and hyphens only — no underscores, no uppercase.

---

## 3. Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/). Format:

```
<type>(<scope>): <short description>

[optional body]

[optional footer: Fixes #issue]
```

**Types:**

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `security` | Security fix or hardening |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `chore` | Build process, dependency updates, tooling |
| `perf` | Performance improvement |

**Scope** is the module or area affected: `collectors`, `findings`, `scoring`, `ai`, `frontend`, `auth`, `docker`, `migrations`, etc.

**Examples:**

```
feat(collectors): add Azure ARM inventory collector

fix(findings): handle null metadata_json in PublicExposureRule

security(rate-limit): replace InMemoryRateLimiter with Redis sliding window

test(aws-collector): add mock suite for EC2 and EBS collection

docs(architecture): add Phase 1 outlook section
```

---

## 4. Code Style

### Backend (Python)

- **Formatter:** Black (line length 100)
- **Linter:** Ruff
- **Type checker:** mypy (strict mode for new modules)

```bash
# From repo root
make backend-lint         # ruff check
docker compose run --rm backend black --check .
```

Style rules enforced:
- All functions must have type annotations
- `from __future__ import annotations` at the top of every file
- No bare `except:` clauses — always catch specific exceptions
- No `print()` statements — use `logging.getLogger(__name__)`
- Constants in `ALL_CAPS`, classes in `PascalCase`, functions in `snake_case`

### Frontend (TypeScript)

- **Linter:** ESLint with Next.js config
- **Formatter:** Prettier (implicit via ESLint)

```bash
make frontend-lint        # eslint
```

Style rules:
- No `any` types — use explicit types or `unknown`
- Prefer `const` over `let`; avoid `var`
- React components use function declaration (not arrow functions)
- API calls go through `lib/api.ts` — no inline `fetch()` in components

---

## 5. How to Add a Cloud Collector

This is the most common extension point. Adding Azure, GCP, or any other provider follows the same pattern.

### Step 1 — Create the module directory

```
backend/collectors/azure/
├── __init__.py
├── collector.py     # Main collector class
├── normalizers.py   # Per-resource normalization functions
├── session.py       # Credential/session factory
└── errors.py        # Provider-specific error handling
```

### Step 2 — Implement the session factory

Create `collectors/azure/session.py`:

```python
from dataclasses import dataclass
from models.cloud_account import CloudAccount


@dataclass
class AzureSessionFactory:
    cloud_account: CloudAccount

    def create_credential(self):
        """Return an Azure credential object from the cloud account credentials."""
        from azure.identity import ClientSecretCredential
        return ClientSecretCredential(
            tenant_id=self.cloud_account.azure_tenant_id,
            client_id=self.cloud_account.azure_client_id,
            client_secret=self.cloud_account.azure_client_secret,
        )
```

### Step 3 — Implement the collector

Create `collectors/azure/collector.py` and implement the `collect_all()` method:

```python
from __future__ import annotations

from typing import Any
from models.cloud_account import CloudAccount
from collectors.azure.session import AzureSessionFactory


class AzureInventoryCollector:
    def __init__(self, cloud_account: CloudAccount, *, timeout_seconds: int) -> None:
        self.cloud_account = cloud_account
        self.session_factory = AzureSessionFactory(cloud_account)
        self.credential = self.session_factory.create_credential()
        self.partial_errors: list[dict[str, str]] = []

    def collect_all(self) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        collectors = [
            self.collect_virtual_machines,
            self.collect_managed_disks,
            self.collect_storage_accounts,
        ]
        resources: list[dict[str, Any]] = []
        for collect in collectors:
            resources.extend(collect())
        return resources, self.partial_errors

    def collect_virtual_machines(self) -> list[dict[str, Any]]:
        from collectors.azure.normalizers import normalize_vm
        try:
            from azure.mgmt.compute import ComputeManagementClient
            client = ComputeManagementClient(self.credential, self.cloud_account.azure_subscription_id)
            vms = client.virtual_machines.list_all()
            return [normalize_vm(vm) for vm in vms]
        except Exception as exc:
            self.partial_errors.append({"service": "virtual_machines", "type": "azure_error", "message": str(exc)})
            return []
```

### Step 4 — Implement normalizers

Create `collectors/azure/normalizers.py`. Each function maps a raw provider object to a dict that matches the `Resource` model's unified schema:

```python
from __future__ import annotations

from typing import Any


def normalize_vm(vm: Any) -> dict[str, Any]:
    """Normalize an Azure Virtual Machine to the unified resource schema."""
    tags = dict(vm.tags or {})
    return {
        "provider": "azure",
        "resource_type": "compute",
        "raw_type": "Microsoft.Compute/virtualMachines",
        "resource_id": vm.id,
        "name": vm.name,
        "region": vm.location,
        "availability_zone": None,
        "lifecycle_status": vm.instance_view.statuses[-1].display_status if vm.instance_view else "unknown",
        "exposure_level": "private",  # refine based on NIC/public IP checks
        "tags": tags,
        "environment": tags.get("environment", tags.get("Environment", "unknown")),
        "owner": tags.get("owner", tags.get("Owner")),
        "cost_center": tags.get("cost_center", tags.get("CostCenter")),
        "application": tags.get("application", tags.get("Application")),
        "metadata_json": {
            "vm_size": vm.hardware_profile.vm_size,
            "os_type": vm.storage_profile.os_disk.os_type,
        },
        "provider_details": {},
    }
```

### Step 5 — Register the collector

In `services/inventory.py`, add the Azure collector to the provider dispatch:

```python
# services/inventory.py

from collectors.azure.collector import AzureInventoryCollector

def _get_collector(cloud_account: CloudAccount, settings: Settings):
    if cloud_account.provider == "aws":
        return AWSInventoryCollector(cloud_account, timeout_seconds=settings.aws_scan_timeout_seconds)
    if cloud_account.provider == "oci":
        return OCIInventoryCollector(cloud_account, timeout_seconds=settings.oci_scan_timeout_seconds)
    if cloud_account.provider == "azure":
        return AzureInventoryCollector(cloud_account, timeout_seconds=settings.azure_scan_timeout_seconds)
    raise ValueError(f"Unknown provider: {cloud_account.provider}")
```

### Step 6 — Add the database migration

Add any new credential columns to `CloudAccount` and generate a migration:

```bash
cd backend
alembic revision --autogenerate -m "add_azure_cloud_account_fields"
# Review the generated migration, then apply:
alembic upgrade head
```

### Step 7 — Add tests

Create `backend/tests/test_azure_collector.py` following the pattern in `test_aws_collector.py`. Mock the Azure SDK clients and verify that:
- Resources are returned with the correct `resource_type` and `provider` fields
- Access denied errors are recorded as `partial_errors` without failing the collection
- Tags are mapped to governance fields (`environment`, `owner`, `cost_center`)

### Step 8 — Update documentation

- Add Azure to the "Supported Clouds" table in `README.md`
- Add a normalizer description to `ARCHITECTURE.md` section 3.2
- Add credential fields to `API_REFERENCE.md` section on `POST /cloud-accounts`

---

## 6. How to Add a Finding Type

Finding types are implemented as classes inheriting from `BaseFindingRule` in `backend/findings/rules.py`. The registry auto-discovers all subclasses.

### Step 1 — Define the finding type enum value

In `findings/enums.py`, add the new type:

```python
class FindingType(StrEnum):
    MISSING_TAGS = "missing_tags"
    PUBLIC_EXPOSURE = "public_exposure"
    IDLE_COMPUTE = "idle_compute"
    UNATTACHED_VOLUME = "unattached_volume"
    OBSERVABILITY_GAP = "observability_gap"
    ENCRYPTION_GAP = "encryption_gap"        # new
```

If the finding belongs to a new category, add it to `FindingCategory` as well.

### Step 2 — Implement the rule

Add the new rule class to `findings/rules.py`:

```python
class EncryptionGapRule(BaseFindingRule):
    rule_id = "phase6.encryption_gap.v1"
    finding_type = FindingType.ENCRYPTION_GAP
    category = FindingCategory.SECURITY
    severity = FindingSeverity.HIGH

    def evaluate(self, resource: Resource) -> FindingCandidate | None:
        # Only applies to storage and database resources
        if resource.resource_type not in {"block_storage", "database", "object_storage"}:
            return None

        metadata = _metadata(resource)
        encrypted = metadata.get("encrypted")

        # Skip if we don't have encryption info
        if encrypted is None:
            return None

        if encrypted is True:
            return None

        severity_hint = (
            FindingSeverity.CRITICAL.value
            if resource.environment == "prod"
            else self.severity.value
        )

        return FindingCandidate(
            title="Resource is not encrypted at rest",
            description=(
                f"Resource {resource.name or resource.resource_id} "
                f"does not have encryption at rest enabled."
            ),
            evidence=_evidence_base(resource) | {
                "encrypted": encrypted,
                "severity_hint": severity_hint,
            },
            recommendation=(
                "Enable encryption at rest. For EBS volumes, use encrypted snapshots. "
                "For RDS, enable storage encryption at instance creation or restore to an encrypted instance."
            ),
        )
```

### Step 3 — Register the rule

The `FindingRuleRegistry` auto-discovers all `BaseFindingRule` subclasses at import time. Just ensure the module is imported somewhere in the application. If your rule is in `findings/rules.py`, it is already imported.

If you add rules in a separate file (e.g., `findings/rules_phase2.py`), import it in `findings/__init__.py`:

```python
# findings/__init__.py
from findings import rules, rules_phase2  # noqa: F401
```

### Step 4 — Ensure the normalizer sets the required metadata field

The rule evaluates `metadata_json.get("encrypted")`. Verify that the AWS and OCI normalizers set this field for the relevant resource types.

For AWS EBS volumes (`collectors/aws/normalizers.py`):
```python
"metadata_json": {
    "encrypted": volume.get("Encrypted", False),
    ...
}
```

### Step 5 — Add tests

Create a test in `backend/tests/test_findings_rules.py`:

```python
def test_encryption_gap_rule_detects_unencrypted_volume():
    resource = make_resource(
        resource_type="block_storage",
        metadata_json={"encrypted": False}
    )
    rule = EncryptionGapRule()
    result = rule.evaluate(resource)
    assert result is not None
    assert result.title == "Resource is not encrypted at rest"


def test_encryption_gap_rule_passes_encrypted_volume():
    resource = make_resource(
        resource_type="block_storage",
        metadata_json={"encrypted": True}
    )
    rule = EncryptionGapRule()
    result = rule.evaluate(resource)
    assert result is None


def test_encryption_gap_rule_skips_compute():
    resource = make_resource(resource_type="compute", metadata_json={})
    rule = EncryptionGapRule()
    result = rule.evaluate(resource)
    assert result is None
```

### Step 6 — Update documentation

- Add the new finding type to the findings table in `ARCHITECTURE.md` section 3.3
- Add it to the `finding_type` query parameter in `API_REFERENCE.md`

---

## 7. How to Add an AI Provider

AI providers implement `BaseAIProvider` in `backend/ai/providers/`. The factory in `ai/provider.py` selects the implementation based on `AI_PROVIDER`.

### Step 1 — Create the provider file

```python
# backend/ai/providers/gemini.py
from __future__ import annotations

from ai.providers.base import BaseAIProvider
from ai.schemas import AIProviderStatus
from ai.enums import AIProvider
from core.config import settings


class GeminiProvider(BaseAIProvider):
    provider_name = "gemini"

    @property
    def model_name(self) -> str:
        return settings.gemini_model  # add to config.py

    def generate_analysis(self, prompt: str, max_tokens: int, temperature: float) -> str:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        )
        return response.text

    def health_check(self) -> AIProviderStatus:
        configured = bool(settings.gemini_api_key)
        return AIProviderStatus(
            provider=AIProvider.GEMINI,
            configured=configured,
            enabled=configured,
            model_name=self.model_name,
            message="OK" if configured else "GEMINI_API_KEY not set",
        )
```

### Step 2 — Register in the factory

In `ai/provider.py`, add the new provider to the dispatch:

```python
from ai.providers.gemini import GeminiProvider

def get_ai_provider(provider: AIProvider) -> BaseAIProvider:
    if provider == AIProvider.CLAUDE:
        return ClaudeProvider()
    if provider == AIProvider.OPENAI:
        return OpenAIProvider()
    if provider == AIProvider.DEEPSEEK:
        return DeepSeekProvider()
    if provider == AIProvider.GEMINI:
        return GeminiProvider()
    raise AIProviderConfigurationError(f"Unknown AI provider: {provider}")
```

### Step 3 — Add to enum and config

In `ai/enums.py`:
```python
class AIProvider(StrEnum):
    CLAUDE = "claude"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"     # new
    NONE = "none"
```

In `core/config.py`:
```python
gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
gemini_model: str = Field(default="gemini-1.5-pro", alias="GEMINI_MODEL")
```

In `.env.example`:
```
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-pro
```

---

## 8. Testing

### Backend tests

```bash
# Run all tests
make backend-test

# Run a specific file
docker compose run --rm backend pytest tests/test_findings_rules.py -v

# Run with coverage
docker compose run --rm backend pytest --cov=. --cov-report=term-missing
```

Test files live in `backend/tests/`. Each test file corresponds to a module:

| Module | Test file |
|---|---|
| `findings/rules.py` | `tests/test_findings_rules.py` |
| `findings/engine.py` | `tests/test_findings_engine.py` |
| `ai/service.py` | `tests/test_ai_phase9.py` |
| `auth/security.py` | `tests/test_auth_security.py` |
| `collectors/aws/` | `tests/test_aws_normalizers.py` |
| `collectors/oci/` | `tests/test_oci_normalizers.py` |

**Fixtures:** Use `conftest.py` for shared fixtures (DB session, mock cloud account, sample resource factory).

**Mocking external services:** Use `unittest.mock.patch` or `pytest-mock` for boto3 and oci SDK calls. Never make real cloud API calls in tests.

### Frontend tests (Phase 1)

The frontend does not yet have a test framework configured. When adding tests, follow the setup in [PLAN_MEJORA.md](../PLAN_MEJORA_northbound_control_tower.md) — Fase C, tarea F08.

---

## 9. Pull Request Process

### Before opening a PR

- [ ] All existing tests pass: `make backend-test`
- [ ] Linting passes: `make backend-lint && make frontend-lint`
- [ ] New code has corresponding tests
- [ ] If adding a collector, normalizer tests cover tag mapping and error handling
- [ ] If adding a finding rule, tests cover the positive, negative, and edge cases
- [ ] Documentation updated if the change affects the API, architecture, or user-facing behavior

### PR title

Use the same Conventional Commit format as commit messages:

```
feat(collectors): add Azure ARM virtual machine collector
fix(findings): handle null tags in MissingTagsRule
```

### PR description template

```markdown
## What
Brief description of the change.

## Why
Problem this solves or motivation.

## How
Technical approach, key decisions made.

## Testing
How you verified this works.

## Checklist
- [ ] Tests pass
- [ ] Linting passes
- [ ] Documentation updated
- [ ] No credentials or secrets in the diff
```

### Review expectations

- PRs are reviewed within 2 business days
- One approval required to merge
- Feedback is addressed before merge — no force-pushing over resolved comments
- Squash merge is preferred for feature branches; merge commit for long-running branches

---

## 10. Documentation Updates

Update documentation in the same PR as the code change that necessitates it. Do not open separate "docs" PRs for changes caused by code.

| Change type | Docs to update |
|---|---|
| New cloud provider | README (Supported Clouds table), ARCHITECTURE.md (3.1, 3.2), API_REFERENCE.md (cloud accounts) |
| New finding type | ARCHITECTURE.md (3.3 rules table), API_REFERENCE.md (findings filter params) |
| New AI provider | ARCHITECTURE.md (3.6), API_REFERENCE.md (AI analysis provider enum) |
| New API endpoint | API_REFERENCE.md |
| Architecture change | ARCHITECTURE.md |
| Setup step change | QUICKSTART.md |
| New env variable | `.env.example` (with comment), QUICKSTART.md if user-facing |

Documentation files live in `docs/`. The README.md lives at the repository root.
