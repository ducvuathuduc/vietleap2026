"""PDF page handling for the notes readers: text layer, cell grid, and a page image for the vision reader.

A Vietnamese bank statement usually ships with a text layer (pdfplumber reads it directly); a scanned one has
none, which is exactly the case where the page is rendered to PNG and read by the vision reader. Everything
here takes the PDF bytes and returns plain Python, so the callers stay testable without a PDF.
"""

import io


def page_texts(content):
    """Extracted text of every page, in order (page 1 first). Empty pages come back as ''."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return [(page.extract_text() or "") for page in pdf.pages]


def page_tables(content):
    """[(page, rows)] where rows are cell lists, for every page that has a detectable table."""
    import pdfplumber

    out = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables() or []:
                out.append((index, table))
    return out


def page_png(content, page, scale=2.0):
    """PNG bytes of one 1-based page, rendered at `scale` (2.0 is ~144 dpi, enough for 8pt digits)."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(content)
    try:
        bitmap = document[page - 1].render(scale=scale)
        image = bitmap.to_pil()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    finally:
        document.close()


def has_text_layer(texts, min_chars=200):
    """True when the pages carry a real text layer (a scanned page extracts to nothing or a few stray marks)."""
    return sum(len((text or "").strip()) for text in texts or []) >= min_chars


def text_pages(texts, min_chars=60):
    """1-based numbers of the pages whose text layer is worth reading with the text readers."""
    return [index for index, text in enumerate(texts or [], start=1) if len((text or "").strip()) >= min_chars]
