# Auditoria Fase 0 - NORTHBOUND CONTROL TOWER

## 1. Objetivo

Completar la recuperacion de Fase 0 sin borrar ni reiniciar el repositorio, dejando funcional el arranque base con Docker Compose para backend, frontend, PostgreSQL, Redis, Prometheus y Grafana.

## 2. Alcance

Alcance incluido:

- Arquitectura modular monolith.
- Clouds iniciales limitados a AWS y OCI.
- Backend placeholder FastAPI.
- Frontend placeholder Next.js.
- PostgreSQL, Redis, Prometheus y Grafana en Docker Compose.
- Documentacion inicial y archivo de auditoria.

Fuera de alcance:

- Kubernetes.
- Microservices.
- Azure o GCP.
- Auto-remediation.
- Autonomous agents.
- Advanced RBAC.

## 3. Auditoria inicial

Archivos existentes encontrados:

- `docker-compose.yml`
- `.env.example`
- `Makefile`
- `README.md`
- `docs/architecture.md`
- `docs/development.md`
- `docs/audit-phase-0.md`
- `backend/Dockerfile`
- `backend/api/main.py`
- `backend/api/routes/health.py`
- `backend/requirements.txt`
- `frontend/Dockerfile`
- `frontend/package.json`
- `frontend/app/page.tsx`
- `frontend/app/layout.tsx`
- `observability/prometheus/prometheus.yml`
- `observability/grafana/provisioning/datasources/prometheus.yml`

Problemas detectados:

- `docker compose up --build -d` fallaba por conflicto del puerto host `5432`.
- Despues de corregir PostgreSQL, `docker compose up --build -d` fallaba por conflicto del puerto host `8000`.
- Prometheus apuntaba a `/metrics`, lo que generaba redireccion a `/metrics/`.
- Grafana montaba todo `/etc/grafana/provisioning`, ocultando directorios internos y generando errores por rutas de provisioning ausentes.
- `make backend-test` usaba `pytest`; dentro del contenedor el ejecutable no resolvia `api`, mientras `python -m pytest` si funcionaba.
- El frontend no tenia `.dockerignore`, por lo que `node_modules` y `.next` entraban al contexto Docker.
- `next@15.1.3` reportaba advertencia de vulnerabilidad durante `npm install`.
- `next build` fallaba escribiendo `/app/.next/trace` sobre bind mount de Windows.

## 4. Plan tecnico

Plan aplicado:

1. Mantener el repositorio y la estructura existente.
2. Cambiar solo puertos host por defecto para evitar conflictos locales comunes.
3. Mantener puertos internos de contenedores para no romper comunicacion Docker.
4. Limitar el montaje de Grafana al datasource requerido.
5. Ajustar Prometheus al path final de metricas.
6. Corregir comandos de test sin cambiar codigo de negocio.
7. Actualizar Next.js a version estable actual consultada con `npm view next version`.
8. Aislar `.next` en volumen Docker para evitar fallos de filesystem en Windows.

## 5. Arquitectura

La arquitectura queda como modular monolith:

- `backend`: FastAPI, rutas HTTP, healthchecks, configuracion, database, Redis y modulos de dominio.
- `frontend`: Next.js placeholder para dashboard inicial.
- `postgres`: base relacional local para desarrollo.
- `redis`: cache/broker local.
- `prometheus`: scraping del backend via `/metrics/`.
- `grafana`: UI de observabilidad con datasource Prometheus provisionado.

El flujo conceptual sigue siendo:

`Cloud Accounts -> Inventory Collectors -> Resource Normalization -> Findings Engine -> Risk Scoring -> AI Context Builder -> Reports & Dashboards`

## 6. Archivos creados

- `docs/audits/auditoria-fase-0.md`
- `frontend/.dockerignore`: excluye `node_modules`, `.next`, artefactos de build, coverage, logs npm/yarn/pnpm, archivos `.env*` y `.DS_Store`.
- `backend/.dockerignore`: excluye caches Python, bytecode, virtualenvs, coverage, artefactos de build, metadata egg, archivos `.env*` y `.DS_Store`.
- `frontend/package-lock.json`

## 7. Archivos modificados

- `docker-compose.yml`
- `.env.example`
- `README.md`
- `Makefile`
- `observability/prometheus/prometheus.yml`
- `frontend/package.json`
- `frontend/tsconfig.json`

## 8. Implementacion

Cambios aplicados:

- PostgreSQL host port por defecto: `5433:5432`.
- Backend host port por defecto: `8001:8000`.
- `NEXT_PUBLIC_API_BASE_URL` actualizado a `http://localhost:8001`.
- README actualizado con puertos reales.
- Prometheus usa `metrics_path: /metrics/`.
- Grafana monta solo `observability/grafana/provisioning/datasources`.
- `make backend-test` ejecuta `python -m pytest`.
- Next.js actualizado de `15.1.3` a `16.2.6`.
- `eslint-config-next` actualizado a `16.2.6`.
- `.next` aislado con volumen `frontend_next`.
- `.dockerignore` agregado en backend y frontend.

## 9. Validacion

Validaciones ejecutadas:

