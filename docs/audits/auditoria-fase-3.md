# Auditoria Fase 3 - AWS Inventory Collector

## 1. Objetivo

Implementar el AWS Inventory Collector read-only para NORTHBOUND CONTROL TOWER, persistiendo recursos normalizados, tracking de scans, audit logs y dejando DeepSeek configurado solo como base de proveedor AI sin usarlo en inventario.

## 2. Alcance

Incluido:

- AWS cloud account model.
- AWS collector foundation con boto3/botocore.
- EC2, EBS, S3, RDS, IAM, VPC/Subnet/SecurityGroup y CloudWatch alarms basic.
- Normalizacion a modelo unificado `Resource`.
- Persistencia PostgreSQL.
- Tracking de `InventoryScan`.
- Endpoints JWT-protected para cloud accounts, scans y resources.
- RBAC basico por roles existentes.
- Audit logging para eventos de AWS inventory.
- DeepSeek/OpenAI-compatible provider foundation sin llamadas de analisis.

Fuera de alcance:

- OCI collector.
- Azure/GCP.
- Findings engine.
- Risk scoring.
- AI report generation.
- Remediation.
- Kubernetes.
- Microservices.
- Autonomous agents.
- Advanced RBAC.

## 3. Auditoría inicial

Estado previo:

- Fases 0-2 estaban funcionales.
- Existian tenants, users, JWT auth, RBAC basico y audit logs.
- Existia estructura `collectors`, pero sin collector AWS real.
- No existian modelos `cloud_accounts`, `resources` ni `inventory_scans`.
- No existian endpoints de cloud accounts/inventory/resources.
- No existia configuracion DeepSeek/AI provider.

Brechas detectadas:

- Faltaban dependencias AWS SDK y OpenAI-compatible SDK.
- Faltaba migracion para inventario.
- Faltaba aislamiento tenant-aware en queries de inventario.
- Faltaba evitar exponer credenciales por API.

## 4. Plan técnico

Plan aplicado:

1. Agregar settings AWS y AI sin hardcodear secretos.
2. Crear provider abstraction AI con DeepSeek como cliente OpenAI-compatible opcional.
3. Crear modelos SQLAlchemy para cloud accounts, resources e inventory scans.
4. Crear normalizadores AWS testeables sin credenciales.
5. Crear AWS session factory para access keys, role arn y profile/env fallback.
6. Crear collector AWS con paginacion y manejo de errores parciales.
7. Crear endpoints protegidos por JWT/RBAC.
8. Crear migracion Alembic.
9. Validar Docker, migraciones, endpoints base, auth flow y tests.

## 5. Arquitectura

Flujo implementado:

`Cloud Account -> AWS Collector -> Raw AWS response parsing -> Resource Normalization -> PostgreSQL resources table -> Scan status -> Audit log`

Componentes:

- `collectors/aws/session.py`: sesiones boto3 y helpers de error AWS.
- `collectors/aws/collector.py`: recoleccion por servicio.
- `collectors/aws/normalizers.py`: conversion de respuestas AWS a recursos normalizados.
- `models/cloud_account.py`: credenciales/config AWS tenant-aware.
- `models/resource.py`: recurso normalizado.
- `models/inventory_scan.py`: estado de scan.
- `services/inventory.py`: orquestacion scan, persistencia y audit logs.
- `api/routes/cloud_accounts.py`: crear/listar cuentas cloud.
- `api/routes/inventory.py`: ejecutar scan y leer status.
- `api/routes/resources.py`: listar/leer recursos.
- `ai/provider.py`: abstraccion AI configurable.

## 6. Archivos creados

- `backend/ai/provider.py`
- `backend/alembic/versions/2026_05_11_0145-0002_aws_inventory_base.py`
- `backend/api/routes/cloud_accounts.py`
- `backend/api/routes/inventory.py`
- `backend/api/routes/resources.py`
- `backend/api/schemas/inventory.py`
- `backend/collectors/aws/__init__.py`
- `backend/collectors/aws/collector.py`
- `backend/collectors/aws/normalizers.py`
- `backend/collectors/aws/session.py`
- `backend/models/cloud_account.py`
- `backend/models/inventory_scan.py`
- `backend/models/resource.py`
- `backend/services/inventory.py`
- `backend/tests/test_ai_provider.py`
- `backend/tests/test_aws_normalizers.py`
- `docs/audits/auditoria-fase-3.md`

## 7. Archivos modificados

- `.env.example`
- `backend/api/router.py`
- `backend/core/config.py`
- `backend/models/__init__.py`
- `backend/requirements.txt`

## 8. Implementación

Endpoints agregados:

- `POST /api/v1/cloud-accounts/aws`
- `GET /api/v1/cloud-accounts`
- `POST /api/v1/inventory/aws/scan/{cloud_account_id}`
- `GET /api/v1/inventory/scans/{scan_id}`
- `GET /api/v1/resources`
- `GET /api/v1/resources/{resource_id}`

RBAC:

- `ADMIN`, `ANALYST`: crear cloud accounts y ejecutar scans.
- `ADMIN`, `ANALYST`, `VIEWER`: listar/leer recursos y leer scan status.

Servicios AWS iniciales:

- EC2 instances -> `compute`.
- EBS volumes -> `block_storage`.
- S3 buckets -> `object_storage`.
- RDS instances -> `database`.
- IAM users/roles/policies -> `identity`.
- VPC/subnets/security groups -> `network`.
- CloudWatch alarms -> `monitoring`.

AI provider foundation:

