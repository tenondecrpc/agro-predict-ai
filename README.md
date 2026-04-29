# AgroBuy - Copiloto Inteligente de Compras

> Hackathon Deep Dive 2026. Verticalizacion del desafio oficial
> "Copiloto Inteligente de Compras" al sector cooperativas agro
> paraguayas.
>
> Stack: Oracle APEX (UI buyer-facing) + FastAPI + LangGraph
> orchestration + 4 LLM agents + ML supplier predictor + scoring
> dual con datos climaticos en vivo (Open-Meteo).

## Contexto

El brief oficial pide un copiloto que registre solicitudes, cargue
cotizaciones, compare alternativas, recomiende una opcion justificada
y genere mensajes de negociacion - todo sobre Oracle APEX, con
agentes de IA. AgroBuy verticaliza ese desafio al sector agro PY:
Cooperativa Yguazu (Itapua) comprando urea, semilla y agroquimicos
para la zafra de soja 26/27.

**Diferenciadores tecnicos** (vs el wrapper de LLMs tipico):

1. **4 agentes LLM** con propositos distintos (extractor, comparador,
   recomendador, negociador) - todos con fallback deterministico.
2. **ML predictor real** (`GradientBoostingClassifier`, AUC 0.748
   sobre 329 muestras sinteticas) para probabilidad de cumplimiento
   de proveedor.
3. **Anomaly detection** sobre precios contra bandas del catalogo agro.
4. **Dual scoring**: Urgency (0.45 weather + 0.40 stock + 0.15
   volatility) + Offer (0.35 supplier ML + 0.40 terms + 0.25
   delivery risk) con matriz de decision explicable.
5. **Open-Meteo en vivo** para riesgo climatico por departamento PY,
   y FX USD/PYG en vivo para normalizacion de cotizaciones.
6. **APEX + REST**: APEX es consumidor puro de la API; cero
   duplicacion de schema.

**Plan de producto vinculante**: ver
[`compras/COMPRAS_AGRO_plan.md`](compras/COMPRAS_AGRO_plan.md).
Plan de desarrollo ejecutable: [`compras/DEV_PLAN.md`](compras/DEV_PLAN.md).

## Status

| Fase | Componente | Estado |
|---|---|---|
| 0 | Bootstrap del repo + scaffold | hecho |
| 1 | Domain layer (spec 018): requests, suppliers, quotations, audit, RLS | hecho |
| 2 | External signals: Open-Meteo + FX USD/PYG con cache 6h/1h | hecho |
| 3 | Scoring + ML: dual score + GBM predictor + anomaly | hecho |
| 4 | LLM agents: extractor + comparator + recommender + negotiator | hecho |
| 5 | Orchestrator + 3 endpoints (extract, recommend, negotiate) | hecho |
| 6 | APEX app (spec 021) - **build guide listo, app por construir** | en curso |
| 7 | Fixtures + seed CLI (8 proveedores, 5 solicitudes, 15 cotizaciones, 157 deliveries) | hecho |

**62/62 tests procurement verdes**. **528 tests totales**. Lint clean.
Smoke E2E contra Postgres + Open-Meteo + open.er-api.com en vivo
funcionando.

## Quick start (Git Bash, Windows)

