#!/usr/bin/env python3
"""
hipaa_redact.py
---------------
HIPAA Safe Harbor de-identification tool for discharge summary PDFs.
Handles both text-based and scanned (image-based) PDFs via OCR.

Usage:
    python hipaa_redact.py input.pdf [output_REDACTED.pdf] [options]

Options:
    --offset-days N       Days to shift all dates (default: random 30-180)
    --names "Name1" ...   Known patient/provider names to explicitly redact
    --facilities "X" ...  Known facility names to explicitly redact

Examples:
    # Basic — auto date offset, regex patterns only:
    python hipaa_redact.py report.pdf

    # With known names, facilities, fixed offset:
    python hipaa_redact.py report.pdf redacted.pdf --offset-days 45 \
        --names "John Smith" "Dr. Jane Doe" \
        --facilities "Morristown Medical Center"

Dependencies:
    pip install pdfplumber reportlab pikepdf pytesseract pdf2image
    sudo apt install tesseract-ocr poppler-utils   # (Linux)

Notes:
    - Always manually review output — automated redaction is never 100%.
    - This tool is a starting point, not a substitute for legal review.
"""

import re
import sys
import os
import random
import argparse
from datetime import datetime, timedelta
from collections import OrderedDict

import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER


# ---------------------------------------------------------------------------
# 1.  DETECT WHETHER PDF IS IMAGE-BASED (SCANNED)
# ---------------------------------------------------------------------------

