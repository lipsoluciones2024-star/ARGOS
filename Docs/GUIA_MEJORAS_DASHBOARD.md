# GUÍA DE MEJORAS: Dashboard Enterprise Nivel XAI

**Versión:** 1.0  
**Fecha:** 2026-07-16  
**Objetivo:** Transformar el dashboard actual de ARGOS a una interfaz enterprise nivel Grafana/Datadog inspirada en patrones de UI de grok-build

---

## 1. VISIÓN GENERAL

### 1.1 Estado Actual
ARGOS tiene un dashboard básico en Vanilla JS con:
- SPA simple con vistas estáticas
- Componentes no reutilizables
- Sin sistema de layouts
- Sin personalización
- Monitoreo básico
- Sin analytics avanzados

### 1.2 Estado Objetivo
Dashboard enterprise con:
- Sistema de componentes reutilizables
- Layouts configurables y persistentes
- Paneles movibles (drag & drop)
- Sistema de temas (dark/light/custom)
- Atajos de teclado globales
- Búsqueda global instantánea
- Real-time monitoring con sparklines
- Advanced analytics con múltiples chart types
- Responsive design mobile-first

### 1.3 Inspiración
- **Grafana:** Dashboards configurables, paneles movibles
- **Datadog:** UI moderna, analytics avanzados
- **Kibana:** Búsqueda global, visualizaciones ricas
- **grok-build TUI:** Componentes modulares, layouts flexibles

---

## 2. ARQUITECTURA FRONTEND

### 2.1 Estructura de Directorios

```
dashboard/
├── index.html                   # Entry point
├── css/
│   ├── variables.css             # CSS variables (theming)
│   ├── components.css            # Component styles
│   ├── layouts.css              # Layout styles
│   ├── utilities.css            # Utility classes
│   └── themes/
│       ├── dark.css             # Dark theme
│       ├── light.css            # Light theme
│       └── custom.css           # Custom theme
├── js/
│   ├── app.js                   # Main application
│   ├── router.js                # Client-side router
│   ├── store.js                 # State management
│   ├── components/
│   │   ├── base.js              # Base component class
│   │   ├── panels/
│   │   │   ├── monitoring.js    # Real-time monitoring
│   │   │   ├── analytics.js     # Analytics engine
│   │   │   ├── configuration.js # Config panel
│   │   │   ├── security.js      # Security panel
│   │   │   └── admin.js         # Admin console
│   │   ├── charts/
│   │   │   ├── line.js          # Line charts
│   │   │   ├── bar.js           # Bar charts
│   │   │   ├── donut.js         # Donut charts
│   │   │   ├── gauge.js         # Gauge charts
│   │   │   ├── heatmap.js        # Heatmap charts
│   │   │   └── sparkline.js    # Sparklines
│   │   ├── ui/
│   │   │   ├── modal.js         # Modal component
│   │   │   ├── drawer.js        # Drawer component
│   │   │   ├── tabs.js          # Tabs component
│   │   │   ├── table.js         # Table component
│   │   │   ├── dropdown.js      # Dropdown component
│   │   │   ├── search.js        # Search component
│   │   │   └── notification.js  # Notification component
│   │   └── layout/
│   │       ├── sidebar.js       # Sidebar
│   │       ├── header.js        # Header
│   │       ├── grid.js          # Grid layout
│   │       └── breadcrumbs.js   # Breadcrumbs
│   ├── services/
│   │   ├── api.js               # API client
│   │   ├── websocket.js         # WebSocket client
│   │   ├── sse.js               # SSE client
│   │   └── cache.js             # Cache service
│   └── utils/
│       ├── formatting.js        # Formatting utilities
│       ├── validation.js        # Validation utilities
│       ├── performance.js       # Performance utilities
│       └── keyboard.js         # Keyboard shortcuts
└── assets/
    ├── images/
    │   └── background.jpg       # Background image
    └── fonts/
        └── icons/               # Icon fonts
```

### 2.2 Stack Tecnológico

```yaml
Core: Vanilla ES6+ (sin frameworks pesados)
UI Library: Component System custom
Charts: Chart.js + D3.js (advanced visualizations)
Real-time: WebSocket + SSE
State Management: Custom store con pub/sub
Build: Vite (optimización)
Icons: Lucide (icon library ligero)
Fonts: Inter (Google Fonts)
```

