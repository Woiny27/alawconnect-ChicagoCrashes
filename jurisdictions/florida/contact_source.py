from typing import Any


def fetch_from_flhsmv(report_id: str) -> Any:
    """Placeholder for FLHSMV lookup when eligibility and purchase rules are satisfied."""
    raise NotImplementedError("FLHSMV contact lookup integration is not configured")


class FloridaContactSource:
    def lookup(self, report_id):
        # only if eligible + purchased
        return fetch_from_flhsmv(report_id)
