# ML Method Recommendations — Transit-AI Hackathon

> **Purpose:** Self-contained prompt for external AI agents to recommend ML
> approaches for improving our Tram Ridership Forecasting model beyond
> current best **WAPE-score = 0.82121** on platform.
> Copy-paste ready. Updated 2026-09-26.

---

## 1. Project Context

**Transit-AI** — hackathon project for Moscow Tram Ridership Forecasting
(трамвайный пассажиропоток). We predict boardings per `(route, date, hour)`
for **61 days × 24 hours × 10 routes = 14,640 cells** (Nov 1 – Dec 31, 2025).

| Stack | Details |
|---|---|
| ML | Python 3.12, PyTorch 2.14+CUDA13, XGBoost, LightGBM, CatBoost, scikit-learn |
| Hardware | RTX 5060 Laptop 8GB VRAM (target), or RTX 4070 12GB |
| Evaluation | `WAPE = Σ|y − ŷ| / Σy` (raw), `WAPE-score = max(0, 1 − WAPE) ∈ [0,1]` |
| Time limits | Training ≤60 min total (R6), Inference ≤2 sec/request |
| Code constraint | No LLM >4B params for inference (R2), no internet at runtime (R4) |

---

## 2. Data Schema (CRITICAL — read carefully)

### `data/real/train.csv` — raw tap-in events (49M rows, Jan-Sep 2025)

**Columns (14):**
```
tran_no;device_no;tran_date_time;begin_date_time;input_date_time;
crd_hashcode;validation_result;tran_type_id;place_id;good_type;
pass_route;ngpt_route;bus_exit_no;garage_number
```

**Key columns:**
- `ngpt_route` (col 12): **9 unique tram routes** — `'1 трамвай'`, `'7 трамвай'`, `'11 трамвай'`, `'12 трамвай'`, `'17 трамвай'`, `'25 трамвай'`, `'26 трамвай'`, `'28 трамвай'`, `'50 трамвай'`. **Route 5 НЕ СУЩЕСТВУЕТ в raw data** (F-051).
- `place_id` (col 9): **5 unique stop stations** — `39706`, `39707`, `39708`, `39709`, `39710`.
- `tran_date_time` (col 3): timestamp of validation.
- `pass_route` (col 11): **combined journey** (МЦД + Мосметро + НГПТ) — НЕ useful for tram-only prediction.
- `good_type` (col 10): ticket type (`'30 дней'`, `'90 дней'`, `'СКМ МГТ'`, etc.).

**Top routes by volume:** `17 трамвай` (11.6M), `12 трамвай` (7.7M), `11 трамвай` (7.4M).

### `data/real/labels/labels_day_{train,test}.csv` — aggregated ground truth

**Schema:** `route;date;hour;boardings` (separator=`;`)
- `labels_day_train.csv`: 46,234 rows (Jan 1 – Aug 31, 2025)
- `labels_day_test.csv`: 11,317 rows (Sep 1 – Oct 31, 2025)

### `data/real/test_submission.csv` — submission template

**Schema:** `route;date;hour;prediction` (separator=`;`), 14,640 rows
- Routes: 1, 5, 7, 11, 12, 17, 25, 26, 28, 50 (**route 5 INCLUDED**, 1464 cells)
- Dates: 2025-11-01 to 2025-12-31
- Hours: 0..23

### External data (`data/external/`)

- `weather_2025.csv`: daily weather (temp_max, temp_min, precip, snow, wind)
- `poi_moscow.json`: POI catalog (~146 objects, categories: university, school, clinic, park, mall, theater, etc.)
- `events_moscow.json`: infrastructure events Sep-Oct 2025 (Troickaya line opening, МГТУ Баумана, etc.) with `affected_routes` + exponential decay
- `traffic_osm_moscow.json`: 40 hardcoded traffic jam points (no live API per R4)
- `stops_routes.json`: stop coordinates per route
- `validators_lookup.csv`: per (route_id, weekday, hour) mean validator count

---

## 3. Best Result So Far

