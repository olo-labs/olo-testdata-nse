# Contributing

Contributions that improve correctness, reproducibility, documentation, portability, or query ergonomics are welcome.

## Before changing the repository

- Do not commit credentials, private feeds, or data that cannot legally be redistributed.
- Treat source submodules as independent datasets with their own contribution history.
- Prefer deterministic builder changes over manual edits to generated Parquet files.
- Preserve the shared eight-column output schema unless a schema change has been discussed and documented.
- Keep examples analytical and reproducible; do not imply guaranteed trading performance.

## Types of contributions

- reproducible data-quality reports and fixes;
- DuckDB, pandas, Polars, PyArrow, or Spark recipes;
- builder performance and memory improvements;
- schema and manifest validation;
- platform-neutral launchers and developer tooling;
- accessibility or documentation improvements;
- new source adapters with clear provenance and redistribution rights.

## Generated data

Files under `database/` are generated outputs. When a builder or source change affects them:

1. explain why regeneration is necessary;
2. identify the source commits used;
3. run the documented verification command;
4. summarize changed symbol/file counts and validation results;
5. avoid mixing unrelated generated updates into the same pull request.

Do not hand-edit a Parquet file as the only fix. Correct the source or transformation so the result can be reproduced.

## Validation

Run the relevant automated tests and then validate generated outputs:

```powershell
.\parquet_database\run.bat --verify-only
```

Follow the additional checks in [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md). If a full database rebuild is impractical, state exactly which symbols, timeframes, and tests were exercised.

## Reporting a data issue

Include:

- repository commit and source-submodule commits;
- symbol and `day.parquet` or `1m.parquet` path;
- affected timestamp or date range;
- expected and observed values;
- a minimal DuckDB or Python reproduction;
- the evidence used to determine the expected value.

Do not attach large repackaged datasets when a query, representative rows, and checksum are sufficient.

## Documentation style

Use descriptive headings and expand abbreviations on first use. Distinguish traded `volume` from daily deliverable quantity (`delivery`) and delivery percentage (`del_percent`). Mark assumptions about timezones, corporate actions, and missing candles explicitly.