---

## 3. SISTEMA DE COMPONENTES

### 3.1 Base Component Class

```javascript
// js/components/base.js
class BaseComponent {
    constructor(element, props = {}) {
        this.element = element;
        this.props = props;
        this.state = {};
        this.subscriptions = [];
        this.destroyed = false;
    }

    setState(newState) {
        if (this.destroyed) return;
        
        this.state = { ...this.state, ...newState };
        this.render();
    }

    subscribe(store, callback) {
        if (this.destroyed) return;
        
        const unsubscribe = store.subscribe(callback);
        this.subscriptions.push(unsubscribe);
    }

    render() {
        // Override in subclasses
    }

    destroy() {
        this.destroyed = true;
        this.subscriptions.forEach(unsub => unsub());
    }

    onMount() {
        // Override in subclasses
    }

    onUnmount() {
        // Override in subclasses
    }
}
```

### 3.2 Componentes de Paneles

#### Monitoring Panel

```javascript
// js/components/panels/monitoring.js
class MonitoringPanel extends BaseComponent {
    constructor(element, props) {
        super(element, props);
        this.charts = {};
        this.websocket = null;
        this.metrics = {};
        this.init();
    }

    init() {
        this.setupCharts();
        this.connectWebSocket();
        this.startRealTimeUpdates();
        this.setupKeyboardShortcuts();
    }

    setupCharts() {
        // Sparklines para métricas en tiempo real
        this.charts.cpu = new SparklineChart('#cpu-chart', {
            color: '#00ff00',
            maxPoints: 60,
            height: 50
        });
        
        this.charts.memory = new SparklineChart('#memory-chart', {
            color: '#0088ff',
            maxPoints: 60,
            height: 50
        });
        
        this.charts.network = new SparklineChart('#network-chart', {
            color: '#ff8800',
            maxPoints: 60,
            height: 50
        });
        
        this.charts.events = new SparklineChart('#events-chart', {
            color: '#ff0088',
            maxPoints: 60,
            height: 50
        });
    }

    connectWebSocket() {
        this.websocket = new WebSocket('ws://localhost:8000/ws');
        
        this.websocket.onopen = () => {
            console.log('WebSocket connected');
        };
        
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleRealTimeData(data);
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket disconnected, reconnecting in 5s...');
            setTimeout(() => this.connectWebSocket(), 5000);
        };
    }

    handleRealTimeData(data) {
        if (data.type === 'metrics') {
            this.updateMetrics(data.metrics);
        } else if (data.type === 'alert') {
            this.showAlert(data.alert);
        } else if (data.type === 'event') {
            this.updateEventCount(data.count);
        }
    }

    updateMetrics(metrics) {
        // Actualizar sparklines
        this.charts.cpu.push(metrics.cpu);
        this.charts.memory.push(metrics.memory);
        this.charts.network.push(metrics.network);
        this.charts.events.push(metrics.events_per_sec);
        
        // Actualizar valores numéricos
        this.updateMetricValue('cpu-value', metrics.cpu);
        this.updateMetricValue('memory-value', metrics.memory);
        this.updateMetricValue('network-value', metrics.network);
        this.updateMetricValue('events-value', metrics.events_per_sec);
    }

    updateMetricValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value.toFixed(1);
        }
    }

    showAlert(alert) {
        const notification = document.createElement('div');
        notification.className = 'alert-notification';
        notification.innerHTML = `
            <div class="alert-content">
                <span class="alert-severity ${alert.severity}">${alert.severity.toUpperCase()}</span>
                <span class="alert-message">${alert.message}</span>
                <span class="alert-time">${new Date(alert.time).toLocaleTimeString()}</span>
            </div>
        `;
        
        document.getElementById('notifications-container').appendChild(notification);
        
        // Auto-remove después de 10 segundos
        setTimeout(() => notification.remove(), 10000);
    }

    startRealTimeUpdates() {
        // Actualizar cada segundo
        setInterval(() => {
            this.fetchMetrics();
        }, 1000);
    }

    async fetchMetrics() {
        try {
            const response = await fetch('/api/v1/metrics');
            const metrics = await response.json();
            this.updateMetrics(metrics);
        } catch (error) {
            console.error('Error fetching metrics:', error);
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+M: Toggle monitoring panel
            if (e.ctrlKey && e.key === 'm') {
                e.preventDefault();
                this.toggle();
            }
        });
    }

    toggle() {
        this.element.classList.toggle('collapsed');
    }

    render() {
        this.element.innerHTML = `
            <div class="monitoring-panel">
                <div class="panel-header">
                    <h2>Real-time Monitoring</h2>
                    <div class="panel-controls">
                        <button class="btn-icon" onclick="this.closest('.monitoring-panel').classList.toggle('collapsed')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="18 15 12 9 6 15"></polyline>
                            </svg>
                        </button>
                    </div>
                </div>
                
                <div class="panel-content">
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">CPU</div>
                            <div class="metric-value" id="cpu-value">0.0</div>
                            <div class="metric-chart" id="cpu-chart"></div>
                        </div>
                        
                        <div class="metric-card">
                            <div class="metric-label">Memory</div>
                            <div class="metric-value" id="memory-value">0.0</div>
                            <div class="metric-chart" id="memory-chart"></div>
                        </div>
                        
                        <div class="metric-card">
                            <div class="metric-label">Network</div>
                            <div class="metric-value" id="network-value">0.0</div>
                            <div class="metric-chart" id="network-chart"></div>
                        </div>
                        
                        <div class="metric-card">
                            <div class="metric-label">Events/sec</div>
                            <div class="metric-value" id="events-value">0.0</div>
                            <div class="metric-chart" id="events-chart"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Re-inicializar charts después del render
        this.setupCharts();
    }

    destroy() {
        super.destroy();
        if (this.websocket) {
            this.websocket.close();
        }
        Object.values(this.charts).forEach(chart => chart.destroy());
    }
}
```

#### Analytics Panel

```javascript
// js/components/panels/analytics.js
class AnalyticsPanel extends BaseComponent {
    constructor(element, props) {
        super(element, props);
        this.charts = {};
        this.filters = {};
        this.init();
    }

