# Auditoria Branding Dashboard Northbound

## 1. Objetivo

Aplicar la identidad visual dark enterprise de Northbound Control Tower al dashboard ejecutivo usando el logo oficial y la paleta gris/negra definida.

## 2. Alcance

Cambios limitados al frontend visual: tema Tailwind, estilos globales, componentes de layout, login, tarjetas, tablas, estados vacios/error y graficas. No se cambiaron APIs, modelos, reglas de negocio ni integraciones backend.

## 3. Archivos modificados

- `frontend/public/brand/logo-northbound.png`
- `frontend/tailwind.config.ts`
- `frontend/app/globals.css`
- `frontend/app/login/page.tsx`
- `frontend/app/error.tsx`
- `frontend/components/layout/DashboardShell.tsx`
- `frontend/components/ui/Button.tsx`
- `frontend/components/ui/Card.tsx`
- `frontend/components/ui/Input.tsx`
- `frontend/components/ui/Select.tsx`
- `frontend/components/ui/Badge.tsx`
- `frontend/components/ui/EmptyState.tsx`
- `frontend/components/dashboard/ExecutiveDashboard.tsx`
- `frontend/components/dashboard/MetricCard.tsx`
- `frontend/components/dashboard/ChartPanel.tsx`
- `frontend/components/scores/ScoreCharts.tsx`
- `frontend/components/findings/FindingsTable.tsx`
- `frontend/components/resources/InventoryTable.tsx`

## 4. Paleta aplicada

Se agrego el namespace `northbound` en Tailwind:

- `black100`: `#0A0E15`
- `black90`: `#212631`
- `black80`: `#373F4E`
- `black70`: `#4E576A`
- `black60`: `#667085`
- `white100`: `#FFFFFF`
- `white90`: `#F0F1F5`
- `white80`: `#E0E4EB`
- `white70`: `#D1D6E0`
- `white60`: `#BFC6D4`

El dashboard usa `#0A0E15` como fondo principal, `#212631` para paneles, `#373F4E` para bordes y texto blanco/gris claro para jerarquia visual.

## 5. Logo integrado

El logo oficial fue copiado a `frontend/public/brand/logo-northbound.png` y se usa con `next/image` y `object-contain` en:

- Login desktop
- Login mobile
- Sidebar desktop
- Header mobile

No se estira ni deforma la imagen.

## 6. Validacion

Validaciones requeridas:

- `npm run lint`
- `npm run build`
- `docker compose up --build`
- Abrir `http://localhost:3000`
- Verificar login y dashboard en tema dark Northbound
- Verificar que no queden tarjetas blancas en el dashboard principal

## 7. Riesgos

- El almacenamiento de token del MVP sigue siendo localStorage por diseno de Fase 8; debe migrarse a cookies httpOnly en produccion.
- Las graficas dependen de ECharts en cliente; si no hay datos, se mantienen estados vacios.
- Report branding backend ya soporta `logo_url`, pero esta actualizacion no cambia el flujo de reportes para evitar acoplarlo al frontend static path.

## 8. Auditoria final

La identidad visual queda alineada con un SaaS enterprise oscuro, metalico y sobrio. Se conservaron colores operativos para severidad, se eliminaron clases claras heredadas del dashboard principal y se mantuvo contraste alto para lectura y foco.

## 9. Commit sugerido

`style: apply northbound dark brand system to executive dashboard`
