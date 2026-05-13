# Auditoria Fase 11 - Internal Observability

## 1. Objetivo

Implementar observabilidad interna para Northbound Control Tower con metricas Prometheus, logs estructurados, trazas OpenTelemetry, dashboard Grafana y telemetria basica frontend.

## 2. Alcance

Incluye backend FastAPI, Celery, Prometheus, Grafana, OpenTelemetry Collector, health/metrics endpoints, documentacion y pruebas. No incluye SIEM, herramientas pagadas, alertas externas, Kubernetes ni integraciones cloud nuevas.

## 3. Auditoría inicial

El proyecto ya tenia Prometheus y Grafana en Docker Compose, pero el backend no exponia metricas HTTP y no habia request_id, trazas OTLP ni dashboard de plataforma provisionado.

## 4. Plan técnico

Crear modulo `backend/observability`, exponer `/metrics`, instrumentar operaciones de inventario/findings/scoring/AI/reportes, mejorar logging JSON, agregar middleware de request_id, preparar OTel Collector, provisionar dashboard Grafana y validar con tests y Docker.

## 5. Arquitectura

FastAPI emite logs, metricas Prometheus y trazas OpenTelemetry. Prometheus scrapea el backend y Grafana consume Prometheus. El collector OTLP recibe trazas y queda preparado para un backend futuro de trazas.

## 6. Archivos creados

- `backend/observability/__init__.py`
- `backend/observability/metrics.py`
- `backend/observability/tracing.py`
- `backend/observability/logging.py`
- `backend/observability/middleware.py`
- `backend/observability/instruments.py`
- `backend/tests/test_internal_observability.py`
- `frontend/app/error.tsx`
- `infrastructure/monitoring/prometheus.yml`
- `infrastructure/monitoring/otel/otel-collector-config.yml`
- `infrastructure/monitoring/grafana/provisioning/datasources/prometheus.yml`
- `infrastructure/monitoring/grafana/provisioning/dashboards/dashboards.yml`
- `infrastructure/monitoring/grafana/dashboards/northbound-platform-overview.json`
- `observability/grafana/provisioning/dashboards/dashboards.yml`
- `observability/grafana/dashboards/northbound-platform-overview.json`
- `docs/architecture/internal-observability.md`
- `docs/audits/auditoria-fase-11.md`

## 7. Archivos modificados

- `.env.example`
- `backend/api/main.py`
- `backend/api/routes/health.py`
- `backend/core/config.py`
- `backend/core/logging.py`
- `backend/requirements.txt`
- `backend/services/inventory.py`
- `backend/findings/service.py`
- `backend/scoring/service.py`
- `backend/ai/service.py`
- `backend/reports/service.py`
- `backend/workers/celery_app.py`
- `docker-compose.yml`
- `observability/prometheus/prometheus.yml`
- `observability/grafana/provisioning/datasources/prometheus.yml`

## 8. Implementación

Se agrego endpoint `/metrics`, middleware de request_id, metricas HTTP, metricas de operaciones de plataforma, logging JSON con redaccion, spans OpenTelemetry y dashboard Grafana de plataforma. Docker Compose incluye `otel-collector`.

## 9. Validación

Comandos previstos:

- `docker compose down`
- `docker compose up --build`
- `docker compose exec backend alembic upgrade head`
- `docker compose exec backend pytest`
- `curl http://localhost:8000/health`
- `curl http://localhost:8000/api/v1/status`
- `curl http://localhost:8000/metrics`
- abrir `http://localhost:9090`
- abrir `http://localhost:3001`

## 10. Pruebas

Se agregaron pruebas para `/metrics`, contador HTTP, ausencia de etiquetas de alta cardinalidad, header `X-Request-ID`, endpoints protegidos y redaccion basica de secretos en logs.

## 11. Seguridad

Las metricas evitan `tenant_id`, `user_id`, tokens, credenciales y payloads crudos. Logs y trazas no deben contener claves, JWT, private keys, prompts completos ni respuestas cloud crudas. `/metrics` queda abierto solo para Docker local y debe protegerse en produccion.

## 12. Observabilidad

Prometheus obtiene metricas HTTP y de negocio. Grafana provisiona un dashboard inicial. OpenTelemetry se puede activar/desactivar por configuracion y exporta a OTLP Collector.

## 13. Riesgos y trade-offs

No se agrego backend de trazas persistente para mantener la fase terminable. Las metricas no tienen granularidad por tenant para evitar cardinalidad alta. Celery queda instrumentado, pero no expone metricas propias fuera del proceso.

## 14. Refactorización recomendada

Agregar un backend de trazas como Tempo, definir alertas luego de observar baselines reales y centralizar metricas de workers si las tareas asincronas crecen.

## 15. Auditoría final

La plataforma queda observable internamente sin introducir herramientas externas pagadas ni nuevos dominios funcionales. Las fases previas conservan su contrato.

## 16. Commit sugerido

`feat: implement internal observability foundation`