    init() {
        this.setupCharts();
        this.setupFilters();
        this.loadData();
    }

    setupCharts() {
        // Line chart para timeline de eventos
        this.charts.timeline = new LineChart('#timeline-chart', {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Events',
                    data: [],
                    borderColor: '#0088ff',
                    backgroundColor: 'rgba(0, 136, 255, 0.1)',
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour'
                        }
                    }
                }
            }
        });

        // Bar chart para distribución por severidad
        this.charts.severity = new BarChart('#severity-chart', {
            type: 'bar',
            data: {
                labels: ['Low', 'Medium', 'High', 'Critical'],
                datasets: [{
                    label: 'Events',
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#00ff00', '#ffff00', '#ff8800', '#ff0000']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });

        // Donut chart para distribución por categoría
        this.charts.category = new DonutChart('#category-chart', {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#0088ff', '#00ff00', '#ff8800', '#ff0088',
                        '#8800ff', '#ff00ff', '#00ffff', '#ffff00'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });

        // Heatmap para patrones temporales
        this.charts.heatmap = new HeatmapChart('#heatmap-chart', {
            data: [],
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    setupFilters() {
        // Time range filter
        this.filters.timeRange = '24h';
        
        // Severity filter
        this.filters.severity = 'all';
        
        // Category filter
        this.filters.category = 'all';
        
        // Host filter
        this.filters.host = 'all';
    }

    async loadData() {
        try {
            const response = await fetch(`/api/v1/analytics?${this.buildQueryString()}`);
            const data = await response.json();
            
            this.updateCharts(data);
        } catch (error) {
            console.error('Error loading analytics:', error);
        }
    }

    buildQueryString() {
        const params = new URLSearchParams();
        
        if (this.filters.timeRange !== 'all') {
            params.append('time_range', this.filters.timeRange);
        }
        
        if (this.filters.severity !== 'all') {
            params.append('severity', this.filters.severity);
        }
        
        if (this.filters.category !== 'all') {
            params.append('category', this.filters.category);
        }
        
        if (this.filters.host !== 'all') {
            params.append('host', this.filters.host);
        }
        
        return params.toString();
    }

    updateCharts(data) {
        // Actualizar timeline
        this.charts.timeline.data.labels = data.timeline.labels;
        this.charts.timeline.data.datasets[0].data = data.timeline.values;
        this.charts.timeline.update();

        // Actualizar severity
        this.charts.severity.data.datasets[0].data = data.severity;
        this.charts.severity.update();

        // Actualizar category
        this.charts.category.data.labels = data.category.labels;
        this.charts.category.data.datasets[0].data = data.category.values;
        this.charts.category.update();

        // Actualizar heatmap
        this.charts.heatmap.data = data.heatmap;
        this.charts.heatmap.update();
    }

    render() {
        this.element.innerHTML = `
            <div class="analytics-panel">
                <div class="panel-header">
                    <h2>Analytics</h2>
                    <div class="panel-controls">
                        <button class="btn" onclick="this.closest('.analytics-panel').querySelector('.filters-panel').classList.toggle('visible')">
                            Filters
                        </button>
                        <button class="btn" onclick="this.closest('.analytics-panel').loadData()">
                            Refresh
                        </button>
                    </div>
                </div>
                
                <div class="filters-panel">
                    <div class="filter-group">
                        <label>Time Range:</label>
                        <select onchange="this.closest('.analytics-panel').filters.timeRange = this.value; this.closest('.analytics-panel').loadData()">
                            <option value="1h">Last Hour</option>
                            <option value="24h" selected>Last 24 Hours</option>
                            <option value="7d">Last 7 Days</option>
                            <option value="30d">Last 30 Days</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label>Severity:</label>
                        <select onchange="this.closest('.analytics-panel').filters.severity = this.value; this.closest('.analytics-panel').loadData()">
                            <option value="all" selected>All</option>
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label>Category:</label>
                        <select onchange="this.closest('.analytics-panel').filters.category = this.value; this.closest('.analytics-panel').loadData()">
                            <option value="all" selected>All</option>
                            <option value="process">Process</option>
                            <option value="network">Network</option>
                            <option value="file">File</option>
                            <option value="registry">Registry</option>
                        </select>
                    </div>
                </div>
                
                <div class="panel-content">
                    <div class="charts-grid">
                        <div class="chart-container">
                            <h3>Event Timeline</h3>
                            <div class="chart" id="timeline-chart"></div>
                        </div>
                        
                        <div class="chart-container">
                            <h3>Severity Distribution</h3>
                            <div class="chart" id="severity-chart"></div>
                        </div>
                        
                        <div class="chart-container">
                            <h3>Category Distribution</h3>
                            <div class="chart" id="category-chart"></div>
                        </div>
                        
                        <div class="chart-container">
                            <h3>Temporal Patterns</h3>
                            <div class="chart" id="heatmap-chart"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Re-inicializar charts después del render
        setTimeout(() => this.setupCharts(), 0);
    }

    destroy() {
        super.destroy();
        Object.values(this.charts).forEach(chart => chart.destroy());
    }
}
```

### 3.3 Componentes de Charts

#### Sparkline Chart

```javascript
// js/components/charts/sparkline.js
class SparklineChart {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            color: '#0088ff',
            maxPoints: 60,
            height: 50,
            ...options
        };
        
        this.data = [];
        this.init();
    }

    init() {
        this.container.innerHTML = `
            <svg class="sparkline" width="100%" height="${this.options.height}">
                <path class="sparkline-path" d="" fill="none" stroke="${this.options.color}" stroke-width="2"/>
            </svg>
        `;
        
        this.path = this.container.querySelector('.sparkline-path');
    }

    push(value) {
        this.data.push(value);
        
        if (this.data.length > this.options.maxPoints) {
            this.data.shift();
        }
        
        this.render();
    }

    render() {
        if (this.data.length < 2) return;
        
        const width = this.container.offsetWidth;
        const height = this.options.height;
        
        const min = Math.min(...this.data);
        const max = Math.max(...this.data);
        const range = max - min || 1;
        
        const points = this.data.map((value, index) => {
            const x = (index / (this.data.length - 1)) * width;
            const y = height - ((value - min) / range) * height;
            return `${x},${y}`;
        }).join(' ');
        
        this.path.setAttribute('d', `M ${points}`);
    }

    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}
```

#### Line Chart

```javascript
// js/components/charts/line.js
class LineChart {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = options;
        this.chart = null;
        this.init();
    }

    init() {
        this.chart = new Chart(this.container, this.options);
    }

    update() {
        if (this.chart) {
            this.chart.update();
        }
    }

    destroy() {
        if (this.chart) {
            this.chart.destroy();
        }
    }
}
```

### 3.4 Componentes UI

#### Modal Component

```javascript
// js/components/ui/modal.js
class Modal {
    constructor(options = {}) {
        this.options = {
            title: '',
            content: '',
            size: 'medium',
            closable: true,
            ...options
        };
        
        this.element = null;
        this.create();
    }

    create() {
        this.element = document.createElement('div');
        this.element.className = `modal modal-${this.options.size}`;
        this.element.innerHTML = `
            <div class="modal-backdrop"></div>
            <div class="modal-container">
                <div class="modal-header">
                    <h3>${this.options.title}</h3>
                    ${this.options.closable ? '<button class="modal-close">&times;</button>' : ''}
                </div>
                <div class="modal-body">
                    ${this.options.content}
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary modal-cancel">Cancel</button>
                    <button class="btn btn-primary modal-confirm">Confirm</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.element);
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        const closeBtn = this.element.querySelector('.modal-close');
        const cancelBtn = this.element.querySelector('.modal-cancel');
        const confirmBtn = this.element.querySelector('.modal-confirm');
        const backdrop = this.element.querySelector('.modal-backdrop');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.close());
        }
        
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                if (this.options.onConfirm) {
                    this.options.onConfirm();
                }
                this.close();
            });
        }
        
        if (backdrop) {
            backdrop.addEventListener('click', () => this.close());
        }
        
        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.element.classList.contains('visible')) {
                this.close();
            }
        });
    }

    open() {
        this.element.classList.add('visible');
        document.body.style.overflow = 'hidden';
    }

    close() {
        this.element.classList.remove('visible');
        document.body.style.overflow = '';
        
        if (this.options.onClose) {
            this.options.onClose();
        }
    }

    destroy() {
        if (this.element) {
            this.element.remove();
        }
    }
}
```

#### Search Component

```javascript
// js/components/ui/search.js
class SearchComponent {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            placeholder: 'Search...',
            onSearch: null,
            ...options
        };
        
        this.init();
    }

    init() {
        this.container.innerHTML = `
            <div class="search-component">
                <input 
                    type="text" 
                    class="search-input" 
                    placeholder="${this.options.placeholder}"
                    autocomplete="off"
                />
                <button class="search-button">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                </button>
                <div class="search-results hidden"></div>
            </div>
        `;
        
        this.input = this.container.querySelector('.search-input');
        this.results = this.container.querySelector('.search-results');
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        let debounceTimer;
        
        this.input.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            
            debounceTimer = setTimeout(() => {
                this.search(e.target.value);
            }, 300);
        });
        
        this.input.addEventListener('focus', () => {
            if (this.input.value) {
                this.results.classList.remove('hidden');
            }
        });
        
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.results.classList.add('hidden');
            }
        });
    }

    async search(query) {
        if (!query || query.length < 2) {
            this.results.classList.add('hidden');
            return;
        }
        
        if (this.options.onSearch) {
            const results = await this.options.onSearch(query);
            this.displayResults(results);
        }
    }

    displayResults(results) {
        if (results.length === 0) {
            this.results.innerHTML = '<div class="no-results">No results found</div>';
        } else {
            this.results.innerHTML = results.map(result => `
                <div class="search-result" data-type="${result.type}" data-id="${result.id}">
                    <div class="result-icon">${result.icon}</div>
                    <div class="result-content">
                        <div class="result-title">${result.title}</div>
                        <div class="result-description">${result.description}</div>
                    </div>
                </div>
            `).join('');
            
            // Add click handlers
            this.results.querySelectorAll('.search-result').forEach(result => {
                result.addEventListener('click', () => {
                    this.handleResultClick(result.dataset);
                });
            });
        }
        
        this.results.classList.remove('hidden');
    }

    handleResultClick(data) {
        if (this.options.onResultClick) {
            this.options.onResultClick(data);
        }
        
        this.input.value = '';
        this.results.classList.add('hidden');
    }
}
```

---

## 4. SISTEMA DE LAYOUTS

### 4.1 Layout Engine

```javascript
// js/components/layout/grid.js
class GridLayout {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            columns: 12,
            gap: 16,
            ...options
        };
        
        this.panels = [];
        this.init();
    }

    init() {
        this.container.classList.add('grid-layout');
        this.container.style.display = 'grid';
        this.container.style.gridTemplateColumns = `repeat(${this.options.columns}, 1fr)`;
        this.container.style.gap = `${this.options.gap}px`;
        
        this.loadLayout();
        this.setupDragAndDrop();
    }

    addPanel(panel, options = {}) {
        const panelConfig = {
            element: panel,
            x: options.x || 0,
            y: options.y || 0,
            width: options.width || 4,
            height: options.height || 3,
            ...options
        };
        
        this.panels.push(panelConfig);
        this.renderPanel(panelConfig);
        this.saveLayout();
    }

    renderPanel(config) {
        config.element.style.gridColumnStart = config.x + 1;
        config.element.style.gridColumnEnd = config.x + config.width + 1;
        config.element.style.gridRowStart = config.y + 1;
        config.element.style.gridRowEnd = config.y + config.height + 1;
        
        config.element.classList.add('grid-panel');
        config.element.dataset.panelId = config.id;
    }

    setupDragAndDrop() {
        let draggedPanel = null;
        let startX, startY, initialX, initialY;
        
        this.container.addEventListener('mousedown', (e) => {
            const panel = e.target.closest('.grid-panel');
            if (!panel) return;
            
            draggedPanel = panel;
            startX = e.clientX;
            startY = e.clientY;
            
            const rect = panel.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;
            
            panel.classList.add('dragging');
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!draggedPanel) return;
            
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            
            draggedPanel.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
        });
        
        document.addEventListener('mouseup', (e) => {
            if (!draggedPanel) return;
            
            draggedPanel.classList.remove('dragging');
            draggedPanel.style.transform = '';
            
            // Calculate new position
            const containerRect = this.container.getBoundingClientRect();
            const panelRect = draggedPanel.getBoundingClientRect();
            
            const newX = Math.round((panelRect.left - containerRect.left) / (containerRect.width / this.options.columns));
            const newY = Math.round((panelRect.top - containerRect.top) / 100); // Assuming 100px row height
            
            // Update panel position
            const panelConfig = this.panels.find(p => p.element === draggedPanel);
            if (panelConfig) {
                panelConfig.x = Math.max(0, Math.min(newX, this.options.columns - panelConfig.width));
                panelConfig.y = Math.max(0, newY);
                this.renderPanel(panelConfig);
                this.saveLayout();
            }
            
            draggedPanel = null;
        });
    }

    saveLayout() {
        const layout = this.panels.map(p => ({
            id: p.id,
            x: p.x,
            y: p.y,
            width: p.width,
            height: p.height
        }));
        
        localStorage.setItem('dashboard-layout', JSON.stringify(layout));
    }

    loadLayout() {
        const savedLayout = localStorage.getItem('dashboard-layout');
        
        if (savedLayout) {
            try {
                const layout = JSON.parse(savedLayout);
                layout.forEach(config => {
                    const panel = this.panels.find(p => p.id === config.id);
                    if (panel) {
                        Object.assign(panel, config);
                        this.renderPanel(panel);
                    }
                });
            } catch (error) {
                console.error('Error loading layout:', error);
            }
        }
    }
}
```

### 4.2 Sidebar Component

```javascript
// js/components/layout/sidebar.js
class Sidebar {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            collapsed: false,
            items: [],
            ...options
        };
        
        this.init();
    }

    init() {
        this.render();
        this.setupEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="sidebar ${this.options.collapsed ? 'collapsed' : ''}">
                <div class="sidebar-header">
                    <div class="logo">ARGOS</div>
                    <button class="sidebar-toggle">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="3" y1="12" x2="21" y2="12"></line>
                            <line x1="3" y1="6" x2="21" y2="6"></line>
                            <line x1="3" y1="18" x2="21" y2="18"></line>
                        </svg>
                    </button>
                </div>
                
                <nav class="sidebar-nav">
                    ${this.options.items.map(item => `
                        <a href="${item.href}" class="nav-item ${item.active ? 'active' : ''}">
                            <span class="nav-icon">${item.icon}</span>
                            <span class="nav-label">${item.label}</span>
                        </a>
                    `).join('')}
                </nav>
                
                <div class="sidebar-footer">
                    <div class="user-info">
                        <div class="user-avatar">A</div>
                        <div class="user-details">
                            <div class="user-name">Admin</div>
                            <div class="user-role">Administrator</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const toggleBtn = this.container.querySelector('.sidebar-toggle');
        
        toggleBtn.addEventListener('click', () => {
            this.toggle();
        });
    }

    toggle() {
        this.options.collapsed = !this.options.collapsed;
        this.container.classList.toggle('collapsed');
    }
}
```

---

## 5. STATE MANAGEMENT

### 5.1 Store Implementation

```javascript
// js/store.js
class Store {
    constructor() {
        this.state = {};
        this.listeners = [];
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    getState() {
        return { ...this.state };
    }

    subscribe(listener) {
        this.listeners.push(listener);
        
        // Return unsubscribe function
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }
}

// Global store instance
const store = new Store();

// Initialize state
store.setState({
    user: null,
    theme: 'dark',
    layout: 'default',
    panels: {
        monitoring: true,
        analytics: true,
        security: true,
        admin: false
    },
    alerts: [],
    metrics: {},
    events: []
});
```

---

## 6. ROUTING

### 6.1 Client-side Router

```javascript
// js/router.js
class Router {
    constructor() {
        this.routes = {};
        this.currentRoute = null;
        this.init();
    }

