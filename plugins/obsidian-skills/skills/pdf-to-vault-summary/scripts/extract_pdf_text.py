#!/usr/bin/env python3
"""Extract text from a PDF, printing each page wrapped in a ===== PAGE N ===== marker.

Usage:
    python extract_pdf_text.py "<PDF_PATH>"

Dependency: pdfplumber (install into the managed venv:
    .../envs/default/Scripts/python.exe -m pip install pdfplumber pypdf)

If most pages come back empty, the PDF is likely scanned/image-based and needs OCR
(pdf2image + pytesseract), not this script.
"""
import sys

try:
    import pdfplumber
except ImportError:
    sys.stderr.write("NEED_PDFPLUMBER: install pdfplumber into the managed venv\n")
    sys.exit(2)


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: extract_pdf_text.py <PDF_PATH>\n")
        sys.exit(1)

    pdf_path = sys.argv[1]
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            empty = 0
            for i, page in enumerate(pdf.pages):
                txt = page.extract_text() or ""
                if not txt.strip():
                    empty += 1
                print(f"\n===== PAGE {i + 1} =====")
                print(txt)
            if total and empty / total > 0.6:
                sys.stderr.write(
                    f"WARNING: {empty}/{total} pages empty -> PDF may be image-only; consider OCR\n"
                )
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"EXTRACT_ERROR: {exc}\n")
        sys.exit(3)


if __name__ == "__main__":
    main()
