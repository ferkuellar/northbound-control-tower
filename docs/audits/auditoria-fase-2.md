# Auditoria Fase 2 - Auth & Tenant Base

## 1. Objetivo

Implementar la base inicial de autenticacion, tenants, usuarios, RBAC basico y audit logging para NORTHBOUND CONTROL TOWER, manteniendo el alcance limitado al backend.

## 2. Alcance

Incluido:

- Tenants.
- Users.
- JWT authentication.
- Password hashing con bcrypt.
- Login endpoint.
- Current user dependency.
- Basic RBAC dependencies.
- Audit log model.
- Audit log service.
- Alembic migration.
- Tests y validacion HTTP real.

Fuera de alcance:

- AWS collectors.
- OCI collectors.
- AI layer.
- Frontend dashboard.
- Advanced RBAC.
- SSO.
- Multi-factor authentication.
- Azure/GCP.
- Kubernetes.
- Auto-remediation.
- Autonomous agents.

## 3. Auditoria inicial

Fase 1 ya tenia:

- FastAPI app factory.
- Router base `/api/v1`.
- PostgreSQL con SQLAlchemy.
- Redis.
- Alembic base.
- Health checks.
- Logging estructurado.
- Celery base.

Brechas para Fase 2:

- No existian tablas `tenants`, `users` ni `audit_logs`.
- No existian utilidades de hashing/JWT.
- No existian endpoints `/api/v1/auth/*`.
- No existia dependencia `get_current_user`.
- No existia RBAC basico.
- No existia servicio de audit log.
- No existia migracion Alembic para auth/tenant/audit.

## 4. Plan técnico

Plan aplicado:

1. Crear modelos SQLAlchemy para tenant, user y audit log.
2. Agregar schemas Pydantic para bootstrap, login, token, usuario actual y tenants.
3. Implementar hashing y JWT en `backend/auth`.
4. Implementar dependencias de autenticacion y roles.
5. Montar rutas `/api/v1/auth` y `/api/v1/tenants`.
6. Agregar audit logging en bootstrap, login exitoso, login fallido y lectura de usuario actual.
7. Escribir migracion Alembic manual y validarla en Docker.
8. Validar flujo completo con token real.

## 5. Arquitectura

Componentes agregados:

- `models/tenant.py`: tenant con UUID, slug unico y status.
- `models/user.py`: usuario tenant-aware con email unico, password hash, role e `is_active`.
- `models/audit_log.py`: bitacora de acciones con tenant/user opcionales y metadata JSONB.
- `auth/security.py`: hashing bcrypt, verify, JWT encode/decode.
- `auth/dependencies.py`: `get_current_user` y `require_roles`.
- `auth/schemas.py`: contratos Pydantic de auth/tenant/user.
- `services/audit_log.py`: persistencia centralizada de eventos de auditoria.
- `api/routes/auth.py`: bootstrap, login y me.
- `api/routes/tenants.py`: tenant actual.

## 6. Archivos creados

- `backend/alembic/versions/2026_05_11_0125-0001_auth_tenant_audit_base.py`
- `backend/api/routes/auth.py`
- `backend/api/routes/tenants.py`
- `backend/auth/dependencies.py`
- `backend/auth/schemas.py`
- `backend/auth/security.py`
- `backend/models/audit_log.py`
- `backend/models/tenant.py`
- `backend/models/user.py`
- `backend/services/audit_log.py`
- `backend/tests/test_auth_security.py`
- `docs/audits/auditoria-fase-2.md`

## 7. Archivos modificados

- `.env.example`
- `backend/alembic/env.py`
- `backend/api/router.py`
- `backend/core/config.py`
- `backend/models/__init__.py`
- `backend/requirements.txt`

## 8. Implementación

Implementado:

- `POST /api/v1/auth/bootstrap`
  - Solo habilitado para `development`, `local` o `test`.
  - Rechaza crear bootstrap si ya existe al menos un usuario.
  - Crea tenant activo y primer usuario ADMIN.
  - Guarda password solo como hash.
  - Registra `bootstrap_admin_created`.

- `POST /api/v1/auth/login`
  - Verifica password bcrypt.
  - Devuelve JWT bearer.
  - Registra `user_login_success` o `user_login_failed`.

- `GET /api/v1/auth/me`
  - Requiere Bearer token.
  - Devuelve usuario autenticado.
  - Registra `current_user_read`.

- `GET /api/v1/tenants/me`
  - Requiere Bearer token.
  - Devuelve tenant del usuario autenticado.

- RBAC:
  - `get_current_user`.
  - `require_roles(["ADMIN"])`.
  - `require_roles(["ADMIN", "ANALYST"])`.

- Settings:
  - `JWT_SECRET_KEY`.
  - `JWT_ALGORITHM`.
  - `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`.

## 9. Validación

Comandos ejecutados:

- `docker compose down`: OK.
- `docker compose up --build -d`: OK.
- `docker compose exec backend alembic upgrade head`: OK.
- `docker compose ps`: backend healthy, postgres healthy, redis healthy; frontend, prometheus, grafana y worker arriba.

