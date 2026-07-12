---
título: 15 - Persistencia
objetivo: Documentar el almacenamiento persistente del sistema según la documentación base.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 2,6,7,10; Docs/KiloGateway 02.
dependencias: 04-Arquitectura.md; 14-Logging.md.
referencias: 11-Gestion-Configuracion.md.
---

# 15 - Persistencia

La documentación base **sí especifica** mecanismos de persistencia. Se documentan a continuación.

## 1. Almacenamiento de eventos (componente D)

- **OpenSearch** (fork libre de Elasticsearch, Apache 2.0): cubre búsqueda full-text (investigación ad-hoc) y series temporales (dashboards/anomalías).
- **ClickHouse**: más eficiente para eventos de alto volumen si el volumen crece mucho.
- Patrones de acceso requeridos: full-text + series temporales.

## 2. Vector store (capa de IA)

- **Qdrant** o **Chroma** (Apache 2.0): guarda resúmenes + embeddings de eventos crudos para RAG/consulta semántica.

## 3. Buffer local del agente (transporte)

- **SQLite embebido** (sugerido): el agente bufferea eventos localmente si se cae la conexión y reenvía al reconectar.

## 4. Log de auditoría inmutable

- Append-only con **hash-chaining estilo Merkle**: persiste cada acción propuesta/aprobada/ejecutada (quién propuso, quién aprobó, timestamp, resultado). Detecta tampering.

## 5. Baseline de comportamiento

- Se mantiene un baseline contra el cual se diffean periódicamente la persistencia (ej. Run keys, launchd, servicios) para detectar anomalías.

## 6. Retención

- Mínimo **90 días en caliente** para investigación activa; más tiempo en frío para forense posterior (sección 10).

## 7. Orquestación de la persistencia

- Collector (Vector.dev/Fluent Bit) normaliza a OCSF y enruta a almacenamiento.

> **Información no especificada en la documentación original.** No se especifican esquemas exactos de tablas/índices, conexiones, credenciales de la base, ni política de backup/restore.
