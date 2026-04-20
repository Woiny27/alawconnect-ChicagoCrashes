from __future__ import annotations

import pandas as pd


def ensure_crash_join_id(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure a DataFrame has crash_join_id using known fallback columns."""
    out = df.copy()

    if "crash_join_id" in out.columns:
        return out

    if "crash_record_id" in out.columns:
        out["crash_join_id"] = out["crash_record_id"]
        return out

    if "crash_id" in out.columns:
        out["crash_join_id"] = out["crash_id"]
        return out

    if "rd" in out.columns:
        out["crash_join_id"] = out["rd"]
        return out

    raise ValueError(
        "DataFrame must include 'crash_join_id', 'crash_record_id', 'crash_id', or 'rd'"
    )


def merge_crashes_with_contacts(
    crashes_df: pd.DataFrame,
    contacts_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge crash and contact dataframes on crash_join_id with safe key normalization."""
    normalized_crashes = ensure_crash_join_id(crashes_df)
    normalized_contacts = ensure_crash_join_id(contacts_df)

    return normalized_crashes.merge(
        normalized_contacts,
        how="left",
        on="crash_join_id",
        suffixes=("", "_contact"),
    )