Validacion HTTP:

- `POST /api/v1/auth/bootstrap`: 201 Created con payload solicitado.
- Segundo `POST /api/v1/auth/bootstrap`: 409 Conflict, bloqueado correctamente.
- `POST /api/v1/auth/login`: 200 OK, devuelve `access_token`.
- Login con password incorrecto: 401 Unauthorized.
- `GET /api/v1/auth/me` con Bearer token: 200 OK, devuelve `admin@northbound.local` y role `ADMIN`.
- `GET /api/v1/tenants/me` con Bearer token: 200 OK, devuelve tenant `northbound-demo`.

Audit logs confirmados en PostgreSQL:

- `bootstrap_admin_created`: 1.
- `user_login_success`: 1 o mas.
- `user_login_failed`: 1.
- `current_user_read`: 1 o mas.

## 10. Pruebas

Pruebas ejecutadas:

- `docker compose run --rm backend ruff check .`: OK.
- `docker compose run --rm backend python -m pytest`: OK, 3 passed.

Pruebas agregadas:

- Hashing no almacena plaintext y verifica password correcta/incorrecta.
- JWT access token round-trip con subject, tenant_id y role.

Warnings observados:

- `passlib` usa `crypt`, marcado deprecated para Python 3.13.
- `python-jose` usa `datetime.utcnow()`, marcado deprecated.

No bloquean Fase 2, pero deben revisarse antes de subir runtime Python.

## 11. Seguridad

Controles implementados:

- Passwords nunca se almacenan en plaintext.
- JWT secret se lee desde settings/env.
- `.env.example` usa placeholder seguro, no secreto real.
- No se loguean passwords ni JWT tokens.
- Bootstrap queda limitado a entorno local/dev/test.
- Bootstrap queda bloqueado si ya existe cualquier usuario.
- Queries autenticadas usan `tenant_id` del usuario actual.
- `/tenants/me` solo devuelve el tenant del usuario autenticado.
- Errores de auth no revelan si email o password fue el dato incorrecto.

Riesgos pendientes:

- No hay MFA ni SSO por alcance.
- No hay rotacion/refresh tokens.
- No hay lockout/rate limit ante fuerza bruta.
- El JWT secret default de desarrollo debe reemplazarse en entornos compartidos.

## 12. Observabilidad

Implementado:

- Audit logs persistidos en PostgreSQL.
- Acciones minimas auditadas:
  - `bootstrap_admin_created`
  - `user_login_success`
  - `user_login_failed`
  - `current_user_read`
- Logs estructurados existentes se mantienen.
- Health checks y Prometheus se mantienen intactos.

## 13. Riesgos y trade-offs

- Se uso JWT bearer simple para mantener Fase 2 terminable y auditable.
- Se implemento RBAC basico por roles directos en usuario, sin permisos granulares.
- `email` se valida como string con limites, no como `EmailStr`, porque el payload requerido usa `admin@northbound.local` y la validacion estricta de emails rechaza dominios reservados.
- `AuditLog.metadata` se mapea como atributo `metadata_json` en SQLAlchemy porque `metadata` es nombre reservado en declarative models; la columna real en PostgreSQL se llama `metadata`.
- Se fijo `bcrypt==4.0.1` por compatibilidad con `passlib==1.7.4`.
- No se agregaron endpoints de administracion de usuarios para evitar ampliar alcance.

## 14. Refactorización recomendada

Para fases posteriores:

- Agregar rate limiting a login y bootstrap.
- Agregar refresh tokens o sesiones revocables.
- Extraer responses comunes de API.
- Agregar tests de integracion con DB efimera.
- Agregar indices adicionales si crecen consultas de audit logs.
- Evaluar reemplazo de `python-jose` y/o `passlib` antes de Python 3.13.
- Agregar administracion de usuarios y tenants solo cuando el alcance lo permita.

## 15. Auditoría final

Resultado:

- Tenant model: OK.
- User model: OK.
- AuditLog model: OK.
- Auth schemas: OK.
- Password hashing: OK.
- JWT generation/decoding: OK.
- JWT settings: OK.
- Bootstrap endpoint: OK.
- Login endpoint: OK.
- Current user endpoint: OK.
- Tenant current endpoint: OK.
- RBAC dependencies: OK.
- Audit log service: OK.
- Alembic migration: OK.
- Docker Compose compatibility: OK.
- Tests: OK.

El stack queda corriendo y los endpoints principales funcionan con token real.

## 16. Commit sugerido

```bash
git add .env.example backend/alembic/env.py backend/alembic/versions/2026_05_11_0125-0001_auth_tenant_audit_base.py backend/api/router.py backend/api/routes/auth.py backend/api/routes/tenants.py backend/auth/dependencies.py backend/auth/schemas.py backend/auth/security.py backend/core/config.py backend/models/__init__.py backend/models/audit_log.py backend/models/tenant.py backend/models/user.py backend/requirements.txt backend/services/audit_log.py backend/tests/test_auth_security.py docs/audits/auditoria-fase-2.md
git commit -m "feat: implement auth tenant base and audit logging"
```
