# OLO DB Viewer

Repository-local Windows desktop checker for the generated OLO Parquet database.

![OLO DB Viewer interface with NSE candlestick, volume, and delivery charts](../docs/assets/olo-db-viewer-snapshot.png)

## Launch

Double-click `olo-db-viewer.bat` here or in the repository root. The first launch creates `olo-db-viewer/.venv` and installs the pinned dependencies; later launches reuse that environment.

The app always reads `../database` from this repository. It does not accept an external database override and does not depend on repositories outside this repository or its configured submodules.

## Database checks

Select a symbol, timeframe, and cutoff to inspect 1m, 5m, 15m, Day, Week, Month, Quarter, or Year candles. The chart supports Volume, Delivery, Delivery %, and RSI in the bottom panel, plus price overlays configured by `indicators.json`.

Each indicator is listed once and is calculated on the currently selected chart timeframe:

- EMA(5), EMA(9), EMA(20), EMA(36), EMA(100), and EMA(200)
- AMA(10,2,30) using OHLC/4
- Super Trend(10,3)
- RSI(14)
- Anchored VWAP for the configured calendar reset boundaries

The visible-bars and end-time controls make it possible to inspect historical slices without allowing later candles into indicator calculations. UI selections and custom colors are stored locally in the ignored `viewer_state.json` file.

TL indicators are intentionally excluded because their data belongs to another repository.

To update the documentation image after a UI change, replace `../docs/assets/olo-db-viewer-snapshot.png` while keeping that filename.