### Platform score progression (full curve)

| Submission | Platform WAPE-score | Δ vs base |
|---|---|---|
| Base v11 (no route 5 zero) | 0.73231 | — |
| + route 5 zero (F-051) | 0.82075 | **+0.08844** ⭐ MASSIVE |
| + night zero (8 safe pairs) | 0.82092 | +0.00017 |
| + pred≤20 h0-4 | 0.82113 | +0.00038 |
| + pred≤50 h0-4 | 0.82114 | +0.00039 |
| + pred≤55 h0-4 (**F-060 BEST**) | **0.82121** | **+0.00046** |
| + pred≤100 h0-4 (overreach) | 0.82067 | -0.00008 |
| F-063: pred≤55 h0-6 layered | 0.82099 | -0.00022 |
| F-063: pred≤55 h0-5 layered | 0.82105 | -0.00016 |
| F-063: pred≤65 h0-4 layered | 0.82117 | -0.00004 |

**F-060 best strategy:**
1. `route 5 → 0` (route 5 не существует, штраф ~1.31M predictions)
2. `per-route bias calibration` (T-147, log-space)
3. `predictions ≤ 55 in hours 0-4 → 0` (раннее утро: мало пассажиров, физически не выводят трамвай)

**Local holdout** (Sep-Oct 2025): WAPE-score = **0.8751** with calibration.

---

## 4. Tried Approaches & Results

### Models tested (chronological)

| ID | Approach | Local holdout | Platform | Status |
|---|---|---|---|---|
| F-049 | GRU solo (initial) | 0.10–0.18 | — | ❌ negative |
| F-051 | Route 5 zero | 0.8751 | **+0.08844** | ✅ CRITICAL |
| F-052 | Same as F-051 | — | validated | ✅ |
| F-054 | B (8 night zeros) | — | +0.00017 | ✅ tiny |
| F-054 | C (blend raw+cal) | — | **−0.236** | ❌ |
| F-056..F-060 | pred≤X sweep (20, 25, 35, 45, 50, 55, 100) | — | peak at 55 | ✅ peak confirmed |
| F-061 | Bug: replay suggestion | — | — | clinerule fix |
| F-062 | T-178/T-179 standalone (no route 5 zero) | — | **−0.14** | ❌ critical bug |
| F-063 | 3 F-060 layered variants | — | 0.821-0.822 | ✅ peak reaffirmed |
| F-064 | GRU v2_extended (h=128, l=2, w=336) | 0.13 | — | ❌ blend worsens XGB |
| F-065 | GRU sweep (7 configs) | best 0.1128 (h=64 l=1 w=168) | — | ❌ vs XGB 0.9051 |
| F-066 | LSTM ЛУЧШЕ GRU | 0.1099 | — | ⚠️ promising but not tested on platform |

### Feature ablation (`docs/reports/ablation_2026-09-26.csv`)

| Variant | WAPE-score | Δ vs full |
|---|---|---|
| full (56 features) | 0.9051 | baseline |
| with_traffic (+3) | 0.9045 | −0.0006 (worse) |
| no_events | 0.9027 | −0.0024 |
| no_poi | 0.9051 | ~0 |
| no_external (no POI/events/traffic) | 0.9053 | +0.0002 (negligible) |
| base_only (17 features, no geo) | 0.8974 | **−0.0077** |

**Insight:** POI/events/traffic features have NEGLIGIBLE effect on holdout. Geography + base features dominate.

### Best single model

| Model | Local holdout WAPE-score |
|---|---|
| **XGBoost v9_events** (with calibration) | **0.8751** (platform: 0.82121 with F-060 layered) |
| XGBoost v11_base_only | ~0.9051 raw |
| CatBoost v1 | similar to XGBoost |
| GRU best (h=64 l=1 w=168) | 0.1276 holdout |
| **LSTM best** (h=64 l=1 w=168) | **0.1099** holdout |
| Mamba smoke (h=32 w=48 ep=2) | 0.1492 holdout |

---

