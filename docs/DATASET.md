# Dataset card: NSE India OHLCV and delivery data in Parquet

## Summary

This repository provides query-ready historical National Stock Exchange of India market data organized as one Apache Parquet file per symbol and timeframe. It combines daily equity candles and delivery statistics with one-minute equity and index candles in a consistent eight-column schema.

The symbol-oriented layout is designed for DuckDB, pandas, Polars, PyArrow, Spark, and other tools that read Parquet. It avoids loading a market-wide source archive when an analysis needs only one instrument.

## Dataset components

| Component | File | Frequency | Instruments | Delivery fields |
| --- | --- | --- | --- | --- |
| Daily market and delivery data | `database/<bucket>/<SYMBOL>/day.parquet` | one row per available trading date | NSE equities in the exported `EQ` universe | populated when supplied by the source |
| Intraday market data | `database/<bucket>/<SYMBOL>/1m.parquet` | minute-level candles | available NSE equities and indices | null by design |

`<bucket>` is the lowercase first character of the symbol. For example, `RELIANCE` maps to `database/r/RELIANCE/` and `3MINDIA` maps to `database/3/3MINDIA/`.

## Observation model

One row represents one OHLCV candle for the symbol implied by its parent directory. The row contains:

```text
timestamp, open, high, low, close, volume, delivery, del_percent
```

The symbol is encoded in the path rather than repeated as a Parquet column. Read the [data dictionary](DATA_DICTIONARY.md) for types, nullability, units, and field semantics.

## Intended uses

- Indian equity and index market research;
- delivery-volume and delivery-percentage analysis;
- backtesting inputs after independent validation;
- technical indicators, charting, and screening;
- Parquet, DuckDB, pandas, and Polars examples;
- machine-learning and time-series feature engineering;
- reproducible educational datasets.

## Out-of-scope uses

This is not a real-time feed, tick-by-tick trade dataset, quote feed, order book, corporate-action database, security master, or investment recommendation. It is not affiliated with or endorsed by the National Stock Exchange of India.

Do not assume that minute `volume` means deliverable quantity. Delivery information belongs to the daily `delivery` and `del_percent` fields; minute delivery fields are null.

## Sources and transformation

The generated Parquet database normalizes two repository submodules:

- `olo-testdata-nse-day-delivery-candle` supplies daily equity OHLCV and delivery observations;
- `olo-testdata-nse-min-candle` supplies one-minute equity and index OHLCV observations.

The builder normalizes source names and types into the shared schema and groups output by symbol. Source fingerprints and build state are recorded in `database/manifest.json`. See the [builder documentation](../parquet_database/README.md) for implementation and verification details.

## Biases and limitations

- Coverage varies by symbol and timeframe; file existence does not guarantee a complete interval.
- Symbols can be renamed, delisted, merged, or reused. No point-in-time security master is included.
- Corporate-action adjustment status must be confirmed from the upstream source documentation.
- Missing minute rows are not necessarily zero-volume candles.
- Row order is not guaranteed; queries should explicitly sort by `timestamp`.
- Historical membership based on a present-day symbol list can introduce survivorship bias.
- Delivery values may be unavailable or null for some daily observations.
- Source-data errors can be preserved by normalization.

Read [data quality and validation](DATA_QUALITY.md) before using the data in research or backtests.

## Reproducibility

Record the Git commit or release, symbol path, query, and access date. For critical workflows, also retain Parquet file checksums and the relevant `database/manifest.json` snapshot.

```bash
git rev-parse HEAD
```

The generated database changes as upstream sources are updated, so a repository URL without a commit is not a complete dataset version.

## License and attribution

Repository code and documentation are covered by the root [Apache License 2.0](../LICENSE). Source market data may carry separate rights, exchange terms, or jurisdiction-specific restrictions. Users are responsible for verifying that their intended use and redistribution are permitted.

Use the root [`CITATION.cff`](../CITATION.cff) when citing this dataset.
