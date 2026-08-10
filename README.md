# NSE India OHLCV and Delivery Data in Parquet

![OLO DB Viewer displaying NSE daily OHLC candles, delivery data, volume, EMA, and relative comparison lines](docs/assets/olo-db-viewer-snapshot.png)

Open, query-ready **National Stock Exchange of India (NSE) historical market data** organized as one Parquet file per symbol and timeframe. This repository combines daily OHLCV candles, traded volume, deliverable quantity, delivery percentage, and one-minute OHLCV data in a consistent analytics-friendly schema.

Use it for Indian stock-market research, DuckDB or pandas analysis, backtesting inputs, charting, screening, data engineering, machine learning, and reproducible educational examples.

> [!IMPORTANT]
> This is an independent community project. It is not affiliated with, endorsed by, or operated by the National Stock Exchange of India. The data is provided for research and education, not as investment advice. Verify data and applicable source-data rights before production or redistribution use.

## What is included

- One `day.parquet` file per NSE equity with OHLC, volume, deliverable quantity, and delivery percentage.
- One `1m.parquet` file per available equity or index with one-minute OHLCV candles.
- A stable eight-column schema shared by both timeframes.
- Symbol-partitioned paths for reading a single instrument without scanning the full dataset.
- Incremental and full-rebuild tooling backed by DuckDB.
- Source submodules for daily delivery data and minute candles.
- **OLO DB Viewer**, a repository-local desktop checker for inspecting candles and indicators.

Common discovery terms: NSE historical data Parquet, NSE delivery data, Indian stock market OHLCV dataset, NSE deliverable quantity history, NSE delivery percentage, NSE one-minute candles, NSE daily candles, DuckDB market data, pandas NSE data, Indian equities dataset, and stock delivery volume analysis.

## Start here

| Goal | Documentation |
| --- | --- |
| Understand dataset scope and intended use | [Dataset card](docs/DATASET.md) |
| Understand folders and filenames | [File structure](docs/FILE_STRUCTURE.md) |
| Understand every Parquet column | [Data dictionary](docs/DATA_DICTIONARY.md) |
| Query with DuckDB, Python, pandas, or Polars | [Quick start](docs/QUICKSTART.md) |
| Validate values and handle limitations | [Data quality](docs/DATA_QUALITY.md) |
| Find direct answers to common questions | [FAQ](docs/FAQ.md) |
| Build or update the database | [Builder documentation](parquet_database/README.md) |
| Help AI tools index the repository | [LLM index](llms.txt) |
| Read machine-readable metadata | [Schema.org Dataset metadata](metadata/dataset.jsonld) |
| Cite this dataset | [Citation metadata](CITATION.cff) |

## Repository layout

```text
olo-testdata-parquet/
├── database/                              # generated query-ready Parquet database
│   ├── a/ABAN/day.parquet                 # daily OHLCV + delivery data
│   ├── a/ABAN/1m.parquet                  # one-minute OHLCV data
│   ├── _cache/                            # incremental build cache
│   ├── manifest.json                      # source fingerprints/build state
│   └── build.log                          # build progress and diagnostics
├── olo-testdata-nse-day-delivery-candle/ # daily delivery-data source submodule
├── olo-testdata-nse-min-candle/          # minute-data source submodule
├── parquet_database/                     # normalizers, builder, verification, tests
├── olo-db-viewer/                        # current desktop database checker
├── olo-viewer/                           # placeholder for the future viewer
├── docs/                                 # consumer documentation
├── incremental.bat                       # update sources and rebuild changed outputs
└── recreate.bat                          # rebuild all generated outputs
```

Symbols are grouped by their lowercase first character. For example, `RELIANCE` is stored under `database/r/RELIANCE/`, while `3MINDIA` is under `database/3/3MINDIA/`.

## Parquet schema

Every symbol file uses this ordered schema:

