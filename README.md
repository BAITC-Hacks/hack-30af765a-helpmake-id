# Akim for 5 Hours — AI City Management Simulator

> HackAlem AI 2026 · Astana Innovations Special Track  
> **Status:** Hackathon MVP in development

The working Situation Center UI and Simulation API are documented in
[IMPLEMENTATION.md](IMPLEMENTATION.md). Run those components with the commands there.

## Overview

**Akim for 5 Hours** is an AI-assisted city-management simulator for exploring how a limited municipal budget can affect quality of life across hypothetical districts of Astana.

A user receives the same starting budget and city dataset, makes **exactly five management decisions**, and sees how those decisions change district indicators and the final **Astana Quality of Life Score**.

The product combines two layers:

1. **Deterministic simulation engine** — validates the scenario and calculates all numerical effects.
2. **AI Decision Advisor** — explains the calculated outcome, trade-offs, strengths, risks, and possible improvements.

**Core principle: the LLM explains the simulation; it does not invent or calculate the score.**

---

## Problem

City-development decisions require balancing several areas at the same time:

- transport;
- greening / environment;
- social infrastructure;
- safety;
- city services.

Resources are limited. Improving one area can leave another district or indicator behind. Decision-makers therefore need a way to compare scenarios and understand not only **what score changed**, but **why it changed and what trade-offs were created**.

---

## User

Primary users defined by the challenge:

- city manager;
- city analyst;
- simulator user.

The hackathon MVP is designed as a compact **decision-support simulation**, not as a production municipal information system.

---

## Core User Journey

1. Review the baseline condition of five hypothetical city districts.
2. Receive a fixed virtual budget of **100 units**.
3. Select **exactly 5 initiatives** from the available catalogue.
4. Assign a district when an initiative is district-specific.
5. The validator checks budget, duplicates, category limits, district requirements and incompatible measures.
6. The simulation engine applies costs, implementation lags, effects and synergies.
7. The system recalculates district indicators and the **Astana Quality of Life Score**.
8. The AI Advisor explains the result: strengths, risks, trade-offs and possible next steps.
9. The user can change the five decisions and compare the new outcome.

---

## Challenge Requirements

### Must Have

- [ ] Same virtual budget for every user
- [ ] Decisions across the five specified urban-development areas
- [ ] Automatic budget-overrun prevention
- [ ] AI analysis of selected decisions
- [ ] Astana Quality of Life Score calculation
- [ ] Explanation of strengths, risks and possible consequences
- [ ] Different valid decision sets produce different scores

### Optional / Stretch

- [ ] Comparison of multiple team scenarios
- [ ] Visualization of district indicator changes
- [ ] AI recommendations for improving a scenario
- [ ] Unexpected city events requiring budget reallocation
- [ ] Automatic short presentation generation

---

## Simulation Dataset

The provided hackathon dataset is synthetic and contains no personal or restricted data.

### Districts

| District | Population share | Baseline district score | Main profile |
|---|---:|---:|---|
| Esil | 0.27 | 62.99 | Strong overall; congestion and school capacity pressure |
| Almaty | 0.24 | 57.06 | Aging utilities and congestion |
| Saryarka | 0.20 | 54.65 | Air pollution and weak greening |
| Baikonur | 0.13 | 56.63 | Relatively balanced |
| Nura | 0.16 | 49.18 | Weakest social-infrastructure and transport profile |

### Indicators

Each district has 10 indicators on a 0–100 scale:

| Code | Area | Indicator |
|---|---|---|
| T1 | Transport | Road congestion |
| T2 | Transport | Public transport accessibility |
| E1 | Environment | Greening |
| E2 | Environment | Air quality |
| S1 | Social | Schools and kindergartens |
| S2 | Social | Clinics and primary healthcare |
| B1 | Safety | Street safety |
| B2 | Safety | Road safety |
| C1 | Services | Utility reliability |
| C2 | Services | Speed of resolving resident requests |

---

## Initiative Catalogue