- `docker compose config`: OK.
- `docker compose up --build -d`: OK despues de corregir puertos.
- `docker compose ps`: backend, frontend, postgres, redis, prometheus y grafana arriba.
- `GET http://localhost:8001/health/live`: 200 OK.
- `GET http://localhost:8001/health/ready`: 200 OK.
- `GET http://localhost:8001/api/v1/platform/scope`: 200 OK.
- `GET http://localhost:3000`: 200 OK.
- `GET http://localhost:9090/-/ready`: 200 OK.
- `GET http://localhost:3001/api/health`: 200 OK.

Validacion pendiente:

- Reejecutar `docker compose run --rm --no-deps frontend npm run build` despues de agregar el volumen `frontend_next`. La solicitud de permiso para esta ejecucion fue rechazada, por lo que queda documentada como pendiente.

## 10. Pruebas

Resultados:

- `docker compose run --rm backend ruff check .`: OK.
- `docker compose run --rm backend python -m pytest`: OK, 1 test passed.
- `docker compose run --rm backend pytest`: falla por resolucion de import `api`; se corrigio el Makefile para usar `python -m pytest`.
- `docker compose run --rm --no-deps frontend npm run build`: fallo antes del volumen `frontend_next` por `/app/.next/trace`.

## 11. Seguridad

Controles actuales:

- Variables sensibles se mantienen fuera del codigo y se documentan en `.env.example`.
- Los contextos Docker de backend y frontend excluyen `.env` y `.env.*` para reducir riesgo de copiar secretos a imagenes.
- No se agregaron credenciales reales.
- CORS limitado por variable `BACKEND_CORS_ORIGINS`.
- Grafana usa credenciales locales por defecto solo para desarrollo.

Riesgos:

- `npm install` reporta 4 vulnerabilidades restantes: 2 low y 2 moderate. No se aplico `npm audit fix --force` porque puede introducir cambios breaking fuera del objetivo minimo de Fase 0.
- Grafana queda expuesto localmente con `admin/admin` si no se cambia `.env`.

## 12. Observabilidad

Estado:

- FastAPI expone metricas con `prometheus_client` en `/metrics/`.
- Prometheus scrapea `backend:8000`.
- Grafana provisiona Prometheus como datasource default.
- Los `.dockerignore` no excluyen archivos de `observability`, por lo que la configuracion de Prometheus y el datasource de Grafana siguen entrando en el contexto requerido por Compose.

Notas:

- Grafana emite mensajes internos sobre plugin `xychart` ya registrado. El healthcheck de Grafana responde OK y no se atribuye a la configuracion del proyecto.

## 13. Riesgos y trade-offs

- Se eligieron puertos host `5433` y `8001` para evitar conflictos con PostgreSQL y APIs locales ya instaladas.
- El backend sigue usando puerto interno `8000`, por lo que no cambia la red Docker.
- Se dejo el servicio `worker` existente porque ya estaba en el repositorio y no bloquea el objetivo, aunque no es obligatorio en la lista minima de Fase 0.
- Se agrego `frontend_next` para estabilidad en Windows; esto evita problemas con artefactos `.next` sobre bind mounts.
- Se excluyeron artefactos generados y caches de los contextos Docker. Esto mejora velocidad, seguridad y reproducibilidad, con el trade-off de que cualquier archivo generado que sea requerido en runtime debe declararse explicitamente en el Dockerfile.
- No se aplicaron refactors amplios ni cambios de arquitectura.

## 14. Refactorizacion recomendada

Recomendado para Fase 1 o hardening posterior:

- Separar `docker-compose.dev.yml` si se requiere distinguir dev server, worker y build productivo.
- Agregar healthcheck al frontend.
- Agregar endpoint de readiness de Prometheus/Grafana en Makefile.
- Revisar `npm audit` y actualizar dependencias frontend sin `--force` cuando sea posible.
- Decidir si `worker` pertenece a Fase 0 o debe quedar bajo profile `worker`.
- Agregar migraciones Alembic iniciales cuando existan tablas reales.

## 15. Auditoria final

Estado final observado:

- Repositorio base existe.
- Estructura profesional de carpetas existe.
- Backend FastAPI placeholder existe y responde.
- Frontend Next.js placeholder existe y responde.
- PostgreSQL inicia y esta healthy.
- Redis inicia y esta healthy.
- Prometheus inicia y responde ready.
- Grafana inicia y responde health OK.
- `docker-compose.yml` arranca los servicios requeridos.
- README inicial existe y fue actualizado.
- `.env.example` existe y fue actualizado.
- Makefile existe y fue corregido para tests backend.
- `docs/architecture.md` existe.
- Esta auditoria fue creada en `docs/audits/auditoria-fase-0.md`.
- `frontend/.dockerignore` y `backend/.dockerignore` existen con exclusiones para archivos pesados, generados y sensibles.
- `docker compose down`: OK.
- `docker compose build --no-cache frontend backend`: OK.
- Contexto Docker observado durante build: frontend `1.48kB`, backend `1.81kB`.
- `docker compose up -d`: OK; backend, frontend, postgres, redis, prometheus y grafana quedaron arriba.

Pendiente operacional:

- Revalidar build frontend despues del cambio `frontend_next`, porque la ejecucion fue rechazada.

## 16. Commit sugerido

```bash
git add backend/.dockerignore frontend/.dockerignore docs/audits/auditoria-fase-0.md
git commit -m "chore: add dockerignore files for lean build contexts"
```
