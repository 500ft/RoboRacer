#!/usr/bin/env python3
"""Build the item-12 Markdown source as a review-ready PDF."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports" / "final_report.md"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "roboracer_design_review_report.pdf"
PAGE_WIDTH, PAGE_HEIGHT = A4


def ascii_safe(text: str) -> str:
    """Keep the portable built-in PDF fonts free of unsupported glyphs."""
    replacements = {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2192": "->",
        "\u2190": "<-",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00b1": "+/-",
        "\u00d7": "x",
        "\u00b2": "^2",
        "\u00b3": "^3",
        "\u00b0": " deg",
        "\u03c3": "sigma",
        "\u03b4": "delta",
        "\u03b8": "theta",
        "\u03c0": "pi",
        "\u03c8": "psi",
        "\u03b2": "beta",
        "\u2248": "~",
        "\u2245": "~",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def inline_markup(text: str) -> str:
    """Convert the small Markdown inline subset used by the report."""
    escaped = html.escape(ascii_safe(text.strip()))
    code_tokens: list[str] = []
    link_tokens: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_tokens.append(
            f'<font name="Courier" color="#263746">{match.group(1)}</font>'
        )
        return f"@@CODE{len(code_tokens) - 1}@@"

    def stash_link(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        link_tokens.append(
            f'<link href="{target}" color="#145A7D"><u>{label}</u></link>'
        )
        return f"@@LINK{len(link_tokens) - 1}@@"

    escaped = re.sub(r"`([^`]+)`", stash_code, escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", stash_link, escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", escaped)
    for index, token in enumerate(link_tokens):
        escaped = escaped.replace(f"@@LINK{index}@@", token)
    for index, token in enumerate(code_tokens):
        escaped = escaped.replace(f"@@CODE{index}@@", token)
    return escaped


def is_table_delimiter(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_table(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    raw_rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
    ]
    if len(raw_rows) > 1 and is_table_delimiter(lines[1]):
        raw_rows.pop(1)
    column_count = max(len(row) for row in raw_rows)
    rows = [row + [""] * (column_count - len(row)) for row in raw_rows]
    paragraph_rows = []
    for row_index, row in enumerate(rows):
        style = styles["table_header"] if row_index == 0 else styles["table_cell"]
        paragraph_rows.append([Paragraph(inline_markup(cell), style) for cell in row])

    available = PAGE_WIDTH - 32 * mm
    lengths = []
    for column_index in range(column_count):
        longest = max(len(row[column_index]) for row in rows)
        lengths.append(max(7, min(longest, 34)))
    total = sum(lengths)
    widths = [available * length / total for length in lengths]

    table = Table(
        paragraph_rows,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173A50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#A9B8C2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3.2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3.2),
                ("TOPPADDING", (0, 0), (-1, -1), 3.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F2F6F8"),
                ]),
            ]
        )
    )
    return table


def image_flowable(
    source: Path,
    alt_text: str,
    styles: dict[str, ParagraphStyle],
) -> KeepTogether:
    max_width = PAGE_WIDTH - 38 * mm
    max_height = (
        105 * mm
        if source.name == "model_vs_gym_trajectory_error.png"
        else 75 * mm
    )
    width, height = ImageReader(str(source)).getSize()
    scale = min(max_width / width, max_height / height, 1.0)
    image = Image(str(source), width=width * scale, height=height * scale)
    image.hAlign = "CENTER"
    caption = Paragraph(inline_markup(alt_text), styles["caption"])
    return KeepTogether([image, Spacer(1, 2.5 * mm), caption])


def build_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=29,
            textColor=colors.HexColor("#12364A"),
            alignment=TA_LEFT,
            spaceAfter=9 * mm,
        ),
        "h2": ParagraphStyle(
            "Section",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#12364A"),
            spaceBefore=2 * mm,
            spaceAfter=5 * mm,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Subsection",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#24667D"),
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.2,
            textColor=colors.HexColor("#1F2B33"),
            spaceAfter=2.8 * mm,
            allowWidows=0,
            allowOrphans=0,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=sample["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12.5,
            textColor=colors.HexColor("#355767"),
            leftIndent=7 * mm,
            rightIndent=5 * mm,
            borderColor=colors.HexColor("#56A6B8"),
            borderWidth=1.5,
            borderPadding=4,
            spaceAfter=3 * mm,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=sample["Code"],
            fontName="Courier",
            fontSize=7.8,
            leading=10.3,
            textColor=colors.HexColor("#1E333E"),
            backColor=colors.HexColor("#EDF3F5"),
            borderPadding=6,
            leftIndent=3 * mm,
            rightIndent=3 * mm,
            spaceBefore=1.5 * mm,
            spaceAfter=3 * mm,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=sample["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor("#4A5B64"),
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=8.2,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=6.8,
            leading=8.4,
            textColor=colors.HexColor("#1F2B33"),
            wordWrap="CJK",
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.2,
            textColor=colors.HexColor("#64757E"),
        ),
    }


def parse_markdown(path: Path, styles: dict[str, ParagraphStyle]) -> list[object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    story: list[object] = []
    index = 0
    in_code = False
    code_lines: list[str] = []

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                story.append(Preformatted(ascii_safe("\n".join(code_lines)), styles["code"]))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if not stripped:
            index += 1
            continue
        if stripped == "<!-- pagebreak -->":
            story.append(PageBreak())
            index += 1
            continue
        if stripped == "---":
            story.append(Spacer(1, 1.5 * mm))
            index += 1
            continue
        if stripped.startswith("# "):
            story.append(Spacer(1, 15 * mm))
            story.append(Paragraph(inline_markup(stripped[2:]), styles["title"]))
            index += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(inline_markup(stripped[3:]), styles["h2"]))
            index += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), styles["h3"]))
            index += 1
            continue
        if stripped.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            story.extend([parse_table(table_lines, styles), Spacer(1, 3 * mm)])
            continue
        if re.match(r"^[-*] ", stripped):
            items = []
            while index < len(lines) and re.match(r"^[-*] ", lines[index].strip()):
                item_text = re.sub(r"^[-*] ", "", lines[index].strip())
                items.append(
                    ListItem(Paragraph(inline_markup(item_text), styles["body"]))
                )
                index += 1
            story.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="circle",
                    leftIndent=7 * mm,
                    bulletFontName="Helvetica",
                    bulletFontSize=7,
                    spaceAfter=2 * mm,
                )
            )
            continue
        if re.match(r"^\d+\. ", stripped):
            items = []
            while index < len(lines) and re.match(r"^\d+\. ", lines[index].strip()):
                item_text = re.sub(r"^\d+\. ", "", lines[index].strip())
                items.append(
                    ListItem(Paragraph(inline_markup(item_text), styles["body"]))
                )
                index += 1
            story.append(
                ListFlowable(
                    items,
                    bulletType="1",
                    leftIndent=8 * mm,
                    bulletFontName="Helvetica-Bold",
                    bulletFontSize=8,
                    spaceAfter=2 * mm,
                )
            )
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if (
                not candidate
                or candidate == "<!-- pagebreak -->"
                or candidate == "---"
                or candidate.startswith("#")
                or candidate.startswith("|")
                or candidate.startswith("```")
                or re.match(r"^[-*] ", candidate)
                or re.match(r"^\d+\. ", candidate)
            ):
                break
            paragraph_lines.append(candidate)
            index += 1
        paragraph = " ".join(paragraph_lines)
        image_match = re.fullmatch(r"!\[([^\]]+)\]\(([^)]+)\)", paragraph)
        if image_match:
            alt_text, relative = image_match.groups()
            story.append(image_flowable((path.parent / relative).resolve(), alt_text, styles))
        elif paragraph.startswith(">"):
            story.append(
                Paragraph(inline_markup(paragraph.lstrip("> ")), styles["quote"])
            )
        else:
            story.append(Paragraph(inline_markup(paragraph), styles["body"]))

    return story


def draw_header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D3DEE3"))
    canvas.setLineWidth(0.4)
    canvas.line(16 * mm, 14 * mm, PAGE_WIDTH - 16 * mm, 14 * mm)
    canvas.setFillColor(colors.HexColor("#60717A"))
    canvas.setFont("Helvetica", 7.3)
    footer = "RoboRacer - Item 12 Design Review"
    canvas.drawString(16 * mm, 9 * mm, footer)
    page_text = f"Page {doc.page}"
    canvas.drawRightString(PAGE_WIDTH - 16 * mm, 9 * mm, page_text)
    if doc.page > 1:
        header = "MODELING, CONTROLS, AND LIDAR MAST DESIGN REVIEW"
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(colors.HexColor("#47616E"))
        canvas.drawString(16 * mm, PAGE_HEIGHT - 12 * mm, header)
    canvas.restoreState()


def build_pdf(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=19 * mm,
        title="RoboRacer Modeling, Controls, and LiDAR Mast Design Review",
        author="500ft",
        subject="Item 12 evidence-traceable design review",
        creator="scripts/build_final_report.py",
    )
    story = parse_markdown(source, styles)
    document.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_pdf(args.input.resolve(), args.output.resolve())
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
