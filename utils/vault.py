import logging
import os

logger = logging.getLogger(__name__)


class Vault:
    """
    Secure storage for API keys and credit tokens used by paywall-protected
    data sources (e.g. Michigan, Indianapolis).

    Credentials are loaded exclusively from environment variables so that no
    secrets are ever committed to source code.  Optionally, a .env file can be
    loaded at start-up by calling ``Vault.load_dotenv()`` before instantiation.

    Environment variable naming convention::

        VAULT_<CITY>_API_KEY   – API key for a city/provider
        VAULT_<CITY>_TOKEN     – bearer / credit token for a city/provider

    Examples::

        VAULT_MICHIGAN_API_KEY=abc123
        VAULT_INDIANAPOLIS_TOKEN=xyz789

    Usage::

        vault = Vault()
        key = vault.get_api_key("michigan")
        token = vault.get_token("indianapolis")
    """

    _PREFIX = "VAULT_"
    _KEY_SUFFIX = "_API_KEY"
    _TOKEN_SUFFIX = "_TOKEN"

    def __init__(self):
        self._cache: dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_api_key(self, city: str) -> str:
        """Return the API key for *city*.

        Raises:
            KeyError: if the corresponding environment variable is not set.
        """
        return self._get(city, self._KEY_SUFFIX)

    def get_token(self, city: str) -> str:
        """Return the bearer/credit token for *city*.

        Raises:
            KeyError: if the corresponding environment variable is not set.
        """
        return self._get(city, self._TOKEN_SUFFIX)

    def has_api_key(self, city: str) -> bool:
        """Return True if an API key is configured for *city*."""
        return self._env_var(city, self._KEY_SUFFIX) in os.environ

    def has_token(self, city: str) -> bool:
        """Return True if a token is configured for *city*."""
        return self._env_var(city, self._TOKEN_SUFFIX) in os.environ

    # ------------------------------------------------------------------
    # Class helpers
    # ------------------------------------------------------------------

    @staticmethod
    def load_dotenv(dotenv_path: str = ".env") -> bool:
        """Optionally load a .env file into the process environment.

        Returns True on success, False if *python-dotenv* is not installed or
        the file does not exist.  Both outcomes are acceptable — credentials
        may already be injected by the deployment platform.

        Existing environment variables are **never** overridden.
        """
        try:
            from dotenv import load_dotenv as _load  # type: ignore[import]

            loaded = _load(dotenv_path=dotenv_path, override=False)
            if loaded:
                logger.info("Vault: loaded credentials from %s", dotenv_path)
            return bool(loaded)
        except ImportError:
            logger.debug("Vault: python-dotenv not installed; skipping .env load")
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _env_var(self, city: str, suffix: str) -> str:
        """Build the canonical environment variable name for *city* + *suffix*."""
        return f"{self._PREFIX}{city.upper().replace(' ', '_')}{suffix}"

    def _get(self, city: str, suffix: str) -> str:
        var = self._env_var(city, suffix)
        if var in self._cache:
            return self._cache[var]
        value = os.environ.get(var)
        if value is None:
            raise KeyError(
                f"Vault: credential '{var}' not found. "
                f"Set the environment variable or add it to your .env file."
            )
        self._cache[var] = value
        logger.debug("Vault: loaded credential '%s' (value masked)", var)
        return value