    init() {
        window.addEventListener('popstate', () => {
            this.handleRouteChange();
        });
        
        this.handleRouteChange();
    }

    register(path, handler) {
        this.routes[path] = handler;
    }

    navigate(path) {
        window.history.pushState({}, '', path);
        this.handleRouteChange();
    }

    handleRouteChange() {
        const path = window.location.pathname;
        
        if (this.routes[path]) {
            this.currentRoute = path;
            this.routes[path]();
        } else {
            // Default route
            this.routes['/']();
        }
    }
}

// Global router instance
const router = new Router();

// Register routes
router.register('/', () => {
    // Load dashboard
});

router.register('/security', () => {
    // Load security panel
});

router.register('/admin', () => {
    // Load admin panel
});
```

---

## 7. CSS VARIABLES & THEMING

### 7.1 CSS Variables

```css
/* css/variables.css */
:root {
    /* Colors */
    --color-primary: #0088ff;
    --color-secondary: #00ff88;
    --color-success: #00ff00;
    --color-warning: #ff8800;
    --color-danger: #ff0000;
    --color-info: #00ffff;
    
    /* Background */
    --bg-primary: #0a0e17;
    --bg-secondary: #111827;
    --bg-tertiary: #1f2937;
    --bg-elevated: #374151;
    
    /* Text */
    --text-primary: #f9fafb;
    --text-secondary: #d1d5db;
    --text-tertiary: #9ca3af;
    
    /* Borders */
    --border-primary: #374151;
    --border-secondary: #4b5563;
    
    /* Spacing */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
    
    /* Typography */
    --font-family: 'Inter', system-ui, sans-serif;
    --font-size-xs: 12px;
    --font-size-sm: 14px;
    --font-size-base: 16px;
    --font-size-lg: 18px;
    --font-size-xl: 24px;
    
    /* Effects */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.2);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.3);
    
    /* Transitions */
    --transition-fast: 150ms ease;
    --transition-base: 300ms ease;
    --transition-slow: 500ms ease;
}

