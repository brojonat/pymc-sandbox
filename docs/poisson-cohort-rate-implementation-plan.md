### Poisson Cohort Rate – Implementation Plan

#### Overview

We want to estimate and compare event rates across many cohorts (and event types) using a Poisson model. The system ingests observations over time, updates the posterior for each cohort, and answers questions like: “Is cohort A’s rate higher than cohort B’s?”

#### Objectives

- **Accurate rates**: Estimate per‑cohort (and per‑event‑type) rates with uncertainty.
- **Comparisons**: Compute probabilities that one cohort’s rate exceeds another’s.
- **Incremental updates**: Support streaming/batch ingestion that updates posteriors.
- **API + CLI**: Provide an HTTP API and a simple CLI to ingest data and query results.
- **Observability**: Prometheus metrics and structured logs.

#### Data Model (conceptual)

- **Cohort**: A group identifier (e.g., a tuple of model, model year, production batch).
- **EventType**: The event being counted (e.g., repair order, warranty claim, NHTSA report).
- **Observation (row‑per‑event)**: Each row is a single event occurrence.
  - Minimal fields: `(timestamp, cohort_id, event_type)`
  - Optional metadata: `entity_id`, `location`, etc.

Example CSV schema for ingestion (one row per event):

```
timestamp,cohort_id,event_type
2025-01-01T00:00:00Z,A,signup
2025-01-01T00:03:10Z,A,signup
2025-01-01T00:10:00Z,B,signup
```

#### Statistical Model

- Single cell model (cohort c, event e) over a query window `[start, end)` with unit `U`:
  - Let `k_ce` be the number of event rows in `[start, end)` for `(c, e)` (COUNT in DuckDB).
  - Let `T` be exposure, the window duration in units `U` (e.g., hours, days).
  - Likelihood: `k_ce ~ Poisson(lambda_ce * T)`
  - Prior on rate: `lambda_ce ~ Gamma(alpha0, beta0)`
  - Conjugate posterior in window: `Gamma(alpha0 + k_ce, beta0 + T)`.
- Hierarchical extension (recommended once basics work):
  - `lambda_ce ~ Gamma(alpha_e, beta_e)` with hyperpriors for `(alpha_e, beta_e)` to borrow strength across cohorts within an event type.
  - Fit via PyMC (NUTS) when you need partial pooling and richer comparisons.
- Posterior queries:
  - Per‑cohort posterior mean/median and credible intervals for `lambda_ce`.
  - Pairwise `P(lambda_ci > lambda_cj)` estimates (by Monte Carlo from posterior samples or via conjugate draws for the simple model).

#### Inference Strategy

- **Phase 1 (fast + windowed)**: Use Gamma–Poisson conjugacy with windowed queries:
  - Compute `k_ce` via `COUNT(*)` over `[start, end)` filtered by `(cohort, event)` in DuckDB.
  - Compute `T` as `(end - start)` expressed in the requested unit.
  - Posterior parameters: `alpha = alpha0 + k_ce`, `beta = beta0 + T`.
  - Sampling from posterior is trivial with `Gamma(alpha, beta)`.
- **Phase 2 (hierarchical)**: Use PyMC to fit a hierarchical Gamma–Poisson model:
  - Periodically (or on demand) run MCMC and cache posterior samples.
  - Optionally warm‑start by seeding priors from conjugate posteriors.

#### System Architecture

- **API (FastAPI)**
  - `POST /ingest` — Upload event rows (CSV or JSON list). Each row is one event.
  - `GET /cohorts` — List cohorts and event types with summary stats.
  - `GET /posterior/{cohort}/{event}` — Posterior summary for a cell in a window.
  - `GET /posterior/{cohort}/{event}/samples` — Full posterior draws for the cell (conjugate case) in a window.
  - `GET /compare` — Compare two cohorts for an event in a window, returns `P(A > B)`.
  - `GET /healthz` — Liveness.
  - `GET /metrics` — Prometheus.
  - Optional: JWT Bearer auth for mutating endpoints.
  - Hierarchical (Phase 2): `GET /posterior/hierarchical/{event}/samples` — Posterior draws for hierarchical params and per‑cohort rates.
