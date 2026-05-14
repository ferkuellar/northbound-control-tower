<div align="center">

<img src="docs/screenshots/login.png" alt="Northbound Control Tower — Executive cloud operations dashboard" width="100%">

<br/>
<br/>

# Northbound Control Tower

**Multicloud operational intelligence for teams that need visibility, not complexity.**

[![Phase](https://img.shields.io/badge/phase-0%20%E2%80%94%20Foundation-blue)](https://claude.ai/chat/ARCHITECTURE.md)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20Next.js%20%7C%20PostgreSQL-informational)](https://claude.ai/chat/a8637936-f29a-4ce6-bfb6-0b0b8006db00#tech-stack)
[![Clouds](https://img.shields.io/badge/clouds-AWS%20%7C%20OCI-orange)](https://claude.ai/chat/a8637936-f29a-4ce6-bfb6-0b0b8006db00#supported-clouds)
[![License](https://img.shields.io/badge/license-proprietary-lightgrey)](https://claude.ai/chat/LICENSE)
[![Status](https://img.shields.io/badge/status-active%20development-yellow)](https://claude.ai/chat/a8637936-f29a-4ce6-bfb6-0b0b8006db00)

---

## Overview

Northbound Control Tower is an enterprise-oriented multicloud operational intelligence platform.
It gives cloud teams and executives a single, structured view of their cloud estate — covering inventory, cost exposure, governance gaps, observability readiness, and resilience posture — without requiring deep expertise in each provider's native tooling.

The platform ingests raw cloud data, normalizes it across providers, runs a findings engine against it, scores risk, and feeds the results into an AI-assisted reporting layer that produces both technical assessments and executive-ready summaries.

**The core problem it solves:**
Most organizations operating across AWS and OCI have fragmented visibility. Native consoles are siloed. Cost anomalies go undetected. Governance failures surface late. Executive reporting is manual. Control Tower closes those gaps in a single operational layer.

---

## What This Is Not (Phase 0 Scope)

Phase 0 establishes a deliberate, production-grade foundation. The following are **out of scope by design** and will be addressed in subsequent phases:

| Out of Scope — Phase 0                   | Rationale                                         |
| ----------------------------------------- | ------------------------------------------------- |
| Kubernetes-native deployment              | Operational complexity deferred                   |
| Microservices / event-driven architecture | Modular monolith first; split when justified      |
| Event buses (Kafka, SQS)                  | Not required at current data volume               |
| Auto-remediation                          | Trust must be established before automation acts  |
| Real-time streaming                       | Near-realtime via scheduled polling is sufficient |
| Advanced RBAC / multi-tenant auth         | Single-tenant API key auth in Phase 0             |
| Azure, GCP, or other clouds               | AWS + OCI only until core model is stable         |
| Billing ingestion at line-item level      | Aggregate FinOps diagnostics only                 |

---

## Key Capabilities

<table>
<tr>
<td width="50%" valign="top">

### ☁️ Cloud Inventory

Collects, normalizes, and stores resource data from AWS and OCI into a unified schema. Compute, storage, networking, and IAM resources are catalogued continuously via scheduled collectors.

### 💰 FinOps Diagnostics

Identifies cost exposure signals: idle compute instances, unattached volumes, oversized resources, and resources missing budget-alignment tags. Findings are scored and surfaced with remediation context.

### 🔒 Governance Analysis

Evaluates cloud resources against governance baselines: missing required tags, publicly exposed assets, lack of encryption at rest or in transit, and deviation from resource naming conventions.

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

Feeds normalized findings and risk scores into a structured AI context layer. Produces two output types:

* **Technical Assessment** — detailed findings with remediation steps, severity, and affected resources.
* **Executive Summary** — plain-language narrative for C-level and board-level audiences, with risk posture, cost exposure, and prioritized action items.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Cloud Accounts                            │
│                    AWS (IAM Role) │ OCI (API Key)                │
└─────────────────────┬─────────────────────┬──────────────────────┘
                      │                     │
          ┌───────────▼─────────────────────▼───────────┐
          │           Inventory Collectors              │
          │     Scheduled Celery tasks per provider     │
          └───────────────────────┬─────────────────────┘
                                  │
          ┌───────────────────────▼─────────────────────┐
          │         Resource Normalization Layer        │
          │   Provider-specific → unified resource model│
          │              (PostgreSQL + SQLAlchemy)      │
          └───────────────────────┬─────────────────────┘
                                  │
          ┌───────────────────────▼─────────────────────┐
          │              Findings Engine                │
          │   Rule-based evaluation: idle, exposed,     │
          │   untagged, unattached, observability gaps  │
          └───────────────────────┬─────────────────────┘
                                  │
          ┌───────────────────────▼─────────────────────┐
          │             Risk Scoring Module             │
          │    Severity × Impact × Coverage = Score     │
          └───────────────────────┬─────────────────────┘
                                  │
          ┌───────────────────────▼─────────────────────┐
          │            AI Context Builder               │
          │  Structures findings into prompts for LLMs  │
          └───────────────────────┬─────────────────────┘
                                  │
          ┌───────────────────────▼─────────────────────┐
          │         Claude / OpenAI Analysis            │
          │   Technical assessments + executive reports │
          └──────────────────────┬──────────────────────┘
                                 │
                  ┌──────────────▼───────────────┐
                  │   Dashboards & Reports       │
                  │   Next.js + ECharts + API    │
                  └──────────────────────────────┘
```

For a full breakdown of each component, data models, and design decisions, see [ARCHITECTURE.md](https://claude.ai/chat/ARCHITECTURE.md).

---

## Tech Stack

| Layer                    | Technology                | Role                                              |
| ------------------------ | ------------------------- | ------------------------------------------------- |
| **API**            | FastAPI                   | REST API, async endpoints, OpenAPI schema         |
| **Task Queue**     | Celery + Redis            | Scheduled collectors, async report generation     |
| **Database**       | PostgreSQL + SQLAlchemy   | Primary data store, ORM                           |
| **Migrations**     | Alembic                   | Schema versioning and migration management        |
| **Cache / Broker** | Redis                     | Celery broker, result backend, short-lived cache  |
| **Frontend**       | Next.js + TailwindCSS     | Dashboard UI, report viewer                       |
| **Charts**         | Apache ECharts            | Resource distribution, risk trends, cost signals  |
| **AI Layer**       | Anthropic Claude / OpenAI | Executive summaries, technical assessments        |
| **Metrics**        | Prometheus                | Collector metrics, task duration, finding counts  |
| **Tracing**        | OpenTelemetry             | Distributed tracing, instrumentation hooks        |
| **Dashboards**     | Grafana                   | Operational observability for the platform itself |
| **Infrastructure** | Docker Compose            | Local and staging environments                    |

---

## Supported Clouds

| Provider | Status     | Credential Method                |
| -------- | ---------- | -------------------------------- |
| AWS      | ✅ Phase 0 | IAM Role (assumed) or Access Key |
| OCI      | ✅ Phase 0 | API Key + config file            |
| Azure    | 🔜 Phase 1 | —                               |
| GCP      | 🔜 Phase 2 | —                               |

---

## Documentation

| Document                                                 | Purpose                                                | Audience                |
| -------------------------------------------------------- | ------------------------------------------------------ | ----------------------- |
| **README** *(this file)*                         | Platform overview, capabilities, architecture          | All                     |
| [ARCHITECTURE.md](https://claude.ai/chat/ARCHITECTURE.md)   | Component design, data model, technical decisions      | Engineers, Architects   |
| [QUICKSTART.md](https://claude.ai/chat/QUICKSTART.md)       | Run the stack locally in under 30 minutes              | Engineers               |
| [API_REFERENCE.md](https://claude.ai/chat/API_REFERENCE.md) | Full endpoint reference, request/response schemas      | Developers, Integrators |
| [CONTRIBUTING.md](https://claude.ai/chat/CONTRIBUTING.md)   | Branch conventions, how to add collectors and findings | Contributors            |

---

## Roadmap

Control Tower is developed in phases. Each phase delivers a stable, production-usable increment before extending scope.

| Phase             | Focus                                                                  | Status     |
| ----------------- | ---------------------------------------------------------------------- | ---------- |
| **Phase 0** | Modular monolith foundation — AWS + OCI, core findings, AI reports    | 🔵 Active  |
| **Phase 1** | Azure support, advanced RBAC, multi-tenant accounts, billing ingestion | ⚪ Planned |
| **Phase 2** | GCP support, auto-remediation workflows, Slack/Teams alerting          | ⚪ Planned |
| **Phase 3** | Kubernetes-native deployment, event-driven architecture, SaaS mode     | ⚪ Planned |

Phase boundaries are intentional. New capabilities are added only after the current phase is stable and operationally validated.


---

## License

Proprietary. All rights reserved.
© Northbound — NorthFinOps

For licensing inquiries, contact: [`<!-- TODO: insert contact email -->`]

<div align="center">
<sub>Built with FastAPI · Next.js · PostgreSQL · Celery · Prometheus · OpenTelemetry · Claude AI</sub>
</div>