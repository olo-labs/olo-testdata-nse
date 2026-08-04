from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

from .base import SourceAdapter


class NseMinuteZipAdapter(SourceAdapter):
    name = "nse_minute_zip"
    timeframe = "1m"
    version = 2

    def discover(self) -> Iterable[Path]:
        return sorted(self.root.glob("*.zip"))

    def ingest(self, connection, source: Path, source_key: str) -> set[str]:
        with zipfile.ZipFile(source) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) != 1:
                raise ValueError(f"Expected exactly one CSV in {source}, found {len(members)}")
            with tempfile.TemporaryDirectory(prefix="nse-minute-") as temp_dir:
                extracted = Path(archive.extract(members[0], temp_dir))
                connection.execute(
                    """
                    INSERT INTO candles
                    SELECT
                        ? AS source_key,
                        '1m' AS timeframe,
                        regexp_replace(trim(ticker), '(\\.NC)?\\.NSE$', '') AS symbol,
                        strptime(trim(date) || ' ' || trim(time), '%d/%m/%Y %H:%M:%S') AS timestamp,
                        CAST(open AS DOUBLE),
                        CAST(high AS DOUBLE),
                        CAST(low AS DOUBLE),
                        CAST(_close AS DOUBLE),
                        CAST(volume AS BIGINT),
                        NULL::BIGINT AS delivery,
                        NULL::DOUBLE AS del_percent
                    FROM read_csv(?, header=true, all_varchar=true, normalize_names=true)
                    WHERE regexp_matches(trim(ticker), '(\\.NC)?\\.NSE$')
                      AND regexp_replace(trim(ticker), '(\\.NC)?\\.NSE$', '') IN
                          (SELECT symbol FROM equity_symbols)
                    """,
                    [source_key, str(extracted)],
                )
        # Any changed minute archive can affect the full equity universe. The
        # orchestrator marks that universe for bulk export, avoiding a costly
        # full-table DISTINCT scan after every archive.
        return set()
