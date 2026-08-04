# NSE Parquet Database File Structure

This page specifies how NSE daily OHLCV, delivery data, and one-minute candle files are laid out in `olo-testdata-parquet`.

## Consumer-facing files

```text
database/<group>/<symbol>/day.parquet
database/<group>/<symbol>/1m.parquet
```

`<group>` is the lowercase first character of the symbol when it is ASCII alphanumeric; otherwise `_` is used. `<symbol>` is a filesystem-safe encoded symbol name.

Examples:

```text
database/a/ABAN/day.parquet
database/a/ABAN/1m.parquet
database/r/RELIANCE/day.parquet
database/3/3MINDIA/day.parquet
```

Do not assume every symbol has both files. A symbol can be daily-only, minute-only, or have both, depending on source coverage. Minute index symbols are exported without the daily equity-universe filter and commonly have only `1m.parquet`.

## `day.parquet`

One row represents one NSE trading date for one symbol. `timestamp` is stored as a timestamp at the daily boundary. The file includes OHLC, traded volume, deliverable quantity, and delivery percentage.

Logical key: `timestamp` within the symbol file.

Expected columns:

```text
timestamp, open, high, low, close, volume, delivery, del_percent
```

## `1m.parquet`

One row represents one source minute candle for one symbol. It uses the same schema as daily data, but `delivery` and `del_percent` are null because the minute source does not provide those fields.

Logical key: `timestamp` within the symbol file.

## Internal build files

These support reproducible incremental builds and are not the primary consumer API:

| Path | Purpose |
| --- | --- |
| `database/_cache/` | Normalized source-level Parquet caches |
| `database/_cache/equity_symbols.parquet` | Daily `EQ` export universe |
| `database/manifest.json` | Content fingerprints and cache mappings |
| `database/build.log` | Human-readable build progress/errors |
| `database/submodule-revisions.txt` | Exact source commits used by release automation |
| `database/state.duckdb` | State used by the legacy/general builder when present |

Applications should read `database/*/*/day.parquet` or `database/*/*/1m.parquet` and ignore paths beneath `_cache`.

## Glob patterns

All daily symbol files:

```text
database/*/*/day.parquet
```

All minute symbol files:

```text
database/*/*/1m.parquet
```

DuckDB can add each source filename for symbol/path extraction:

```sql
SELECT filename, count(*) AS rows
FROM read_parquet('database/*/*/day.parquet', filename = true, union_by_name = true)
GROUP BY filename
ORDER BY filename;
```

## Ordering and partition assumptions

- Physical row order is not part of the contract; query with `ORDER BY timestamp`.
- Symbols are encoded in paths, not repeated as a Parquet column.
- Timeframe is encoded by the filename, not stored as a Parquet column.
- Schema changes should increment the builder schema/version and update the data dictionary.
