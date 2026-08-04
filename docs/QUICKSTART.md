# Query NSE Parquet Data: DuckDB, pandas, and Polars

Run examples from the repository root. Replace `RELIANCE` with an available symbol and use the matching lowercase first-character directory.

## DuckDB SQL

Daily OHLCV and delivery history:

```sql
SELECT *
FROM read_parquet('database/r/RELIANCE/day.parquet')
ORDER BY timestamp;
```

Find high-delivery sessions:

```sql
SELECT timestamp, close, volume, delivery, del_percent
FROM read_parquet('database/r/RELIANCE/day.parquet')
WHERE del_percent >= 60
ORDER BY timestamp DESC;
```

Scan all daily files without loading minute data:

```sql
SELECT filename, min(timestamp) AS first_date, max(timestamp) AS last_date,
       count(*) AS trading_days
FROM read_parquet('database/*/*/day.parquet', filename = true, union_by_name = true)
GROUP BY filename
ORDER BY filename;
```

Aggregate one-minute data into five-minute candles:

```sql
SELECT
  time_bucket(INTERVAL '5 minutes', timestamp) AS timestamp,
  first(open ORDER BY timestamp) AS open,
  max(high) AS high,
  min(low) AS low,
  last(close ORDER BY timestamp) AS close,
  sum(volume) AS volume
FROM read_parquet('database/r/RELIANCE/1m.parquet')
GROUP BY 1
ORDER BY 1;
```

## Python with DuckDB

```python
import duckdb

con = duckdb.connect()
daily = con.execute("""
    SELECT timestamp, open, high, low, close, volume, delivery, del_percent
    FROM read_parquet(?)
    WHERE timestamp BETWEEN ? AND ?
    ORDER BY timestamp
""", [
    "database/r/RELIANCE/day.parquet",
    "2024-01-01",
    "2024-12-31",
]).df()

print(daily.describe())
```

Use bound parameters for user-selected paths and dates rather than interpolating untrusted text into SQL.

## pandas

```python
import pandas as pd

daily = pd.read_parquet("database/r/RELIANCE/day.parquet")
daily = daily.sort_values("timestamp")
daily["delivery_to_volume"] = daily["delivery"] / daily["volume"] * 100
print(daily.tail())
```

Install a Parquet engine such as `pyarrow` if pandas does not already have one.

## Polars

```python
import polars as pl

daily = (
    pl.scan_parquet("database/r/RELIANCE/day.parquet")
    .filter(pl.col("timestamp") >= pl.date(2024, 1, 1))
    .sort("timestamp")
    .collect()
)
print(daily.tail())
```

## Discover available symbols

PowerShell:

```powershell
Get-ChildItem database -Directory |
  Where-Object Name -ne '_cache' |
  Get-ChildItem -Directory |
  Select-Object -ExpandProperty Name |
  Sort-Object -Unique
```

Python:

```python
from pathlib import Path
from urllib.parse import unquote

symbols = sorted({unquote(path.parent.name) for path in Path("database").glob("*/*/day.parquet")})
print(symbols[:20])
```

## Open OLO DB Viewer

On Windows, double-click `olo-db-viewer.bat` in the repository root. The viewer is a checker and exploration aid; programmatic pipelines should use the Parquet contract documented here.

![OLO DB Viewer charting daily NSE OHLC, volume, and delivery data](assets/olo-db-viewer-snapshot.png)

The interface provides symbol search, timeframe selection, point-in-time cutoffs, visible-bar controls, price indicators, and bottom-panel volume/delivery metrics.
