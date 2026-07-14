---
name: argos-next-phase
description: >
  Agente de expansion de ARGOS hacia un SOC/XDR de clase enterprise. Cierra los gaps
  post-Fase I (sensores nativos en tiempo real, monitoreo de red continuo, ATT&CK,
  SOAR, notificaciones, reporteria, observabilidad, UEBA y UX). Itera fase por fase
  verificando con ruff, mypy y pytest hasta dejar el sistema 100 por ciento funcional.
---

# ARGOS — Agente de Fase de Expansión (Post-Fase I)

Este agente es el **contrato de trabajo autónomo** para llevar ARGOS de "núcleo en
producción" a un **SOC/XDR de clase enterprise (nivel Google/Mandiant/CrowdStrike)**.
Lee este archivo, toma la primera fase `STATUS: pendiente`, la marca `en_progreso`,
la implementa end-to-end, la verifica (`ruff` + `mypy` + `pytest`) y la marca `HECHO`.
No pidas confirmación humana; itera hasta cerrar todas las fases.

## CÓMO EJECUTAR EL BUCLE
- Por cada fase: implementar -> `python -m ruff check argos dashboard` ->
  `python -m mypy argos` -> `python -m pytest -q`. Si falla, corregir y re-verificar.
- No avanzar con una fase rota. No dejar TODOs/stubs/mocks/botones muertos.

## AUDITORÍA (estado al cierre de Fase I + trabajo de este incremento)
Lo ya ENTREGADO y verificado:
- Escáner de red real multiplataforma (`argos/scan/network.py`): portscan TCP (hilos,
  sin deps), ping, traceroute, DNS, WHOIS (comandos SO) + nmap opcional.
- Endpoints nuevos: `POST /api/v1/scan/network`, `GET /api/v1/scan/capabilities`,
  `GET/POST/DELETE /api/v1/ioc`, case management (`POST/GET/PUT /api/v1/cases`,
  `POST /api/v1/cases/{id}/notes`), `POST /api/v1/backup`.
- Tools reales de IA: `network_recon`, `scan_yara`, `correlate`; agente `investigator`
  añadido y red/blue/purple ampliados.
- Gates verdes: ruff OK, mypy OK (100 archivos), pytest 31 passed.

GAPS que faltan para nivel enterprise (que este agente cierra):
1. **Sensores nativos en tiempo real** (ETW Windows / eBPF Linux / ESF macOS) en vez de
   polling; captura sub-segundo de proceso, archivo, red, registro. (Deferido en Fase G.)
2. **Monitoreo de red continuo** (no solo on-demand): baseline de conexiones + alerta por
   nueva conexión saliente / C2. Integrar `network_scan` en el scheduler/autonomía.
3. **Catálogo ATT&CK** expuesto (`GET /api/v1/attack`) y mapeo de técnicas a reglas.
4. **Playbooks SOAR** editables (librería CRUD) + ejecución programada/automática.
5. **Integraciones de notificación** (Webhook/Slack/Email) y endpoint de configuración.
6. **Etiquetas/asignación de alertas** y watchlist de activos/IPs críticos.
7. **Reportería** (export PDF/HTML de caso + timeline) y métricas Prometheus (`/metrics`).
8. **Enriquecimiento** GeoIP/ASN (lib opcional `maxminddb` o API) en `correlate`.
9. **UEBA / comportamiento de usuario** y kill-chain visualization en el dashboard.
10. **Persistencia de layout** del dashboard (paneles movibles) y temas (ya documentado).

## FASES (orden por dependencia)

### Fase J — Sensores nativos en tiempo real
STATUS: pendiente
- Reemplazar polling de `RealtimeCollector` por suscripción nativa cuando la plataforma
  lo permita: `agent/sources/etw.py` (Windows, pywin32/psutil), `agent/sources/ebpf.py`
  (Linux), `agent/sources/esf.py` (macOS). Mantener polling como fallback.
- `collect_processes/network/fim` alimentan el mismo `OcsfEvent`.
- Gate: tests de cada fuente nativa con fallback a polling; latencia < 1s en entorno nativo.

### Fase K — Monitoreo de red continuo + baseline
STATUS: pendiente
- `network_recon` se ejecuta en el scheduler cada N min contra hosts críticos; diff contra
  baseline de puertos/conexiones; emite evento `network`/`exfiltration` al aparecer
  conexión nueva a IP externa.
- Endpoint `GET /api/v1/network/baseline` y `POST /api/v1/network/scan/schedule`.
- Gate: test de detección de nueva conexión vs baseline.

### Fase L — ATT&CK + SOAR + notificaciones
STATUS: pendiente
- `GET /api/v1/attack` (técnicas, mapeo a reglas, cobertura).
- Playbooks CRUD (`/api/v1/playbooks`) y ejecución programada vía scheduler.
- `POST /api/v1/integrations` (webhook/slack/email) + disparo desde auditoría/alertas.
- Gate: tests de CRUD playbook e integración (mock webhook).

### Fase M — Alerts 2.0, reportería y observabilidad
STATUS: pendiente
- Etiquetas/asignación de alertas (`PUT /api/v1/alerts/{id}`), watchlist de activos.
- Export reporte de caso en HTML/PDF (`GET /api/v1/cases/{id}/report`).
- `/metrics` Prometheus (eventos/seg, alertas/seg, latencia detección).
- Gate: tests de endpoints nuevos + script de carga.

### Fase N — Enriquecimiento, UEBA y UX enterprise
STATUS: pendiente
- GeoIP/ASN en `correlate` (lib opcional); behavior analytics de usuario.
- Persistencia de layout del dashboard (paneles) y temas; kill-chain view.
- Gate: tests de serialización + smoke de UI.

## CRITERIO DE ACEPTACIÓN
- Cada fase cierra con: código funcional, ruff/mypy/pytest verdes, endpoint documentado
  en OpenAPI, y (si aplica) botón en el dashboard cableado sin acciones muertas.
- NO dejar funcionalidad a medias. El objetivo es un XDR/SOC autónomo, observable y
  auditable de extremo a extremo.
