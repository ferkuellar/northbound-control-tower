# Auditoria Fase 4 - OCI Inventory Collector

## 1. Objetivo

Implementar el colector de inventario OCI read-only para Compute, Block Volumes, VCN/networking, Load Balancers, Compartments, IAM basico y Monitoring alarms, preservando la arquitectura modular monolith y la compatibilidad Docker existente.

## 2. Alcance

Incluido en esta fase:
- Integracion de cuentas OCI.
- SDK foundation con `oci`.
- Session/config factory para `oci_config` y `oci_api_key`.
- Traversal basico de compartments activos.
- Colector OCI sincronico.
- Normalizacion hacia el modelo `Resource`.
- Tracking con `InventoryScan`.
- Audit logging para creacion de cuenta, inicio, exito, fallo y access denied parcial.
- Migracion Alembic para campos OCI en `cloud_accounts`.

Fuera de alcance:
- Azure, GCP, OCI avanzado, findings engine, scoring, AI reports, remediation, Kubernetes, microservices, autonomous agents y RBAC avanzado.

## 3. Auditoria inicial

El repositorio ya tenia Phase 3 funcional con AWS collector, recursos normalizados, scans, auditoria y AI provider foundation. La base existente permitia extender el modelo `CloudAccount`, reutilizar `InventoryScan`, `Resource`, tenant isolation y RBAC basico.

Se detecto durante la recuperacion que `backend/services/inventory.py` habia quedado con el bloque `except` de AWS desplazado despues de la funcion OCI. Se corrigio antes de validar.

## 4. Plan tecnico

1. Extender configuracion y dependencias.
2. Extender `CloudProvider`, `CloudAccountAuthType` y `CloudAccount`.
3. Agregar migracion Alembic no destructiva.
4. Crear paquete `collectors/oci`.
5. Agregar schemas y endpoints OCI.
6. Reutilizar el servicio de inventario para persistencia y auditoria.
7. Agregar pruebas unitarias de normalizacion, contratos de provider y no exposicion de secretos.
8. Validar Docker, migraciones, health checks, lint, tests y endpoints protegidos.

## 5. Arquitectura

Flujo implementado:

```text
OCI Cloud Account
-> OCI Session/Config Factory
-> Compartment Traversal
-> OCI Collector
-> Resource Normalization
-> PostgreSQL resources table
-> InventoryScan status
-> AuditLog
```

La integracion OCI comparte las tablas existentes con AWS usando `provider=oci` y mantiene aislamiento por `tenant_id`.

## 6. Archivos creados

- `backend/alembic/versions/2026_05_11_0215-0003_oci_cloud_account_fields.py`
- `backend/collectors/oci/__init__.py`
- `backend/collectors/oci/errors.py`
- `backend/collectors/oci/session.py`
- `backend/collectors/oci/collector.py`
- `backend/collectors/oci/normalizers.py`
- `backend/tests/test_oci_normalizers.py`
- `backend/tests/test_oci_integration_contracts.py`
- `docs/audits/auditoria-fase-4.md`

## 7. Archivos modificados

- `.env.example`
- `backend/requirements.txt`
- `backend/core/config.py`
- `backend/models/cloud_account.py`
- `backend/api/schemas/inventory.py`
- `backend/api/routes/cloud_accounts.py`
- `backend/api/routes/inventory.py`
- `backend/services/inventory.py`

## 8. Implementacion

Se agrego `oci==2.141.1` al backend.

Settings nuevos:
- `OCI_DEFAULT_REGION`
- `OCI_SCAN_TIMEOUT_SECONDS`

`CloudProvider` ahora soporta:
- `aws`
- `oci`

`CloudAccountAuthType` ahora soporta:
- `access_keys`
- `role_arn`
- `profile`
- `oci_config`
- `oci_api_key`

Campos OCI agregados a `CloudAccount`:
- `tenancy_ocid`
- `user_ocid`
- `fingerprint`
- `private_key`
- `private_key_passphrase`
- `region`
- `compartment_ocid`

Endpoints nuevos:
- `POST /api/v1/cloud-accounts/oci`
- `POST /api/v1/inventory/oci/scan/{cloud_account_id}`

El colector implementa metodos base para:
- Compute instances.
- Boot volumes y block volumes.
- VCN, subnets, security lists y NSGs.
- Load balancers.
- Compartments.
- IAM users, groups y policies basicos.
- Monitoring alarms basicos.

## 9. Validacion

Comandos ejecutados:

```powershell
docker compose down
docker compose up --build -d
docker compose exec backend alembic upgrade head
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/status
docker compose exec backend python -m ruff check .
docker compose exec backend python -m pytest
```

