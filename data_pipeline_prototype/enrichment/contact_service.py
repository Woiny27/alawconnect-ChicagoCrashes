import os


class ContactService:
    def __init__(self, data_source, google_creds=None, sheet_name=None):
        self.data_source = data_source
        self.google_creds = google_creds or os.getenv("GOOGLE_CREDS")
        self.sheet_name = sheet_name or os.getenv("SHEET_NAME", "crash_contacts")

    def get_contact(self, crash_id):
        # lookup from private source
        return self.data_source.get(crash_id)

    def get_crash_contact(self, crash_id):
        """Direct accessor for crash contact lookup."""
        return self.get_contact(crash_id)

    def has_crash_contact(self, crash_id):
        """Return True when a crash_id has an associated contact."""
        return self.get_contact(crash_id) is not None
