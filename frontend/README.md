# Akim AI frontend

React + TypeScript + Vite interface for the existing API. Requires Node.js 20.19+ and a running backend.

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Set `AKIM_API_URL` for another backend when starting Vite, for example `AKIM_API_URL=https://api.helpmake-id.live npm run dev`. For a separately hosted production frontend, set `VITE_API_BASE_URL` to the backend origin during build and allow that origin in backend CORS.

The UI reads all district names, codes, map anchors, indicators, rules and M1–M14 from `/api/v1/data`. It sends selected `measure_id` and, for district measures, `district_code` to `/api/v1/simulate`. A `200` response with `valid:false` displays backend violations. A valid result drives all Score, before/after and Q0–Q8 views; the same result is sent to `/api/v1/advisor/explain`. Advisor failure leaves the numeric result visible.

`/data` has no baseline city or district Score. To show the initial city Score, the frontend makes one valid service simulation derived from the current catalog and displays only its `baseline_score`. If that request fails, it shows `—` until the user's scenario is calculated. Initial district cards therefore display raw indicator values, not a locally calculated Score. District scores appear after simulation. `map_anchor` gives illustrative points only; the map is explicitly schematic and does not draw administrative boundaries or use invented coordinates.

The Figma canvas was inspected through the authenticated Chrome session. Figma MCP refused design context for this file with an editor access error, so exact asset extraction and pixel level verification were unavailable. The interface follows the observed layout, hierarchy, colors and user journey without changing backend files or datasets.
