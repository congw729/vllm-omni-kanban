# Qwen3 Omni — Buildkite Raw Ingest & Filename Schema Plan

**Date:** 2026-04-02  
**Last updated:** 2026-04-02  
**Status:** In progress (sync + MkDocs hook implemented; filename/`request_rate` chart pipeline items still open — see §8)  
**References:** [Kanban design](2025-03-13-kanban-design.md) · [Implementation plan](2026-03-13-implementation-plan.md)

---

## 1. Background

The Qwen3 Omni page (`docs/models/qwen3-omni.md`) depends on `generate_charts.py` reading `result_test_*.json` under `data/results/qwen3omni/`, aggregating them into `docs/assets/charts/qwen3_omni_history.json`, which `render_charts.js` then renders.

Nightly artifacts land first under **`data/buildkite_nightly_raw/<build_number>/...`** (via `fetch_buildkite_nightly_files.py` and Actions). This plan adds a **repeatable sync** from that tree into `data/results/<model_name>/` and wires it into **local MkDocs** runs.

---

## 2. Goals

1. **Automated sync:** Scan `data/buildkite_nightly_raw/` for JSON result files matching a configurable path substring (`--model-keywords`) and copy them into `data/results/<model_name>/` as the canonical input for `generate_charts.py` (e.g. `qwen3omni` must match `kanban_pages.qwen3_omni_history.source_dir` in `config.json`).
2. **File contents win:** Any field already present in the JSON (e.g. `num_prompts`, `max_concurrency`, `request_rate`, `date`, …) **must** take precedence over filename-derived values; filename parsing is fallback or supplemental for `test_name` / `dataset_name` / ordering.
3. **Fix random-mm floats in filenames:** In `result_test_qwen3_omni_*random-mm_0.1_10_<ts>.json`, `0.1` is **request rate**, not `max_concurrency`; that segment must not be passed through `int()`. Display and grouping for rate must follow the in-file `request_rate`.
4. **Correct grouping:** Workloads swept by **request rate** must include **`request_rate`** (or an equivalent field) in the grouping dimensions so different rates are not merged into one configuration series.

---

## 3. Current flow (as implemented vs remaining)

| Step | Behavior |
|------|----------|
| Fetch | CI or local `fetch_buildkite_nightly_files.py` writes under `data/buildkite_nightly_raw/<build>/...`. |
| Collect | **`scripts/sync_buildkite_raw_model_results.py`** copies `result_test_*.json` paths containing `--model-keywords` into `data/results/<model-name>/`. Same basename under multiple builds: **higher numeric build folder wins**, then **newer mtime**. If `data/buildkite_nightly_raw` is missing, the script **exits 0** and does nothing. |
| **MkDocs** | **`mkdocs serve`** and **`mkdocs build`** load `mkdocs.yml` → **`hooks`** → **`scripts/mkdocs_hooks.py`**. On each CLI run, **`on_startup`** runs each entry in **`_BUILDKITE_RAW_SYNCS`** (currently `("qwen3omni", "qwen3_omni")`) via the sync script, then runs **`generate_charts.py`**. So a normal local preview **refreshes** `data/results/qwen3omni/` and **regenerates** `docs/assets/charts/*.json` before the site is served/built. |
| Charts / page | `generate_charts.py` builds `qwen3_omni_history.json`; the Omni page consumes it. **Note:** filename parsing for `random-mm` float slots and **`request_rate` grouping in config** are still **to do** (see §8) — until then, some raw files may still be skipped or merged incorrectly. |

---

## 4. Target data pipeline (reference diagram)

### 4.1 End-to-end

```
data/buildkite_nightly_raw/
  └── <build>/.../result_test_*.json   # path contains --model-keywords
           │
           │  sync_buildkite_raw_model_results.py (copy; see §5)
           ▼
data/results/<model_name>/
           │
           ▼
scripts/generate_charts.py  →  docs/assets/charts/qwen3_omni_history.json (and other charts)
```

### 4.2 Local developer entry point

- Run from repo root: **`mkdocs serve`** (or **`mkdocs build`**).
- No separate manual sync step is required for preview **if** raw data already exists under `data/buildkite_nightly_raw/`.
- To add another model later: extend **`_BUILDKITE_RAW_SYNCS`** in `scripts/mkdocs_hooks.py` with a new `(model_name, model_keywords)` pair, and ensure `generate_charts` / any dedicated page reads from `data/results/<model_name>/`.

### 4.3 CI (optional follow-up)

- Run **sync** before `generate_charts` in **GitHub Actions** (e.g. after nightly fetch) so committed `data/results/` and charts match the latest raw pull in one commit.
- Sequence: `fetch` → `sync_buildkite_raw_model_results.py` (per model) → `generate_charts.py`.

