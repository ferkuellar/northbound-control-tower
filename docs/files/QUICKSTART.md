# Quickstart — Northbound Control Tower

> Run the full platform locally in under 30 minutes.

---

## Prerequisites

| Tool | Minimum version | Check |
|---|---|---|
| Docker | 24.0 | `docker --version` |
| Docker Compose | 2.20 | `docker compose version` |
| Git | 2.40 | `git --version` |
| Make | any | `make --version` |

A cloud account is not required to start the platform. You can run the dashboard and explore the UI before connecting any cloud provider.

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/ferkuellar/northbound-control-tower.git
cd northbound-control-tower
```

---

## Step 2 — Configure environment

```bash
make setup
```

This copies `.env.example` to `.env`. Open `.env` and set the required values:

```bash
# Required — change before running
JWT_SECRET_KEY=your-secret-key-minimum-32-characters

# Optional — needed only to use AI report generation
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...

# Optional — Grafana admin credentials (defaults: admin/admin)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

Everything else in `.env` can be left at the default values for local development.

---

## Step 3 — Start the platform

```bash
make up
```

This builds and starts all services. On first run, Docker pulls base images and installs dependencies — expect 3–5 minutes. Subsequent starts take under 30 seconds.

**What starts:**

| Container | Port | Purpose |
|---|---|---|
| `nct-backend` | 8000 | FastAPI REST API |
| `nct-worker` | — | Celery task worker |
| `nct-frontend` | 3000 | Next.js dashboard |
| `nct-postgres` | 5433 | PostgreSQL 16 |
| `nct-redis` | 6379 | Redis 7 (broker + cache) |
| `nct-prometheus` | 9090 | Metrics scraper |
| `nct-otel-collector` | 4317, 4318 | OpenTelemetry collector |
| `nct-grafana` | 3001 | Grafana dashboards |

**Verify all services are healthy:**

```bash
make ps
```

All containers should show `healthy` or `running`. The backend takes ~20 seconds to pass its health check on first start.

---

## Step 4 — Verify connectivity

```bash
# Backend health
curl http://localhost:8000/health/live
# → {"status": "ok"}

# API docs
open http://localhost:8000/docs

# Frontend dashboard
open http://localhost:3000

# Prometheus
open http://localhost:9090

# Grafana (admin/admin)
open http://localhost:3001
```

---

## Step 5 — Create your first tenant and user

The platform uses multi-tenant architecture. You need a tenant before creating users.

```bash
# Create tenant
curl -s -X POST http://localhost:8000/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Organization",
    "slug": "my-org"
  }' | python3 -m json.tool
```

Note the `id` from the response — this is your `TENANT_ID`.

```bash
# Create admin user
curl -s -X POST http://localhost:8000/api/v1/tenants/{TENANT_ID}/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@my-org.com",
    "password": "YourSecurePassword123!",
    "full_name": "Admin User",
    "role": "ADMIN"
  }' | python3 -m json.tool
```

---

## Step 6 — Sign in

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@my-org.com",
    "password": "YourSecurePassword123!"
  }' | python3 -m json.tool
```

Save the `access_token` from the response. Use it as `Bearer <token>` in all subsequent requests.

You can also sign in through the dashboard at [http://localhost:3000](http://localhost:3000).

---

## Step 7 — Connect a cloud account

### Option A: AWS with Access Keys

```bash
curl -s -X POST http://localhost:8000/api/v1/cloud-accounts \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "name": "AWS Production",
    "auth_type": "access_keys",
    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "default_region": "us-east-1"
  }' | python3 -m json.tool
```

**Minimum IAM permissions required:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:ListAllMyBuckets", "s3:GetBucketLocation", "s3:GetBucketTagging",
        "rds:Describe*",
        "iam:ListUsers", "iam:ListRoles", "iam:ListPolicies",
        "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    }
  ]
}
```

### Option B: AWS with IAM Role

```bash
curl -s -X POST http://localhost:8000/api/v1/cloud-accounts \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "name": "AWS Production",
    "auth_type": "role_arn",
    "role_arn": "arn:aws:iam::123456789012:role/NorthboundReadOnly",
    "external_id": "optional-external-id",
    "default_region": "us-east-1"
  }' | python3 -m json.tool
```

### Option C: OCI with API Key

```bash
curl -s -X POST http://localhost:8000/api/v1/cloud-accounts \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "oci",
    "name": "OCI Production",
    "auth_type": "oci_api_key",
    "tenancy_ocid": "ocid1.tenancy.oc1..aaaa...",
    "user_ocid": "ocid1.user.oc1..aaaa...",
    "fingerprint": "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
    "default_region": "us-ashburn-1"
  }' | python3 -m json.tool
```

Note the `id` from the response — this is your `ACCOUNT_ID`.

