from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

import duckdb

from adapters import NseDayDeliveryAdapter, NseMinuteZipAdapter

SCHEMA_VERSION = 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build incremental NSE symbol Parquet files.")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--refresh", action="store_true", help="Delete generated state/output and rebuild all files.")
    parser.add_argument("--verify-only", action="store_true", help="Validate an existing database without changing it.")
    return parser.parse_args()


def resolve_config(path: Path) -> dict:
    path = path.resolve()
    config = json.loads(path.read_text(encoding="utf-8"))
    for key in ("database_dir", "day_source", "minute_source"):
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
        candidate = Path(config[key])
        config[key] = (path.parent / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    config.setdefault("compression", "zstd")
    if config["compression"].lower() not in {"zstd", "snappy", "gzip", "lz4", "uncompressed"}:
        raise ValueError("compression must be zstd, snappy, gzip, lz4, or uncompressed")
    return config


def validate_paths(config: dict) -> None:
    for key in ("day_source", "minute_source"):
        if not config[key].is_dir():
            raise FileNotFoundError(f"Configured {key} does not exist: {config[key]}")
    project_root = Path(__file__).resolve().parent.parent
    output = config["database_dir"]
    if output == project_root or project_root not in output.parents:
        raise ValueError(f"database_dir must be a child of {project_root}: {output}")


def create_schema(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata(key VARCHAR PRIMARY KEY, value VARCHAR NOT NULL);
        CREATE TABLE IF NOT EXISTS sources(
            source_key VARCHAR PRIMARY KEY,
            adapter VARCHAR NOT NULL,
            path VARCHAR NOT NULL,
            fingerprint VARCHAR NOT NULL,
            processed_at TIMESTAMP NOT NULL DEFAULT current_timestamp
        );
        CREATE TABLE IF NOT EXISTS candles(
            source_key VARCHAR NOT NULL,
            timeframe VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            delivery BIGINT,
            del_percent DOUBLE
        );
        CREATE TABLE IF NOT EXISTS equity_symbols(symbol VARCHAR PRIMARY KEY);
        CREATE INDEX IF NOT EXISTS candles_source_idx ON candles(source_key);
        CREATE INDEX IF NOT EXISTS candles_symbol_idx ON candles(symbol, timeframe);
        """
    )
    version = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    if version and int(version[0]) != SCHEMA_VERSION:
        raise RuntimeError("Database schema changed; run run.bat --refresh")
    connection.execute(
        "INSERT OR REPLACE INTO metadata VALUES ('schema_version', ?)", [str(SCHEMA_VERSION)]
    )


def safe_symbol_name(symbol: str) -> str:
    return quote(symbol, safe="-_.&()")


def symbol_group(symbol: str) -> str:
    first = symbol[0].lower() if symbol else "_"
    return first if first.isascii() and first.isalnum() else "_"


def export_symbols(connection, database_dir: Path, symbols: set[str], compression: str) -> None:
    ordered = sorted(symbols)
    if not ordered:
        return
    connection.execute("CREATE OR REPLACE TEMP TABLE affected_exports(partition_id INTEGER, symbol VARCHAR)")
    connection.executemany(
        "INSERT INTO affected_exports VALUES (?, ?)",
        [(index, symbol) for index, symbol in enumerate(ordered)],
    )
    with tempfile.TemporaryDirectory(prefix="_export_", dir=database_dir) as temporary_dir:
        escaped = temporary_dir.replace("'", "''")
        connection.execute(
            f"""
            COPY (
                SELECT
                    affected.partition_id,
                    candles.timeframe,
                    candles.timestamp,
                    candles.open,
                    candles.high,
                    candles.low,
                    candles.close,
                    candles.volume,
                    candles.delivery,
                    candles.del_percent
                FROM candles
                JOIN affected_exports affected USING (symbol)
            ) TO '{escaped}' (
                FORMAT PARQUET,
                COMPRESSION {compression.upper()},
                PARTITION_BY (partition_id, timeframe),
                FILENAME_PATTERN 'data_{{i}}'
            )
            """
        )
        for index, symbol in enumerate(ordered):
            symbol_dir = database_dir / symbol_group(symbol) / safe_symbol_name(symbol)
            for timeframe in ("day", "1m"):
                output = symbol_dir / f"{timeframe}.parquet"
                pieces = sorted(
                    (Path(temporary_dir) / f"partition_id={index}" / f"timeframe={timeframe}").glob("*.parquet")
                )
                if not pieces:
                    if output.exists():
                        output.unlink()
                    continue
                symbol_dir.mkdir(parents=True, exist_ok=True)
                if len(pieces) == 1:
                    os.replace(pieces[0], output)
                else:
                    piece_list = ",".join(
                        "'" + str(piece).replace("'", "''") + "'" for piece in pieces
                    )
                    temporary_output = output.with_suffix(".parquet.tmp")
                    connection.execute(
                        f"COPY (SELECT * FROM read_parquet([{piece_list}]) ORDER BY timestamp) "
                        f"TO '{str(temporary_output).replace("'", "''")}' "
                        f"(FORMAT PARQUET, COMPRESSION {compression.upper()})"
                    )
                    os.replace(temporary_output, output)
            if symbol_dir.exists() and not any(symbol_dir.iterdir()):
                symbol_dir.rmdir()


def verify(connection, database_dir: Path) -> None:
    source_count = connection.execute("SELECT count(*) FROM sources").fetchone()[0]
    candle_count = connection.execute("SELECT count(*) FROM candles").fetchone()[0]
    symbols = connection.execute("SELECT count(*) FROM equity_symbols").fetchone()[0]
    parquet_files = list(database_dir.glob("*/*/*.parquet"))
    timeframe_counts = dict(
        connection.execute("SELECT timeframe, count(*) FROM candles GROUP BY timeframe").fetchall()
    )
    for timeframe in ("day", "1m"):
        if timeframe_counts.get(timeframe, 0) == 0:
            raise RuntimeError(f"No {timeframe} candle rows were generated")
    if candle_count and not parquet_files:
        raise RuntimeError("Candles exist in DuckDB but no Parquet files were found")
    malformed = [p for p in parquet_files if p.name not in {"1m.parquet", "day.parquet"}]
    if malformed:
        raise RuntimeError(f"Unexpected Parquet filename: {malformed[0]}")
    if parquet_files:
        glob_path = str(database_dir / "*" / "*" / "*.parquet").replace("'", "''")
        bad_schema = connection.execute(
            f"""
            SELECT count(*) FROM (
                DESCRIBE SELECT * FROM read_parquet('{glob_path}', union_by_name=true)
            ) WHERE column_name NOT IN
                ('timestamp','open','high','low','close','volume','delivery','del_percent')
            """
        ).fetchone()[0]
        if bad_schema:
            raise RuntimeError("One or more generated Parquet files have an unexpected schema")
    print(
        f"Verified: {source_count:,} sources, {symbols:,} equities, "
        f"{timeframe_counts['day']:,} day rows, {timeframe_counts['1m']:,} minute rows, "
        f"{len(parquet_files):,} Parquet files"
    )


def process_adapter(
    connection, adapter, known: dict, force_all: bool = False, collect_affected: bool = True
) -> tuple[set[str], dict, bool]:
    discovered = {adapter.source_key(path): path for path in adapter.discover()}
    existing_keys = {key for key, row in known.items() if row["adapter"] == adapter.name}
    deleted = existing_keys - discovered.keys()
    changed = {
        key
        for key, path in discovered.items()
        if force_all or key not in known or known[key]["fingerprint"] != adapter.fingerprint(path)
    }
    affected: set[str] = set()
    work = sorted(deleted | changed)
    if not work:
        print(f"{adapter.name}: no changes ({len(discovered):,} files already processed)")
        return affected, discovered, False
    print(f"{adapter.name}: {len(changed):,} new/changed, {len(deleted):,} deleted")
    for index, key in enumerate(work, 1):
        connection.execute("BEGIN TRANSACTION")
        try:
            if collect_affected:
                old_symbols = connection.execute(
                    "SELECT DISTINCT symbol FROM candles WHERE source_key=?", [key]
                ).fetchall()
                affected.update(row[0] for row in old_symbols)
            connection.execute("DELETE FROM candles WHERE source_key=?", [key])
            connection.execute("DELETE FROM sources WHERE source_key=?", [key])
            if key in discovered:
                source = discovered[key]
                loaded_symbols = adapter.ingest(connection, source, key)
                if collect_affected:
                    affected.update(loaded_symbols)
                connection.execute(
                    "INSERT INTO sources(source_key,adapter,path,fingerprint) VALUES (?,?,?,?)",
                    [key, adapter.name, str(source), adapter.fingerprint(source)],
                )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        if index % 25 == 0 or index == len(work):
            print(f"  processed {index:,}/{len(work):,}")
    return affected, discovered, True


def main() -> int:
    args = parse_args()
    config = resolve_config(args.config)
    validate_paths(config)
    database_dir: Path = config["database_dir"]
    if args.refresh and args.verify_only:
        raise ValueError("--refresh and --verify-only cannot be used together")
    if args.refresh and database_dir.exists():
        print(f"Full refresh: removing generated database {database_dir}")
        shutil.rmtree(database_dir)
    database_dir.mkdir(parents=True, exist_ok=True)
    for orphan in database_dir.glob("_export_*"):
        if orphan.is_dir():
            shutil.rmtree(orphan)
    state_path = database_dir / "state.duckdb"
    if args.verify_only and not state_path.exists():
        raise FileNotFoundError(f"No database to verify: {state_path}")
    connection = duckdb.connect(str(state_path))
    connection.execute(f"SET temp_directory='{str(database_dir / '_temp').replace("'", "''")}'")
    connection.execute("SET preserve_insertion_order=false")
    create_schema(connection)
    if args.verify_only:
        verify(connection, database_dir)
        return 0

    rows = connection.execute("SELECT source_key,adapter,fingerprint FROM sources").fetchall()
    known = {row[0]: {"adapter": row[1], "fingerprint": row[2]} for row in rows}
    day_adapter = NseDayDeliveryAdapter(config["day_source"])
    minute_adapter = NseMinuteZipAdapter(config["minute_source"])

    started = time.monotonic()
    day_affected, _, _ = process_adapter(connection, day_adapter, known)
    previous_universe = {row[0] for row in connection.execute("SELECT symbol FROM equity_symbols").fetchall()}
    connection.execute("DELETE FROM equity_symbols")
    connection.execute("INSERT INTO equity_symbols SELECT DISTINCT symbol FROM candles WHERE timeframe='day'")
    current_universe = {row[0] for row in connection.execute("SELECT symbol FROM equity_symbols").fetchall()}
    universe_changed = previous_universe != current_universe
    # A changed universe requires rebuilding minute rows so newly classified equities are included.
    rows = connection.execute("SELECT source_key,adapter,fingerprint FROM sources").fetchall()
    known = {row[0]: {"adapter": row[1], "fingerprint": row[2]} for row in rows}
    minute_affected, _, minute_changed = process_adapter(
        connection,
        minute_adapter,
        known,
        force_all=universe_changed and bool(previous_universe),
        collect_affected=False,
    )
    if minute_changed:
        minute_affected = set(current_universe)

    affected = (day_affected | minute_affected | (previous_universe ^ current_universe))
    if not previous_universe:  # first build
        affected = current_universe
    # Recover cleanly when an earlier run committed sources but was interrupted
    # during the atomic bulk-export phase.
    expected_outputs = connection.execute(
        "SELECT DISTINCT symbol, timeframe FROM candles"
    ).fetchall()
    for symbol, timeframe in expected_outputs:
        output = database_dir / symbol_group(symbol) / safe_symbol_name(symbol) / f"{timeframe}.parquet"
        if not output.is_file():
            affected.add(symbol)
    print(f"Exporting {len(affected):,} affected symbols...")
    export_symbols(connection, database_dir, affected, config["compression"])
    print(f"  exported {len(affected):,}/{len(affected):,}")
    connection.execute("CHECKPOINT")
    verify(connection, database_dir)
    print(f"Completed in {time.monotonic() - started:,.1f} seconds")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
