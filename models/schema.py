class Record:
    """
    Normalized data schema.
    """

    def __init__(self, record_id, timestamp, location, magnitude):
        self.record_id = record_id
        self.timestamp = timestamp
        self.location = location
        self.magnitude = magnitude

    def to_dict(self):
        return {
            "id": self.record_id,
            "timestamp": self.timestamp,
            "location": self.location,
            "magnitude": self.magnitude,
        }