# Architecture & Product Decisions

This log records decisions that materially affect the Akim AI MVP. It is intentionally short: implementation details belong in code and dedicated technical documentation.

## ADR-001 — The LLM does not calculate the score

**Decision:** All authoritative numerical results are produced by the deterministic Simulation Engine.

**Reason:** Reproducibility, testability and protection from hallucinated calculations.

**Consequence:** Frontend and AI consume backend results; neither independently calculates the official score.

## ADR-002 — AI receives structured simulation results

**Decision:** AI Advisor receives structured calculated facts rather than being asked to simulate the city from raw natural-language instructions.

**Reason:** Keep the backend as the source of truth and make AI output auditable.

## ADR-003 — Submitted simulation results are revalidated

**Decision:** Before AI analysis, backend recalculates the submitted decisions and checks key fields against the authoritative result.

**Reason:** Prevent stale or client-altered values from becoming AI “facts”.

## ADR-004 — AI failure must not break the simulator

**Decision:** AI Advisor is optional at runtime. Provider failure returns an unavailable state.

**Reason:** The core value—validation, simulation, score and Before/After—must remain usable during provider/API failure and live demo instability.

## ADR-005 — Evidence-based AI explanations

**Decision:** The target Advisor contract requires material claims to be tied to evidence from the structured simulation result.

**Reason:** Make explanations inspectable and reduce unsupported claims.

## ADR-006 — Human remains the decision-maker

**Decision:** AI explains consequences and may suggest a scenario to compare, but does not declare a universally correct city-management choice.

**Reason:** The product is decision support, not an autonomous municipal decision-maker.

## ADR-007 — Level 1 before stretch features

**Decision:** The team completes the end-to-end Level 1 flow before implementing optional features.

**Level 1:**

```text
Situation Center
→ 5 decisions
→ validation
→ simulation
→ Before / After
→ Quality of Life Score
→ AI explanation
```

**Reason:** A stable challenge-compliant demo has higher priority than multiple incomplete features.

## ADR-008 — Situation Center is the primary UX metaphor

**Decision:** The main interface presents the city as a current state with district problems, budget and decisions—not as a generic chatbot.

**Reason:** Users should understand the city state before choosing initiatives.

## ADR-009 — Time is modeled through implementation lag in Level 1

**Decision:** Level 1 simulates the provided eight-quarter horizon mathematically without requiring a full turn-by-turn game loop.

**Reason:** Preserve the challenge model while keeping the MVP achievable and clear.

## ADR-010 — Smart City and game references are context, not claims

**Decision:** Supplied Smart City materials inform product framing and Situation Center concepts. Turn-based strategy products may inspire the state → decision → consequence UX loop.

**Reason:** Avoid claiming unsupported real-world deployment, a full digital twin, or features that are not implemented.

## ADR-011 — Stretch feature ladder

After Level 1 is stable:

1. **Level 2 — PLUS:** scenario comparison and stronger visualization.
2. **Level 3 — AI:** goal-based AI recommendations and validated agent loop.
3. **Level 4 — GAME:** deterministic city events, timeline, natural-language intent mapping.
4. **Level 5 — WOW:** experimental AI-Akim mode and human/AI strategy comparison.

Each level is optional and must not destabilize the previous one.

## ADR-012 — Documentation follows implemented reality

**Decision:** README distinguishes implemented, in-progress and stretch functionality.

**Reason:** Repository documentation must remain reproducible and must not present roadmap ideas as completed features.
