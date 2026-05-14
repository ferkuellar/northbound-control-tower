# Iniciar NORTHBOUND CONTROL TOWER para demo

Guía rápida para clonar el repositorio y levantar la plataforma localmente para una demostración con cliente.

## 1. Prerrequisitos

Instala y verifica:

- Git
- Docker Desktop
- Docker Compose
- Node.js 22 o superior, solo si quieres correr frontend fuera de Docker
- Python 3.12, solo si quieres correr backend fuera de Docker

Verifica Docker:

```powershell
docker --version
docker compose version
```

## 2. Clonar el repositorio

```powershell
git clone <URL_DEL_REPOSITORIO>
cd northbound-control-tower
```

## 3. Crear archivo de entorno

Copia el ejemplo:

```powershell
Copy-Item .env.example .env
```

Revisa `.env` y confirma como mínimo:

```env
POSTGRES_DB=northbound
POSTGRES_USER=northbound
POSTGRES_PASSWORD=northbound

JWT_SECRET_KEY=change-this-local-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
AI_PROVIDER=none
```

Para una demo local, no agregues credenciales reales de AWS, OCI, OpenAI, Claude o DeepSeek salvo que sean necesarias y seguras.

## 4. Levantar la plataforma

```powershell
docker compose down
docker compose up --build -d
```

Verifica contenedores:

```powershell
docker compose ps
```

Servicios esperados:

- `backend`
- `frontend`
- `postgres`
- `redis`
- `worker`
- `prometheus`
- `grafana`
- `otel-collector`

## 5. Aplicar migraciones

```powershell
docker compose exec backend alembic upgrade head
```

## 6. Validar salud del backend

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/status
```

Respuestas esperadas:

```json
{"status":"ok"}
```

y:

```json
{
  "success": true,
  "service": "backend"
}
```

## 7. Crear usuario administrador inicial

Si la base de datos está vacía, crea el primer tenant y usuario admin:

```powershell
curl -X POST http://localhost:8000/api/v1/auth/bootstrap `
  -H "Content-Type: application/json" `
  -d "{\"tenant\":{\"name\":\"Northbound Demo\",\"slug\":\"northbound-demo\"},\"user\":{\"email\":\"admin@northbound.local\",\"full_name\":\"Northbound Admin\",\"password\":\"ChangeMe123!\",\"role\":\"ADMIN\"}}"
```

Credenciales demo:

```text
Email: admin@northbound.local
Password: ChangeMe123!
```

Si el endpoint responde que ya existen usuarios, usa el admin existente.

## 8. Acceder al frontend

Abre:

```text
http://localhost:3000/login
```

Inicia sesión con:

```text
admin@northbound.local
ChangeMe123!
```

Después abre:

```text
http://localhost:3000/dashboard
```

## 9. Cargar demo Clara Fintech

Desde el frontend:

1. Entra a `Clients`.
2. Presiona `Seed Clara Demo`.
3. Abre el cliente `Clara Fintech`.
4. Entra a `Cost View`.

También puedes usar API:

```powershell
$login = curl -s -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"admin@northbound.local\",\"password\":\"ChangeMe123!\"}" | ConvertFrom-Json

$token = $login.access_token

curl -X POST http://localhost:8000/api/v1/cost-optimization/demo/clara `
  -H "Authorization: Bearer $token"
```

La demo Clara incluye:

- Cliente Clara Fintech
- AWS Production cloud account
- Inventario normalizado de ejemplo
- Findings FinOps y governance
- Scores determinísticos
- Breakdown de gasto mensual AWS
- Recomendaciones de optimización
- Export CSV de modelo de costos

## 10. Flujo recomendado para demo con cliente

1. Mostrar login.
2. Entrar al dashboard ejecutivo.
3. Explicar selector de cliente y cloud account.
4. Abrir `Clients`.
5. Mostrar Clara Fintech.
6. Abrir `Cost View`.
7. Mostrar gasto mensual actual.
8. Mostrar recomendaciones y ahorro estimado.
9. Descargar `Cost Model CSV`.
10. Generar `Executive Report`.
11. Previsualizar o descargar PDF.
12. Mostrar observabilidad:

```text
http://localhost:3001
http://localhost:9090
```

## 11. URLs útiles

```text
Frontend:      http://localhost:3000
Login:         http://localhost:3000/login
Dashboard:     http://localhost:3000/dashboard
Backend API:   http://localhost:8000
Health:        http://localhost:8000/health
API Status:    http://localhost:8000/api/v1/status
Prometheus:    http://localhost:9090
Grafana:       http://localhost:3001
```

## 12. Comandos de validación

Backend tests:

```powershell
docker compose exec backend pytest
```

Frontend lint/build:

```powershell
cd frontend
npm run lint
npm run build
cd ..
```

Logs:

```powershell
docker compose logs -f backend
docker compose logs -f frontend
```

## 13. Apagar la plataforma

```powershell
docker compose down
```

Si quieres borrar volúmenes y datos locales:

```powershell
docker compose down -v
```

Usa `-v` solo si quieres reiniciar la demo desde cero.

## 14. Notas de seguridad para demo

- No uses credenciales cloud reales en demos públicas.
- No compartas `.env`.
- Cambia `JWT_SECRET_KEY` antes de ambientes compartidos.
- La contraseña `ChangeMe123!` es solo para demo local.
- Las recomendaciones de Clara son estimaciones basadas en datos de prueba, no precios exactos de AWS.

## 15. Problemas comunes

### El backend no responde

```powershell
docker compose ps
docker compose logs backend
```

### Las migraciones fallan

```powershell
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

### El frontend no conecta al backend

Verifica en `.env`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Luego reconstruye:

```powershell
docker compose up --build -d frontend
```

### Puerto ocupado

Revisa si están ocupados:

- `3000`
- `8000`
- `5433`
- `6379`
- `9090`
- `3001`

Puedes detener servicios previos con:

```powershell
docker compose down
```
