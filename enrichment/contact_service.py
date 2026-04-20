class ContactService:
    def __init__(self, data_source):
        self.data_source = data_source

    def get_contact(self, crash_id):
        # lookup from private source
        return self.data_source.get(crash_id)

    def get_crash_contact(self, crash_id):
        """Direct accessor for crash contact lookup."""
        return self.get_contact(crash_id)

    def has_crash_contact(self, crash_id):
        """Return True when a crash_id has an associated contact."""
        return self.get_contact(crash_id) is not None
