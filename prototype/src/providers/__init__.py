from typing import Any

__all__ = [
	"DetroitProvider",
	"LAPDProvider",
	"LegacyPortalProvider",
	"NYCProvider",
	"SequentialWorkerProvider",
]


def __getattr__(name: str) -> Any:
	if name == "DetroitProvider":
		from .detroit_provider import DetroitProvider

		return DetroitProvider
	if name == "LAPDProvider":
		from .lapd_provider import LAPDProvider

		return LAPDProvider
	if name == "LegacyPortalProvider":
		from .legacy_portal_provider import LegacyPortalProvider

		return LegacyPortalProvider
	if name == "NYCProvider":
		from .nyc_provider import NYCProvider

		return NYCProvider
	if name == "SequentialWorkerProvider":
		from .sequential_worker_provider import SequentialWorkerProvider

		return SequentialWorkerProvider

	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
