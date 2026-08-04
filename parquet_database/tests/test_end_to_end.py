from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILDER = PROJECT_ROOT / "parquet_database" / "fast_build_database.py"


class EndToEndTest(unittest.TestCase):
    def test_build_incremental_update_and_refresh(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temporary:
            root = Path(temporary)
            day = root / "input" / "day"
            minute = root / "input" / "minute"
            output = root / "database"
            day.mkdir(parents=True)
            minute.mkdir(parents=True)
            daily_file = day / "delivery_01-Jan-2025.csv"
            self.write_day(daily_file, close="105")
            self.write_minute(minute / "01012025.zip")
            config = root / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "database_dir": str(output),
                        "day_source": str(day),
                        "minute_source": str(minute),
                        "compression": "zstd",
                    }
                ),
                encoding="utf-8",
            )

            first = self.run_builder(config)
            self.assertIn("Verified 2 output files", first.stdout)
            day_parquet = output / "a" / "ABC" / "day.parquet"
            minute_parquet = output / "a" / "ABC" / "1m.parquet"
            self.assertTrue(day_parquet.is_file())
            self.assertTrue(minute_parquet.is_file())
            connection = duckdb.connect()
            self.assertEqual(connection.execute("SELECT close FROM read_parquet(?)", [str(day_parquet)]).fetchone()[0], 105)
            self.assertEqual(connection.execute("SELECT delivery FROM read_parquet(?)", [str(day_parquet)]).fetchone()[0], 500)
            self.assertIsNone(connection.execute("SELECT delivery FROM read_parquet(?)", [str(minute_parquet)]).fetchone()[0])

            second = self.run_builder(config)
            self.assertIn("No source changes", second.stdout)
            self.write_day(daily_file, close="106")
            third = self.run_builder(config)
            self.assertIn("Day 1/1 processed", third.stdout)
            self.assertEqual(connection.execute("SELECT close FROM read_parquet(?)", [str(day_parquet)]).fetchone()[0], 106)

            refreshed = self.run_builder(config, "--refresh")
            self.assertIn("Day 1/1 processed", refreshed.stdout)
            verified = self.run_builder(config, "--verify-only")
            self.assertIn("Verified", verified.stdout)

    @staticmethod
    def write_day(path: Path, close: str) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["SYMBOL", " SERIES", " DATE1", " PREV_CLOSE", " OPEN_PRICE", " HIGH_PRICE", " LOW_PRICE", " LAST_PRICE", " CLOSE_PRICE", " AVG_PRICE", " TTL_TRD_QNTY", " TURNOVER_LACS", " NO_OF_TRADES", " DELIV_QTY", " DELIV_PER"])
            writer.writerow(["ABC", " EQ", " 01-Jan-2025", " 99", " 100", " 110", " 90", close, close, " 101", " 1000", " 1", " 5", " 500", " 50"])
            writer.writerow(["BOND1", " BE", " 01-Jan-2025", " 1", " 1", " 1", " 1", " 1", " 1", " 1", " 1", " 1", " 1", " 1", " 100"])

    @staticmethod
    def write_minute(path: Path) -> None:
        csv_text = "Ticker,Date,Time,Open,High,Low,Close,Volume,Open Interest\nABC.NC.NSE,01/01/2025,09:15:59,100,101,99,100.5,10,0\nBOND1.NC.NSE,01/01/2025,09:15:59,1,1,1,1,1,0\n"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("minute.csv", csv_text)

    @staticmethod
    def run_builder(config: Path, *arguments: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--config", str(config), *arguments],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise AssertionError(f"Builder failed ({result.returncode}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result


if __name__ == "__main__":
    unittest.main()