The simulation currently defines **14 possible measures**.

Examples include:

- dedicated bus lanes;
- adaptive smart traffic lights;
- LRT expansion;
- parks and public green spaces;
- clean-fuel conversion;
- city greening;
- school + kindergarten construction;
- family health centre;
- neighbourhood sport hubs;
- Safe City lighting and cameras;
- safe crossings and school zones;
- unified resident-request platform;
- heat/water network modernization;
- utility emergency teams and early warning.

Each measure has:

- cost;
- area;
- district/city scope;
- implementation lag;
- numerical effects on one or more indicators.

The engine also supports defined **synergies** and **incompatibilities** between measures.

---

## Scenario Rules

A valid scenario must satisfy all challenge rules:

- budget = **100**;
- exactly **5 decisions**;
- no repeated initiative;
- district must be selected for district-level measures;
- city-level measures do not take a district;
- maximum **2 initiatives from the same area**;
- incompatible measures cannot be selected together;
- decision order does not affect the result.

Invalid scenarios do not receive a score. The validator returns the reason.

---

## Simulation Model

The simulation horizon is **8 quarters (2 conditional years)**.

For an initiative with implementation lag `L`, the realized share of its full effect is:

```text
realized_effect = (8 - L) / 8
```

For district `d` and indicator `k`:

```text
I'₍d,k₎ = clip(
  I₍d,k₎
  + Σ(measure_effect × realized_effect)
  + synergies,
  0,
  100
)
```

### Indicator Weights

| Indicator | T1 | T2 | E1 | E2 | S1 | S2 | B1 | B2 | C1 | C2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Weight | .10 | .10 | .09 | .11 | .11 | .11 | .09 | .09 | .10 | .10 |

The district score is:

```text
D_d = Σ(weight_k × indicator'_d,k)
```

The city average is population-weighted:

```text
D_avg = Σ(population_share_d × D_d)
```

### Astana Quality of Life Score

```text
Score = 0.7 × D_avg
      + 0.3 × min(D_d)
      - 1.0 × N_crit
```

Where `N_crit` is the number of district × indicator pairs strictly below **40** after all effects.

### Why this matters

The model deliberately rewards both:

- overall city improvement; and
- improvement of the weakest district.

This prevents a strategy from maximizing already strong districts while leaving critical urban problems unresolved.

**Baseline score without interventions: 52.56.**

---

## AI Decision Advisor

The AI layer receives **calculated structured results** from the simulation engine, for example:

- selected initiatives;
- total cost and remaining budget;
- baseline and resulting indicators;
- district deltas;
- contribution of each measure;
- triggered synergies;
- unresolved critical indicators;
- final score.

The AI then generates a human-readable decision brief.

### AI responsibilities

- explain why the score changed;
- identify strengths of the scenario;
- identify remaining risks;
- describe major trade-offs;
- explain which districts benefited;
- compare scenarios;
- suggest alternative decisions using the available initiative catalogue.

### AI must NOT

- calculate the authoritative score;
- invent indicator values;
- change the simulation rules;
- silently override an invalid scenario;
- present unsupported claims as dataset facts.

This separation keeps the numerical result **deterministic, reproducible and testable**, while using AI where natural-language reasoning is useful.

---

## Smart City Context

The project is informed by the provided **Smart City concept** materials.

The source material frames Smart City around:

- safe and comfortable living conditions;
- effective city management;
- transport and logistics;
- social services;
- safety;
- utilities and environment;
- data-driven city management.

Several initiatives in the simulator map naturally to Smart City concepts such as adaptive traffic management, Safe City, resident-request services, utility monitoring, greening and situation-centre analytics.

### Situation Center Concept

For the MVP, we use the **city situation center** as the main product metaphor:

```text
City data
   ↓
District indicators
   ↓
Management decisions
   ↓
Simulation Engine
   ↓
New city state + Quality of Life Score
   ↓
AI Decision Advisor
```

