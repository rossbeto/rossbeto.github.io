"""Adapter: HTML → PDF with WeasyPrint. The only module that imports `weasyprint`.

WeasyPrint needs system libraries (Pango, HarfBuzz). When they are missing, the import fails
with an OSError; that becomes `PDFUnavailable`, and the caller decides whether that is fatal
(`PORTFOLIO_PDF=required` in CI) or a skipped PDF (a laptop without Pango).
"""

from dataclasses import dataclass
from importlib.resources import as_file, files


class PDFUnavailable(Exception):
    """WeasyPrint or its system libraries are not installed."""


@dataclass(frozen=True)
class RenderedPDF:
    data: bytes
    pages: int


def render_pdf(html: str) -> RenderedPDF:
    """Title, author, description and keywords come from the HTML's <title> and <meta> tags.

    Relative URLs (the bundled fonts) resolve against the package's templates folder.
    """
    try:
        from weasyprint import HTML  # noqa: PLC0415  (optional system dependency)
    except (ImportError, OSError) as exc:
        raise PDFUnavailable(f"WeasyPrint is not usable here ({exc})") from exc
    with as_file(files("portfolio") / "templates") as templates:
        document = HTML(string=html, base_url=f"{templates}/").render()
    data = document.write_pdf()
    assert data is not None  # no target given → bytes  # noqa: S101
    return RenderedPDF(data=data, pages=len(document.pages))
