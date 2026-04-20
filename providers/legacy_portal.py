from providers.nhtsa_discovery import NHTSADiscoveryModule


class LegacyPortalProvider(NHTSADiscoveryModule):
    """Legacy portal provider backed by NHTSA CrashAPI helpers."""