Pre-requisitos: Docker Desktop corriendo, [uv](https://docs.astral.sh/uv/),
Python 3.12 (uv lo gestiona si no esta).

```bash
cd /c/Users/franc/Desktop/hackaton/agro-predict-ai-main

# 1. Levantar infra (Postgres + Redis + ARQ worker)
docker compose --profile worker up -d

# 2. Sincronizar deps de backend
uv sync --project backend --dev

# 3. Cargar variables de entorno (Fernet key, webhook secret, db urls)
set -a; source .env.local; set +a

# 4. Aplicar migraciones (incluye las 5 procurement: 0021..0025)
uv run --project backend python -c "
from backend.persistence.migrations import MigrationRunner
print(MigrationRunner().ensure_current().current_revision)
"

# 5. Entrenar el predictor ML (ya esta entrenado en backend/models/, pero re-correr no rompe)
uv run --project backend python -m backend.procurement.ml.train

# 6. Cargar datos demo (8 proveedores agro PY, 5 solicitudes, 15 cotizaciones, 157 deliveries)
uv run --project backend python -m backend.procurement.fixtures.seed

# 7. Levantar el backend
uv run --project backend uvicorn backend.app:app --host 127.0.0.1 --port 8000

# 8. (otra terminal) verificar
curl -s http://127.0.0.1:8000/healthz | python -m json.tool
curl -s "http://127.0.0.1:8000/api/v1/procurement/requests?tenant_id=tenant-yguazu&team_id=team-compras" | python -m json.tool
```

**Endpoints clave** (ver `/docs` para Swagger):

| Method | Path | Que hace |
|---|---|---|
| `POST` | `/api/v1/procurement/requests/{id}/recommend` | Pipeline completa: load -> ML -> anomaly -> scoring -> compare LLM -> recommend LLM -> persist |
| `POST` | `/api/v1/procurement/quotations/extract` | LLM extractor (texto crudo -> JSON estructurado) |
| `POST` | `/api/v1/procurement/quotations/{id}/negotiate` | LLM negotiator (email tono agro PY) |
| `GET` | `/api/v1/procurement/weather/risk` | Open-Meteo + scoring 0-100 + cache 6h |
| `GET` | `/api/v1/procurement/fx/usd_pyg` | Tipo de cambio + cache 1h + fallback |

## Estructura del repo

```
agro-predict-ai-main/
+-- backend/
|   +-- alembic/versions/             # 25 migraciones (las nuestras: 0022-0025)
|   +-- src/backend/
|   |   +-- procurement/              # MODULO PRINCIPAL DEL HACKATON
|   |   |   +-- models.py             # Pydantic: PurchaseRequest, Quotation, Supplier, etc.
|   |   |   +-- repository.py         # Postgres + InMemory con RLS
|   |   |   +-- service.py            # CRUD + audit
|   |   |   +-- data_quality_gate.py  # Validity / currency / lead time / units
|   |   |   +-- decision_repository.py # Scores, recommendations, negotiation messages, history
|   |   |   +-- orchestrator.py       # Pipeline end-to-end (load -> ML -> score -> agents -> persist)
|   |   |   +-- api.py                # Router /api/v1/procurement/*
|   |   |   +-- agents/               # Fase 4: 4 LLM agents
|   |   |   |   +-- base.py           # JSON extraction, safe_complete, fallback helpers
|   |   |   |   +-- prompts.py        # Prompts en ingles (per AGENTS.md)
|   |   |   |   +-- schemas.py        # ExtractedQuotation, ComparisonResult, Recommendation, NegotiationMessage
|   |   |   |   +-- extractor.py      # Texto crudo -> JSON
|   |   |   |   +-- comparator.py     # N quotes -> comparativa normalizada
|   |   |   |   +-- recommender.py    # comparativa + scores -> markdown
|   |   |   |   +-- negotiator.py     # quote + brechas -> email Spanish
|   |   |   +-- ml/                   # Fase 3: ML supplier predictor + anomaly detector
|   |   |   |   +-- supplier_predictor.py  # GBM + rules fallback
|   |   |   |   +-- anomaly_detector.py    # Z-score sobre catalog bands
|   |   |   |   +-- features.py            # 9 features per supplier
|   |   |   |   +-- train.py               # CLI: synthetic dataset + train + persist .joblib
|   |   |   +-- scoring/              # Fase 3: dual scoring
|   |   |   |   +-- urgency.py        # 0.45 weather + 0.40 delivery + 0.15 volatility
|   |   |   |   +-- offer.py          # 0.35 supplier + 0.40 terms + 0.25 (100-risk)
|   |   |   |   +-- decision_matrix.py
|   |   |   +-- external/             # Fase 2: Open-Meteo + FX
|   |   |   |   +-- weather.py        # Open-Meteo client + risk score
|   |   |   |   +-- fx.py             # open.er-api.com + fallback configurable
|   |   |   |   +-- departments.py    # 17 dpto PY -> coords
|   |   |   |   +-- repository.py
|   |   |   |   +-- service.py        # Cache-aside
|   |   |   +-- fixtures/             # Fase 7: seed demo data
|   |   |       +-- agro_data.py      # 8 proveedores, 6 catalogo, 5 solicitudes, 15 cotizaciones
|   |   |       +-- seed.py           # CLI: wipe + reseed contra Postgres
|   |   +-- llm/                      # adapter LLM compartido (existente del repo)
|   |   +-- predictions/              # pipeline agronomic (NO usamos, queda intacto)
|   |   +-- integrations/oracle_apex/ # adapter APEX read-only + write-back (heredado)
|   |   +-- ...                       # tenancy, billing, observability, etc. (plataforma base)
|   +-- models/
|   |   +-- procurement_supplier_predictor_v1.joblib  # GBM entrenado, AUC 0.748
|   |   +-- corn_rf_v1.0.0_*.joblib                   # modelo corn agronomic (no usado)
|   +-- tests/
|       +-- integration/
|           +-- test_procurement_domain.py            # 12 tests
|           +-- test_procurement_external_signals.py  # 10 tests
|           +-- test_procurement_scoring_and_ml.py    # 20 tests
|           +-- test_procurement_agents.py            # 11 tests
|           +-- test_procurement_orchestrator.py      # 9 tests
+-- compras/
|   +-- COMPRAS_AGRO_plan.md          # Plan vinculante (verticalizacion agro)
|   +-- COMPRAS_plan.md               # Plan generico de respaldo
|   +-- DEV_PLAN.md                   # Plan de desarrollo ejecutable (7 fases)
+-- operations/apex/                  # Build guide para Fase 6 (APEX app)
|   +-- README.md                     # Indice + arquitectura + tiempos
|   +-- 01_prerequisites.md           # APEX workspace + ngrok + seed
|   +-- 02_workspace_setup.md         # App shell, app items, theme
|   +-- 03_rest_sources.md            # 16 REST Data Sources al backend
|   +-- 04_pages/                     # Build guide pagina por pagina
|   |   +-- 01_login.md               # Mock role selector
|   |   +-- 02_inbox.md               # Lista de solicitudes
|   |   +-- 03_create_request.md      # Form de creacion
|   |   +-- 04_request_detail.md      # Detalle + cotizaciones
|   |   +-- 05_upload_quotation.md    # Extractor IA
|   |   +-- 06_compare_recommend.md   # STAR PAGE
|   +-- 05_demo_script.md             # 90 segundos del demo arc
|   +-- 06_export_checklist.md        # Pre-export + import + tag
+-- specs/                            # SpecKit features (006, 018-021 son las nuestras)
|   +-- 018-procurement-domain/       # spec.md + plan.md
|   +-- 019-procurement-decision-pipeline/
|   +-- 020-procurement-negotiation-assistant/
|   +-- 021-procurement-apex-application/
+-- agro_procurement_weather_scoring.md  # Fundamentacion del scoring climatico
+-- frontend/                         # Vite/React (operator console del upstream, no del comprador)
+-- helm/, k8s/                       # NO usados en el hackaton
+-- AGENTS.md                         # Guia para agentes / repo conventions
+-- CLAUDE.md                         # Bootstrap defers a AGENTS.md
+-- .env.example, .env.local          # .env.local gitignored
```

## Demo arc (90 segundos)

Ver [`operations/apex/05_demo_script.md`](operations/apex/05_demo_script.md).
Resumen:

1. Login como Comprador (Ana Rojas, Cooperativa Yguazu).
2. Inbox: 5 solicitudes activas; abrir la de urea zafra soja 26/27.
3. Detalle: 4 cotizaciones recibidas; click "Comparar y recomendar".
4. Tabla normalizada con FX del dia; Atlantic flagged anomaly.
5. Pipeline corre 3 segundos. Recomendacion: **Tecnomyl**, score 65,
   banda `buy_with_followup`. 3 score cards visibles. Markdown con
   citas a ML p_on_time, weather risk, supplier history.
6. "Generar mensaje de negociacion": email Spanish 250 palabras,
   tono agro PY, listo para enviar.
7. (Opcional) Switch a rol Director, dashboard ejecutivo.

## Pending work (estado al 2026-04-29)

### Critico para el demo

- [ ] **Construir las 6 paginas APEX** siguiendo
      `operations/apex/04_pages/`. Tiempo estimado: 4 horas.
      Prioridad: P1 + P2 + P4 + P6. Si hay tiempo: P3 + P5.
- [ ] **ngrok configurado** y URL inyectada como `BACKEND_URL` en
      APEX antes de cada demo.
- [ ] **LLM keys**: setear `LLM_ENABLED=true` + `LLM_API_KEY` en
      `.env.local` para que los agentes usen el LLM real (sino quedan
      en modo `fallback` deterministico, que tambien funciona pero el
      pitch es mejor con LLM real).
- [ ] **Pre-warm LLM** con un call dummy 30s antes del demo para
      evitar cold start.
- [ ] **Video de respaldo** del demo grabado, por si falla la
      conectividad.
- [ ] **Ensayar** el demo arc 2 veces.

### Polish opcional

- [ ] Ajustar bandas del catalogo agro para que Atlantic salga
      claramente como anomalia (actualmente con FX live el flag puede
      moverse). Editar `procurement/fixtures/agro_data.py` y re-seed.
- [ ] **Frontend Lovable** alternativo o complementario al APEX,
      apuntando a los mismos endpoints REST. Prompt listo en chat
      anterior si lo querias.
- [ ] **Pagina 7 (catalogo proveedores)** y **pagina 8 (dashboard
      ejecutivo)** en APEX si sobra tiempo - no son criticas.
- [ ] PDF parser real para el extractor (actualmente solo texto). Ver
      `procurement/agents/extractor.py` - agregar `pypdf` y vision
      branch.
- [ ] Exponer history per supplier en un endpoint (`GET
      /api/v1/procurement/suppliers/{id}/history`) si APEX quiere
      mostrarla.

### Tests / robustez

- [ ] Tests de integracion contra Postgres real (los actuales usan
      InMemory para velocidad). El smoke E2E ya valida el path de
      Postgres pero no esta en CI.
- [ ] Test de carga del orchestrator con 50+ cotizaciones simultaneas
      (no es realista para procurement pero buen para defender
      escalabilidad si el jurado pregunta).
- [ ] Mock del LLM en tests del orchestrator para verificar que el
      Markdown del recomendador tiene el formato esperado (actualmente
      solo verificamos que arranca con `## Recommendation:`).

### Hardening que NO hace falta para el demo

- LangGraph state machinery sobre el orchestrator (actualmente es
  Python lineal). El plan menciona reusar `predictions/graph.py` -
  refactor de 1 dia, no lo hagas pre-demo.
- LangSmith tracing para debugging de los agentes en vivo. Util en
  produccion, irrelevante para el demo.
- Deploy a OCI Compute / Render. Solo necesario si querias presentar
  con APEX en cloud apuntando a un backend remoto fijo (en lugar de
  ngrok). Ver tabla en `operations/apex/01_prerequisites.md`.

## Comandos utiles

```bash
# Tests procurement (rapido, sin DB)
uv run --project backend pytest backend/tests/integration/test_procurement_*.py

# Lint
uv run --project backend ruff check backend/src/backend/procurement

# Re-seed demo
uv run --project backend python -m backend.procurement.fixtures.seed

# Re-train ML predictor
uv run --project backend python -m backend.procurement.ml.train

# Aplicar migraciones
uv run --project backend python -c "
from backend.persistence.migrations import MigrationRunner
print(MigrationRunner().ensure_current())
"

# Ngrok para exponer a APEX
ngrok http 8000
```

## Built on AgroPredict AI

Este proyecto se construye sobre la plataforma AgroPredict AI - un
sistema multi-agente para prediccion agropecuaria con LangGraph,
FastAPI, Postgres y Oracle APEX adapter. El modulo
`backend/src/backend/procurement/` corre en paralelo al pipeline
agronomic original (`backend/src/backend/predictions/`); ambos
coexisten sin tocarse.

Capas reutilizadas tal cual:
- `backend.llm.adapter` - LLM client + circuit breaker
- `backend.integrations.oracle_apex` - APEX adapter (no usado en
  este flujo pero queda disponible)
- `backend.persistence` - Postgres connection + RLS GUC pattern
- `backend.queue` - ARQ worker

Reglas del repo: ver [`AGENTS.md`](AGENTS.md). Convencion principal:
ingles en codigo y docs; ASCII puro (sem em-dashes); tests primero
para todo lo que toca el pipeline de produccion.

## Licencia

Hackathon project. No production-ready. Ver upstream LICENSE para
los componentes heredados.
