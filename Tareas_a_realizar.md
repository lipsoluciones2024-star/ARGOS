# Prompt para Auditoría, Rediseño UX/UI y Dashboard Profesional

Analiza el proyecto completo (frontend, backend y base de datos) y realiza una propuesta de rediseño profesional **sin romper la arquitectura existente**. El objetivo es transformar la aplicación en una plataforma de nivel Enterprise similar a herramientas como Cloudflare Dashboard, Grafana, Kibana, Datadog, Azure Portal o AWS Console.

## 1. Análisis completo

Analiza absolutamente todo el proyecto:

* Todos los endpoints.
* Todas las APIs.
* Todos los módulos.
* Todas las páginas.
* Todos los componentes.
* Todas las rutas.
* Todos los layouts.
* Estados globales.
* Hooks.
* Middleware.
* Autenticación.
* Permisos.
* Navegación.
* Responsive Design.
* Accesibilidad.
* Rendimiento.
* UX.
* UI.

Detecta:

* Pantallas innecesarias.
* Componentes repetidos.
* Componentes reutilizables.
* Código duplicado.
* Mejoras de navegación.
* Mejoras visuales.
* Mejoras de experiencia de usuario.

---

# 2. Reorganizar por módulos

Reorganiza toda la aplicación por módulos.

Ejemplo:

## Dashboard

* Overview
* Estado general
* KPIs
* Métricas

---

## Agentes IA

* Lista
* Estado
* Configuración
* Crear
* Editar
* Logs
* Ejecuciones

---

## Automatizaciones

* Reglas
* Tareas
* Scheduler
* Triggers
* Historial

---

## Seguridad

* Alertas
* Eventos
* Amenazas
* Auditoría
* Reglas
* Firewall

---

## Monitoreo

* CPU
* RAM
* Requests
* Latencia
* Workers
* Procesos
* Eventos

---

## Configuración

* Variables
* API Keys
* Integraciones
* Usuarios
* Roles
* Permisos

---

# 3. Analizar todos los Endpoints

Para cada endpoint generar:

* descripción
* propósito
* método HTTP
* parámetros
* respuestas
* errores
* permisos
* frecuencia de uso
* qué pantalla lo utiliza
* qué componente lo consume

Si existen endpoints redundantes:

* fusionarlos
* simplificarlos
* reutilizarlos

---

# 4. Dashboard profesional

Rediseñar completamente el Dashboard.

Inspirarse en:

* Cloudflare
* Grafana
* Kibana
* Datadog
* Azure
* Google Cloud
* AWS Console

Debe verse extremadamente profesional.

Debe tener múltiples paneles.

Muchos widgets.

Muchos indicadores.

Muchos gráficos.

Muchos estados.

Muchos paneles laterales.

Muchos filtros.

Muchos accesos rápidos.

Muchos menús.

---

# 5. Layout estilo Cloud

Crear un layout moderno tipo plataforma Cloud.

Debe incluir:

* Sidebar izquierdo.
* Header superior.
* Panel derecho opcional.
* Breadcrumb.
* Barra de búsqueda global.
* Quick Actions.
* Notificaciones.
* Perfil.
* Estado del sistema.
* Selector de tema.
* Selector de idioma.
* Atajos.

Debe soportar:

* Expandir Sidebar.
* Contraer Sidebar.
* Paneles flotantes.
* Tabs.
* Cards.
* Modales.
* Drawers.
* Popups.

---

# 6. Muchísimas opciones visuales

Agregar una gran cantidad de controles profesionales:

* Dropdowns
* Selectores
* Toggles
* Switches
* Radio Buttons
* Checkboxes
* Tabs
* Acordeones
* Menús contextuales
* Tooltips
* Badges
* Chips
* Tags
* Filtros
* Buscadores
* Paginación
* Ordenamiento
* Favoritos
* Quick Actions

Todo debe ser consistente.

---

# 7. Botones de Control Global

Todo proceso ejecutable del sistema debe poder controlarse.