def is_scanned_pdf(pdf_path, sample_pages=5):
    """Return True if the PDF has no extractable text (image/scanned)."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = min(sample_pages, len(pdf.pages))
            found = sum(
                1 for i in range(pages_to_check)
                if (pdf.pages[i].extract_text() or "").strip()
            )
            return found == 0
    except Exception:
        return True


# ---------------------------------------------------------------------------
# 2.  TEXT EXTRACTION  (native text OR OCR)
# ---------------------------------------------------------------------------

def extract_pages_native(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text(x_tolerance=2, y_tolerance=2) or "")
    return pages


def extract_pages_ocr(pdf_path, dpi=200):
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        print("ERROR: OCR requires:  pip install pdf2image pytesseract")
        sys.exit(1)

    print(f"  Scanned PDF detected — running OCR at {dpi} DPI ...")
    images = convert_from_path(pdf_path, dpi=dpi)
    pages = []
    for i, img in enumerate(images):
        print(f"    OCR page {i+1}/{len(images)}...", end="\r", flush=True)
        pages.append(pytesseract.image_to_string(img, config="--psm 6"))
    print()
    return pages


def extract_pages(pdf_path):
    if is_scanned_pdf(pdf_path):
        return extract_pages_ocr(pdf_path)
    return extract_pages_native(pdf_path)


# ---------------------------------------------------------------------------
# 3.  PHI PATTERN DEFINITIONS
# ---------------------------------------------------------------------------

def build_patterns(custom_names=None, custom_facilities=None):
    p = OrderedDict()

    # SSN
    p["SSN"] = re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b|\bxxx-xx-xxxx\b", re.IGNORECASE
    )
    # MRN / Patient ID
    p["MRN"] = re.compile(
        r"\b(?:MR\s*#?\s*|MRN\s*[:#]?\s*|Patient\s+ID\s*[:#]?\s*)[A-Z0-9\-]{5,20}\b"
        r"|\b[A-Z]{1,2}\d{7,10}\b",
        re.IGNORECASE,
    )
    # CSN / Encounter number
    p["CSN"] = re.compile(r"\bCSN\s*[:#]?\s*\d{6,12}\b", re.IGNORECASE)
    # NPI
    p["NPI"] = re.compile(r"\bNPI\s*[:#]?\s*\d{10}\b", re.IGNORECASE)
    # Insurance / auth / subscriber IDs
    p["INSURANCE_ID"] = re.compile(
        r"\b(?:Subscriber\s+ID|SID|Group\s+ID|Auth(?:orization)?\s+(?:number|#|num)|MCARE#)"
        r"\s*[:#]?\s*[A-Z0-9\-]{5,25}\b",
        re.IGNORECASE,
    )
    # Long alphanumeric subscriber codes  e.g. YKZ3HZN95133120
    p["SUBSCRIBER_CODE"] = re.compile(r"\b[A-Z]{3}\d[A-Z]{3}\d{8,12}\b")
    # Phone / fax
    p["PHONE"] = re.compile(
        r"\+?1?\s*\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b"
    )
    # Email
    p["EMAIL"] = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
    # IP address
    p["IP_ADDRESS"] = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    # URLs
    p["URL"] = re.compile(r"https?://[^\s]+|www\.[^\s]+\.[a-z]{2,}", re.IGNORECASE)
    # Street addresses
    p["ADDRESS"] = re.compile(
        r"\b\d{1,5}\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|"
        r"Court|Ct|Place|Pl|Way|Circle|Cir|Highway|Hwy)\b"
        r"(?:\s*,?\s*(?:Apt|Suite|Ste|Unit|#)\s*[A-Z0-9]+)?",
        re.IGNORECASE,
    )
    # State + ZIP
    p["ZIP"] = re.compile(
        r"\b(?:NJ|NY|PA|CT|MA|FL|CA|TX|GA|OH|MI|IL|WA|AZ|CO|MN|WI|VA|NC|TN|IN|KY)"
        r"\s+\d{5}(?:-\d{4})?\b|\b\d{5}-\d{4}\b",
        re.IGNORECASE,
    )
    # Device / serial numbers
    p["DEVICE_ID"] = re.compile(
        r"\b(?:Serial\s*#?|Device\s+ID|Lot\s*#?|Catalog\s*#?)\s*:?\s*[A-Z0-9\-]{6,20}\b",
        re.IGNORECASE,
    )

    # Explicit names
    if custom_names:
        for name in custom_names:
            name = name.strip()
            if name:
                p[f"NAME:{name}"] = re.compile(
                    r"(?<![A-Za-z])" + re.escape(name) + r"(?![A-Za-z])",
                    re.IGNORECASE,
                )

    # Explicit facilities
    if custom_facilities:
        for fac in custom_facilities:
            fac = fac.strip()
            if fac:
                p[f"FACILITY:{fac}"] = re.compile(
                    r"(?<![A-Za-z])" + re.escape(fac) + r"(?![A-Za-z])",
                    re.IGNORECASE,
                )

    return p


# ---------------------------------------------------------------------------
# 4.  DATE OFFSET
# ---------------------------------------------------------------------------

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
_MONTH_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
    re.IGNORECASE,
)


def offset_dates(text, days):
    def shift_slash(m):
        try:
            mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            y = y + 2000 if y < 100 else y
            dt = datetime(y, mo, d) + timedelta(days=days)
            fmt = "%-m/%-d/%y" if len(m.group(3)) == 2 else "%-m/%-d/%Y"
            return dt.strftime(fmt)
        except Exception:
            return m.group(0)

    def shift_month(m):
        try:
            mn = MONTH_MAP.get(m.group(1).lower(), 0)
            if not mn:
                return m.group(0)
            dt = datetime(int(m.group(3)), mn, int(m.group(2))) + timedelta(days=days)
            return dt.strftime("%B %-d, %Y")
        except Exception:
            return m.group(0)

    text = _SLASH_RE.sub(shift_slash, text)
    text = _MONTH_RE.sub(shift_month, text)
    return text


# ---------------------------------------------------------------------------
# 5.  PLACEHOLDER MAP & REDACTION
# ---------------------------------------------------------------------------

PLACEHOLDERS = {
    "SSN":             "[SSN REDACTED]",
    "MRN":             "[MRN REDACTED]",
    "CSN":             "[CSN REDACTED]",
    "NPI":             "[NPI REDACTED]",
    "INSURANCE_ID":    "[INS-ID REDACTED]",
    "SUBSCRIBER_CODE": "[SUBSCRIBER-ID REDACTED]",
    "PHONE":           "[PHONE REDACTED]",
    "EMAIL":           "[EMAIL REDACTED]",
    "IP_ADDRESS":      "[IP REDACTED]",
    "URL":             "[URL REDACTED]",
    "ADDRESS":         "[ADDRESS REDACTED]",
    "ZIP":             "[ZIP REDACTED]",
    "DEVICE_ID":       "[DEVICE-ID REDACTED]",
}


def placeholder(label):
    if label.startswith("NAME:"):
        initials = "".join(p[0].upper() for p in label[5:].split() if p)
        return f"[NAME-{initials} REDACTED]"
    if label.startswith("FACILITY:"):
        return "[FACILITY REDACTED]"
    return PLACEHOLDERS.get(label, "[REDACTED]")


def redact(text, patterns, offset_days):
    text = offset_dates(text, offset_days)
    for label, pat in patterns.items():
        text = pat.sub(placeholder(label), text)
    return text


# ---------------------------------------------------------------------------
# 6.  BUILD OUTPUT PDF
# ---------------------------------------------------------------------------

def build_pdf(pages, output_path, source_name, offset_days):
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
    )
    ss = getSampleStyleSheet()
    mono  = ParagraphStyle("Mono",  parent=ss["Normal"], fontName="Courier",
                            fontSize=7.5, leading=11, wordWrap="CJK")
    red   = ParagraphStyle("Red",   parent=ss["Normal"], fontName="Helvetica-Bold",
                            fontSize=9, textColor=colors.HexColor("#8B0000"))
    grey  = ParagraphStyle("Grey",  parent=ss["Normal"], fontName="Helvetica-Oblique",
                            fontSize=7.5, textColor=colors.grey)
    ctr   = ParagraphStyle("Ctr",   parent=ss["Normal"], fontName="Helvetica",
                            fontSize=7.5, textColor=colors.HexColor("#555555"),
                            alignment=TA_CENTER)

    story = []
    story.append(Paragraph(
        "\u26a0  DE-IDENTIFIED COPY \u2014 HIPAA Safe Harbor Applied  \u26a0", red))
    story.append(Paragraph(
        f"Source: {source_name}   |   Date offset: {offset_days:+d} days   |   "
        f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M')}", grey))
    story.append(HRFlowable(width="100%", thickness=1.5,
                             color=colors.HexColor("#8B0000")))
    story.append(Spacer(1, 10))

    for i, page_text in enumerate(pages):
        if i > 0:
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            story.append(Paragraph(f"\u2014  Page {i+1}  \u2014", ctr))
            story.append(Spacer(1, 6))
        for line in page_text.split("\n"):
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line.strip():
                story.append(Paragraph(line, mono))
            else:
                story.append(Spacer(1, 3))

    doc.build(story)


# ---------------------------------------------------------------------------
# 7.  COUNT REDACTIONS
# ---------------------------------------------------------------------------

def count_redactions(original, redacted):
    counts = {}
    all_ph = list(PLACEHOLDERS.values())
    for orig, redc in zip(original, redacted):
        for ph in all_ph:
            n = redc.count(ph)
            if n:
                counts[ph] = counts.get(ph, 0) + n
        for m in re.finditer(r"\[NAME-[A-Z]+ REDACTED\]|\[FACILITY REDACTED\]", redc):
            k = m.group(0)
            counts[k] = counts.get(k, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# 8.  MAIN
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="HIPAA Safe Harbor de-identification for discharge summary PDFs"
    )
    ap.add_argument("input",  help="Input PDF path")
    ap.add_argument("output", nargs="?",
                    help="Output PDF path (default: <input>_REDACTED.pdf)")
    ap.add_argument("--offset-days", type=int, default=None,
                    help="Days to shift dates (default: random 30-180)")
    ap.add_argument("--names", nargs="*", default=[],
                    help='Known names to redact, e.g. --names "John Smith" "Dr. Doe"')
    ap.add_argument("--facilities", nargs="*", default=[],
                    help='Known facilities to redact, e.g. --facilities "City Hospital"')
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: File not found: {args.input}")
        sys.exit(1)

    out = args.output or os.path.splitext(args.input)[0] + "_REDACTED.pdf"

    offset = args.offset_days
    if offset is None:
        offset = random.randint(30, 180)
        print(f"  Date offset: randomly selected {offset:+d} days")
    else:
        print(f"  Date offset: {offset:+d} days")

    print(f"\n  Input:  {args.input}")
    print(f"  Output: {out}")

    patterns = build_patterns(custom_names=args.names, custom_facilities=args.facilities)
    print(f"  PHI patterns: {len(patterns)}")

    print("\nExtracting text...")
    orig_pages = extract_pages(args.input)
    print(f"  {len(orig_pages)} pages extracted")

    print("Applying redactions...")
    redc_pages = [redact(p, patterns, offset) for p in orig_pages]

    counts = count_redactions(orig_pages, redc_pages)

    print("Building output PDF...")
    build_pdf(redc_pages, out, os.path.basename(args.input), offset)

    print("\n" + "="*58)
    print("  REDACTION COMPLETE")
    print("="*58)
    print(f"  Saved: {out}")
    print("\n  Redactions applied:")
    if counts:
        for label, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {label:<40} {n:>4}x")
    else:
        print("    None detected by regex.")
        print("    Tip: Pass --names and --facilities for known identifiers.")
    print()
    print("  \u26a0  Always manually review the output before sharing.")
    print("     OCR accuracy varies on scanned documents.")
    print("="*58)


if __name__ == "__main__":
    main()
