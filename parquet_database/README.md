# NSE Parquet database builder

This folder builds one daily and one minute Parquet file per NSE equity. It is incremental: unchanged source files are recorded in `database/manifest.json` and cached as compact source-level Parquet files, so they are not parsed again.

Minute indices from `olo-testdata-nse-min-candle/Minute/NSE_IDX` are also supported. They are exported as minute-only symbols without the equity-universe filter; selecting one in the desktop viewer automatically switches to the `1m` timeframe.

## One-click usage

Double-click `run.bat`, or run it from PowerShell:

```powershell
.\parquet_database\run.bat
```

The root-level one-click commands are:

```bat
recreate.bat
incremental.bat
```

`recreate.bat` deletes and recreates the complete database with the high-memory local profile. `incremental.bat` first initializes and updates all submodules recursively to their latest configured remote revisions, then preserves the manifest/cache and processes detected source changes with the fast local profile. The build does not start if a submodule update fails. Extra options can be appended to either command.

The first run creates a local `.venv` and installs the pinned DuckDB Python package. If Python is unavailable, the launcher installs Python 3.12 for the current Windows user with `winget`.

DuckDB reads each CSV directly with `read_csv(...)` and writes its cache with `COPY ... TO PARQUET`. ZIP files are only extracted to a temporary CSV first; Python does not parse their rows. Content-based fingerprints make the manifest stable across fresh Git/CI checkouts, so subsequent runs process only genuinely new, changed, or removed source files.

Detailed progress is printed and appended to `database/build.log`, including overall percentage, elapsed seconds, phase counts, filenames, and whether each source was processed or served from cache.

Two resource profiles are included in `config.json`:

- `local` (default): 112 GB and 72 DuckDB threads for producing a base release on the 128 GB / 80-thread workstation. Export uses 128 hash buckets instead of one global sort so CPU and memory can work in parallel.
- `ci`: 8 GB and 4 threads for a bounded Git-triggered incremental build.

`release_version` is the version used by the manual GitHub release workflow. Update it (for example, from `V1.0.0` to `V1.0.1`), update the heading/content in `../RELEASE_NOTES.md`, commit both changes, and run **Actions > Manual database release > Run workflow**. The workflow performs a clean build, verifies it, and publishes an immutable GitHub release containing the database without its build cache, the viewer, release notes, and license.

The workflow first attempts to upload a single `olo-testdata-nse-Vx.y.z.zip` together with its SHA-256 checksum. If that upload fails (for example, because it exceeds GitHub's per-asset size limit), the draft release instead receives one daily ZIP and one or more numbered minute ZIPs, each safely below the asset limit. All fallback archives include the viewer, release notes, and license. Extract every fallback ZIP into the same destination: their matching versioned root and `database/` paths merge, and the included viewer automatically discovers both sets of files as one database.

The processing manifest is committed only after output verification, so an interrupted export is retried safely. Incremental export is timeframe-aware: changing delivery data rewrites only `day.parquet`; changing minute data rewrites only `1m.parquet`.

Force a complete rebuild:

```powershell
.\parquet_database\run.bat --refresh
```

CI/resource-limited run:

```powershell
.\parquet_database\build.ps1 -Profile ci
```

For a release pipeline, restore both `database/` and `database/_cache/` from the previous release artifact, update the submodules, run the CI profile, verify, and atomically publish the new `database/` artifact. Keep the manifest and `_cache` in the build artifact even if consumers receive only symbol Parquets; they are what make incremental processing possible. A major release uses `-Refresh -Profile local`. A rolling fortnight release should replace only its rolling release asset/tag, while versioned major release assets remain immutable.

The included `.github/workflows/incremental-database-release.yml` runs when either checked-in submodule pointer changes, when the builder changes, when manually dispatched, or when it receives a `submodule-updated` repository-dispatch event. A daily scheduled run is a fallback for missed events. It resolves both submodules to their configured latest branches, downloads the `nse-parquet-database.7z.*` volumes from the `database-fortnight-latest` release, runs an incremental CI build, verifies it, and replaces that rolling release. It never modifies versioned major releases. The archive is split into 1.9 GB volumes to remain below GitHub's per-asset size limit; download every volume and extract `.001`. `database/submodule-revisions.txt` records the exact input commits used.

For immediate cross-repository triggering, each source repository can send this event after pushing its data commit (using a token that can dispatch events to this repository):

```bash
gh api repos/olo-labs/olo-testdata-parquet/dispatches -f event_type=submodule-updated
```

Before the first automated run, publish the rolling base after `recreate.bat` succeeds:

```powershell
7z a -t7z -mx=5 -v1900m nse-parquet-database.7z database
gh release create database-fortnight-latest nse-parquet-database.7z.* --title "Latest fortnight database"
```

Validate the existing DuckDB state and all output Parquet schemas:

```powershell
.\parquet_database\run.bat --verify-only
```

## Output layout

```text
database/
  state.duckdb
  a/
    ABC/
      day.parquet
      1m.parquet
  3/
    3MINDIA/
      day.parquet
      1m.parquet
```

Each file has this ordered schema:

`timestamp, open, high, low, close, volume, delivery, del_percent`

Row order is not guaranteed; use `ORDER BY timestamp` when chronological ordering is required. Avoiding a global sort allows updates to stream efficiently across more than 100 million minute rows.

Minute data has null `delivery` and `del_percent` because those values do not exist in the minute source. Only symbols present as `EQ` in the daily source are exported.

The daily adapter detects and reads upstream Excel workbooks even when they are incorrectly named with a `.csv` extension.

## Adding another source format

Implement `SourceAdapter` from `adapters/base.py`, including deterministic discovery and normalized insertion into the `candles` table. Register the adapter in `build_database.py`. The incremental manifest and export logic require no changes.

Paths and Parquet compression are controlled by `config.json`. Relative paths are resolved from that configuration file.