The long-term direction could connect this decision-simulation layer to richer GIS or digital-twin systems. The hackathon MVP itself does **not** claim to be a full digital twin.

---

## Proposed MVP Interface

### Header

- current Astana Quality of Life Score;
- remaining budget;
- decisions selected: `0/5`.

### District Overview

A visual overview of the five districts and their key indicators.

### Initiative Panel

Cards for available measures showing:

- category;
- cost;
- implementation lag;
- target scope;
- expected indicator effects.

### Scenario Panel

The five selected decisions, validation state and total cost.

### Simulation Result

After **Simulate**:

- score before → after;
- district before → after;
- indicator deltas;
- critical indicators;
- synergies;
- AI explanation.

---

## Architecture

Target MVP architecture:

```text
┌──────────────────────────────┐
│          Frontend            │
│  Districts / Decisions / UI  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│           Backend            │
│ Validation + Scenario API    │
└──────────────┬───────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌─────────────┐   ┌──────────────┐
│ Simulation  │   │ AI Advisor   │
│   Engine    │   │ LLM / API    │
│ deterministic│  │ explanation  │
└──────┬──────┘   └───────┬──────┘
       │                   │
       └─────────┬─────────┘
                 ▼
        ┌────────────────┐
        │ Scenario Result│
        └────────────────┘
```

The exact implementation stack will be documented as development progresses.

---

## Demo Scenario

A demo should answer one question:

> **What happens when an Akim has a limited budget and must choose between competing city needs?**

Suggested flow:

1. Show the city baseline: **52.56**.
2. Highlight weak district/indicator combinations.
3. Select five initiatives while staying within budget.
4. Run the simulation.
5. Show before/after district and city metrics.
6. Show the new Quality of Life Score.
7. Let the AI Advisor explain the result and trade-offs.
8. Change one decision and demonstrate that the score and explanation change.

---

## Evaluation Alignment

The hackathon task defines the following evaluation structure:

| Criterion | Points |
|---|---:|
| Task compliance and functionality | 25 |
| Technical implementation | 25 |
| README and reproducibility | 25 |
| Value and applicability | 15 |
| Development potential and originality | 10 |
| **Total** | **100** |

This repository is therefore being developed with emphasis on:

- a complete working core flow;
- deterministic and verifiable calculations;
- clear separation between simulation and AI;
- reproducibility;
- transparent documentation;
- a concise live demo.

---

## Repository Documentation Plan

As implementation progresses, this README will be extended with:

- [ ] exact technology stack;
- [ ] repository structure;
- [ ] local installation;
- [ ] environment variables;
- [ ] API configuration;
- [ ] database setup;
- [ ] run commands;
- [ ] tests;
- [ ] deployment instructions;
- [ ] API examples;
- [ ] screenshots;
- [ ] final demo link;
- [ ] AI / third-party disclosure.

---

## AI & Third-Party Disclosure

This project uses AI-assisted development.

Current/prepared tooling may include:

- ChatGPT — product analysis, documentation, prompt engineering and development assistance;
- Codex — code assistance;
- OpenAI API — candidate runtime AI provider;
- NVIDIA API — available hackathon resource; runtime usage will be documented if integrated.

The final README will distinguish between:

- AI-generated code/content;
- AI-assisted work;
- third-party libraries/services;
- code and product decisions implemented directly by the team.

---

## Current Status

**Hackathon MVP — active development.**

The current specification, simulation dataset and Smart City reference materials have been analyzed. The immediate objective is to implement the smallest end-to-end flow:

```text
Baseline → 5 decisions → validation → simulation → score → AI explanation
```

---

## Team

HackAlem AI 2026 hackathon team.

Roles:

- **Product / Prompt Engineering / Documentation**
- **Backend / Integrations**
- **Frontend / UX**

---

## Disclaimer

This is a **hackathon prototype** using a synthetic dataset and conditional costs/effects. It is intended to demonstrate a city-management decision-simulation approach and should not be interpreted as a production municipal planning system or as a factual forecast of real-world policy outcomes.
