"""Render any page from a DOCX file to PNG.

This helper uses Microsoft Word to export the requested DOCX page to PDF, then
renders that PDF page to PNG. It is useful for visually checking generated DOCX
layout without manually opening Word after every change.

Examples:
    python render_docx_page.py generated_graduation_book.docx --page 1
    python render_docx_page.py "Graduation Book.docx" --page 3
    python render_docx_page.py --generate --page 1
    python render_docx_page.py --generate --full-pdf

The --generate option rebuilds generated_graduation_book.docx from content/book.json
and any chapter Markdown files referenced there.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import fitz
import win32com.client

from generate_graduation_book import BOOK_DATA, OUTPUT_DOCX, build_book


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUT_DIR = BASE_DIR / "rendered_pages"
WD_EXPORT_FORMAT_PDF = 17
WD_EXPORT_ALL_DOCUMENT = 0
WD_EXPORT_FROM_TO = 3
WD_EXPORT_OPTIMIZE_FOR_PRINT = 0
WD_EXPORT_DOCUMENT_CONTENT = 0
WD_EXPORT_CREATE_NO_BOOKMARKS = 0
WD_STATISTIC_PAGES = 2


def resolve_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else BASE_DIR / path


def safe_stem(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "_", path.stem.lower()).strip("_")


def export_page_to_pdf(word, docx_path: Path, pdf_path: Path, *, page: int) -> int:
    doc = word.Documents.Open(str(docx_path), ReadOnly=True)
    try:
        doc.Repaginate()
        page_count = doc.ComputeStatistics(WD_STATISTIC_PAGES)
        if page > page_count:
            raise ValueError(f"{docx_path.name} has {page_count} page(s), cannot render page {page}.")
        doc.ExportAsFixedFormat(
            OutputFileName=str(pdf_path),
            ExportFormat=WD_EXPORT_FORMAT_PDF,
            OpenAfterExport=False,
            OptimizeFor=WD_EXPORT_OPTIMIZE_FOR_PRINT,
            Range=WD_EXPORT_FROM_TO,
            From=page,
            To=page,
            Item=WD_EXPORT_DOCUMENT_CONTENT,
            IncludeDocProps=True,
            KeepIRM=True,
            CreateBookmarks=WD_EXPORT_CREATE_NO_BOOKMARKS,
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False,
        )
        return page_count
    finally:
        doc.Close(False)


def export_full_docx_to_pdf(word, docx_path: Path, pdf_path: Path) -> int:
    doc = word.Documents.Open(str(docx_path), ReadOnly=True)
    try:
        doc.Repaginate()
        page_count = doc.ComputeStatistics(WD_STATISTIC_PAGES)
        doc.ExportAsFixedFormat(
            OutputFileName=str(pdf_path),
            ExportFormat=WD_EXPORT_FORMAT_PDF,
            OpenAfterExport=False,
            OptimizeFor=WD_EXPORT_OPTIMIZE_FOR_PRINT,
            Range=WD_EXPORT_ALL_DOCUMENT,
            Item=WD_EXPORT_DOCUMENT_CONTENT,
            IncludeDocProps=True,
            KeepIRM=True,
            CreateBookmarks=WD_EXPORT_CREATE_NO_BOOKMARKS,
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False,
        )
        return page_count
    finally:
        doc.Close(False)


def render_pdf_page(pdf_path: Path, png_path: Path, *, scale: float) -> None:
    pdf = fitz.open(str(pdf_path))
    try:
        pix = pdf[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        pix.save(str(png_path))
    finally:
        pdf.close()


def render_docx_page(word, docx_path: Path, out_dir: Path, *, page: int, scale: float) -> tuple[Path, Path, int]:
    stem = safe_stem(docx_path)
    page_label = f"page_{page:03d}"
    pdf_path = out_dir / f"{stem}_{page_label}.pdf"
    png_path = out_dir / f"{stem}_{page_label}.png"
    page_count = export_page_to_pdf(word, docx_path, pdf_path, page=page)
    render_pdf_page(pdf_path, png_path, scale=scale)
    return pdf_path, png_path, page_count


def render_full_pdf(word, docx_path: Path, out_dir: Path) -> tuple[Path, int]:
    pdf_path = out_dir / f"{safe_stem(docx_path)}_full.pdf"
    page_count = export_full_docx_to_pdf(word, docx_path, pdf_path)
    return pdf_path, page_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a DOCX page to PNG.")
    parser.add_argument("docx", nargs="?", default=str(OUTPUT_DOCX), help="DOCX path to render.")
    parser.add_argument("--page", type=int, default=1, help="1-based page number to render.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory.")
    parser.add_argument("--scale", type=float, default=2.0, help="PDF render scale for PNG output.")
    parser.add_argument("--full-pdf", action="store_true", help="Export the full DOCX to one PDF instead of rendering one page.")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Regenerate generated_graduation_book.docx from content/book.json before rendering it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docx_path = resolve_path(args.docx)
    out_dir = resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.page < 1:
        raise SystemExit("--page must be 1 or greater.")

    if args.generate:
        if docx_path.resolve() != OUTPUT_DOCX.resolve():
            raise SystemExit("--generate can only be used with generated_graduation_book.docx.")
        build_book(BOOK_DATA, docx_path)
        print(f"Regenerated: {docx_path}")
    elif not docx_path.exists():
        raise SystemExit(f"DOCX not found: {docx_path}")

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    try:
        if args.full_pdf:
            pdf_path, page_count = render_full_pdf(word, docx_path, out_dir)
            print(f"Exported full PDF with {page_count} page(s): {docx_path}")
            print(f"PDF: {pdf_path}")
            return

        pdf_path, png_path, page_count = render_docx_page(
            word,
            docx_path,
            out_dir,
            page=args.page,
            scale=args.scale,
        )
    finally:
        word.Quit()

    print(f"Rendered page {args.page} of {page_count}: {docx_path}")
    print(f"PDF: {pdf_path}")
    print(f"PNG: {png_path}")


if __name__ == "__main__":
    main()
