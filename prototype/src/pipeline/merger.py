from pathlib import Path

import pandas as pd

from src.providers.chicago_contacts import ChicagoContactsProvider
from src.providers.chicago_crashes import ChicagoCrashesProvider


def merge_public_with_contacts(
    contacts_filename: str = "contacts_template.csv", limit: int | None = 200
) -> pd.DataFrame:
    """Merge public crash data with local contacts data using crash_join_id as key."""
    crashes_provider = ChicagoCrashesProvider()
    contacts_provider = ChicagoContactsProvider()

    crashes_rows = crashes_provider.fetch(limit=limit)
    crashes_df = pd.DataFrame(crashes_rows)

    if "crash_join_id" not in crashes_df.columns:
        if "crash_record_id" in crashes_df.columns:
            crashes_df["crash_join_id"] = crashes_df["crash_record_id"]
        elif "rd" in crashes_df.columns:
            crashes_df["crash_join_id"] = crashes_df["rd"]

    contacts_df = contacts_provider.fetch(filename=contacts_filename)

    if "crash_join_id" not in contacts_df.columns:
        if "crash_id" in contacts_df.columns:
            contacts_df["crash_join_id"] = contacts_df["crash_id"]
        elif "rd" in contacts_df.columns:
            contacts_df["crash_join_id"] = contacts_df["rd"]

    if "crash_join_id" not in contacts_df.columns:
        raise ValueError(
            "Contacts file must include 'crash_join_id', 'crash_id', or 'rd' column"
        )

    merged = crashes_df.merge(
        contacts_df,
        how="left",
        on="crash_join_id",
        suffixes=("", "_contact"),
    )
    return merged


def run(
    contacts_filename: str = "contacts_template.csv",
    output_filename: str = "merged_output.csv",
    limit: int | None = 200,
) -> Path:
    """Run merge pipeline and write merged CSV output."""
    root = Path(__file__).resolve().parents[2]
    output_path = root / "data" / output_filename

    merged_df = merge_public_with_contacts(
        contacts_filename=contacts_filename,
        limit=limit,
    )
    merged_df.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    out = run()
    print(f"Merged output written to: {out}")