[data-theme="light"] {
    --bg-primary: #ffffff;
    --bg-secondary: #f3f4f6;
    --bg-tertiary: #e5e7eb;
    --bg-elevated: #d1d5db;
    
    --text-primary: #111827;
    --text-secondary: #374151;
    --text-tertiary: #6b7280;
}
```

---

## 8. INTEGRACIÓN CON BACKEND

### 8.1 API Service

```javascript
// js/services/api.js
class APIService {
    constructor(baseURL = '/api/v1') {
        this.baseURL = baseURL;
    }

    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseURL}${endpoint}`);
        Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        
        const response = await fetch(url);
        return response.json();
    }

    async post(endpoint, data) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        return response.json();
    }

    async put(endpoint, data) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        return response.json();
    }

    async delete(endpoint) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'DELETE'
        });
        
        return response.json();
    }
}

// Global API service instance
const api = new APIService();
```

---

## 9. TESTING

### 9.1 Component Tests

```javascript
// tests/components/test_monitoring_panel.js
describe('MonitoringPanel', () => {
    let container;
    let panel;

    beforeEach(() => {
        container = document.createElement('div');
        document.body.appendChild(container);
        panel = new MonitoringPanel(container);
    });

    afterEach(() => {
        panel.destroy();
        container.remove();
    });

    test('should initialize charts', () => {
        expect(panel.charts.cpu).toBeDefined();
        expect(panel.charts.memory).toBeDefined();
    });

    test('should update metrics', () => {
        panel.updateMetrics({
            cpu: 50.5,
            memory: 60.2,
            network: 30.1,
            events_per_sec: 10
        });

        expect(panel.charts.cpu.data.length).toBeGreaterThan(0);
    });
});
```