- **Storage**
  - Minimal viable: DuckDB (or Postgres) with tables:
    - `observations(id, ts, cohort_id, event_type, ...)` // one row per event
    - (Optional) `window_cache(key, k_ce, T, alpha, beta, created_at)`
    - (Phase 2) `hierarchical_cache(event_type, samples_blob, created_at)`
- **Processing**
  - On ingest: validate rows, upsert cohorts/event types, update sufficient stats, emit metrics.
  - Background worker (optional): batch MCMC for hierarchical model and store samples.

#### API Shapes (concise)

- `POST /ingest` (JSON):
  ```json
  {
    "rows": [
      {
        "ts": "2025-01-01T00:00:00Z",
        "cohort": "A",
        "event": "signup",
        "count": 42,
        "exposure": 1000
      }
    ]
  }
  ```
  Response: `{ "ingested": 1 }`.
- `GET /posterior/{cohort}/{event}`:
  ```json
  { "alpha": 100.0, "beta": 2300.0, "mean": 0.0435, "hdi95": [0.035, 0.053] }
  ```
  - `GET /posterior/{cohort}/{event}/samples?n=5000` (conjugate):
    ```json
    {
      "cohort": "A",
      "event": "signup",
      "alpha": 100.0,
      "beta": 2300.0,
      "samples": [0.0382, 0.0461, 0.0401, 0.0449, ...]
    }
    ```
  - Hierarchical (Phase 2): `GET /posterior/hierarchical/{event}/samples?n=5000`:
    ```json
    {
      "event": "signup",
      "hyperparams": {"alpha": [ ... ], "beta": [ ... ]},
      "rates": {
        "A": [ ... ],
        "B": [ ... ]
      }
    }
    ```
- `GET /compare?event=signup&A=A&B=B`:
  ```json
  { "p_A_gt_B": 0.78 }
  ```

#### CLI (pv)

- `pv ingest --file data.csv`
- `pv summary --event signup --cohort A`
- `pv compare --event signup --A A --B B`

#### Observability

- **Logging**: `structlog` with service name, request ids, and timing.
- **Metrics**: request latency, ingest counts, per‑cohort update counters.

#### Testing Plan

- Unit tests: validators, sufficient‑stat updates, posterior math (conjugate cases).
- Statistical tests: synthetic data where true rates are known; ensure calibrated posteriors.
- API tests: endpoint contracts and error handling.

#### Milestones

- **M0**: Server skeleton, JWT auth, metrics, logging.
- **M1**: Data model + `/ingest` with validation and sufficient‑stat updates.
- **M2**: Posterior summaries + comparisons using conjugacy.
- **M3**: Hierarchical PyMC model + cached samples; comparison endpoints use samples.
- **M4**: CLI flows; docs and examples.

#### Risks & Considerations

- Data sparsity: use informative but weak priors; consider pooling.
- Non‑stationarity: allow time‑windowed stats or piecewise constant rates.
- Exposure quality: ensure exposure is measured consistently; default to 1 if absent.

#### Client Side (browser)

Goal: an in-browser view that overlays the two posterior distributions for `lambda_ce` (cohort A vs cohort B) over the same window, plus summary stats and `P(A > B)`.

Page structure

- Controls: event selector, cohort A, cohort B, `start`/`end` date pickers, `unit` (day|hour), number of samples `n`, optional `seed`.
- Chart area: overlayed density or histogram for both cohorts.
- Stats panel: mean, 95% interval for each cohort, and `P(lambda_A > lambda_B)`.

Endpoints used

- `GET /posterior/{cohort}/{event}/samples?start=...&end=...&unit=day&n=5000&seed=42`
  - Called twice (once per cohort) with identical window/query params.

Minimal HTML template

