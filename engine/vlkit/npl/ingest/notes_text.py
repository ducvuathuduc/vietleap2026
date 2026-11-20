"""Two independent text readers of a financial-statement page: the cell grid and the plain text lines.

The notes a Vietnamese bank publishes are two-column tables (current period, prior period) with a leading
label cell and, on the balance sheet, a small "Mã số" code between the label and the amounts. Both readers
therefore take the FIRST AMOUNT after the label and skip a leading code (an integer below 1,000 that sits
next to a much larger number). Labels are matched diacritic-free so one catalogue serves every bank, and
every value keeps the page it came from.

Reader "table" reads pdfplumber's cell grid; reader "text" reads the extracted text lines. They are separate
code paths on purpose: a number both readers return is graded verified, a number only one reader returns is
graded single, and disagreement is graded contested — nothing is silently averaged.

Sign convention: provision balances and write-offs are magnitudes (a balance sheet prints the provision as a
negative asset); the charge and the amount used keep the sign the statement prints, so a reversal stays
visible as a negative charge.
"""
import re

from ...vn import ascii_key
from .notes_contract import FIELDS, numbers_in, parse_number, unit_scale

LABELS = {
    "loans_customer": ["cho vay khach hang", "du no cho vay khach hang"],
    "group_1_current": ["no du tieu chuan"],
    "group_2_watch": ["no can chu y"],
    "group_3_substandard": ["no duoi tieu chuan"],
    "group_4_doubtful": ["no nghi ngo"],
    "group_5_loss": ["no co kha nang mat von"],
    "provision_opening": ["so du dau ky", "du phong dau ky", "so du dau nam"],
    "provision_charge": ["so trich lap trong ky", "trich lap trong ky", "so trich lap du phong trong ky",
                         "trich lap du phong rui ro trong ky", "du phong trich lap trong ky"],
    "provision_used_writeoff": ["so su dung trong ky", "su dung trong ky", "so su dung de xu ly rui ro",
                                "da su dung de xu ly rui ro", "su dung du phong de xoa no",
                                "so duoc su dung trong ky", "du phong da su dung de xu ly rui ro"],
    "provision_closing": ["du phong rui ro cho vay khach hang", "du phong rui ro tin dung",
                          "du phong cho vay khach hang", "so du cuoi ky", "du phong cuoi ky"],
    "writeoff_period": ["no xau da xu ly", "gia tri no da xu ly rui ro", "no da xu ly rui ro",
                        "tong no da xu ly", "no xau da xu ly bang nguon du phong", "gia tri no da xu ly"],
}
BALANCE_CLOSING = ["du phong rui ro cho vay khach hang", "du phong rui ro tin dung", "du phong cho vay khach hang"]
MOVEMENT_CLOSING = ["so du cuoi ky", "du phong cuoi ky"]
GROUPS = ["group_1_current", "group_2_watch", "group_3_substandard", "group_4_doubtful", "group_5_loss"]
MOVEMENT = ["provision_opening", "provision_charge", "provision_used_writeoff"]
MAGNITUDE = {"provision_opening", "provision_closing", "writeoff_period"}
CODE_MAX = 1000                     # a "Mã số" / note reference: an integer below this
NUMBER_CELL = re.compile(r"^\(?-?[\d.,]+\)?$")


def key_of(text):
    return ascii_key(text)


def matches(key, field):
    """True when `key` is one of the field's labels (whole label, so 'cho vay khach hang theo loai hinh' counts)."""
    return any(key == variant or key.startswith(variant + " ") for variant in LABELS[field])


def is_number_cell(token):
    token = str(token or "").strip()
    return bool(token) and NUMBER_CELL.match(token) is not None and parse_number(token) is not None


def cell_amounts(cells):
    """(index, value) for every cell that is nothing but a number."""
    return [(index, parse_number(str(cell).strip())) for index, cell in enumerate(cells) if is_number_cell(cell)]


def skip_code(amounts):
    """Drop a leading Mã số: an integer below 1,000 sitting next to a number at least ten times larger."""
    if len(amounts) >= 2 and float(amounts[0][1]).is_integer() and abs(amounts[0][1]) < CODE_MAX \
            and abs(amounts[1][1]) >= 10 * max(abs(amounts[0][1]), 1):
        return amounts[1:]
    return amounts