| Column | Parquet type | Meaning | Daily | One minute |
| --- | --- | --- | --- | --- |
| `timestamp` | `TIMESTAMP` | Candle date/time | date at midnight | minute timestamp |
| `open` | `DOUBLE` | First traded price in the candle | yes | yes |
| `high` | `DOUBLE` | Highest traded price | yes | yes |
| `low` | `DOUBLE` | Lowest traded price | yes | yes |
| `close` | `DOUBLE` | Last traded/closing price | yes | yes |
| `volume` | `BIGINT` | Total traded quantity | yes | yes |
| `delivery` | `BIGINT` | Deliverable quantity | yes | null |
| `del_percent` | `DOUBLE` | Deliverable quantity as a percentage of volume | yes | null |

Row order is not guaranteed. Always use `ORDER BY timestamp` when chronological order matters.

## Query one symbol in seconds

DuckDB SQL:

```sql
SELECT timestamp, open, high, low, close, volume, delivery, del_percent
FROM read_parquet('database/r/RELIANCE/day.parquet')
WHERE timestamp >= DATE '2024-01-01'
ORDER BY timestamp;
```

Python and DuckDB:

```python
import duckdb

reliance = duckdb.sql("""
    SELECT *
    FROM read_parquet('database/r/RELIANCE/day.parquet')
    ORDER BY timestamp
""").df()

print(reliance.tail())
```

See [Quick start](docs/QUICKSTART.md) for pandas, Polars, multi-symbol scans, delivery filters, and intraday aggregation.

## Build and update

Initialize/update the source submodules and process only changed inputs:

```bat
incremental.bat
```

Recreate the complete database:

```bat
recreate.bat
```

Validate existing outputs without rebuilding:

```powershell
.\parquet_database\run.bat --verify-only
```

Detailed resource profiles, cache behavior, release automation, and adapter extension instructions are in [parquet_database/README.md](parquet_database/README.md).

## Automated releases

The versioned database release remains available through the manual GitHub
Actions workflow. Its required version input accepts `V1.0.0` or `v1.0.0`;
rerunning an existing version replaces that release's tag and assets. A rolling
`nse-database-latest` pre-release is also
rebuilt whenever the minute-candle repository successfully publishes an `RC:`
commit. The rolling release uses the exact minute-candle commit carried in the
cross-repository dispatch and publishes bounded daily/minute ZIP assets with a
SHA-256 checksum file.

Release builds update submodules to the latest commit on each configured
tracking branch before generating the database. Both source submodules track
`main` in `.gitmodules`; the rolling RC workflow then checks out the exact
dispatched minute-candle commit to keep that release reproducible.

Cross-repository triggering requires a `PARENT_REPO_TOKEN` Actions secret in
`olo-testdata-nse-min-candle`. Use a fine-grained token scoped to
`olo-labs/olo-testdata-nse` with **Contents: write** permission.

## Desktop database checker

On Windows, double-click `olo-db-viewer.bat` in the repository root. OLO DB Viewer reads only this repository's `database/` folder and provides candlestick, volume, delivery, delivery-percentage, RSI, EMA, AMA, Super Trend, and anchored VWAP inspection.

The screenshot uses a stable replace-in-place filename. When the interface changes, overwrite `docs/assets/olo-db-viewer-snapshot.png`; documentation links do not need to change.

## Sources and scope

The generated database normalizes two source submodules:

- [`olo-testdata-nse-day-delivery-candle`](olo-testdata-nse-day-delivery-candle/): daily NSE OHLC, traded quantity, deliverable quantity, and delivery percentage.
- [`olo-testdata-nse-min-candle`](olo-testdata-nse-min-candle/): one-minute NSE equity and index OHLCV archives.

Only daily rows in the `EQ` series define the exported equity universe. Minute index symbols are supported separately and may have only `1m.parquet`.

## Contributing

Useful contributions include schema validation, reproducible data-quality reports, additional query recipes, platform-neutral launchers, documentation corrections, and new source adapters. Keep changes deterministic and avoid committing credentials or proprietary datasets.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for generated-file, validation, and pull-request conventions.

## License and attribution

Repository code is covered by [LICENSE](LICENSE). Source data may have separate terms or restrictions; review the upstream source documentation and applicable exchange policies. Cite the dataset with [CITATION.cff](CITATION.cff) and record the commit or release used so results can be reproduced.