---

## 10. PERFORMANCE OPTIMIZATION

### 10.1 Lazy Loading

```javascript
// js/utils/lazy_load.js
class LazyLoader {
    constructor() {
        this.observedElements = new Set();
    }

    observe(element, callback) {
        if (this.observedElements.has(element)) return;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    callback();
                    observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '100px'
        });

        observer.observe(element);
        this.observedElements.add(element);
    }
}

const lazyLoader = new LazyLoader();
```

### 10.2 Code Splitting

```javascript
// Dynamic imports for code splitting
async function loadPanel(panelName) {
    switch (panelName) {
        case 'monitoring':
            return await import('./components/panels/monitoring.js');
        case 'analytics':
            return await import('./components/panels/analytics.js');
        case 'security':
            return await import('./components/panels/security.js');
        default:
            throw new Error(`Unknown panel: ${panelName}`);
    }
}
```

---

## 11. DEPLOYMENT

### 11.1 Build Process

```javascript
// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
    build: {
        outDir: 'dist',
        rollupOptions: {
            output: {
                manualChunks: {
                    'vendor': ['chart.js', 'd3'],
                    'components': ['./js/components'],
                    'panels': ['./js/components/panels']
                }
            }
        }
    },
    server: {
        port: 3000,
        proxy: {
            '/api': 'http://localhost:8000',
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true
            }
        }
    }
});
```

