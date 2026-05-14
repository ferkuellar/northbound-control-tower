# Auditoria Fase 12 - SaaS Hardening

## 1. Objetivo

Endurecer Northbound Control Tower como plataforma SaaS multi-tenant con aislamiento estricto, permisos RBAC, rate limiting, auditoria mejorada, manejo seguro de secretos y middleware de seguridad.

## 2. Alcance

Incluye tenant context, permisos por rol, guards de autorizacion, rate limiting, security headers, validacion basica de requests, audit trail consultable, abstraccion de secretos, pruebas y documentacion.

## 3. Auditoría inicial

El backend ya tenia JWT, roles basicos y filtros `tenant_id` en endpoints principales. Faltaban permisos explicitos, auditoria consultable, middleware de seguridad, rate limits y una abstraccion formal de secretos.

## 4. Plan técnico

Agregar modulos `auth`, `security`, `middleware` y `audit`; migrar audit logs; reemplazar checks de rol por permisos; proteger endpoints criticos con rate limits; documentar limitaciones de secretos locales.

## 5. Arquitectura

JWT autentica al usuario, `TenantContextMiddleware` fija contexto tenant, `require_permission` valida permisos, las rutas ejecutan queries filtradas por tenant y el audit trail registra eventos criticos con `request_id`.

## 6. Archivos creados

- `backend/auth/permissions.py`
- `backend/auth/roles.py`
- `backend/auth/guards.py`
- `backend/auth/decorators.py`
- `backend/security/__init__.py`
- `backend/security/rate_limit.py`
- `backend/security/headers.py`
- `backend/security/secrets.py`
- `backend/security/hashing.py`
- `backend/security/validation.py`
- `backend/middleware/__init__.py`
- `backend/middleware/tenant.py`
- `backend/middleware/auth.py`
- `backend/middleware/rate_limit.py`
- `backend/audit/__init__.py`
- `backend/audit/service.py`
- `backend/audit/schemas.py`
- `backend/audit/filters.py`
- `backend/api/routes/audit.py`
- `backend/alembic/versions/2026_05_13_0200-0009_saas_hardening_audit.py`
- `backend/tests/test_saas_hardening.py`
- `docs/architecture/saas-hardening.md`
- `docs/audits/auditoria-fase-12.md`

## 7. Archivos modificados

- `.env.example`
- `backend/api/main.py`
- `backend/api/router.py`
- `backend/auth/dependencies.py`
- `backend/auth/schemas.py`
- `backend/core/config.py`
- `backend/models/audit_log.py`
- `backend/services/audit_log.py`
- rutas API de tenants, cloud accounts, inventory, resources, findings, scores, AI y reports

## 8. Implementación

Se implemento RBAC por permisos, audit API admin-only, rate limiting para login/AI/reportes/inventario, headers de seguridad, limite de tamano de payload, tenant context desde JWT y helper `get_current_tenant`.

## 9. Validación

Comandos previstos:

- `docker compose down`
- `docker compose up --build`
- `docker compose exec backend pytest`
- `curl http://localhost:8000/health`

## 10. Pruebas

Se agregaron pruebas para headers, viewer sin writes, analyst sin auditoria, admin con auditoria, bloqueo cross-tenant, no exposicion de secretos y rate limiting HTTP 429.

## 11. Seguridad

Los endpoints criticos ahora usan permisos explicitos. Las respuestas de cloud accounts no exponen secrets. Rate limiting protege endpoints sensibles. Los logs de denegacion y rate limit evitan payloads sensibles.

## 12. Observabilidad

Los eventos de permisos denegados, rate limiting y audit trail incluyen `request_id` por la base de observabilidad de Fase 11. No se agregaron etiquetas Prometheus de tenant o user.

## 13. Riesgos y trade-offs

El rate limiter es in-memory y no sirve para multiples replicas. Los secretos de cloud accounts siguen en DB como deuda tecnica documentada. No se implemento RLS en base de datos para mantener la fase terminable.

## 14. Refactorización recomendada

Mover rate limits a Redis, cifrar o externalizar credenciales en vault, agregar RLS de PostgreSQL, centralizar repositorios tenant-aware y crear API formal de administracion de usuarios.

## 15. Auditoría final

La plataforma queda endurecida para operacion SaaS inicial con permisos explicitos, aislamiento por tenant en rutas principales, auditoria consultable, rate limits y controles HTTP de seguridad.

## 16. Commit sugerido

`feat: implement saas hardening with tenant isolation rbac and security controls`
