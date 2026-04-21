class Provider:
    """
    Base provider interface.
    All providers must implement fetch().
    """

    def fetch(self):
        raise NotImplementedError("Provider must implement fetch method")