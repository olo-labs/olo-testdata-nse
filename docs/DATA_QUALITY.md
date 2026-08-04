# NSE Parquet Data Quality and Validation

Historical market-data users should validate files before research, backtesting, model training, or publication. Passing structural checks does not guarantee economic completeness or suitability for trading decisions.

## Built-in verification

```powershell
.\parquet_database\run.bat --verify-only
```

The builder verifies that sources were processed, expected symbol files exist, filenames are recognized, and generated Parquet schemas contain the required eight columns.

## Recommended consumer checks

### Schema

```sql
DESCRIBE SELECT * FROM read_parquet('database/r/RELIANCE/day.parquet');
```

Expected order: `timestamp, open, high, low, close, volume, delivery, del_percent`.

### Duplicate timestamps

```sql
SELECT timestamp, count(*) AS occurrences
FROM read_parquet('database/r/RELIANCE/day.parquet')
GROUP BY timestamp
HAVING count(*) > 1;
```

### OHLC bounds

```sql
SELECT *
FROM read_parquet('database/r/RELIANCE/day.parquet')
WHERE high < greatest(open, low, close)
   OR low > least(open, high, close);
```

### Delivery fields

```sql
SELECT *
FROM read_parquet('database/r/RELIANCE/day.parquet')
WHERE delivery < 0 OR del_percent < 0 OR del_percent > 100;
```

For `1m.parquet`, `delivery` and `del_percent` should be null by design.

## Known limitations

- Coverage depends on the source submodules and varies by symbol and timeframe.
- Minute and daily starting dates may differ.
- Missing trading dates can represent exchange holidays, suspensions, absent source files, or parsing exclusions.
- OHLC prices are not guaranteed to be adjusted for corporate actions.
- Symbols can change over time; the dataset does not currently provide a canonical security-master history.
- Delivery statistics are daily source fields and must not be inferred at one-minute resolution.
- Source corrections can cause historical output to change in a later build.

For reproducibility, record the Git commit, submodule revisions, build profile, and release/archive identifier used by an analysis.
