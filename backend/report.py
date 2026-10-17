"""Printable PDF report from the exact API simulation payload and results."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String
from reportlab.platypus import Flowable, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

INK = colors.HexColor("#152238")
TEAL = colors.HexColor("#087e77")
PALETTE = [TEAL, colors.HexColor("#a36d13"), colors.HexColor("#3468a7"),
           colors.HexColor("#a34b70"), colors.HexColor("#7259b1"), colors.HexColor("#4f8d36")]
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)


def brl(value: str) -> str:
    from decimal import Decimal

    formatted = f"{Decimal(value):,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _chart(series: list[tuple[str, list[float]]], total_months: int, *, title: str) -> Drawing:
    """Vector line chart with one legend entry per plotted series."""
    width, height = 760, 215
    drawing = Drawing(width, height)
    left, right, bottom, top = 55, 12, 48, 28
    chart_width, chart_height = width - left - right, height - bottom - top
    all_values = [value for _, values in series for value in values]
    low, high = min([0.0, *all_values]), max([1.0, *all_values])
    if low == high:
        high = low + 1
    drawing.add(String(left, height - 12, title, fontName="Helvetica-Bold", fontSize=11, fillColor=INK))
    drawing.add(Line(left, bottom, left + chart_width, bottom, strokeColor=INK, strokeWidth=0.7))
    drawing.add(Line(left, bottom, left, bottom + chart_height, strokeColor=INK, strokeWidth=0.7))
    drawing.add(String(left, 9, "Mês 1", fontSize=8, fillColor=INK))
    drawing.add(String(left + chart_width - 45, 9, f"Mês {total_months}", fontSize=8, fillColor=INK))
    drawing.add(String(2, bottom, f"{low:,.0f}", fontSize=7, fillColor=INK))
    drawing.add(String(2, bottom + chart_height, f"{high:,.0f}", fontSize=7, fillColor=INK))
    drawing.add(String(left + 4, bottom + chart_height - 8, "Saldo / valor (R$)", fontSize=8, fillColor=INK))
    for index, (name, values) in enumerate(series):
        color = PALETTE[index % len(PALETTE)]
        points = []
        for offset, value in enumerate(values):
            x = left + chart_width * offset / max(1, total_months - 1)
            y = bottom + chart_height * (value - low) / (high - low)
            points.extend([x, y])
        if len(points) >= 4:
            drawing.add(PolyLine(points, strokeColor=color, strokeWidth=1.7, fillColor=None))
        else:
            drawing.add(Line(points[0], points[1], points[0] + 0.1, points[1],
                             strokeColor=color, strokeWidth=2))
        legend_x = left + (index % 4) * 170
        legend_y = 37 - (index // 4) * 10
        swatch = Rect(legend_x, legend_y, 10, 3)
        swatch.fillColor = color
        swatch.strokeColor = None
        drawing.add(swatch)
        drawing.add(String(legend_x + 15, legend_y - 2, name[:23], fontSize=7, fillColor=INK))
    return drawing


def _styled_table(rows: list[list], widths: list[int], *, repeat_header: bool = True) -> LongTable:
    table = LongTable(rows, colWidths=widths, repeatRows=1 if repeat_header else 0, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEADING", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef5f5")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def create_pdf(data: dict) -> bytes:
    """Build an in-memory, multi-page PDF without storing user parameters."""
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=28,
                                 rightMargin=28, topMargin=26, bottomMargin=28)
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("HeadingCustom", parent=styles["Heading1"], textColor=INK, spaceAfter=10)
    subheading = ParagraphStyle("SubheadingCustom", parent=styles["Heading2"], textColor=TEAL,
                                spaceBefore=10, spaceAfter=7)
    small = ParagraphStyle("SmallCustom", parent=styles["Normal"], fontSize=9, leading=13)
    table_name = ParagraphStyle("TableName", parent=small, fontSize=7, leading=9, wordWrap="CJK")
    parameters = data["parameters"]
    base = data["base"]
    alternatives = data["scenarios"]
    entries = [("Sem retiradas", base), *[(item["name"], item) for item in alternatives]]
    story: list[Flowable] = [Paragraph("Relatório de investimento", heading),
             Paragraph(f"Prazo: {parameters['months']} meses | Aporte mensal: {brl(parameters['monthly_contribution'])} | "
                       f"Aporte pontual: {brl(parameters['one_time_contribution'])} no mês {parameters['one_time_month']} | "
                       f"Taxa anual efetiva: {parameters['annual_rate_pct']}%", small),
             Paragraph("Premissas", subheading),
             Paragraph("A taxa mensal equivale a (1 + taxa anual/100)^(1/12) - 1. "
                       "Aportes entram no início de cada mês, juros são creditados em seguida e retiradas ocorrem "
                       "no fim do mês. Juros são arredondados a centavos a cada mês (meio para cima). "
                       "Projeção nominal, sem impostos nem inflação. Retiradas acima do saldo disponível "
                       "são limitadas ao saldo e o restante aparece como não atendido.", small),
             Paragraph("Resumo comparativo", subheading)]
    summary_rows = [["Cenário", "Aportado", "Retirado", "Rendimento", "Saldo final", "Não atendido"]]
    for name, result in entries:
        total = result["summary"]
        summary_rows.append([Paragraph(escape(name), table_name), brl(total["contributions_total"]),
                             brl(total["withdrawals_total"]), brl(total["earnings_total"]),
                             brl(total["final_balance"]), brl(total["unmet_withdrawal_total"])])
    story.extend([_styled_table(summary_rows, [110, 130, 125, 130, 140, 145]), Spacer(1, 10)])
    balance_series = [(name, [float(row["balance"]) for row in result["months"]])
                      for name, result in entries]
    story.append(_chart(balance_series, parameters["months"], title="Evolução do saldo por cenário"))
    composition_series = [
        ("Aportes líquidos", [float(row["net_contributions_total"]) for row in base["months"]]),
        ("Rendimento acumulado", [float(row["earnings_total"]) for row in base["months"]]),
    ]
    story.append(_chart(composition_series, parameters["months"], title="Composição da projeção-base"))
    for index, (name, result) in enumerate(entries):
        if index:
            story.append(PageBreak())
        story.extend([Paragraph(f"Evolução mensal: {escape(name)}", heading),
                      Paragraph("Valores em reais (R$). Retirada não atendida = solicitada menos efetiva.", small),
                      Spacer(1, 8)])
        monthly_rows = [["Mês", "Aporte", "Juros", "Ret. solicitada", "Ret. efetiva", "Não atendida", "Saldo"]]
        for row in result["months"]:
            monthly_rows.append([str(row["month"]), brl(row["contribution"]), brl(row["interest"]),
                                 brl(row["withdrawal_requested"]), brl(row["withdrawal"]),
                                 brl(row["unmet_withdrawal"]), brl(row["balance"])])
        story.append(_styled_table(monthly_rows, [42, 100, 100, 112, 112, 112, 198]))

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(INK)
        canvas.drawCentredString(PAGE_WIDTH / 2, 14, f"Projeção ilustrativa • Página {doc.page}")

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