---

## 12. ACCESIBILIDAD

### 12.1 Keyboard Navigation

```javascript
// js/utils/keyboard.js
class KeyboardNavigation {
    constructor() {
        this.focusableElements = [];
        this.currentIndex = 0;
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                e.preventDefault();
                this.navigate(e.shiftKey ? -1 : 1);
            }
        });
    }

    navigate(direction) {
        this.focusableElements = document.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        this.currentIndex += direction;
        
        if (this.currentIndex < 0) {
            this.currentIndex = this.focusableElements.length - 1;
        } else if (this.currentIndex >= this.focusableElements.length) {
            this.currentIndex = 0;
        }

        this.focusableElements[this.currentIndex].focus();
    }
}
```

---

## 13. PRÓXIMOS PASOS

1. **Inmediato:**
   - Implementar base component system
   - Crear 5 componentes principales
   - Setup build process con Vite

2. **Corto plazo (1 semana):**
   - Implementar monitoring panel
   - Implementar analytics panel
   - Setup WebSocket real-time updates

3. **Mediano plazo (2 semanas):**
   - Implementar layout engine
   - Agregar drag & drop
   - Implementar sistema de temas

4. **Largo plazo (1 mes):**
   - Completar todos los componentes
   - Optimizar performance
   - Testing extensivo

---

## CONCLUSIÓN

Esta guía proporciona un camino completo para transformar el dashboard de ARGOS a una interfaz enterprise nivel Grafana/Datadog, con componentes reutilizables, layouts configurables, y monitoreo en tiempo real, inspirado en los patrones de UI de grok-build.