```html
<div id="controls">
  <select id="event"></select>
  <select id="cohortA"></select>
  <select id="cohortB"></select>
  <input id="start" type="date" />
  <input id="end" type="date" />
  <select id="unit">
    <option>day</option>
    <option>hour</option>
  </select>
  <input id="n" type="number" value="5000" min="100" max="50000" />
  <button id="run">Update</button>
  <div id="stats"></div>
  <div id="chart"></div>
</div>
<script type="module" src="/static/posterior.js"></script>
```

Client JS (sketch)

```javascript
async function fetchSamples(base, cohort, event, params) {
  const url = new URL(
    `${base}/posterior/${encodeURIComponent(cohort)}/${encodeURIComponent(
      event
    )}/samples`
  );
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetch failed: ${r.status}`);
  const j = await r.json();
  return j.samples; // array of lambda_ce draws
}

function probabilityAGreaterB(a, b) {
  const n = Math.min(a.length, b.length);
  let c = 0;
  for (let i = 0; i < n; i++) if (a[i] > b[i]) c++;
  return c / n;
}

function summarize(samples) {
  const sorted = [...samples].sort((x, y) => x - y);
  const mean = samples.reduce((s, x) => s + x, 0) / samples.length;
  const q = (p) => sorted[Math.floor(p * (sorted.length - 1))];
  return { mean, hdi95: [q(0.025), q(0.975)] };
}
```

Rendering with Observable Plot

```javascript
import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";

function renderChart(container, aSamples, bSamples) {
  const dataA = aSamples.map((x) => ({ x, cohort: "A" }));
  const dataB = bSamples.map((x) => ({ x, cohort: "B" }));
  const chart = Plot.plot({
    height: 280,
    marginLeft: 50,
    color: { legend: true },
    marks: [
      Plot.density(dataA, {
        x: "x",
        stroke: "#1f77b4",
        fill: "#1f77b4",
        fillOpacity: 0.15,
      }),
      Plot.density(dataB, {
        x: "x",
        stroke: "#d62728",
        fill: "#d62728",
        fillOpacity: 0.15,
      }),
    ],
    x: { label: "lambda_ce (rate)" },
    y: { label: "density" },
  });
  container.innerHTML = "";
  container.append(chart);
}
```

Putting it together

```javascript
const base = ""; // same-origin FastAPI
document.getElementById("run").addEventListener("click", async () => {
  const params = {
    start: document.getElementById("start").value,
    end: document.getElementById("end").value,
    unit: document.getElementById("unit").value,
    n: document.getElementById("n").value || 5000,
  };
  const event = document.getElementById("event").value;
  const A = document.getElementById("cohortA").value;
  const B = document.getElementById("cohortB").value;

  const [sa, sb] = await Promise.all([
    fetchSamples(base, A, event, params),
    fetchSamples(base, B, event, params),
  ]);

  const pa = probabilityAGreaterB(sa, sb);
  const sumA = summarize(sa);
  const sumB = summarize(sb);
  document.getElementById("stats").textContent =
    `P(A>B)=${pa.toFixed(3)} | A mean=${sumA.mean.toFixed(3)} [${sumA.hdi95
      .map((x) => x.toFixed(3))
      .join(", ")}] | ` +
    `B mean=${sumB.mean.toFixed(3)} [${sumB.hdi95
      .map((x) => x.toFixed(3))
      .join(", ")}]`;
  renderChart(document.getElementById("chart"), sa, sb);
});
```

Performance & UX

- Cap `n` server-side (e.g., 50k) and default to 5k; downsample client-side for plotting if needed.
- Consider `format=ndjson` for large streams; parse incrementally.
- Cache responses by a key of `(cohort,event,start,end,unit,n,alpha0,beta0)`.
- Use colorblind-friendly palette and responsive sizing.

Server layout

- `src/pymc_vibes/server/templates/posterior.html` — the template above.
- `src/pymc_vibes/server/static/posterior.js` — client JS.
- Route: `GET /ui/posterior` renders template; static files served under `/static`.
