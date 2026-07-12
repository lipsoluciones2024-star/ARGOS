---
título: 00 - Índice Maestro
objetivo: Índice navegable de toda la documentación técnica generada para ARGOS.
alcance: Conjunto de 31 documentos derivados de `ARGOS_documento_maestro_arquitectura.md` y `Docs/KiloGateway/01-04`, más la extensión híbrida (Opción C) decidida por el usuario.
dependencias: Todos los documentos listados.
referencias: 01-Resumen-Ejecutivo.md.
---

# 00 - Índice Maestro — Documentación Técnica ARGOS

> Documentación generada a partir de la documentación base del repositorio, bajo las restricciones de `AGENTS.md` (no inventar, no asumir, no rediseñar). Lo no especificado se marca como **Información no especificada en la documentación original**.

## Documentos

| # | Documento | Enlace |
|---|---|---|
| 00 | Índice Maestro | [00-Indice-Maestro.md](00-Indice-Maestro.md) |
| 01 | Resumen Ejecutivo | [01-Resumen-Ejecutivo.md](01-Resumen-Ejecutivo.md) |
| 02 | Requisitos Funcionales | [02-Requisitos-Funcionales.md](02-Requisitos-Funcionales.md) |
| 03 | Requisitos No Funcionales | [03-Requisitos-No-Funcionales.md](03-Requisitos-No-Funcionales.md) |
| 04 | Arquitectura | [04-Arquitectura.md](04-Arquitectura.md) |
| 05 | Arquitectura de Carpetas | [05-Arquitectura-Carpetas.md](05-Arquitectura-Carpetas.md) |
| 06 | Arquitectura del Código | [06-Arquitectura-Codigo.md](06-Arquitectura-Codigo.md) |
| 07 | Flujo General del Sistema | [07-Flujo-General.md](07-Flujo-General.md) |
| 08 | API Gateway | [08-API-Gateway.md](08-API-Gateway.md) |
| 09 | Integración con IA | [09-Integracion-IA.md](09-Integracion-IA.md) |
| 10 | Configuración Local | [10-Configuracion-Local.md](10-Configuracion-Local.md) |
| 11 | Gestión de Configuración | [11-Gestion-Configuracion.md](11-Gestion-Configuracion.md) |
| 12 | Seguridad | [12-Seguridad.md](12-Seguridad.md) |
| 13 | Manejo de Errores | [13-Manejo-Errores.md](13-Manejo-Errores.md) |
| 14 | Logging | [14-Logging.md](14-Logging.md) |
| 15 | Persistencia | [15-Persistencia.md](15-Persistencia.md) |
| 16 | Estados del Sistema | [16-Estados-Sistema.md](16-Estados-Sistema.md) |
| 17 | Diagramas | [17-Diagramas.md](17-Diagramas.md) |
| 18 | Casos de Uso | [18-Casos-Uso.md](18-Casos-Uso.md) |
| 19 | Casos de Error | [19-Casos-Error.md](19-Casos-Error.md) |
| 20 | Convenciones | [20-Convenciones.md](20-Convenciones.md) |
| 21 | Dependencias | [21-Dependencias.md](21-Dependencias.md) |
| 22 | Checklist de Desarrollo | [22-Checklist-Desarrollo.md](22-Checklist-Desarrollo.md) |
| 23 | Checklist de Validación | [23-Checklist-Validacion.md](23-Checklist-Validacion.md) |
| 24 | Glosario Técnico | [24-Glosario.md](24-Glosario.md) |
| 25 | Historias de Usuario | [25-Historias-de-Usuario.md](25-Historias-de-Usuario.md) |
| 26 | Criterios de Aceptación | [26-Criterios-de-Aceptacion.md](26-Criterios-de-Aceptacion.md) |
| 27 | Flujos de Datos y Contratos | [27-Flujos-de-Datos.md](27-Flujos-de-Datos.md) |
| 28 | Especificación de Diseño por Módulo | [28-Especificacion-Diseno-Modulos.md](28-Especificacion-Diseno-Modulos.md) |
| 29 | Arquitectura IA Híbrida (API Gateway + Local) | [29-Arquitectura-IA-Hibrida.md](29-Arquitectura-IA-Hibrida.md) |
| 30 | Descarga y Ejecución del Modelo Local (Qwen2.5-0.5B GGUF) | [30-Descarga-Modelo-Local-Qwen25.md](30-Descarga-Modelo-Local-Qwen25.md) |

## Mapa de dependencias entre documentos

- **Núcleo:** 01 → 04 → 17 (diagramas) y 07 (flujos).
- **Requisitos:** 02 (funcionales) y 03 (no funcionales) derivan de 01.
- **Externo:** 08 (API Gateway) y 09 (Integración IA) son la única salida externa.
- **Implementación:** 05, 06, 10, 11, 21 preparan el desarrollo; 22 y 23 son checklists.
- **Calidad:** 12 (seguridad), 13 (errores), 14 (logging), 15 (persistencia), 16 (estados), 18/19 (casos), 20 (convenciones), 24 (glosario).
- **Desarrollo granular:** 25 (historias de usuario), 26 (criterios de aceptación), 27 (flujos de datos), 28 (especificación de diseño por módulo — qué debe ir en el código).
- **IA Híbrida (Opción C, 2026-07-11):** 29 (arquitectura híbrida API Gateway + modelo local GGUF) y 30 (descarga/ejecución del modelo local Qwen2.5-0.5B-Instruct-GGUF). Modifica también 04, 06, 08, 09, 12, 17, 21, 27, 28, 10.

## Notas de auditoría

- **Conflicto de fuentes resuelto:** Doc 3 vs Doc 4 sobre `mayTrainOnYourPrompts`. Se adopta la posición verificada en vivo de **Doc 4**: todos los 11 `:free` entrenan con prompts. Doc 3 queda desestimado para ese punto.
- **Sin información inventada:** todos los datos provienen de los 5 archivos base.
- **Huecos documentados:** se marcaron como "Información no especificada" los elementos no presentes en la base (lenguaje obligatorio, clases, build/run, apagado, esquemas de BD, etc.).
- **Extensión híbrida (Opción C):** el usuario decidió (2026-07-11) combinar API Gateway con un modelo local GGUF (Qwen2.5-0.5B-Instruct-GGUF). Esto extiende el doc base (que decía "solo API Gateway") y se documenta en 29/30; lo no especificado en el doc base se marca como "decisión de implementación híbrida".
