import warnings


class LegacyImportWarning(FutureWarning):
    """Warning category for deprecated legacy import paths."""


def warn_legacy_import(*, legacy_module: str, canonical_module: str) -> None:
    """Emit a deprecation warning for a legacy import path."""
    warnings.warn(
        (
            f"`{legacy_module}` is deprecated and will be removed in the next major "
            f"release; use `{canonical_module}` instead."
        ),
        LegacyImportWarning,
        stacklevel=3,
    )