- `AI_PROVIDER`: `none`, `openai`, `claude`, `deepseek`.
- DeepSeek usa `DEEPSEEK_BASE_URL`, `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`.
- No se llama DeepSeek desde collector.
- No existe endpoint de AI analysis ni reportes.

## 9. Validación

Comandos ejecutados:

- `docker compose down`: OK.
- `docker compose up --build -d`: OK.
- `docker compose exec backend alembic upgrade head`: OK.
- `curl http://localhost:8000/health`: OK, HTTP 200.
- `curl http://localhost:8000/api/v1/status`: OK, HTTP 200.
- `docker compose ps`: backend/postgres/redis healthy; frontend/prometheus/grafana/worker arriba.

Auth validation:

- Login con admin existente: OK.
- Crear AWS cloud account con payload access-key dummy: OK, HTTP 201.
- La respuesta de cloud account no devuelve `secret_access_key`: OK.
- Ejecutar scan con credenciales dummy: OK a nivel endpoint; scan `completed`, 0 resources, `error_message` presente.
- Leer scan status: OK.
- Listar resources: OK, lista vacia por credenciales dummy.

Nota: no se usaron credenciales AWS reales en esta validacion. Con credenciales read-only validas, el collector ejecuta llamadas boto3 y persiste recursos normalizados.

## 10. Pruebas

Pruebas ejecutadas:

- `docker compose run --rm backend ruff check .`: OK.
- `docker compose run --rm backend python -m pytest`: OK, 7 passed.

Tests agregados:

- Normalizacion EC2 instance.
- Normalizacion EBS volume.
- Normalizacion S3 bucket.
- Configuracion default AI provider `none`.

Warnings conocidos:

- `passlib` usa `crypt`, deprecated para Python 3.13.
- `python-jose` usa `datetime.utcnow()`, deprecated.

## 11. Seguridad

Controles implementados:

- Todos los endpoints AWS requieren JWT.
- Queries de cloud accounts, scans y resources filtran por `tenant_id` del usuario actual.
- `secret_access_key` no se devuelve en responses.
- No se loguean AWS secrets, JWT tokens ni DeepSeek API keys.
- Audit logs de scan registran ids y metadata no sensible.
- DeepSeek queda deshabilitado por default con `AI_PROVIDER=none`.
- AI provider no se invoca durante scans AWS.

Deuda tecnica documentada:

- En Fase 3 local/dev, `secret_access_key` puede almacenarse en DB como placeholder basico.
- Produccion debe usar IAM Role + External ID o secret management respaldado por vault/KMS.

## 12. Observabilidad

Implementado:

- Logs estructurados de inicio, completion y failure de scans.
- Campos incluidos: `scan_id`, `tenant_id`, `cloud_account_id`, `provider`.
- Audit logs:
  - `aws_cloud_account_created`
  - `aws_inventory_scan_started`
  - `aws_inventory_scan_completed`
  - `aws_inventory_scan_failed`
  - `aws_access_denied_partial`

Validacion audit log:

- Se confirmaron eventos `aws_cloud_account_created`, `aws_inventory_scan_started` y `aws_inventory_scan_completed` en PostgreSQL.

No se agregaron componentes nuevos de observabilidad.

## 13. Riesgos y trade-offs

- El scan es sincrono para mantener Fase 3 simple y auditable; en cuentas grandes debe moverse a Celery.
- La cobertura regional es inicial: se usa `default_region` para servicios regionales. S3/IAM se tratan como globales o region base.
- Errores parciales no destruyen todo el scan; se guardan en `error_message` y audit logs cuando aplica.
- Credenciales dummy validan flujo de API, no descubrimiento real.
- `AIProvider.CLAUDE` queda representado en enum/config, pero sin cliente implementado en esta fase.
- `ResourceRead` expone `metadata_json` como nombre de atributo API para evitar conflicto SQLAlchemy con `metadata`.

## 14. Refactorización recomendada

Para fases posteriores:

- Ejecutar scans en Celery con polling de status.
- Agregar multi-region AWS discovery.
- Agregar encryption/vault para secretos.
- Agregar tests con botocore Stubber para collector service.
- Agregar paginacion/filtros en `GET /api/v1/resources`.
- Agregar metricas Prometheus de scans.
- Modelar errores parciales en tabla dedicada si se requiere auditoria detallada.
- Implementar providers AI reales solo cuando exista fase AI/reporting.

## 15. Auditoría final

Resultado:

- AWS account credential model: OK.
- AWS read-only integration foundation: OK.
- AWS collector service: OK.
- AWS inventory scan endpoint: OK.
- Normalized resources persisted/upsert-ready: OK.
- Scan tracking: OK.
- Audit logging for scans: OK.
- CloudWatch basic alarm metadata: OK.
- DeepSeek provider configuration/client foundation: OK.
- Alembic migration: OK.
- Tenant isolation: OK.
- Secrets omitted from API responses: OK.
- Docker Compose compatibility: OK.
- Existing Fase 0-2 endpoints/tests intactos: OK.

## 16. Commit sugerido

```bash
git add .env.example backend/ai/provider.py backend/alembic/versions/2026_05_11_0145-0002_aws_inventory_base.py backend/api/router.py backend/api/routes/cloud_accounts.py backend/api/routes/inventory.py backend/api/routes/resources.py backend/api/schemas/inventory.py backend/collectors/aws backend/core/config.py backend/models/__init__.py backend/models/cloud_account.py backend/models/inventory_scan.py backend/models/resource.py backend/requirements.txt backend/services/inventory.py backend/tests/test_ai_provider.py backend/tests/test_aws_normalizers.py docs/audits/auditoria-fase-3.md
git commit -m "feat: implement aws inventory collector and ai provider foundation"
```