---

## Step 8 — Run your first inventory scan

```bash
curl -s -X POST http://localhost:8000/api/v1/inventory/accounts/{ACCOUNT_ID}/scan \
  -H "Authorization: Bearer <your-token>" \
  | python3 -m json.tool
```

The response includes a `task_id`. Track progress:

```bash
curl -s http://localhost:8000/api/v1/inventory/tasks/{TASK_ID} \
  -H "Authorization: Bearer <your-token>" \
  | python3 -m json.tool
```

Status moves from `pending` → `running` → `completed`. A typical AWS account with 50–200 resources takes 30–90 seconds.

---

## Step 9 — View findings

```bash
# All findings for your tenant
curl -s http://localhost:8000/api/v1/findings \
  -H "Authorization: Bearer <your-token>" \
  | python3 -m json.tool

# Summary by type and severity
curl -s http://localhost:8000/api/v1/findings/summary \
  -H "Authorization: Bearer <your-token>" \
  | python3 -m json.tool
```

Or open the Findings tab in the dashboard at [http://localhost:3000](http://localhost:3000).

---

## Step 10 — View scores

```bash
# Latest scores across all dimensions
curl -s http://localhost:8000/api/v1/scores/latest \
  -H "Authorization: Bearer <your-token>" \
  | python3 -m json.tool
```

---

## Step 11 — Generate an AI report (optional)

Requires `AI_PROVIDER` and the corresponding API key set in `.env`.

```bash
# Set AI provider (edit .env or pass directly)
# AI_PROVIDER=claude
# ANTHROPIC_API_KEY=sk-ant-...

# Restart backend to pick up new env vars
docker compose restart backend

# Trigger executive summary
curl -s -X POST http://localhost:8000/api/v1/ai/analyze \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "executive_summary",
    "cloud_account_id": "{ACCOUNT_ID}"
  }' | python3 -m json.tool
```

The response includes an `id`. Retrieve the completed analysis:

```bash
curl -s http://localhost:8000/api/v1/ai/analyses/{ANALYSIS_ID} \
  -H "Authorization: Bearer <your-token>" \
  | python3 -m json.tool
```

---

## Step 12 — Verify platform observability

```bash
# Prometheus metrics from the backend
curl -s http://localhost:8000/metrics | grep northbound

# Prometheus targets (all should be UP)
open http://localhost:9090/targets

# Grafana dashboard
open http://localhost:3001/d/northbound-overview
```

---

## Common commands

```bash
make up             # Build and start all services
make down           # Stop all services
make restart        # Full stop + rebuild + start
make logs           # Stream logs from all services
make ps             # Show service status and health
make backend-test   # Run pytest suite inside the backend container
make backend-lint   # Run ruff check
make frontend-lint  # Run ESLint
make clean          # Stop services and remove all volumes (destructive)
```

---

## Troubleshooting

**The backend container exits immediately on start**

Check logs:
```bash
docker compose logs backend
```
Most likely cause: `DATABASE_URL` is wrong or PostgreSQL is not yet healthy. Run `make ps` to check the `nct-postgres` health status.

---

**`make up` fails with "port already in use"**

A port is occupied by another service on your machine. In `.env`, change the conflicting port:
```bash
BACKEND_PORT=8001      # default 8000
FRONTEND_PORT=3002     # default 3000
POSTGRES_PORT=5434     # default 5433
GRAFANA_PORT=3002      # default 3001
```

---

**Inventory scan returns `access_denied` partial errors**

The IAM credentials lack permissions for some services. Review the minimum IAM policy in Step 7 and add the missing actions. Partial errors do not fail the scan — resources from accessible services are still collected.

---

**AI report generation fails with `AIProviderConfigurationError`**

Verify the API key is set correctly in `.env` and that `AI_PROVIDER` matches the key you provided (`claude`, `openai`, or `deepseek`). Restart the backend after editing `.env`:
```bash
docker compose restart backend
```

---

**Frontend shows blank page or login loop**

Clear browser local storage and reload:
```javascript
// In browser console
localStorage.clear();
location.reload();
```

---

**Grafana shows "No data" on all panels**

Prometheus must scrape at least one cycle before data appears. Wait 60 seconds after `make up` and reload the Grafana dashboard. Check `http://localhost:9090/targets` — the `nct-backend` target should show `UP`.

---

## Next steps

- Review the full API at [http://localhost:8000/docs](http://localhost:8000/docs)
- Read [ARCHITECTURE.md](./ARCHITECTURE.md) to understand component design
- Read [CONTRIBUTING.md](./CONTRIBUTING.md) to add a new cloud collector or finding type
- Read [API_REFERENCE.md](./API_REFERENCE.md) for the complete endpoint contract
