"""Shared fixtures."""

import os

import pytest


def weasyprint_usable() -> bool:
    try:
        import weasyprint  # noqa: F401, PLC0415
    except (ImportError, OSError):  # OSError: Pango/HarfBuzz missing
        return False
    return True


@pytest.fixture
def pdf_ready() -> None:
    """Skip PDF tests on a machine without WeasyPrint's libraries, except where the PDF is
    required (CI sets PORTFOLIO_PDF=required): there a missing library is a failure."""
    if weasyprint_usable():
        return
    if os.environ.get("PORTFOLIO_PDF") == "required":
        pytest.fail("PORTFOLIO_PDF=required but WeasyPrint can't run here")
    pytest.skip("WeasyPrint's system libraries are not installed")
