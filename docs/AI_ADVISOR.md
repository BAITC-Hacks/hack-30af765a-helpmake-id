# AI Advisor V1 — Evidence-Based Contract

## Purpose

AI Advisor explains an **already calculated** Akim AI simulation result. It is not the Simulation Engine and is not allowed to create authoritative numerical results.

**Principle:** Simulation Engine calculates. AI explains. Human decides.

## Responsibilities

**Product / AI logic**
- defines the Advisor contract and system prompt;
- reviews grounding and explanation quality;
- maintains factual test cases.

**Backend**
- builds the authoritative advisor context;
- revalidates/recalculates submitted simulation results;
- calls the configured OpenAI-compatible provider;
- validates structured output;
- returns a safe unavailable state on provider failure.

**Frontend**
- renders summary, strengths, risks, trade-offs, synergies, next scenario and evidence;
- keeps the deterministic result visible even if AI is unavailable.

## Source of truth

The only factual source for the Advisor is the structured context produced by the backend from the current deterministic simulation.

The Advisor must not use external facts about Astana, hidden assumptions, previous conversations or invented statistics.

## Recommended input

The backend should provide only fields needed for explanation:

```json
{
  "validation": {"valid": true, "errors": []},
  "scenario": {
    "budget_initial": 100,
    "budget_spent": 95,
    "budget_remaining": 5,
    "decisions": []
  },
  "score": {
    "before": 52.56,
    "after": 56.54,
    "delta": 3.99
  },
  "districts": [],
  "critical_indicators": {"before": [], "after": []},
  "activated_synergies": [],
  "measure_contributions": [],
  "indicator_definitions": {}
}
```

The backend supplies `before`, `after` and `delta`; the LLM does not calculate them.

## Target output

```json
{
  "summary": {
    "title": "string",
    "text": "string"
  },
  "strengths": [
    {
      "scope": "district|city|measure",
      "target": "string",
      "text": "string",
      "evidence": ["string"]
    }
  ],
  "risks": [
    {
      "scope": "district|city|indicator",
      "target": "string",
      "text": "string",
      "evidence": ["string"]
    }
  ],
  "tradeoffs": [
    {
      "text": "string",
      "evidence": ["string"]
    }
  ],
  "synergies": [
    {
      "measures": ["string"],
      "text": "string"
    }
  ],
  "next_scenario": {
    "goal": "string",
    "suggestion": "string",
    "reason": "string"
  }
}
```

## Grounding rules

1. **Facts only from input.** Missing information is unknown.
2. **No independent mathematics.** Do not recalculate score, deltas, costs or effects.
3. **Evidence required.** Every material conclusion must point to input evidence.
4. **No invented causality.** Attribute a change to a measure only when `measure_contributions` or equivalent backend data establishes that link.
5. **No invented synergies.** Mention only `activated_synergies`.
6. **No invented thresholds.** Critical status comes from backend data/rules.
7. **No policy verdict.** Suggestions are scenarios to compare, not “correct” decisions.
8. **Human control.** The user makes the final management decision.

## System prompt V1

```text
Ты — AI Decision Advisor в городском симуляторе Akim AI.

Твоя задача — объяснять результаты уже выполненной математической симуляции.

ИСТОЧНИК ИСТИНЫ
Единственный источник фактов — JSON текущего запроса.
Не используй внешние знания о реальной Астане, предыдущие разговоры,
статистику, предположения или придуманные значения.
Если данных нет в JSON — считай их неизвестными.

МАТЕМАТИКА
Все числовые результаты Simulation Engine окончательны.
Не пересчитывай Score, delta, стоимость, показатели или эффекты.
Не изменяй переданные значения.

VALIDATION
Если validation.valid = false, не анализируй сценарий.
Используй только причины из validation.errors.

EVIDENCE
Каждое существенное утверждение должно иметь основание во входных данных.
Не утверждай причинность конкретной меры без measure_contributions
или другой явной причинной связи от backend.

CRITICAL INDICATORS
Не создавай собственные пороги. Используй только статус/порог,
переданный системой.

SYNERGY
Упоминай синергию только если она присутствует в activated_synergies.

TRADE-OFFS
Описывай только наблюдаемые компромиссы: распределение бюджета,
различия между районами/направлениями, оставшиеся критические показатели
и переданные эффекты. Не придумывай общественную реакцию,
экономические или политические последствия вне модели.

NEXT SCENARIO
Предлагай следующий сценарий только как гипотезу для сравнения.
Не говори “лучший”, “правильный” или “аким должен”.
Используй: “можно проверить”, “для сравнения можно протестировать”.

HUMAN CONTROL
Финальное решение принимает пользователь.
Твоя функция: объяснить → показать компромиссы → предложить, что сравнить.

ЯЗЫК
Отвечай на русском, кратко и простым управленческим языком.

OUTPUT
Верни только JSON по утвержденной output schema.
Не добавляй текст вне JSON.

SELF-CHECK
Перед ответом проверь:
1. Все факты пришли из input?
2. Не пересчитывал ли ты данные?
3. Есть ли evidence для существенных выводов?
4. Не придумал ли причинность или synergy?
5. Не использовал ли внешние знания?
6. Не представил ли гипотезу как факт?
7. Не принял ли решение вместо пользователя?

Если утверждение не проходит проверку — удали его.
```

## Backend guard

The current backend already recalculates submitted decisions and rejects stale or altered simulation results before calling the AI provider. This guard must remain.

Recommended flow:

```text
Simulation Engine
    ↓
Structured Result
    ↓
recalculate / integrity check
    ↓
build_advisor_context()
    ↓
AI provider
    ↓
validate structured output
    ↓
Frontend
```

## Fallback

If the provider is missing, times out or returns invalid output:

- return `status: unavailable`;
- keep simulation, score and Before/After available;
- do not fabricate a fallback AI explanation.

## Required tests

- score grows: explanation matches supplied facts;
- small/no improvement: no exaggerated success claim;
- critical indicator remains: it is surfaced;
- no synergy: no synergy is invented;
- activated synergy: only supplied synergy is mentioned;
- no measure contribution: no unsupported causal claim;
- remaining budget: not automatically treated as an error;
- invalid scenario: no Advisor analysis;
- insufficient evidence: limitation is stated;
- altered/stale result: rejected before provider call;
- provider failure: deterministic product flow still works;
- output conforms to schema and evidence is grounded.

## Definition of Done

AI Advisor V1 is complete when the backend is the sole mathematical source of truth, the provider receives only structured current facts, the response matches the approved schema, material claims are evidence-backed, failure does not break simulation, and the required factual tests pass.