---

## 5. Technical design

### 5.1 Scan scope and matching

- **Root:** `data/buildkite_nightly_raw/` (recursive), overridable with `--raw-root`.
- **Files:** `result_test_*.json` only (`rglob`).
- **Match:** full path must contain the **`--model-keywords`** string (POSIX path, case-sensitive). Example for Qwen3 Omni: `qwen3_omni`.

### 5.2 Sync semantics (copy vs move)

| Mode | Use | Notes |
|------|-----|-------|
| **Copy (default)** | CI / local dev / MkDocs hook | Keeps `buildkite_nightly_raw` intact; idempotent overwrites in `data/results/<model_name>/`. |
| **Move** | Local cleanup only | `--move`; **not** used by MkDocs hook. |

**Multi-build collisions:** Prefer **higher build directory number**, then **newer `st_mtime`**.

### 5.3 Sync script (implemented)

- **Path:** `scripts/sync_buildkite_raw_model_results.py`
- **CLI:** `--model-name <dir under data/results/>` (validated single segment), **`--model-keywords <substring>`** (required), optional `--raw-root`, `--dry-run`, `--move`, `-v`.
- **MkDocs:** `scripts/mkdocs_hooks.py` invokes it once per tuple in **`_BUILDKITE_RAW_SYNCS`**.

### 5.4 `generate_charts.py`: filename parsing + JSON first (planned)

**Merge order** after loading each `result_test_*.json`:

1. From **file body:** `num_prompts`, `max_concurrency`, `request_rate`, `date`, plus existing fields such as `endpoint_type`, `backend`, `model_id`, `tokenizer_id`.
2. From **filename:** `test_name`, `dataset_name`, and fallbacks only when missing from the file.
3. **Overrides:** Non-null values from step 1 **win**; `request_rate` from file when present.

**`random-mm` / float slot:** If the third-from-end filename segment parses as **float**, treat as request-rate encoding; **do not** `int()` it.

**Timestamps:** Prefer **`date` in JSON** for `sort_timestamp` when parseable; else filename timestamp.

### 5.5 Grouping / filters: `request_rate` (planned)

- Add **`request_rate`** to `QWEN3_OMNI_GROUP_FIELDS` in `generate_charts.py`.
- Add **`request_rate`** to `kanban_pages.qwen3_omni_history.filters` and `table_columns` in `data/config.json`.
- Normalize numeric vs `"inf"` consistently in grouping and tests.

### 5.6 Front end (if needed)

- Extend series labels / tooltips if `request_rate` is added to grouping (e.g. `render_charts.js`).

---

## 6. Testing plan (TDD order)

1. **`parse_qwen3_omni_filename` / merge helper** — `random-mm` + `0.1` + valid timestamp; JSON overrides.
2. **`load_qwen3_omni_history`** — includes former skip cases for `random-mm`.
3. **`sync_buildkite_raw_model_results`** — temp raw tree, keyword filter, collision policy; **`tests/unit/test_sync_buildkite_raw_model_results.py`**.
4. **Regression:** `pytest` + **`mkdocs serve`** → open Qwen3 Omni page; confirm data and charts.

---

## 7. Documentation & ops

- **Local preview:** Document that **`mkdocs serve`** runs sync + `generate_charts` via **`mkdocs.yml` → `hooks` → `scripts/mkdocs_hooks.py`** (this section + §3).
- Optional: one line in `contributing.md` pointing to this plan.

---

## 8. Rollout checklist

- [x] Add `scripts/sync_buildkite_raw_model_results.py` + unit tests  
- [x] **`mkdocs.yml`** registers **`scripts/mkdocs_hooks.py`**; hook runs sync (per `_BUILDKITE_RAW_SYNCS`) then **`generate_charts.py`**  
- [ ] Update `generate_charts.py` (float filename slot + JSON-first + `request_rate` in `QWEN3_OMNI_GROUP_FIELDS`) + `test_generate_charts.py`  
- [ ] Update `data/config.json` (`filters` / `table_columns` for `request_rate`)  
- [ ] (Optional) `.github/workflows/...`: sync + `generate_charts` before commit/deploy  
- [ ] Verify with real `buildkite_nightly_raw`: `record_count` and `random-mm` groups in `qwen3_omni_history.json`  

---

## 9. Open questions

1. Restrict sync to `tests/dfx/perf/results/` subtree?  
2. Placeholder for **missing** `request_rate` in grouping keys vs concurrency-only runs?  
3. Disallow `--move` in CI only (document for local use)?  

---

**Next step:** Finish §8 unchecked items (especially `generate_charts` + `config.json`), then validate on a full nightly tree.
