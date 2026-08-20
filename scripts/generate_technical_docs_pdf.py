#!/usr/bin/env python3
"""Generate ExamBuddy technical audit PDF from the markdown documentation.

Read-only report generator — does not modify application code.
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "EXAMBUDDY_TECHNICAL_DOCUMENTATION.md"
PDF_PATH = ROOT / "EXAMBUDDY_TECHNICAL_DOCUMENTATION.pdf"


class ReportPDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(90, 90, 90)
        self.cell(0, 6, "ExamBuddy Technical Documentation - Codebase Audit", align="L")
        self.ln(8)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")
        self.set_text_color(0, 0, 0)


def clean_text(text: str) -> str:
    # fpdf core fonts are latin-1; normalize common unicode
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2192": "->",
        "\u2193": "v",
        "\u2500": "-",
        "\u2502": "|",
        "\u250c": "+",
        "\u2510": "+",
        "\u2514": "+",
        "\u2518": "+",
        "\u251c": "+",
        "\u2524": "+",
        "\u252c": "+",
        "\u2534": "+",
        "\u253c": "+",
        "\u25bc": "v",
        "\u2570": "+",
        "\u256f": "+",
        "\u2550": "=",
        "\u2551": "|",
        "\u2554": "+",
        "\u2557": "+",
        "\u255a": "+",
        "\u255d": "+",
        "\u2560": "+",
        "\u2563": "+",
        "\u2566": "+",
        "\u2569": "+",
        "\u256c": "+",
        "\u00a0": " ",
        "\u2026": "...",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00d7": "x",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text


def strip_md_inline(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text


def write_wrapped(pdf: ReportPDF, text: str, size: int = 10, style: str = "", indent: float = 0) -> None:
    pdf.set_font("Helvetica", style, size)
    usable = pdf.w - pdf.l_margin - pdf.r_margin - indent
    pdf.set_x(pdf.l_margin + indent)
    pdf.multi_cell(usable, 5, clean_text(text))


def add_title_page(pdf: ReportPDF) -> None:
    pdf.add_page()
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.ln(40)

    def center_line(text: str, size: int, style: str = "", h: float = 8) -> None:
        pdf.set_font("Helvetica", style, size)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable, h, clean_text(text), align="C")

    center_line("ExamBuddy (SmartStudy)", 24, "B", 12)
    pdf.ln(4)
    center_line("Complete Technical Documentation", 16, "B", 9)
    pdf.ln(8)
    center_line("Codebase Technical Audit Report", 12, "", 7)
    pdf.ln(6)
    for line in [
        "Audit date: 19 August 2026",
        "Scope: Verified from source code only",
        "Constraint: No application code was modified",
        "Source markdown: EXAMBUDDY_TECHNICAL_DOCUMENTATION.md",
    ]:
        center_line(line, 11, "", 7)
    pdf.ln(20)
    center_line(
        "If something could not be verified from the codebase, "
        "the markdown states: Not found in the current codebase.",
        10,
        "I",
        6,
    )


def render_markdown(pdf: ReportPDF, md: str) -> None:
    lines = md.splitlines()
    i = 0
    in_code = False
    code_buf: list[str] = []
    # Skip first H1 (covered by title page) and leading meta until first ##
    started = False

    while i < len(lines):
        line = lines[i]
        raw = line.rstrip()

        if raw.startswith("```"):
            if in_code:
                pdf.ln(1)
                pdf.set_fill_color(245, 245, 245)
                pdf.set_font("Courier", "", 7.5)
                block = "\n".join(code_buf)
                usable = pdf.w - pdf.l_margin - pdf.r_margin
                # Keep code blocks from overflowing pages awkwardly
                for cl in block.splitlines() or [""]:
                    if pdf.get_y() > pdf.h - 20:
                        pdf.add_page()
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(usable, 3.8, clean_text(cl[:140]), fill=True)
                pdf.ln(2)
                code_buf = []
                in_code = False
            else:
                in_code = True
                code_buf = []
            i += 1
            continue

        if in_code:
            code_buf.append(raw)
            i += 1
            continue

        if not started:
            if raw.startswith("## "):
                started = True
            else:
                i += 1
                continue

        if not raw.strip():
            pdf.ln(2)
            i += 1
            continue

        if raw.startswith("---"):
            pdf.ln(2)
            i += 1
            continue

        if raw.startswith("# "):
            if pdf.page_no() > 1 or pdf.get_y() > 30:
                pdf.add_page()
            write_wrapped(pdf, strip_md_inline(raw[2:]), size=16, style="B")
            pdf.ln(2)
            i += 1
            continue

        if raw.startswith("## "):
            if pdf.get_y() > pdf.h - 40:
                pdf.add_page()
            pdf.ln(3)
            write_wrapped(pdf, strip_md_inline(raw[3:]), size=13, style="B")
            pdf.ln(1)
            i += 1
            continue

        if raw.startswith("### "):
            if pdf.get_y() > pdf.h - 30:
                pdf.add_page()
            pdf.ln(2)
            write_wrapped(pdf, strip_md_inline(raw[4:]), size=11, style="B")
            pdf.ln(1)
            i += 1
            continue

        # Markdown table
        if raw.startswith("|") and "|" in raw[1:]:
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_line = lines[i].strip()
                cols = [c.strip() for c in row_line.strip("|").split("|")]
                # skip separator rows
                if all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cols):
                    i += 1
                    continue
                rows.append([strip_md_inline(c) for c in cols])
                i += 1
            if rows:
                render_table(pdf, rows)
            continue

        if raw.lstrip().startswith("- ") or raw.lstrip().startswith("* "):
            bullet = strip_md_inline(raw.lstrip()[2:])
            write_wrapped(pdf, f"- {bullet}", size=10, indent=3)
            i += 1
            continue

        if re.match(r"^\d+\.\s+", raw.lstrip()):
            write_wrapped(pdf, strip_md_inline(raw.lstrip()), size=10, indent=3)
            i += 1
            continue

        write_wrapped(pdf, strip_md_inline(raw), size=10)
        i += 1


def render_table(pdf: ReportPDF, rows: list[list[str]]) -> None:
    if not rows:
        return
    cols = max(len(r) for r in rows)
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    # Cap columns for readability
    col_w = usable / min(cols, 4) if cols else usable
    if cols > 4:
        # Flatten wide tables as text blocks
        for r in rows:
            write_wrapped(pdf, " | ".join(r), size=8)
        pdf.ln(1)
        return

    pdf.set_font("Helvetica", "", 8)
    line_h = 4.2
    for idx, row in enumerate(rows):
        while len(row) < cols:
            row.append("")
        # Estimate height
        max_lines = 1
        cells = []
        for c in row[:cols]:
            text = clean_text(c)
            cells.append(text)
            # rough wrap estimate
            approx = max(1, int(len(text) / max(1, int(col_w / 1.7))) + 1)
            max_lines = max(max_lines, min(approx, 6))
        row_h = line_h * max_lines + 1
        if pdf.get_y() + row_h > pdf.h - 18:
            pdf.add_page()
        y0 = pdf.get_y()
        x0 = pdf.l_margin
        fill = idx == 0
        if fill:
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Helvetica", "B", 8)
        else:
            pdf.set_font("Helvetica", "", 8)
            pdf.set_fill_color(255, 255, 255)
        for j, text in enumerate(cells):
            pdf.set_xy(x0 + j * col_w, y0)
            pdf.multi_cell(col_w, line_h, text[:300], border=1, fill=fill)
        pdf.set_y(y0 + row_h)
    pdf.ln(2)


def main() -> None:
    if not MD_PATH.is_file():
        raise SystemExit(f"Missing {MD_PATH}")

    md = MD_PATH.read_text(encoding="utf-8")
    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(14, 14, 14)

    add_title_page(pdf)
    pdf.add_page()
    render_markdown(pdf, md)

    pdf.output(str(PDF_PATH))
    print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    main()
