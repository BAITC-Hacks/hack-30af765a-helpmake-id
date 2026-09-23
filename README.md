# Akim for 5 Hours — AI City Management Simulator

> HackAlem AI 2026 · Astana Innovations Special Track  
> **Status:** Level 1 MVP in active development

## What we are building

**Akim AI** is a city-management decision simulator. A user receives a synthetic city state and a fixed budget of **100 units**, selects **exactly five initiatives**, and sees how those choices change district indicators and the **Astana Quality of Life Score**.

The product is designed around one principle:

> **The Simulation Engine calculates. AI explains. The human decides.**

The goal is not to tell a city manager what the “right” decision is. The goal is to make the consequences and trade-offs of a scenario visible before comparing it with another scenario.

## Core flow

```text
City State
   ↓
5 Decisions
   ↓
Validator
   ↓
Deterministic Simulation Engine
   ↓
Structured Simulation Result
   ├──→ Before / After UI
   └──→ AI Decision Advisor
             ↓
       Grounded explanation
```

Level 1 is complete only when this flow works end-to-end:

```text
Baseline → 5 decisions → validation → simulation → score → before/after → AI explanation
```

## Current implementation status

### Implemented in backend

- [x] Synthetic city dataset and version/hash
- [x] Five districts and ten indicators
- [x] Catalogue of 14 initiatives
- [x] Budget and scenario rules
- [x] Scenario validator
- [x] Implementation lag
- [x] Positive and negative effects
- [x] Synergies and incompatibilities
- [x] Indicator clipping to 0–100
- [x] District scoring
- [x] Astana Quality of Life Score
- [x] Baseline verification: **52.56**
- [x] Deterministic order-independent simulation
- [x] `POST /api/v1/simulate`
- [x] Structured before/after results
- [x] Measure contributions and activated synergies
- [x] `POST /api/v1/advisor/explain` foundation
- [x] AI-provider fallback
- [x] Protection against stale/altered simulation results
- [x] Domain tests for validation and simulation

### In progress

- [ ] Final evidence-based AI Advisor contract
- [ ] Situation Center frontend
- [ ] Five-initiative selection UX
- [ ] Before / After visualization
- [ ] AI Advisor UI
- [ ] Frontend/backend end-to-end integration
- [ ] Live demo verification

### Stretch after Level 1

- Scenario A/B comparison
- AI strategy recommendations
- City events
- Eight-quarter timeline
- Natural-language intent → structured initiative
- “AI Akim” experimental mode

## Scenario rules

A valid scenario must satisfy:

- budget: **100**;
- exactly **5 decisions**;
- no duplicate initiative;
- district required for district-scoped measures;
- no district for city-scoped measures;
- maximum **2 initiatives from one direction**;
- incompatible measures cannot be selected together;
- decision order does not change the result.

Invalid scenarios do not receive a score.

## Simulation model

The horizon is **8 quarters**. For a measure with lag `L`:

```text
realized_effect = effect × (8 - L) / 8
```

District indicators are updated deterministically from the provided dataset, applicable measure effects and activated synergies, then clipped to the 0–100 range.

The final score is:

```text
Score = 0.7 × D_avg
      + 0.3 × min(D_d)
      - 1.0 × N_crit
```

where `D_avg` is the population-weighted city result, `min(D_d)` is the weakest district score, and `N_crit` is the number of district/indicator pairs strictly below 40.

**Verified baseline:** `52.56`.

## AI Advisor: grounding and safety

The AI Advisor is **not** the source of mathematical truth.

The backend recalculates the submitted scenario before calling the AI provider and rejects a stale or altered simulation result. The advisor receives calculated structured facts rather than being asked to simulate the city itself.

The Advisor must:

- use only facts supplied by the backend;
- never calculate or overwrite the authoritative score;
- avoid unsupported causal claims;
- mention synergies only when activated by the engine;
- distinguish facts from suggestions;
- keep the final management decision with the user.

If the AI provider is unavailable, the deterministic simulation, score and Before/After results must continue to work.

See [AI Advisor specification](docs/AI_ADVISOR.md).

## Repository structure

```text
/
├── README.md
├── backend/
│   ├── api/
│   │   ├── controllers/
│   │   ├── schemas/
│   │   ├── v1/endpoints/
│   │   └── webhooks/
│   ├── data/
│   │   ├── city_data.json
│   │   ├── measures.json
│   │   └── rules.json
│   ├── tests/
│   ├── docs/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── pyproject.toml
├── design/
└── docs/
    ├── AI_ADVISOR.md
    └── DECISIONS.md
```

## API

Current Level 1 endpoints include:

```text
POST /api/v1/simulate
POST /api/v1/advisor/explain
```

The backend also exposes health/readiness endpoints and OpenAPI documentation.

## Testing

Current domain tests verify, among other cases:

- baseline score;
- critical threshold behavior;
- decision count;
- duplicate and unknown measures;
- district requirements;
- budget overflow;
- direction limits;
- incompatibilities;
- negative effects;
- synergies;
- clipping;
- deterministic order independence;
- AI-provider failure handling;
- rejection of unsupported numeric AI output.

## Product context

The supplied Smart City materials inform the **Situation Center** product metaphor and the interpretation of city initiatives. The hackathon MVP does **not** claim to be a production municipal system or a full digital twin.

Ideas from turn-based simulation products are used only as UX inspiration for the loop:

**state → decision → consequence → new state**.

## Architecture decisions

Key engineering/product decisions are recorded in [docs/DECISIONS.md](docs/DECISIONS.md).

## AI & third-party disclosure

AI-assisted development is used in this project. Current/prepared tools include:

- ChatGPT — product analysis, documentation and prompt design;
- Codex — development assistance;
- OpenAI-compatible API — runtime AI Advisor provider when configured;
- NVIDIA API credits — available to the team, but not claimed as a runtime dependency unless actually integrated.

Final submission documentation will distinguish AI-assisted work, runtime AI services, third-party libraries and team-authored product decisions.

## Team responsibilities

- **Product / Prompt Engineering / Documentation** — product scope, AI contract, README, QA, demo and pitch.
- **Backend / Integrations** — dataset, validator, simulation engine, scoring, API, AI integration and tests.
- **Frontend / UX** — Situation Center, initiative selection, Before/After visualization and Advisor UI.

## Documentation

- [AI Advisor contract](docs/AI_ADVISOR.md)
- [Architecture decisions](docs/DECISIONS.md)
- Backend development log: `backend/docs/development-log.md`

## Disclaimer

This is a **hackathon prototype** based on a synthetic dataset and conditional costs/effects. It demonstrates a decision-simulation approach and must not be interpreted as a factual forecast of real municipal policy outcomes.
