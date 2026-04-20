from pathlib import Path
import sys


# Allow importing from data_pipeline_prototype/ when running from repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "data_pipeline_prototype"))

from enrichment.contact_service import ContactService


def enrich_crash(crash, contact_service):
    contact = contact_service.get_contact(crash["crash_id"])

    crash["contact"] = contact
    crash["has_contact"] = contact is not None

    return crash


def main() -> None:
    # Fake private source keyed by crash_id.
    private_contacts = {
        "C-1001": {
            "name": "Alex Rivera",
            "phone": "3125550101",
            "email": "alex@example.com",
        },
        "C-1003": {
            "name": "Jordan Kim",
            "phone": "7735550123",
            "email": "jordan@example.com",
        },
    }

    contact_service = ContactService(data_source=private_contacts)

    crashes = [
        {"crash_id": "C-1001", "city": "Chicago", "severity": "medium"},
        {"crash_id": "C-1002", "city": "Houston", "severity": "high"},
        {"crash_id": "C-1003", "city": "NYC", "severity": "low"},
    ]

    enriched = [enrich_crash(crash, contact_service) for crash in crashes]

    for row in enriched:
        print(row)


if __name__ == "__main__":
    main()
