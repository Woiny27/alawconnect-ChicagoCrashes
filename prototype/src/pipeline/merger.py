from pathlib import Path

import pandas as pd

from src.providers.chicago_contacts import ChicagoContactsProvider
from src.providers.chicago_crashes import ChicagoCrashesProvider
from src.utils.data_merger import merge_crashes_with_contacts


def merge_public_with_contacts(
    contacts_filename: str = "contacts_template.csv", limit: int | None = 200
) -> pd.DataFrame:
    """Merge public crash data with local contacts data using crash_join_id as key."""
    crashes_provider = ChicagoCrashesProvider()
    contacts_provider = ChicagoContactsProvider()

    crashes_rows = crashes_provider.fetch(limit=limit)
    crashes_df = pd.DataFrame(crashes_rows)

    contacts_df = contacts_provider.fetch(filename=contacts_filename)

    merged = merge_crashes_with_contacts(crashes_df, contacts_df)
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
