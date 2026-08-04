# OLO NSE database V1.0.0

Initial packaged release of the query-ready NSE Parquet database and OLO DB Viewer.

## Contents

- Symbol-partitioned daily and one-minute Parquet data.
- OLO DB Viewer and its pinned Python dependencies.
- Repository license and these release notes.

The incremental build cache and temporary build files are not included in the consumer archive.

## Split archive fallback

If the release contains separate `-daily.zip` and `-minute.zip` files, extract both into the same destination folder. Both archives have the identical `olo-testdata-nse-V1.0.0` root layout, so their `database` directories merge. Then launch `olo-db-viewer.bat` from that merged root; the viewer automatically discovers both daily and minute files from the shared `database` directory.