## 5. What We Did NOT Try (opportunities)

### A. Untried model architectures
- **Transformer with positional encoding** for sequences (contest has it)
- **xLSTM (matrix memory)** — modern alternative to LSTM
- **N-BEATS / N-HiTS** — dedicated time-series models
- **TFT (Temporal Fusion Transformer)** — interpretable TS forecasting
- **DeepAR / Prophet** — probabilistic TS forecasting
- **Linear models**: ETS, ARIMA, TBATS (good for short series)
- **TabNet / FT-Transformer** — tabular DL
- **Ensemble of LSTM + XGBoost in log-space** (we tried blend GRU+XGB, got worse — but LSTM is better than GRU)

### B. Untried feature engineering
- **Per-station (place_id) aggregations** from train.csv:
  - `n_validators_per_hour_per_station` (we have 5 stops, not used yet)
  - `transition_matrix` between stations
- **Lag features** at multiple horizons: lag_24h, lag_168h, lag_720h (we use lag_lookup mean, not real lags)
- **Rolling statistics**: rolling_mean_7d, rolling_std_7d per (route, hour)
- **Holiday indicators** explicitly (RU holidays: 4 Nov, etc.)
- **School calendar** (we have use_seasonal_calendar but not granular)
- **Day-of-week × hour interaction features**
- **Public event proximity** to routes (we have events but not used well)
- **Temperature × hour interaction** (cold morning vs warm)
- **Frequency encoding** of high-traffic patterns

### C. Untried post-processing
- **Quantile regression** with q05/q50/q95 → better calibration
- **Isotonic regression** as alternative to per-route bias
- **Conformal prediction** for confidence intervals
- **Stacked generalization**: 2nd-level model on top of XGB+LSTM+CatBoost
- **Time-series cross-validation** (we use single train/holdout split)

