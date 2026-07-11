# Documentación Completa - Plataforma Estadísticas Soccer

## 📋 Tabla de Contenidos

1. [Instalación](#instalación)
2. [Configuración](#configuración)
3. [Estructura de Base de Datos](#estructura-de-base-de-datos)
4. [API REST Endpoints](#api-rest-endpoints)
5. [ProbabilityAgent](#probabilityagent---motor-de-análisis)
6. [Simulación Monte Carlo](#simulación-monte-carlo)
7. [Modelos Machine Learning](#modelos-machine-learning)
8. [Análisis de Cuotas](#análisis-de-cuotas---bet-analyzer)
9. [Sincronización de Datos](#sincronización-de-datos)
10. [Deployment](#deployment)

---

## Instalación

### Requisitos Previos

- Docker & Docker Compose
- Python 3.12+ (para desarrollo local)
- Node.js 20+ (para frontend)
- Ubuntu 24.04 LTS (recomendado)

### Paso 1: Clonar Repositorio

```bash
git clone <repository-url>
cd estadisticas_soccer-1
```

### Paso 2: Crear Archivo .env

```bash
cp .env.example .env
nano .env
```

**Variables críticas:**

```env
DB_PASSWORD=cambiar_password_segura
JWT_SECRET_KEY=cambiar_con_valor_seguro
API_KEY_FOOTBALL=tu_api_key_aqui
API_KEY_SPORTS=tu_api_key_aqui
```

### Paso 3: Iniciar Servicios

```bash
# Build images (primera vez)
docker-compose build

# Iniciar todos los servicios
docker-compose up -d

# Verificar estado
docker-compose ps
```

### Paso 4: Inicializar Base de Datos

```bash
# Las tablas se crean automáticamente al iniciar el backend
# Si necesitas migraciones:
docker-compose exec backend alembic upgrade head
```

### Paso 5: Acceder a la Aplicación

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| RabbitMQ Admin | http://localhost:15672 |
| PgAdmin | http://localhost:5050 |

---

## Configuración

### Variables de Entorno

```env
# Environment
ENVIRONMENT=development        # development|production
DEBUG=true                      # Activa modo debug

# Database
DB_USER=postgres               # Usuario PostgreSQL
DB_PASSWORD=postgres           # Password (cambiar en prod)
DB_NAME=estadisticas_db        # Nombre BD
DB_HOST=postgres               # Host (localhost o postgres en Docker)
DB_PORT=5432                   # Puerto PostgreSQL

# Redis
REDIS_URL=redis://redis:6379/0

# RabbitMQ
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672

# JWT
JWT_SECRET_KEY=tu-clave-secreta-aqui
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Keys (para sincronización)
API_KEY_FOOTBALL=your-api-football-key
API_KEY_SPORTS=your-api-sports-key
API_KEY_RAPIDAPI=your-rapidapi-key

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Application
MAX_SIMULATIONS=10000
MODELS_RETRAIN_FREQUENCY=daily
ODDS_UPDATE_FREQUENCY=hourly
```

### Estructura de Directorios

```
estadisticas_soccer-1/
├── backend/
│   ├── app/
│   │   ├── core/                 # Configuración, BD, seguridad
│   │   ├── models/               # Modelos ORM
│   │   ├── repositories/         # Data Access Layer
│   │   ├── services/             # Business Logic
│   │   ├── api/v1/               # Endpoints REST
│   │   ├── schemas/              # Validadores Pydantic
│   │   ├── tasks/                # Celery tasks
│   │   ├── agents/               # IA - ProbabilityAgent
│   │   ├── analytics/            # Monte Carlo, Bet Analyzer
│   │   ├── machine_learning/     # Modelos ML
│   │   ├── adapters/             # Integraciones APIs externas
│   │   ├── jobs/                 # Scheduled jobs
│   │   └── main.py               # FastAPI app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── app/                  # NextJS pages
│   │   ├── components/           # React components
│   │   └── lib/                  # Utilities
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Estructura de Base de Datos

### Diagrama ER (Versión Simplificada)

```
Sports (1) ──→ (n) Leagues
           ──→ (n) Teams

Leagues (1) ──→ (n) Seasons

Seasons (1) ──→ (n) Rounds
         ──→ (n) TeamSeasons
         ──→ (n) PlayerStatistics

Rounds (1) ──→ (n) Matches

Teams (1) ──→ (n) Players
       ──→ (n) Transfers
       ──→ (n) TeamSeasons
       ──→ (n) Matches (Home/Away)

Players (1) ──→ (n) PlayerStatistics
         ──→ (n) Injuries
         ──→ (n) Suspensions
         ──→ (n) Lineups
         ──→ (n) Transfers

Matches (1) ──→ (n) Lineups
         ──→ (n) MatchEvents
         ──→ (n) Odds
         ──→ (n) Predictions
         ──→ (n) SimulationResults

Bookmakers (1) ──→ (n) Odds
Markets (1) ──→ (n) Odds
```

### Tablas Principales

#### sports
```sql
id: INTEGER PRIMARY KEY
name: STRING UNIQUE
code: STRING UNIQUE
created_at: DATETIME
updated_at: DATETIME
```

#### leagues
```sql
id: INTEGER PRIMARY KEY
sport_id: FOREIGN KEY -> sports.id
name: STRING
code: STRING
country: STRING
logo_url: STRING
created_at: DATETIME
updated_at: DATETIME
UNIQUE(sport_id, code)
```

#### teams
```sql
id: INTEGER PRIMARY KEY
sport_id: FOREIGN KEY -> sports.id
name: STRING
code: STRING
country: STRING
logo_url: STRING
created_at: DATETIME
updated_at: DATETIME
UNIQUE(code, sport_id)
```

#### matches
```sql
id: INTEGER PRIMARY KEY
round_id: FOREIGN KEY -> rounds.id
home_team_id: FOREIGN KEY -> teams.id
away_team_id: FOREIGN KEY -> teams.id
match_date: DATETIME
status: STRING (scheduled, live, finished)
home_goals: INTEGER NULL
away_goals: INTEGER NULL
home_xg: FLOAT
away_xg: FLOAT
home_possession: FLOAT
away_possession: FLOAT
created_at: DATETIME
updated_at: DATETIME
```

#### predictions
```sql
id: INTEGER PRIMARY KEY
match_id: FOREIGN KEY -> matches.id
market: STRING (match_winner, over_under_2_5, both_score, etc)
predicted_outcome: STRING
predicted_probability: FLOAT
confidence_level: FLOAT
model_name: STRING
reasoning: STRING
created_at: DATETIME
```

#### odds
```sql
id: INTEGER PRIMARY KEY
match_id: FOREIGN KEY -> matches.id
bookmaker_id: FOREIGN KEY -> bookmakers.id
market_id: FOREIGN KEY -> markets.id
outcome: STRING
value: FLOAT
probability: FLOAT (implied)
last_updated: DATETIME
created_at: DATETIME
```

---

## API REST Endpoints

### Health & Status

#### GET `/api/v1/health`
Verificar estado del backend

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Teams

#### GET `/api/v1/teams`
Listar todos los equipos con paginación

**Query Parameters:**
```
skip: int (default=0)
limit: int (default=10, max=100)
```

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Manchester United",
      "code": "MU",
      "country": "England",
      "sport_id": 1,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 380,
  "skip": 0,
  "limit": 10
}
```

#### POST `/api/v1/teams`
Crear nuevo equipo

**Request Body:**
```json
{
  "name": "Liverpool FC",
  "code": "LIV",
  "country": "England",
  "sport_id": 1
}
```

#### GET `/api/v1/teams/{id}`
Obtener equipo específico

#### GET `/api/v1/teams/{id}/stats`
Obtener estadísticas de rendimiento del equipo

**Response:**
```json
{
  "team_id": 1,
  "seasons": 5,
  "avg_goals_for": 2.3,
  "avg_goals_against": 1.1,
  "avg_points": 2.1,
  "win_rate": 0.65,
  "total_matches": 150
}
```

### Matches

#### GET `/api/v1/matches`
Listar partidos

**Query Parameters:**
```
skip: int
limit: int
status: string (scheduled, live, finished)
league_id: int (opcional)
```

#### GET `/api/v1/matches/{id}`
Obtener detalles de un partido

#### GET `/api/v1/matches/{id}/odds`
Obtener cuotas disponibles para un partido

### Players

#### GET `/api/v1/players`
Listar jugadores

#### GET `/api/v1/players/{id}`
Obtener detalles de jugador

#### GET `/api/v1/players/{id}/stats`
Obtener estadísticas del jugador para una temporada

### Predictions

#### POST `/api/v1/predictions`
Generar predicción para un partido

**Request Body:**
```json
{
  "match_id": 123,
  "market": "match_winner",
  "use_models": ["voting_ensemble", "xgboost"]
}
```

**Response:**
```json
{
  "id": 1,
  "match_id": 123,
  "market": "match_winner",
  "predictions": [
    {
      "model": "voting_ensemble",
      "home": 0.58,
      "draw": 0.25,
      "away": 0.17,
      "confidence": 0.82
    }
  ],
  "recommendation": "Home Win",
  "created_at": "2024-07-11T10:30:00"
}
```

#### GET `/api/v1/predictions`
Listar predicciones

#### GET `/api/v1/predictions/{id}`
Obtener predicción específica

### Simulación

#### POST `/api/v1/simulate`
Ejecutar simulación Monte Carlo

**Request Body:**
```json
{
  "match_id": 123,
  "simulations": 5000,
  "use_probability_agent": true
}
```

**Response:**
```json
{
  "simulations": 5000,
  "home_win_probability": 0.58,
  "draw_probability": 0.25,
  "away_win_probability": 0.17,
  "most_likely_score": "2-1",
  "average_goals": 2.8,
  "over_2_5_probability": 0.62,
  "both_teams_score_probability": 0.71,
  "score_distribution": {
    "2-1": 412,
    "1-1": 388,
    "2-0": 324,
    "1-0": 281,
    "3-1": 198
  }
}
```

### Análisis de Cuotas

#### POST `/api/v1/odds/analyze`
Analizar valor de una cuota

**Request Body:**
```json
{
  "market": "match_winner",
  "outcome": "Home Win",
  "odds": 2.45,
  "predicted_probability": 0.58,
  "confidence_level": 0.82
}
```

**Response:**
```json
{
  "market": "match_winner",
  "outcome": "Home Win",
  "odds": 2.45,
  "predicted_probability": 0.58,
  "implied_probability": 0.408,
  "expected_value": 0.421,
  "expected_value_percentage": 42.1,
  "kelly_percentage": 0.084,
  "recommended_stake_percentage": 0.021,
  "value_found": true,
  "recommendation": "✓ GOOD VALUE - Good EV, recommended"
}
```

---

## ProbabilityAgent - Motor de Análisis

### Descripción

El ProbabilityAgent es un agente inteligente que analiza múltiples factores para generar probabilidades precisas de eventos deportivos.

### Factores Analizados (11 variables)

```python
{
    "team_form": 0.15,           # Últimos 5 partidos
    "head_to_head": 0.10,        # Historial H2H
    "home_away": 0.12,           # Ventaja local/visitante
    "goals_avg": 0.10,           # Promedio de goles
    "xg_xga": 0.12,              # Expected goals
    "injuries": 0.08,            # Impacto de lesiones
    "possession": 0.08,          # Posesión de pelota
    "clean_sheets": 0.06,        # Portería en cero
    "recent_form": 0.12,         # Forma reciente
    "player_value": 0.05,        # Valor de la plantilla
    "motivation": 0.04,          # Motivación (posición en tabla)
}
```

### Uso

```python
from app.agents.probability_agent import ProbabilityAgent

agent = ProbabilityAgent()

analysis = await agent.analyze_match(
    match_id=123,
    home_team_stats={
        'win_rate': 0.65,
        'avg_goals_for': 2.3,
        'avg_goals_against': 1.1,
        'avg_xg': 1.8,
        'possession': 58.0,
        'clean_sheets': 8,
        'recent_form': 0.60,
        'squad_market_value': 250,
        'position': 2,
    },
    away_team_stats={
        'win_rate': 0.55,
        'avg_goals_for': 1.8,
        'avg_goals_against': 1.5,
        'avg_xg': 1.4,
        'possession': 42.0,
        'clean_sheets': 6,
        'recent_form': 0.40,
        'squad_market_value': 200,
        'position': 5,
    },
    home_injuries=['key_player_1'],
    away_injuries=[],
    historical_h2h={
        'home_wins': 4,
        'draws': 2,
        'away_wins': 2,
        'total_matches': 8,
    }
)

print(f"Home Win: {analysis.home_win_probability:.1%}")
print(f"Draw: {analysis.draw_probability:.1%}")
print(f"Away Win: {analysis.away_win_probability:.1%}")
print(f"Confidence: {analysis.confidence_level:.1%}")
print(f"Reasoning: {analysis.reasoning}")
```

---

## Simulación Monte Carlo

### Descripción

Motor de simulación que utiliza distribución de Poisson para calcular probabilidades exactas.

### Características

- Ejecuta 1000-10000 simulaciones
- Calcula distribución de resultados
- Genera múltiples mercados (Over/Under, Both Score, etc)
- Identifica scores más probables

### Uso

```python
from app.analytics.monte_carlo import MonteCarlo

simulator = MonteCarlo(
    home_team_stats={
        'goals_per_match': 2.3,
        'expected_goals': 1.8,
    },
    away_team_stats={
        'goals_per_match': 1.8,
        'expected_goals': 1.4,
    },
    simulations=5000
)

results = simulator.run()

print(f"Home Win: {results.home_win_probability:.1%}")
print(f"Draw: {results.draw_probability:.1%}")
print(f"Away Win: {results.away_win_probability:.1%}")
print(f"Over 2.5: {results.over_2_5_probability:.1%}")
print(f"Both Score: {results.both_teams_score_probability:.1%}")
print(f"Most Likely Score: {results.most_likely_score}")
```

---

## Modelos Machine Learning

### Modelos Disponibles

1. **Logistic Regression** - Base, interpretable
2. **Random Forest** - Ensamblado, robusto
3. **XGBoost** - Alta precisión, rápido
4. **LightGBM** - Muy rápido, datasets grandes
5. **Voting Ensemble** - Combina todos (RECOMENDADO)

### Entrenamiento

```python
from app.machine_learning.model_trainer import MLModelTrainer

trainer = MLModelTrainer(model_dir="models")

# Preparar datos
X_train, X_test, y_train, y_test = await trainer.prepare_data(X, y)

# Entrenar todos los modelos
metrics = await trainer.train_all_models(X, y)

# Guardar modelos
await trainer.save_models()

# Ver metricas
for model_name, model_metrics in metrics.items():
    print(f"{model_name}: {model_metrics}")
```

### Predicción

```python
# Cargar modelos
await trainer.load_models()

# Hacer predicción
y_pred, y_pred_proba = await trainer.predict(X_new, model_name='voting_ensemble')

# y_pred: predicciones (0/1)
# y_pred_proba: probabilidades [prob_class_0, prob_class_1]
```

### Tipos de Predicción Soportados

```python
PREDICTION_TYPES = {
    'match_winner': ['Home', 'Draw', 'Away'],
    'over_under_2_5': ['Over', 'Under'],
    'over_under_1_5': ['Over', 'Under'],
    'over_under_3_5': ['Over', 'Under'],
    'both_score': ['Yes', 'No'],
    'first_goal': ['Home', 'Away'],
    'last_goal': ['Home', 'Away'],
    'correct_score': ['1-0', '1-1', '2-0', '2-1', ...],
    'double_chance': ['1X', 'X2', '12'],
    'handicap': ['-0.5', '-1.0', '+0.5', ...],
    'corners': ['Over', 'Under'],
    'cards': ['Over', 'Under'],
    'halftime_fulltime': ['Win/Win', 'Draw/Draw', 'Loss/Loss'],
}
```

---

## Análisis de Cuotas - BET ANALYZER

### Función Principal

Analiza value de apuestas comparando probabilidades predichas con implied probabilities de las cuotas.

### Conceptos Clave

**Expected Value (EV)**
```
EV = (Probabilidad * Odds) - 1
```

**ROI (Return on Investment)**
```
ROI = EV * 100%
```

**Kelly Criterion**
```
Kelly = (b*p - q) / b
donde:
  b = odds - 1
  p = probabilidad de ganar
  q = 1 - p
```

**Implied Probability**
```
Implied = 1 / Odds
```

### Uso

```python
from app.analytics.bet_analyzer import BettingAnalyzer

analyzer = BettingAnalyzer(bankroll=1000.0)

# Analizar una apuesta
analysis = analyzer.analyze_bet(
    market='match_winner',
    outcome='Home Win',
    odds=2.45,
    predicted_probability=0.58,
    confidence_level=0.82
)

print(f"EV: {analysis.expected_value_percentage:.2f}%")
print(f"Kelly: {analysis.kelly_percentage:.1%}")
print(f"Stake recomendado: {analysis.recommended_stake_percentage:.1%}")
print(f"Recomendación: {analysis.recommendation}")

# Comparar cuotas entre casas
comparison = analyzer.compare_bookmakers(
    market='match_winner',
    outcome='Home Win',
    predicted_probability=0.58,
    bookmaker_odds={
        'Caliente': 2.45,
        'Bet365': 2.40,
        'Unibet': 2.50,
    }
)

print(f"Mejor casa: {comparison['best_bookmaker']}")
print(f"Mejor odds: {comparison['best_analysis'].odds}")
```

---

## Sincronización de Datos

### Jobs Automáticos

```python
# backend/app/tasks/sync_tasks.py

# Sincronizar equipos (diariamente a las 2 AM)
sync_teams

# Sincronizar partidos (cada hora)
sync_matches

# Sincronizar estadísticas (cada 6 horas)
sync_statistics

# Actualizar cuotas (cada 15 minutos)
sync_odds
```

### Ejecutar Manualmente

```bash
# Desde API
POST http://localhost:8000/api/v1/admin/sync/teams

# Desde CLI
docker-compose exec backend celery -A app.tasks call sync_teams
```

### Adapters Disponibles

#### API-Football (RapidAPI)

```python
from app.adapters.api_football_adapter import APIFootballAdapter

adapter = APIFootballAdapter(api_key='your-key')

# Obtener datos
teams = await adapter.get_teams(league_id=39)
matches = await adapter.get_matches(league_id=39, season=2024)
players = await adapter.get_players(team_id=33)
standings = await adapter.get_standings(league_id=39, season=2024)
statistics = await adapter.get_statistics(match_id=123, team_id=33)
injuries = await adapter.get_injuries(team_id=33)
transfers = await adapter.get_transfers(team_id=33)
odds = await adapter.get_odds(match_id=123)
```

#### Crear Nuevo Adapter

```python
# backend/app/adapters/custom_adapter.py

from app.adapters import BaseAdapter, TeamDTO, MatchDTO, PlayerDTO

class CustomAdapter(BaseAdapter):
    BASE_URL = "https://api.example.com"
    
    async def get_teams(self, league_id: int) -> List[TeamDTO]:
        # Implementar
        pass
    
    async def get_matches(self, league_id: int, season: int) -> List[MatchDTO]:
        # Implementar
        pass
    
    # ... más métodos
```

---

## Deployment

### Producción con Docker Compose

```bash
# Build imágenes
docker-compose -f docker-compose.yml build

# Iniciar (background)
docker-compose up -d

# Ver logs
docker-compose logs -f backend

# Parar
docker-compose down
```

### Variables de Producción

```env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@postgres:5432/stats_db
JWT_SECRET_KEY=valor-super-secreto-cambiar
CORS_ORIGINS=["https://tudominio.com"]
```

### Backup de Base de Datos

```bash
# Backup
docker-compose exec postgres pg_dump -U postgres estadisticas_db > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres < backup.sql
```

### Monitoreo

```bash
# Ver tasks en ejecución
docker-compose exec celery_worker celery -A app.tasks inspect active

# Ver queue
docker-compose exec backend celery -A app.tasks inspect reserved

# Monitor en tiempo real
docker-compose exec celery_worker celery -A app.tasks events
```

---

## Troubleshooting

### Backend no inicia

```bash
# Ver logs
docker-compose logs backend

# Verificar puerto
lsof -i :8000

# Reiniciar
docker-compose restart backend
```

### Base de datos no conecta

```bash
# Verificar PostgreSQL
docker-compose ps postgres
docker-compose logs postgres

# Recrear volumen
docker-compose down -v
docker-compose up -d postgres
```

### Tasks no se ejecutan

```bash
# Verificar RabbitMQ
docker-compose logs rabbitmq

# Reiniciar Celery
docker-compose restart celery_worker celery_beat

# Ver tasks en queue
docker-compose exec backend celery -A app.tasks inspect active
```

### Frontend no ve Backend

```bash
# Verificar conectividad
curl http://localhost:8000/health

# Desde frontend container
docker-compose exec frontend curl http://backend:8000/health
```

---

**Última actualización:** 2026-07-11
**Versión:** 1.0.0
**Rama:** develop
