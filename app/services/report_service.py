"""
PDF report generator using ReportLab.
Produces a multi-section Vedic astrology report from chart data + cached analyses.
"""
import io
from datetime import date
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_PAGE_W, _PAGE_H = A4
_MARGIN = 2 * cm

_GOLD = colors.HexColor("#C9A84C")
_DARK = colors.HexColor("#1A1A2E")
_LIGHT_BG = colors.HexColor("#F5F0E8")
_SOFT = colors.HexColor("#6B6B8A")

_BASE_STYLES = getSampleStyleSheet()

_TITLE_STYLE = ParagraphStyle(
    "Title",
    parent=_BASE_STYLES["Title"],
    fontSize=22,
    textColor=_DARK,
    spaceAfter=6,
    alignment=TA_CENTER,
)
_SUBTITLE_STYLE = ParagraphStyle(
    "Subtitle",
    parent=_BASE_STYLES["Normal"],
    fontSize=11,
    textColor=_SOFT,
    spaceAfter=12,
    alignment=TA_CENTER,
)
_SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=_BASE_STYLES["Heading2"],
    fontSize=14,
    textColor=_DARK,
    spaceBefore=14,
    spaceAfter=6,
    borderPad=4,
)
_BODY_STYLE = ParagraphStyle(
    "Body",
    parent=_BASE_STYLES["Normal"],
    fontSize=10,
    textColor=_DARK,
    spaceAfter=6,
    leading=15,
)
_CAPTION_STYLE = ParagraphStyle(
    "Caption",
    parent=_BASE_STYLES["Normal"],
    fontSize=8,
    textColor=_SOFT,
    spaceAfter=4,
    alignment=TA_CENTER,
)

_TABLE_HEADER = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), _DARK),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_BG, colors.white]),
    ("FONTSIZE", (0, 1), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
])


def _divider(color=_GOLD) -> HRFlowable:
    return HRFlowable(width="100%", thickness=1, color=color, spaceAfter=8, spaceBefore=4)


def _section_header(title: str) -> list:
    return [
        Paragraph(title, _SECTION_STYLE),
        _divider(),
    ]


def _planet_table(planets: dict) -> Table:
    headers = ["Planet", "Sign", "House", "Nakshatra", "Dignity", "Retro"]
    rows = [headers]
    for name, data in sorted(planets.items()):
        sign = data.get("sign_name") or data.get("sign") or "?"
        house = str(data.get("house_parashari", "?"))
        nak = data.get("nakshatra") or "?"
        dignity = data.get("dignity") or ""
        retro = "Yes" if data.get("isRetro") or data.get("retro") else "No"
        rows.append([name.title(), sign, house, nak, dignity, retro])

    col_widths = [3 * cm, 3.5 * cm, 2 * cm, 4 * cm, 3 * cm, 1.5 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_TABLE_HEADER)
    return t


def _yoga_table(yogas: list[dict]) -> Table | None:
    if not yogas:
        return None
    headers = ["Yoga Name", "Type", "Planets Involved"]
    rows = [headers]
    for y in yogas:
        rows.append([
            y.get("name", "?"),
            y.get("type", "?"),
            ", ".join(y.get("planets", [])),
        ])
    col_widths = [7 * cm, 3 * cm, 7 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_TABLE_HEADER)
    return t


def _dasha_table(vimshottari: list[dict]) -> Table | None:
    if not vimshottari:
        return None
    headers = ["Mahadasha Lord", "Start", "End"]
    rows = [headers]
    for md in vimshottari[:12]:  # limit to 12 rows
        lord = (md.get("dasha") or md.get("planet") or md.get("lord") or "?").title()
        start = md.get("start") or md.get("start_date") or "?"
        end = md.get("end") or md.get("end_date") or "?"
        rows.append([lord, str(start)[:10], str(end)[:10]])
    col_widths = [6 * cm, 5 * cm, 5 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_TABLE_HEADER)
    return t


def _analysis_section(section_name: str, content: str) -> list:
    title = section_name.replace("_", " ").title()
    elements = _section_header(f"{title} Analysis")
    for para in content.split("\n\n"):
        para = para.strip()
        if para:
            elements.append(Paragraph(para.replace("\n", "<br/>"), _BODY_STYLE))
            elements.append(Spacer(1, 4))
    return elements


