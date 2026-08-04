# Frequently Asked Questions About NSE OHLCV and Delivery Parquet Data

## Where can I find NSE historical delivery data in Parquet format?

Daily delivery data is stored as `database/<first-character>/<symbol>/day.parquet`. Each row contains OHLC, traded volume, deliverable quantity in `delivery`, and delivery percentage in `del_percent`.

## Does this repository contain NSE one-minute historical data?

Yes. Available equity and index one-minute candles are stored in `1m.parquet` files with timestamp, OHLC, and volume. Delivery fields are null because the minute source does not provide delivery statistics.

## Is there one large Parquet file or one file per stock?

The consumer database uses one file per symbol and timeframe. This allows applications to read a single stock without scanning the entire NSE dataset. DuckDB can still query all files through a glob.

## What is the schema?

`timestamp, open, high, low, close, volume, delivery, del_percent`. See the [data dictionary](DATA_DICTIONARY.md) for types and definitions.

## Is the data sorted by timestamp?

Do not rely on physical Parquet row order. Use `ORDER BY timestamp` or sort the DataFrame before time-series calculations.

## Is delivery percentage available for intraday candles?

No. `delivery` and `del_percent` are daily-only. They are intentionally null in `1m.parquet`.

## Are prices adjusted for splits, dividends, and bonuses?

Adjustment is not guaranteed. Validate corporate actions independently before calculating long-horizon returns or training price-based models.

## How do I update the database?

Run `incremental.bat` from the repository root to update configured submodules and rebuild changed outputs. Run `recreate.bat` for a complete rebuild.

## How do I validate a downloaded or generated database?

Run `.\parquet_database\run.bat --verify-only`, then apply the consumer checks in [DATA_QUALITY.md](DATA_QUALITY.md).

## Can I use pandas, Polars, Spark, or DuckDB?

Yes. The outputs are standard Parquet. DuckDB is used by the builder and is especially convenient for glob queries; pandas and Polars examples are in [QUICKSTART.md](QUICKSTART.md).

## Is this official NSE data or investment advice?

No. This is an independent community repository and is not affiliated with or endorsed by NSE. Verify source rights, data accuracy, and fitness for your use case. Nothing here is investment advice.
