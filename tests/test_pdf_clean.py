"""Hospital PDFs often carry an open-action script. The upload keeps the pages and drops every script, action and
attachment instead of refusing the report."""
import io

from pypdf import PdfWriter

from api.storage import _pdf_danger, safe_document


def _pdf_with_script() -> bytes:
    w = PdfWriter()
    w.add_blank_page(200, 200)
    w.add_js("app.alert('hi');")
    w.add_attachment("x.txt", b"payload")
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


def test_scripted_pdf_is_cleaned_not_refused():
    raw = _pdf_with_script()
    assert _pdf_danger(raw)
    out = safe_document(raw, "application/pdf")
    assert not _pdf_danger(out)
    assert b"/Page" in out and b"payload" not in out