def generate_report(
    chart_row: dict,
    analyses: list[dict],
    include_sections: Optional[list[str]] = None,
) -> bytes:
    """
    Generates a PDF report and returns it as bytes.
    analyses: list of {section, content} dicts from the analyses table.
    include_sections: if provided, only include these sections.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN,
        title=f"Vedic Astrology Report — {chart_row.get('name', 'Chart')}",
    )

    story = []

    # ── Cover ──────────────────────────────────────────────────────
    story.append(Spacer(1, 2 * cm))
    name = chart_row.get("name") or "Birth Chart"
    story.append(Paragraph(f"Vedic Astrology Report", _TITLE_STYLE))
    story.append(Paragraph(name, ParagraphStyle("Name", parent=_TITLE_STYLE, fontSize=18, textColor=_GOLD)))
    story.append(Spacer(1, 0.3 * cm))

    dob = chart_row.get("dob") or ""
    tob = chart_row.get("tob") or ""
    pob = chart_row.get("pob_name") or ""
    story.append(Paragraph(f"Born: {dob} at {str(tob)[:5]} | {pob}", _SUBTITLE_STYLE))
    story.append(Paragraph(f"Generated: {date.today().isoformat()}", _SUBTITLE_STYLE))
    story.append(_divider(_GOLD))
    story.append(Spacer(1, 0.5 * cm))

    # ── Astro Details ─────────────────────────────────────────────
    astro = chart_row.get("astro_details") or {}
    current_dasha = chart_row.get("current_dasha") or {}

    story += _section_header("Chart Overview")
    overview_data = [
        ["Ascendant (Lagna)", astro.get("ascendant", "?")],
        ["Moon Sign (Rashi)", astro.get("moon_sign") or astro.get("moonsign") or "?"],
        ["Sun Sign", astro.get("sun_sign") or "?"],
        ["Current Mahadasha", (current_dasha.get("major_dasha") or current_dasha.get("maha_dasha") or "?").title()],
        ["Current Antardasha", (current_dasha.get("antar_dasha") or current_dasha.get("antar") or "?").title()],
    ]
    ov_table = Table(overview_data, colWidths=[6 * cm, 10 * cm])
    ov_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_LIGHT_BG, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ov_table)

    # ── Planet Positions ──────────────────────────────────────────
    planets = chart_row.get("planets") or {}
    if planets:
        story += _section_header("Planetary Positions")
        story.append(_planet_table(planets))

    # ── Active Yogas ─────────────────────────────────────────────
    yogas = chart_row.get("yogas") or []
    if yogas:
        story += _section_header("Active Yogas")
        t = _yoga_table(yogas)
        if t:
            story.append(t)

    # ── Vimshottari Dasha Timeline ────────────────────────────────
    dashas = chart_row.get("dashas") or {}
    vimshottari = dashas.get("vimshottari") or []
    if vimshottari:
        story += _section_header("Vimshottari Dasha Timeline")
        t = _dasha_table(vimshottari)
        if t:
            story.append(t)

    # ── Analysis Sections ─────────────────────────────────────────
    if analyses:
        story.append(PageBreak())
        story += _section_header("AI Analysis Sections")
        story.append(Paragraph(
            "The following sections are AI-generated interpretations based on classical Vedic astrology principles. "
            "For educational purposes only.",
            _CAPTION_STYLE,
        ))
        story.append(Spacer(1, 0.4 * cm))

        ordered = sorted(analyses, key=lambda a: a.get("section", ""))
        for analysis in ordered:
            section = analysis.get("section") or ""
            content = analysis.get("content") or ""
            if include_sections and section not in include_sections:
                continue
            if content:
                story += _analysis_section(section, content)
                story.append(Spacer(1, 0.3 * cm))

    # ── Footer note ───────────────────────────────────────────────
    story.append(Spacer(1, cm))
    story.append(_divider(_SOFT))
    story.append(Paragraph(
        "This report is generated by Cosmos — a Vedic Astrology Platform. "
        "Interpretations are based on classical Jyotish principles and are for educational purposes only. "
        "Astrology should complement, not replace, professional advice.",
        _CAPTION_STYLE,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
