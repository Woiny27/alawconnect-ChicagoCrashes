class FeatureRegistry:
    """
    Keeps track of feature versions used in production.
    """

    VERSION = "v1.0"

    FEATURES = [
        "lat",
        "lon",
        "hour",
        "is_night",
        "missing_location"
    ]

    def get_features(self):
        return self.FEATURES