Resultados:
- Docker build completo correctamente.
- Servicios levantados: backend, frontend, postgres, redis, prometheus, grafana y worker.
- Migracion `0003_oci_cloud_account_fields` aplicada correctamente.
- `/health` respondio `{"status":"ok"}`.
- `/api/v1/status` respondio JSON valido con `success=true`.
- Ruff paso sin errores.
- Pytest: `15 passed`.

Validacion auth/API:
- Login JWT correcto con el usuario admin existente.
- `POST /api/v1/cloud-accounts/oci` creo una cuenta `oci_config`.
- La respuesta no expuso `private_key`, `private_key_passphrase`, `fingerprint`, `user_ocid` ni `tenancy_ocid`.
- `POST /api/v1/inventory/oci/scan/{cloud_account_id}` creo scan y lo marco `failed` de forma controlada porque el contenedor no tiene `/root/.oci/config`.
- `GET /api/v1/inventory/scans/{scan_id}` devolvio el estado del scan.
- `GET /api/v1/resources` respondio correctamente; sin credenciales OCI reales devolvio lista vacia.

## 10. Pruebas

Pruebas agregadas:
- Normalizacion OCI Compute.
- Normalizacion OCI Block Volume.
- Normalizacion OCI networking.
- Normalizacion OCI Compartment.
- Compatibilidad de enum `CloudProvider` con AWS y OCI.
- Validacion de campos requeridos para `oci_api_key`.
- Resolucion de compartment scoped antes que tenancy root.
- Verificacion de que `CloudAccountRead` no expone secretos OCI/AWS.

Suite final:

```text
15 passed, 2 warnings
```

Las advertencias vienen de dependencias (`passlib`/`python-jose`) y no bloquean Phase 4.

## 11. Seguridad

Los endpoints OCI requieren JWT y roles:
- `ADMIN` o `ANALYST` para crear cuentas OCI.
- `ADMIN` o `ANALYST` para ejecutar scans.
- `ADMIN`, `ANALYST` o `VIEWER` para consultar scans y recursos.

Las consultas filtran por `tenant_id`.

No se devuelven secretos en `CloudAccountRead`:
- No `private_key`.
- No `private_key_passphrase`.
- No `fingerprint`.
- No `tenancy_ocid`.
- No `user_ocid`.
- No AWS secret keys.

Deuda tecnica documentada:
- En Phase 4 se permite almacenar `private_key` en DB para desarrollo local.
- Produccion debe migrar a vault-backed secret management.
- Produccion debe preferir credenciales read-only y rotacion de secretos.

## 12. Observabilidad

El servicio registra eventos estructurados para:
- Inicio de scan OCI.
- Finalizacion de scan OCI.
- Fallo de scan OCI.

Los logs incluyen:
- `scan_id`
- `tenant_id`
- `cloud_account_id`
- `provider`
- `resources_discovered`
- `compartments_scanned`
- `partial_errors`

Audit logs implementados:
- `oci_cloud_account_created`
- `oci_inventory_scan_started`
- `oci_inventory_scan_completed`
- `oci_inventory_scan_failed`
- `oci_compartment_access_denied_partial`

No se agregaron componentes nuevos de observabilidad.

## 13. Riesgos y trade-offs

- El scan es sincronico; puede bloquear requests si una tenancy grande tarda demasiado.
- El almacenamiento temporal de `private_key` en DB no es apto para produccion.
- La cobertura OCI es inicial y read-only; no interpreta riesgos ni findings.
- La recoleccion depende de permisos OCI reales por compartment.
- Sin credenciales OCI reales solo se puede validar creacion de cuenta, error handling y tracking de fallo.
- Partial failures se registran sin abortar el scan cuando ocurren a nivel compartment/servicio.

## 14. Refactorizacion recomendada

- Mover credenciales cloud a vault-backed storage.
- Convertir scans a Celery jobs asincronicos con timeout y reintentos controlados.
- Agregar metadata estructurada de errores parciales en una tabla dedicada o campo JSON de scan.
- Agregar paginacion/filtros a recursos y scans.
- Agregar tests con mocks OCI SDK para traversal y partial access denied.
- Extraer interfaces comunes AWS/OCI para collectors si la duplicacion crece.

## 15. Auditoria final

Phase 4 queda implementada sin introducir Azure, GCP, Kubernetes, microservices, remediation, autonomous agents ni AI analysis.

AWS Phase 3 se preserva y el modelo compartido ahora soporta `provider=oci`.

El stack Docker sigue levantando correctamente con build completo. Las migraciones aplican hasta `head`. Health/status funcionan. Las pruebas pasan en el contenedor backend.

La validacion con `oci_config` sin archivo local demuestra error handling controlado y tracking persistente. Para validar descubrimiento real de recursos se requiere montar `/root/.oci/config` o crear cuenta `oci_api_key` con credenciales OCI read-only reales.

## 16. Commit sugerido

```text
feat: implement oci inventory collector
```
