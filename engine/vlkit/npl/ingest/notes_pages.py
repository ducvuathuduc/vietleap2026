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


def page_tables(content, only=None):
    """[(page, rows)] where rows are cell lists, for every page that has a detectable table.

    `only` restricts the work to those 1-based pages, which is what a text-layer statement needs: the label
    scan has already found the two or three pages that matter, so pdfplumber never walks the other 60.
    """
    import pdfplumber

    wanted = set(only) if only else None
    out = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            if wanted is not None and index not in wanted:
                continue
            for table in page.extract_tables() or []:
                out.append((index, table))
    return out


def fast_page_texts(content):
    """Text per page from PDFium: the same text a reader needs, 10-50x faster than pdfplumber."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(content)
    try:
        return [document[index].get_textpage().get_text_range() for index in range(len(document))]
    finally:
        document.close()


def render_pages(content, pages, scale=2.0):
    """{page: png bytes} for the listed 1-based pages, with one open document (rendering is ~0.02 s a page)."""
    import pypdfium2 as pdfium

    out = {}
    document = pdfium.PdfDocument(content)
    try:
        for page in pages:
            image = document[page - 1].render(scale=scale).to_pil()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            out[page] = buffer.getvalue()
    finally:
        document.close()
    return out


def render_strip(content, pages, scale=0.55, per_row=3, gap=8):
    """One PNG of several pages in reading order, each stamped with its absolute page number.

    This is the cheap locator input: one vision call can see six pages at thumbnail size instead of one call
    per page, and the stamp means the model never has to count positions to report a page number.
    """
    from PIL import Image, ImageDraw
    import pypdfium2 as pdfium

    tiles = []
    document = pdfium.PdfDocument(content)
    try:
        for page in pages:
            tiles.append((page, document[page - 1].render(scale=scale).to_pil().convert("RGB")))
    finally:
        document.close()
    if not tiles:
        return b""
    width, height = tiles[0][1].size
    rows = (len(tiles) + per_row - 1) // per_row
    canvas = Image.new("RGB", (per_row * width + (per_row + 1) * gap, rows * height + (rows + 1) * gap), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (page, image) in enumerate(tiles):
        row, column = divmod(index, per_row)
        x, y = gap + column * (width + gap), gap + row * (height + gap)
        canvas.paste(image, (x, y))
        draw.text((x + 4, y + 2), f"p{page}", fill="red")
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()


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
