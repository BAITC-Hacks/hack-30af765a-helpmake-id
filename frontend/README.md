# Akim AI frontend

React + TypeScript + Vite interface for the existing API. Requires Node.js 20.19+ and a running backend.

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Set `AKIM_API_URL` for another backend when starting Vite, for example `AKIM_API_URL=https://api.helpmake-id.live npm run dev`. For a separately hosted production frontend, set `VITE_API_BASE_URL` to the backend origin during build and allow that origin in backend CORS.

The UI reads all district names, codes, map anchors, indicators, rules and M1–M14 from `/api/v1/data`. It sends selected `measure_id` and, for district measures, `district_code` to `/api/v1/simulate`. A `200` response with `valid:false` displays backend violations. A valid result drives all Score, before/after and Q0–Q8 views; the same result is sent to `/api/v1/advisor/explain`. Advisor failure leaves the numeric result visible.

## Reproduce the main scenario

1. Start the backend as described in the root README, then start Vite with the commands above. Open the local URL printed by Vite.
2. Open Situation Center and check that five districts, the fixed budget and the initial 0/5 counter appear.
3. Select M7, M8 and M10 for Нура, M12 for the whole city, and M5 for Сарыарка. The UI should show 5/5 and 95/100 with the current dataset.
4. Select **SIMULATE**. The result must show the Score supplied by the backend, before/after district values, critical indicators, contributions, synergies when activated, and a separate AI Advisor response.
5. Open the map and switch Q0 through Q8. Return to the result, select **Изменить этот сценарий**, replace a measure and simulate again to check that the Score changes.

## Compare scenarios A/B

After a successful simulation, choose **Сохранить в A**. Create or edit a scenario, simulate it, then choose **Сохранить в B**. Open **Сравнение A/B** to view both backend results side by side: Score, budget spent and remaining, district before/after changes, remaining critical indicators and selected measures. Each slot can be overwritten by saving a new result; **Изменить сценарий A/B** copies its decisions into the editor for another simulation. Results are stored in this browser's local storage and are discarded automatically when `/data` has a different `dataset_hash`. The comparison performs only arithmetic between two backend results; it never recalculates a scenario locally.

Run `npm run build` to check TypeScript and the production bundle. The frontend workflow builds with `VITE_API_BASE_URL=https://api.helpmake-id.live` and publishes the static files to `https://helpmake-id.live` after a push to `main`. The server deployment matches the existing live `index.html` to its document root and replaces that file after uploading the new hashed assets. GitHub Actions uses the same production SSH secrets as the backend workflow.

`/data` has no baseline city or district Score. To show the initial city Score, the frontend makes one valid service simulation derived from the current catalog and displays only its `baseline_score`. If that request fails, it shows `—` until the user's scenario is calculated. Initial district cards therefore display raw indicator values, not a locally calculated Score. District scores appear after simulation. `map_anchor` gives illustrative points only; the map is explicitly schematic and does not draw administrative boundaries or use invented coordinates.

The advisor API returns four prose fields. It has no structured recommendations, next-scenario proposal or links from individual AI claims to evidence. The result therefore shows backend facts and contributions in a separate evidence section and offers manual scenario editing; it does not attribute specific numeric facts to AI statements.

The Figma canvas was inspected through the authenticated Chrome session. Figma MCP refused design context for this file with an editor access error, so exact asset extraction and pixel level verification were unavailable. The interface follows the observed layout, hierarchy, colors and user journey without changing backend files or datasets.
