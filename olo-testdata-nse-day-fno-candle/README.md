# NSE Daily F&O Candles

Incremental archive of NSE F&O UDiFF Common Bhavcopy Final ZIP files under `Day_FNO/NSE`. The report includes index/stock futures and options contracts with daily OHLC, settlement, volume, and open-interest fields.

Run `fno_data_downloader.bat`, or:

```powershell
.\download_fno_data.ps1 -StartDate '2025-01-01' -EndDate '2025-12-31'
```

The downloader skips existing files, ignores weekends/404 holidays, extracts each download temporarily, validates its CSV schema, and retains the original validated ZIP. This independent community project is not affiliated with NSE. NSE data rights and terms remain applicable.
