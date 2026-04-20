import logging
from pathlib import Path
from typing import Any

from src.providers.chicago_crashes import ChicagoCrashesProvider
from src.storage.csv_storage import CsvStorage


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def run_pipeline(limit: int = 50) -> int:
    provider = ChicagoCrashesProvider()
    output_path = Path(__file__).resolve().parents[2] / "data" / "normalized_output.csv"
    storage = CsvStorage(output_path)

    try:
        raw_records = provider.fetch(limit=limit)
    except FileNotFoundError:
        logging.exception("Crash source file was not found.")
        return 1
    except OSError:
        logging.exception("Failed to read crash source data.")
        return 1
    except Exception:
        logging.exception("Unexpected provider error during fetch.")
        return 1

    if not raw_records:
        logging.warning("No data retrieved.")
        return 0

    clean_data = normalize_records(raw_records)
    logging.info("Successfully processed %s records.", len(clean_data))

    try:
        written = storage.upsert(clean_data)
    except OSError:
        logging.exception("Failed to write normalized output.")
        return 1
    except Exception:
        logging.exception("Unexpected storage error during upsert.")
        return 1

    logging.info("Wrote %s normalized records to %s", written, output_path)
    for record in clean_data[:3]:
        print(f"Sample output: {record}")
    return 0


def normalize_records(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for record in raw_records:
        normalized.append(
            {
                "crash_join_id": record.get("crash_join_id")
                or record.get("crash_record_id"),
                "crash_date": record.get("crash_date"),
                "address": build_address(record),
                "status": "normalized",
            }
        )
    return normalized


def build_address(record: dict[str, Any]) -> str | None:
    parts = [
        record.get("street_no"),
        record.get("street_direction"),
        record.get("street_name"),
    ]
    address = " ".join(str(part).strip() for part in parts if part)
    return address or None


if __name__ == "__main__":
    raise SystemExit(run_pipeline())