Agregar botones estándar en todos los módulos donde corresponda:

* ▶ Play
* ⏸ Pause
* ⏹ Stop
* 🔄 Restart
* 🔁 Retry
* ▶ Resume
* ❌ Cancel
* 🗑 Clear
* 📥 Export
* 📤 Import
* ⬇ Download
* ⬆ Upload
* 💾 Save
* ⚙ Configure

Todos deben compartir el mismo diseño.

---

# 8. Sistema de Logs

Implementar un sistema de logs profesional.

Mostrar:

* Logs del sistema
* Logs de IA
* Logs API
* Logs Workers
* Logs Scheduler
* Logs Seguridad
* Logs Usuarios
* Logs Errores
* Logs Auditoría
* Logs Base de Datos
* Logs Automatizaciones

Cada log debe incluir:

* Timestamp
* Severidad
* Usuario
* Módulo
* Acción
* Duración
* Estado
* Metadata
* Trace ID
* Correlation ID

---

# 9. Eventos en Tiempo Real

Toda la actividad del sistema debe visualizarse en tiempo real.

Mostrar:

* Requests
* Respuestas
* Eventos
* Procesos
* Jobs
* IA
* Workers
* Colas
* Scheduler
* Alertas
* Errores
* Cambios

Actualizar automáticamente sin recargar la página.

---

# 10. Mini Monitores

En lugar de listas de texto, representar la información mediante mini gráficos continuos.

Agregar la mayor cantidad posible de pequeños paneles de monitoreo.

Ejemplos:

* CPU
* RAM
* Requests
* Latencia
* Eventos
* Procesos
* IA
* API
* Workers
* Scheduler
* Base de Datos
* Cache
* Cola
* Tokens
* Errores
* Advertencias

Cada uno debe mostrarse como un gráfico de línea continuo, simulando monitores de actividad.

Mientras más indicadores y paneles existan, mejor.

---

# 11. Visualizaciones

Utilizar distintos tipos de gráficos:

* Líneas
* Área
* Barras
* Donut
* Gauge
* Radar
* Heatmap
* Timeline
* Sparklines
* Histogramas
* Estados
* KPIs
* Contadores

Todos deben actualizarse dinámicamente.

---

# 12. UX Profesional

Mejorar completamente la experiencia del usuario.

Reducir clics innecesarios.

Optimizar los flujos.

Agregar:

* Skeleton Loaders
* Estados Vacíos
* Loading Inteligente
* Confirmaciones
* Toasts
* Atajos de teclado
* Ayudas Contextuales
* Tooltips
* Animaciones suaves

---

# 13. UI Profesional

Mantener un diseño moderno.

Oscuro.

Minimalista.

Tecnológico.

Inspirado en plataformas Cloud.

Con excelente jerarquía visual.

Tipografía consistente.

Espaciado uniforme.

Componentes reutilizables.

Diseño limpio.

---

# 14. Imagen de Fondo

Utilizar como fondo principal la imagen existente dentro de la carpeta:

assets/

Debe integrarse con el Dashboard mediante capas, desenfoques, transparencias y efectos para no afectar la legibilidad y el rendimiento por sobre todo.

---

# 15. Componentes Reutilizables

Crear componentes reutilizables para:

* Tarjetas
* Paneles
* Gráficos
* Logs
* Eventos
* Botones
* Tablas
* Formularios
* Modales
* Paneles laterales
* Indicadores
* Estados
* Alertas
* Monitores

---

# 16. Resultado esperado

El resultado final debe ser una plataforma Enterprise de monitoreo y automatización con apariencia de centro de operaciones (NOC/SOC), altamente modular, escalable y profesional, donde todas las páginas estén organizadas por módulos, exista un monitoreo visual continuo mediante gráficos de series temporales, controles universales (Play/Pause/Stop y acciones relacionadas), un sistema completo de logs y eventos en tiempo real, abundantes opciones de configuración y navegación, y una experiencia UX/UI comparable a las principales consolas Cloud del mercado.