### D. Untried routes/hours analysis
- **Per-(route, hour) anomaly detection** — other routes may have similar `route 5 zero` pattern
- **Service schedule integration** (when trams run vs don't run)
- **Holiday zero on Nov 4** (День народного единства) — partially tried in T-180

---

## 6. Constraints (HACKATHON RULES)

| Rule | Constraint |
|---|---|
| R1 | Open-source code (Apache 2.0 / MIT / BSD) |
| R2 | No LLM >4B params for inference |
| R3 | Reproducible (seed=42, uv.lock committed) |
| R4 | **NO internet at runtime** (predictions only use local artifacts) |
| R6 | Total training time ≤60 min on RTX 5060/4070 |
| R7 | All endpoints documented in OpenAPI |
| R8 | Validation report required before submission |
| R9 | Self-review (no team) |

**Time available:** ~26 hours until deadline 2026-09-27 23:59 MSK.

---

## 7. Current Artifacts

| Artifact | Path | WAPE-score |
|---|---|---|
| Best submission (F-060) | `predictions/submission.csv` | **0.82121** |
| Manifest | `predictions/submission_v11_no_route5_nightzero_pred55_*.json` | — |
| Best model | `ml/artifacts/xgboost_v9_events/model.pkl` | 0.9051 raw |
| GRU v2_quick | `ml/artifacts/gru_v2_quick/model.pkl` | 0.13 |
| LSTM smoke | `ml/artifacts/lstm_smoke/model.pkl` | 0.24 (5 ep) / 0.11 (15 ep) |
| Mamba smoke | `ml/artifacts/mamba_smoke2/model.pkl` | 0.15 |

**Sweep results:** `docs/reports/gru_sweep_2026-09-26.csv`, `docs/reports/neural_sweep_2026-09-26.csv`

---

## 8. The Question

**Based on this context, recommend:**

### 8.1 Untried approaches with HIGH potential to beat F-060 (0.82121)
Prioritize by:
- Expected improvement (realistic delta in WAPE-score)
- Implementation cost (1h = single script; 4h = full pipeline)
- Compatibility with our constraints (R4: no internet, R6: ≤60min)

### 8.2 Specific feature engineering ideas
- Which `train.csv` columns or aggregations could add signal?
- Any derived features from `tran_date_time`, `place_id`, `ngpt_route`?

### 8.3 Specific model architectures
- Best 3 model types to try (with hyperparameter ranges)
- For each: should it be standalone or stacked with XGBoost?

### 8.4 Post-processing improvements
- Alternative to per-route bias calibration?
- Quantile regression?
- Better calibration methods?

### 8.5 What we may be missing
- Any pattern in the data that explains the gap between local (0.8751) and platform (0.82121) holdout?
- Possible `train.csv` data leakage if used correctly?
- Why does LSTM beat GRU (0.1099 vs 0.1276)? What does this signal?

---

## 9. Output Format

Please structure your response as:

1. **Top 5 Recommendations** (sorted by expected ROI)
   - Name, expected delta, implementation cost, key risks
2. **Specific code patterns** for the most promising approach
3. **Hyperparameter ranges** to explore
4. **What NOT to try** (lessons learned from our negative results)
5. **Time-budget recommendation** (which experiments to do first given 26h)

Keep response focused and actionable. Avoid generic ML advice — be specific to OUR data and constraints.

---

## 10. Appendix: Critical Codebase Paths

```
hackathon/
├── apps/backend/                    # FastAPI :8000 (not used for predictions)
├── apps/frontend/                   # Vite/React dashboard (presentation layer)
├── ml/
│   ├── transit_ai/
│   │   ├── models/
│   │   │   ├── gru_route.py         # legacy GRU (v2_extended)
│   │   │   ├── route_neural.py      # unified gru/lstm/mamba (NEW, T-177)
│   │   │   ├── xgboost_route.py     # best tabular model
│   │   │   └── catboost_route.py
│   │   ├── data/                    # RealSource, poi_features, validators_lookup, etc.
│   │   ├── calibration/route_bias.py  # per-route log-space bias calibration (T-147)
│   │   └── submission/              # manifest.py, candidate.py
│   ├── scripts/
│   │   ├── train_gru.py             # --kind {gru|lstm|mamba}
│   │   ├── train_xgboost.py
│   │   ├── sweep_gru.py             # sweep runner (T-177-GRU-SWEEP)
│   │   ├── sweep_neural.py          # sweep runner (T-177-NEURAL-CONFIG)
│   │   ├── make_submission.py       # CLI: --zero-route, --pred-cap, --cap-hours, --no-bias-calibration, --zero-hours, --zero-weekends, --zero-holidays
│   │   ├── blend.py
│   │   └── calibrate.py
│   └── artifacts/
│       ├── xgboost_v9_events/       # BEST baseline
│       └── gru_v2_quick/            # GRU v2_extended artifact
├── data/
│   ├── real/
│   │   ├── train.csv                # 49M raw tap-in events
│   │   ├── test_submission.csv      # 14640 cells to predict
│   │   └── labels/                  # ground truth train/test
│   └── external/                    # weather, POI, events, traffic, etc.
├── predictions/                     # current submissions
├── docs/
│   ├── HANDOFF.md                   # source of truth for session state
│   ├── ledger/                      # findings.jsonl, decisions.jsonl
│   ├── reports/                     # ablation, sweep results
│   └── prompts/                     # prompts directory (this file lives here)
└── .clinerules/                     # 30+ project rules (philosophy, architecture, hackathon, etc.)
```

---

**TL;DR for the agent:**
- We predict tram boardings per (route, date, hour) for Nov-Dec 2025.
- Best: 0.82121 (route 5 zero + bias cal + pred≤55 h0-4).
- Holdout gap: local 0.8751 vs platform 0.82121 (platform scores BETTER!).
- Models tried: XGBoost (0.9051 best), LSTM (0.1099), GRU (0.1276), Mamba (0.1492 smoke).
- Untried: TFT, N-BEATS, lag features, per-station aggregations, stacked generalization.
- 26h to deadline, ~9 submission slots left.
- Help us find the next +0.01–0.05 WAPE-score improvement.


