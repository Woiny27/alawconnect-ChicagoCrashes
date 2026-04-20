import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from ..utils.logger import setup_logger


class BaseContactSource(ABC):
    @abstractmethod
    def lookup(self, report_id: str) -> Any:
        raise NotImplementedError


class SheetContactSource(BaseContactSource):
    def __init__(self, sheet: Any):
        self.sheet = sheet

    def lookup(self, report_id):
        return self.sheet.get(report_id)


def purchase_crash_report(report_id: str) -> Any:
    """Placeholder for a paid/authorized crash report lookup integration."""
    raise NotImplementedError("Texas crash report purchase integration is not configured")


class TexasContactSource(BaseContactSource):
    def lookup(self, report_id):
        # requires paid / authorized access
        return purchase_crash_report(report_id)


def fetch_from_flhsmv(report_id: str) -> Any:
    """Placeholder for FLHSMV lookup when eligibility/purchase requirements are met."""
    raise NotImplementedError("FLHSMV contact lookup integration is not configured")


class FloridaContactSource(BaseContactSource):
    def lookup(self, report_id):
        # only if eligible + purchased
        return fetch_from_flhsmv(report_id)


def vendor_lookup(report_id: str) -> Any:
    """Placeholder for preferred California vendor-based contact lookup."""
    raise NotImplementedError("California vendor lookup integration is not configured")


class CaliforniaContactSource(BaseContactSource):
    def lookup(self, report_id):
        return vendor_lookup(report_id)  # preferred


class MidwestContactSource(BaseContactSource):
    def lookup(self, report_id):
        return vendor_lookup(report_id)


def query_buycrash(report_id: str) -> Any:
    """Placeholder for LexisNexis BuyCrash lookup integration."""
    raise NotImplementedError("LexisNexis BuyCrash integration is not configured")


class LexisNexisSource(BaseContactSource):
    def lookup(self, report_id):
        return query_buycrash(report_id)


def query_carfax_portal(report_id: str) -> Any:
    """Placeholder for Carfax portal lookup integration."""
    raise NotImplementedError("Carfax portal integration is not configured")


class CarfaxSource(BaseContactSource):
    def lookup(self, report_id):
        return query_carfax_portal(report_id)


def scrape_or_request(report_id: str) -> Any:
    """Placeholder for Tyler portal scraping or request-based retrieval."""
    raise NotImplementedError("Tyler source integration is not configured")


class TylerSource(BaseContactSource):
    def lookup(self, report_id):
        return scrape_or_request(report_id)


class PrivateDB(BaseContactSource):
    def lookup(self, report_id):
        return None


class VendorSource(BaseContactSource):
    def lookup(self, report_id):
        return None


class StateSource(BaseContactSource):
    def lookup(self, report_id):
        return None


class ContactResolver:
    def __init__(self):
        self.sources = [
            PrivateDB(),
            VendorSource(),
            StateSource(),
        ]

    def resolve(self, report_id):
        for source in self.sources:
            result = source.lookup(report_id)
            if result:
                return result
        return None


class ChicagoContactsProvider:
    """Loads private contacts CSV from your Google Sheet."""

    def __init__(self):
        self.logger = setup_logger()
        root = Path(__file__).resolve().parents[2]
        self.data_dir = str(root / "data")

    def fetch(self, filename="contacts.csv") -> pd.DataFrame:
        """Load the contacts CSV downloaded from your Google Sheet."""
        filepath = os.path.join(self.data_dir, filename)

        if not os.path.exists(filepath):
            self.logger.error(f"Contacts file not found: {filepath}")
            raise FileNotFoundError(f"Place your contacts.csv in {self.data_dir}/")

        self.logger.info(f"Loading contacts from {filepath}")
        df = pd.read_csv(filepath, low_memory=False)

        # Clean phone numbers by removing non-digit characters.
        phone_cols = [col for col in df.columns if "phone" in col.lower()]
        for col in phone_cols:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"\D", "", regex=True)
                .replace("", None)
            )

        self.logger.info(
            f"Loaded {len(df):,} contact records with columns: {list(df.columns)}"
        )
        return df
