"""Scheduling and jurisdiction configuration for ingestion planning."""

from typing import Dict, List, TypedDict


class JurisdictionProfile(TypedDict):
    jurisdiction: str
    agency_place: str
    system_type: str
    access_model: str
    modernization_level: str
    notes: str


INGESTION_JOBS: Dict[str, str] = {
    "chicago": "0 * * * *",
    "nyc": "*/15 * * * *",
    "houston": "30 * * * *",
}


JURISDICTION_PROFILES: List[JurisdictionProfile] = [
    {
        "jurisdiction": "Chicago, IL",
        "agency_place": "Chicago Police / DOT",
        "system_type": "Legacy + hybrid portal",
        "access_model": "Public lookup + internal joins",
        "modernization_level": "Legacy web forms",
        "notes": "RD-based lookup, manual + semi-automated",
    },
    {
        "jurisdiction": "New York, NY",
        "agency_place": "NYPD / NYC Open Data",
        "system_type": "Open data portal + API",
        "access_model": "Open API + public dataset",
        "modernization_level": "Modernized",
        "notes": "Strong API ecosystem",
    },
    {
        "jurisdiction": "Los Angeles, CA",
        "agency_place": "LAPD / CHP",
        "system_type": "Mixed systems",
        "access_model": "Public request + partial API",
        "modernization_level": "Semi-modern",
        "notes": "Some datasets open, some restricted",
    },
    {
        "jurisdiction": "Houston, TX",
        "agency_place": "HPD",
        "system_type": "Vendor + public portal",
        "access_model": "Request-based + limited lookup",
        "modernization_level": "Legacy-heavy",
        "notes": "Often manual retrieval",
    },
    {
        "jurisdiction": "Miami-Dade, FL",
        "agency_place": "FHP / county system",
        "system_type": "Vendor-hosted system",
        "access_model": "Public lookup portal",
        "modernization_level": "Legacy vendor system",
        "notes": "Slow, form-based search",
    },
    {
        "jurisdiction": "Dallas, TX",
        "agency_place": "DPD",
        "system_type": "Custom + public dashboard",
        "access_model": "Open data + request portal",
        "modernization_level": "Moderately modern",
        "notes": "Mix of structured datasets",
    },
    {
        "jurisdiction": "Atlanta, GA",
        "agency_place": "APD",
        "system_type": "State + city hybrid",
        "access_model": "Open data + manual requests",
        "modernization_level": "Mixed legacy",
        "notes": "Some APIs available",
    },
    {
        "jurisdiction": "Philadelphia, PA",
        "agency_place": "PPD",
        "system_type": "Legacy + state system",
        "access_model": "Request + partial public access",
        "modernization_level": "Legacy-heavy",
        "notes": "Manual-heavy workflows",
    },
    {
        "jurisdiction": "Phoenix, AZ",
        "agency_place": "PD / DOT",
        "system_type": "Modern + open data",
        "access_model": "API + download datasets",
        "modernization_level": "Modernized",
        "notes": "Strong GIS integration",
    },
    {
        "jurisdiction": "Detroit, MI",
        "agency_place": "DPD",
        "system_type": "Legacy system",
        "access_model": "Request portal + manual lookup",
        "modernization_level": "Legacy-heavy",
        "notes": "Limited automation support",
    },
]


def get_all_ingestion_jobs() -> Dict[str, str]:
    """Return all city ingestion cron expressions."""
    return dict(INGESTION_JOBS)


def get_ingestion_job_for_city(city: str) -> str:
    """Return a cron expression for a city, raising KeyError when missing."""
    return INGESTION_JOBS[city.lower()]


def get_all_jurisdiction_profiles() -> List[JurisdictionProfile]:
    """Return known jurisdiction system profiles."""
    return [dict(item) for item in JURISDICTION_PROFILES]