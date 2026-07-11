# Estadísticas Soccer - Plataforma de Análisis Deportivo IA

Una plataforma **enterprise** completa para análisis estadístico de eventos deportivos, generación de probabilidades predictivas y comparación con cuotas de casas de apuestas.

## 🏗️ Arquitectura Enterprise

El proyecto sigue **Clean Architecture** con separación clara de responsabilidades:

```
backend/
├── app/
│   ├── core/              # Configuración, seguridad, base de datos
│   ├── models/            # Modelos ORM de SQLAlchemy 2.0
│   ├── repositories/      # Data Access Layer (DAL)
│   ├── services/          # Business Logic Layer
│   ├── api/               # API REST endpoints (versioned)
│   ├── schemas/           # Validadores Pydantic v2
│   ├── tasks/             # Celery tasks
│   ├── agents/            # AI Agents (ProbabilityAgent)
│   ├── analytics/         # Engine de análisis
│   ├── machine_learning/  # Modelos ML
│   ├── jobs/              # Scheduled jobs
│   ├── utils/             # Utilities
│   └── main.py            # FastAPI app factory
└── tests/                 # Tests con Pytest

frontend/
├── src/
│   ├── app/               # NextJS app router
│   ├── components/        # React components
│   ├── pages/             # (App router)
│   ├── lib/               # Utilities & hooks
│   └── styles/            # Tailwind CSS
```

## 📋 Stack Técnico

### Backend

| Componente | Tecnología | Versión |
|---|---|---|
| **Lenguaje** | Python | 3.12.3 |
| **Framework API** | FastAPI | 0.104.1 |
| **Servidor ASGI** | Uvicorn | 0.24.0 |
| **ORM** | SQLAlchemy | 2.0.23 |
| **Migraciones** | Alembic | 1.12.1 |
| **Validación** | Pydantic | 2.5.0 |
| **Base de datos** | PostgreSQL | 17 Alpine |
| **Cache** | Redis | 7 Alpine |
| **Message Broker** | RabbitMQ | 3.13 Management |
| **Task Queue** | Celery | 5.3.4 |

### Data Science & ML

| Componente | Tecnología |
|---|---|
| **DataFrames** | Pandas, Polars |
| **Análisis Numérico** | NumPy |
| **Scikit-Learn** | scikit-learn |
| **Gradient Boosting** | XGBoost, LightGBM |
| **Visualización** | Plotly |

### Frontend

| Componente | Tecnología |
|---|---|
| **Framework** | React 19 + NextJS 15 |
| **Lenguaje** | TypeScript |
| **CSS** | TailwindCSS |
| **Componentes** | shadcn/ui |
| **Estado** | TanStack Query |
| **Gráficas** | Recharts |

---

## 🚀 Inicio Rápido

### 1. Clonar y configurar

```bash
git clone <repository-url>
cd estadisticas_soccer-1
cp .env.example .env
```

### 2. Iniciar servicios

```bash
docker-compose up -d
```

### 3. Acceder

```
Frontend:     http://localhost:3000
Backend API:  http://localhost:8000
Swagger Docs: http://localhost:8000/docs
PgAdmin:      http://localhost:5050
```

---

## 📊 Características Principales

### ✅ Sincronización de Datos
- Integración con múltiples APIs deportivas (API-Football, SportsDataIO)
- Jobs automáticos cada hora/día
- Adapter pattern para fácil cambio de fuentes

### ✅ Analytics Engine
- **ProbabilityAgent** que analiza 20+ variables
- Ponderación automática de factores
- Análisis de forma, lesiones, estadísticas individuales y de equipo

### ✅ Simulación Monte Carlo
- 1000-10000 simulaciones por partido
- Cálculo de probabilidades exactas
- Predicción de marcadores más probables

### ✅ Machine Learning
- 5 modelos entrenados (Logistic Regression, Random Forest, XGBoost, LightGBM, Voting Ensemble)
- Soporte para 20+ tipos de apuestas
- Reentrenamiento automático

### ✅ Análisis de Cuotas
- Comparación con casa de apuestas Caliente
- Cálculo de Expected Value (EV)
- Kelly Criterion para stake óptimo
- ROI esperado

### ✅ Dashboard Moderno
- Predicciones por modelo
- Análisis de cuotas
- Gráficas interactivas (Recharts)
- Comparativas H2H
- Simulaciones en tiempo real

---

## 📖 Documentación Completa

Ver [DOCUMENTACIÓN.md](docs/DOCUMENTACIÓN.md) para:

- Instalación detallada
- Estructura de BD
- Todos los endpoints API
- Guía de ProbabilityAgent
- ML Models & Training
- Análisis Caliente
- Troubleshooting

---

## 🔧 Requisitos

- Docker & Docker Compose
- Python 3.12+ (si desarrollo local)
- Node.js 20+ (si frontend local)
- Ubuntu 24.04 LTS

---

## 📝 Commits

Los commits deben estar en español y separados por funcionalidad:

```
git commit -m "Backend: implementar endpoint GET /teams"
git commit -m "Frontend: crear componente de dashboard"
git commit -m "ML: entrenar modelo XGBoost"
```

---

**Estado:** 🟢 Inicialización completada - 2026-07-11