# OLO NSE database V1.0.0

Initial packaged release of the query-ready NSE Parquet database and OLO DB Viewer.

## Contents

- Symbol-partitioned daily and one-minute Parquet data.
- OLO DB Viewer and its pinned Python dependencies.
- Repository license and these release notes.

The incremental build cache and temporary build files are not included in the consumer archive.

## Split archive fallback

If the release contains a `-daily.zip` and numbered `-minute-001.zip`, `-minute-002.zip`, and subsequent files, extract all of them into the same destination folder. Every archive has the identical `olo-testdata-nse-V1.0.0` root layout, so their `database` directories merge. Then launch `olo-db-viewer.bat` from that merged root; the viewer automatically discovers both daily and minute files from the shared `database` directory.
