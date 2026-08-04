"""Create independently extractable release ZIPs below GitHub's asset limit."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def chunks(files: list[Path], maximum_bytes: int) -> list[list[Path]]:
    groups: list[list[Path]] = []
    current: list[Path] = []
    current_size = 0
    for path in files:
        size = path.stat().st_size
        if current and current_size + size > maximum_bytes:
            groups.append(current)
            current, current_size = [], 0
        current.append(path)
        current_size += size
    if current:
        groups.append(current)
    return groups


def write_zip(output: Path, release_dir: Path, common: list[Path], data: list[Path]) -> None:
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        for path in [*common, *data]:
            archive.write(path, path.relative_to(release_dir))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("version")
    parser.add_argument("--group-bytes", type=int, default=1_800_000_000)
    args = parser.parse_args()

    release_dir = args.release_dir.resolve()
    root = release_dir / f"olo-testdata-nse-{args.version}"
    database = root / "database"
    common_roots = [
        root / "olo-db-viewer",
        root / "olo-db-viewer.bat",
        root / "LICENSE",
        root / "RELEASE_NOTES.md",
    ]
    common = sorted(
        path
        for item in common_roots
        for path in ([item] if item.is_file() else item.rglob("*"))
        if path.is_file()
    )

    daily = sorted(database.rglob("day.parquet"))
    minute = sorted(database.rglob("1m.parquet"))
    if not daily or not minute:
        raise SystemExit("Both daily and minute Parquet files are required for a split release")

    outputs: list[Path] = []
    daily_output = release_dir / f"olo-testdata-nse-{args.version}-daily.zip"
    write_zip(daily_output, release_dir, common, daily)
    outputs.append(daily_output)

    minute_groups = chunks(minute, args.group_bytes)
    for index, group in enumerate(minute_groups, start=1):
        suffix = "minute" if len(minute_groups) == 1 else f"minute-{index:03d}"
        output = release_dir / f"olo-testdata-nse-{args.version}-{suffix}.zip"
        write_zip(output, release_dir, common, group)
        outputs.append(output)

    checksum = release_dir / f"olo-testdata-nse-{args.version}-split.sha256"
    checksum.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in outputs),
        encoding="ascii",
    )
    for path in outputs:
        if path.stat().st_size >= 2_147_483_648:
            raise SystemExit(f"Fallback asset still exceeds GitHub's limit: {path.name}")


if __name__ == "__main__":
    main()