def first_amount(cells):
    amounts = skip_code(cell_amounts(cells))
    return amounts[0][1] if amounts else None


def line_amount(line):
    """First amount of a statement line: split on 2+ spaces into cells, else fall back to the line's numbers."""
    cells = [cell for cell in re.split(r"\s{2,}", line or "") if cell.strip()]
    if len(cells) >= 2:
        value = first_amount(cells[1:])
        if value is not None:
            return value
    amounts = skip_code([(index, value) for index, value in enumerate(numbers_in(line))])
    return amounts[0][1] if amounts else None


def signed(field, value):
    """Magnitudes for balances and write-offs; the printed sign for the charge and the amount used."""
    if value is None:
        return None
    return abs(value) if field in MAGNITUDE else value


def _lines(pages):
    for index, text in enumerate(pages or [], start=1):
        for line in str(text or "").splitlines():
            if line.strip():
                yield index, line


def page_guards(pages):
    """Pages that carry the classification note and pages that carry the provision movement note."""
    group_pages, movement_pages = set(), set()
    for page, line in _lines(pages):
        key = key_of(line)
        if sum(1 for field in GROUPS if matches(key, field)):
            group_pages.add(page)
        if any(variant in key for variant in ("so du dau ky", "so du cuoi ky", "so trich lap trong ky")):
            movement_pages.add(page)
    return group_pages, movement_pages


def _allowed(field, key, page, group_pages, movement_pages):
    if field in GROUPS:
        return page in group_pages
    if field in MOVEMENT:
        return page in movement_pages
    if field == "provision_closing":
        balance = any(key == variant or key.startswith(variant + " ") for variant in BALANCE_CLOSING)
        movement = any(key == variant or key.startswith(variant + " ") for variant in MOVEMENT_CLOSING)
        return movement if page in movement_pages else balance
    return True


def read_text(pages):
    """field -> {value_vnd_bn, page, reader} from the page texts, first page that shows the value wins."""
    scales = {index: unit_scale(text) for index, text in enumerate(pages or [], start=1)}
    group_pages, movement_pages = page_guards(pages)
    found = {}
    for page, line in _lines(pages):
        key = key_of(line)
        for field in FIELDS:
            if field in found or not matches(key, field):
                continue
            if not _allowed(field, key, page, group_pages, movement_pages):
                continue
            value = line_amount(line)
            if value is None:
                continue
            found[field] = {"value_vnd_bn": round(signed(field, value) * scales.get(page, 1.0), 6),
                            "page": page, "reader": "text"}
    return found


def read_tables(tables, scales=None):
    """field -> {value_vnd_bn, page, reader} from pdfplumber cell grids: `tables` = [(page, rows)], rows = cells.

    `scales` maps a page number to its unit multiplier (read from that page's "Đơn vị tính" line by the caller);
    a page without one is taken as tỷ đồng, the unit most banks print.
    """
    found = {}
    scales = scales or {}
    for page, rows in tables or []:
        keys = [key_of(" ".join(str(cell) for cell in row if cell and not is_number_cell(cell))) for row in rows]
        group_hits = sum(1 for key in keys for field in GROUPS if matches(key, field))
        movement_here = any(any(variant in key for variant in ("so du dau ky", "so du cuoi ky")) for key in keys)
        group_pages = {page} if group_hits else set()
        movement_pages = {page} if movement_here else set()
        scale = float(scales.get(page) or unit_scale(" ".join(
            " ".join(str(cell or "") for cell in row) for row in rows)))
        for row, key in zip(rows, keys):
            for field in FIELDS:
                if field in found or not matches(key, field):
                    continue
                if not _allowed(field, key, page, group_pages, movement_pages):
                    continue
                value = first_amount([str(cell or "").strip() for cell in row])
                if value is None:
                    continue
                found[field] = {"value_vnd_bn": round(signed(field, value) * scale, 6), "page": page,
                                "reader": "table"}
    return found
