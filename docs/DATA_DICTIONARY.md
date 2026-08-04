# NSE OHLCV and Delivery Data Dictionary

The daily and one-minute Parquet files share the same ordered eight-column schema. This makes union queries simple while preserving nulls for fields unavailable at one-minute resolution.

| Column | Type | Nullable | Definition |
| --- | --- | --- | --- |
| `timestamp` | `TIMESTAMP` | no in normalized rows | Candle time. Daily rows represent the trading date; minute rows preserve the source date and time. |
| `open` | `DOUBLE` | source-dependent | First traded price recorded for the candle. |
| `high` | `DOUBLE` | source-dependent | Maximum traded price recorded for the candle. |
| `low` | `DOUBLE` | source-dependent | Minimum traded price recorded for the candle. |
| `close` | `DOUBLE` | source-dependent | Final traded or official closing price recorded for the candle. |
| `volume` | `BIGINT` | source-dependent | Total traded quantity during the candle. This is a quantity, not currency turnover. |
| `delivery` | `BIGINT` | yes | Daily deliverable quantity (`DELIV_QTY`) for the security. Null for minute candles. |
| `del_percent` | `DOUBLE` | yes | Daily deliverable quantity percentage (`DELIV_PER`). Null for minute candles. |

## Delivery-data interpretation

Delivery quantity is the reported quantity marked for delivery rather than the total traded quantity. Delivery percentage is normally interpreted as:

```text
delivery percentage = delivery quantity / traded volume × 100
```

Use the published `del_percent` value for source fidelity. If recalculating it, handle zero/null volume and rounding explicitly.

Example daily row:

```text
2019-06-27 00:00:00, 39.75, 39.90, 38.30, 39.90, 123616, 59890, 48.45
```

Example minute row:

```text
2024-11-25 09:15:59, 63.11, 63.11, 63.10, 63.11, 309, null, null
```

## Expected invariants

For ordinary valid candles:

- `high >= open`, `high >= close`, and `high >= low`.
- `low <= open`, `low <= close`, and `low <= high`.
- `volume`, `delivery`, and `del_percent` should not be negative.
- `del_percent` is generally between 0 and 100 when populated.
- timestamps should be unique per symbol/timeframe after normalization.

Corporate actions, symbol changes, suspended instruments, sparse trading, upstream corrections, and source anomalies can affect continuity and price comparability. Do not treat an OHLC series as automatically adjusted for splits, bonuses, or dividends unless separately verified.
