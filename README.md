<div align="center">

<img src="docs/screenshots/login.png" alt="Northbound Control Tower — Executive cloud operations dashboard" width="100%">

<br/>
<br/>

# Northbound Control Tower

**Multicloud operational intelligence for teams that need visibility, not complexity.**

[![Phase](https://img.shields.io/badge/phase-0%20%E2%80%94%20Foundation-3b82f6?style=flat-square)](./docs/architecture.md)
[![Status](https://img.shields.io/badge/status-active%20development-22c55e?style=flat-square)]()
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20Next.js%20%7C%20PostgreSQL-64748b?style=flat-square)]()
[![Clouds](https://img.shields.io/badge/clouds-AWS%20%7C%20OCI-f97316?style=flat-square)]()
[![AI](https://img.shields.io/badge/AI-Claude%20%7C%20OpenAI%20%7C%20DeepSeek-8b5cf6?style=flat-square)]()
[![License](https://img.shields.io/badge/license-proprietary-64748b?style=flat-square)](./LICENSE)

</div>

---

## Overview

Northbound Control Tower is an **enterprise multicloud operational intelligence platform** that gives cloud teams and executives a unified view of their cloud estate — covering inventory, cost exposure, governance gaps, observability readiness, resilience posture, and AI-powered reporting across AWS and OCI.

Most organizations operating across multiple cloud providers suffer from fragmented visibility. Native consoles are siloed. Cost anomalies go undetected. Governance failures surface late. Executive reporting is manual and inconsistent. Control Tower closes those gaps in a single operational layer backed by deterministic scoring and AI-generated insights.

---

## Platform

### Executive Dashboard

Real-time operational scores across six dimensions — FinOps, Governance, Observability, Security, Resilience, and an overall composite — with per-client filtering, inventory summary, and risk breakdown. All scores are deterministic and derived from live cloud inventory data.

<img src="docs/screenshots/dashboard-executive.png" alt="Executive Dashboard — Clara Fintech AWS Production with operational scores, inventory summary and risk breakdown" width="100%">

> **Clara Fintech · AWS Production** — Overall score 73 · 7 open findings · 6 resources inventoried · AI-generated executive and technical reports available in one click.

---

### FinOps Cost Analysis

Deep cost exposure analysis per client and cloud account. Identifies rightsizing opportunities, unattached volumes, S3 lifecycle gaps, and EKS node group inefficiencies — with prioritized recommendations, estimated monthly savings, and a downloadable cost model CSV.

<img src="docs/screenshots/finops-analysis.png" alt="FinOps case study — $250k monthly spend with $40k monthly savings identified across EC2, EBS, RDS, S3 and EKS" width="100%">

> **$250,000/mo current spend · $40,000/mo in identified savings · $480,000/yr annualized** — Five prioritized actions with effort estimates and explicit assumptions per service.

---

### Multi-Tenant Client Management

Full multi-tenant architecture with per-client cloud account isolation. Register clients, assign cloud accounts, track inventory, findings, and scores across the entire portfolio from a single administration view.

<img src="docs/screenshots/clients-admin.png" alt="Client administration — 450 registered tenants with per-client scores, account counts, resource counts and findings" width="100%">

> **450 tenants registered** — Per-client score, account count, resource count, and finding count at a glance. One-click access to cost view per client.

---

## Key Capabilities

<table>
<tr>
<td width="50%" valign="top">

### ☁️ Cloud Inventory
Collects, normalizes, and stores resource data from AWS and OCI into a unified schema. EC2, EBS, RDS, S3, IAM, VPC, CloudWatch, and OCI equivalents — catalogued continuously via scheduled collectors.

</td>
<td width="50%" valign="top">

### 💰 FinOps Diagnostics
Identifies cost exposure: idle compute, unattached volumes, excessive snapshots, missing lifecycle policies, and untagged resources with budget-alignment gaps. Estimated savings per recommendation.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🔒 Governance Analysis
Evaluates resources against governance baselines: missing required tags, publicly exposed assets, deviation from naming conventions, and lack of encryption controls.

</td>
<td width="50%" valign="top">

### 👁️ Observability Readiness
Assesses whether cloud resources have logging, metrics, and alerting configured. Produces a readiness score per account that maps directly to operational risk.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🛡️ HA/DR Readiness
Flags single points of failure: single-AZ deployments, missing backup configurations, absent cross-region replication, and non-redundant load balancer setups.

</td>
<td width="50%" valign="top">

### 🤖 AI-Powered Reporting
Findings and deterministic scores fed into an AI context layer. Produces executive summaries and technical assessments via Claude, OpenAI, or DeepSeek — one click, PDF-ready output.

</td>
</tr>
</table>

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Cloud Accounts                          │
│               AWS (IAM Role) │ OCI (API Key)                 │
└──────────────┬───────────────────────────┬───────────────────┘
               │                           │
   ┌───────────▼───────────────────────────▼──────────┐
   │              Inventory Collectors                 │
   │        Scheduled Celery tasks per provider        │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │          Resource Normalization Layer             │
   │    Provider-specific → unified resource model     │
   │             (PostgreSQL + SQLAlchemy)             │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │               Findings Engine                    │
   │  Rule-based: idle compute · public exposure ·    │
   │  missing tags · unattached volumes · obs gaps    │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │             Risk Scoring Module                  │
   │      Severity × Impact × Coverage = Score        │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │             AI Context Builder                   │
   │   Structures findings into prompts for LLMs      │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │        Claude / OpenAI / DeepSeek                │
   │   Executive summaries · Technical assessments    │
   └──────────────┬────────────────────────────────────┘
                  │
   ┌──────────────▼──────────────────────┐
   │   Next.js Dashboard · PDF Reports  │
   │   Multi-tenant · Role-based RBAC   │
   └─────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **API** | FastAPI | REST API, async endpoints, OpenAPI schema |
| **Task Queue** | Celery + Redis | Scheduled collectors, async report generation |
| **Database** | PostgreSQL + SQLAlchemy | Primary data store, ORM |
| **Migrations** | Alembic | Schema versioning |
| **Cache / Broker** | Redis | Celery broker, result backend |
| **Frontend** | Next.js 16 + TailwindCSS | Dashboard UI, report viewer |
| **Charts** | Apache ECharts | Score trends, cost distribution |
| **AI Layer** | Claude · OpenAI · DeepSeek | Executive summaries, technical assessments |
| **Metrics** | Prometheus | Collector metrics, task duration, finding counts |
| **Tracing** | OpenTelemetry | Distributed tracing |
| **Dashboards** | Grafana | Platform observability |
| **Infrastructure** | Docker Compose | Local and staging environments |

---

## Supported Clouds

| Provider | Status | Resources Collected |
|---|---|---|
| **AWS** | ✅ Phase 0 | EC2, EBS, S3, RDS, IAM, VPC, Subnets, Security Groups, CloudWatch Alarms |
| **OCI** | ✅ Phase 0 | Compute, Block Volumes, VCNs, Load Balancers, Identity, Monitoring Alarms |
| Azure | 🔜 Phase 1 | — |
| GCP | 🔜 Phase 2 | — |

---

## Getting Started

**Prerequisites:** Docker, Docker Compose, Git

```bash
# 1. Clone
git clone https://github.com/ferkuellar/northbound-control-tower.git
cd northbound-control-tower

# 2. Configure environment
make setup
# Edit .env — set JWT_SECRET_KEY and optionally ANTHROPIC_API_KEY / OPENAI_API_KEY

# 3. Start the platform
make up

# 4. Open the dashboard
open http://localhost:3000
```

**Services after `make up`:**

| Service | URL | Description |
|---|---|---|
| Frontend | http://localhost:3000 | Executive Dashboard |
| Backend API | http://localhost:8000 | FastAPI · OpenAPI docs at `/docs` |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3001 | Platform observability (admin/admin) |

**Common commands:**

```bash
make logs           # Stream all service logs
make backend-test   # Run pytest suite
make backend-lint   # Ruff check
make frontend-lint  # ESLint
make down           # Stop all services
make clean          # Stop + remove volumes
```

---

## Phase 0 Scope

This release establishes a deliberate, production-grade foundation. The following are **out of scope by design** and addressed in subsequent phases:

| Out of Scope | Rationale |
|---|---|
| Kubernetes-native deployment | Operational complexity deferred |
| Microservices / event-driven architecture | Modular monolith first; split when justified |
| Event buses (Kafka, SQS) | Not required at current data volume |
| Auto-remediation | Trust established before automation acts |
| Real-time streaming | Near-realtime via scheduled polling is sufficient |
| Azure, GCP | AWS + OCI until core model is stable |
| Billing ingestion at line-item level | Aggregate FinOps diagnostics only |

---

## Documentation

| Document | Purpose | Audience |
|---|---|---|
| **README** *(this file)* | Platform overview, screenshots, getting started | All |
| [QUICKSTART.md](./QUICKSTART.md) | Step-by-step local setup | Engineers |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Component design, data model, decisions | Engineers, Architects |
| [API_REFERENCE.md](./API_REFERENCE.md) | Full endpoint reference, request/response schemas | Developers, Integrators |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Branch conventions, adding collectors and finding types | Contributors |
| [docs/architecture/](./docs/architecture/) | Per-module architecture docs | Engineers |

---

## Roadmap

| Phase | Focus | Status |
|---|---|---|
| **Phase 0** | Modular monolith — AWS + OCI · core findings · deterministic scoring · AI reports · multi-tenant SaaS | 🔵 Active |
| **Phase 1** | Azure support · credential encryption · Redis-based rate limiting · distributed workers | ⚪ Planned |
| **Phase 2** | GCP support · auto-remediation workflows · Slack/Teams alerting · billing line-item ingestion | ⚪ Planned |
| **Phase 3** | Kubernetes-native · event-driven architecture · SaaS marketplace listing | ⚪ Planned |

Phase boundaries are intentional. Each phase is stable and operationally validated before scope expands.

---

## License

Proprietary. All rights reserved.  
© Northbound — NorthFinOps 

For licensing and enterprise inquiries, contact the maintainers through the repository.

---

<div align="center">
<sub>Built with FastAPI · Next.js · PostgreSQL · Celery · Prometheus · OpenTelemetry · Claude AI</sub>
</div>
