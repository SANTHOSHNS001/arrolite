import io
from datetime import datetime

from django.http import HttpResponse
from django.views import View

# PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics

# Excel
import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

from app.models.expenses.expenses_model import Expenses, ExpensesItems


import io
from datetime import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Table, TableStyle, Paragraph, Spacer,
)

from django.http import HttpResponse
from django.views import View

 


# ══════════════════════════════════════════════════════════════════════
#  BRAND COLOURS
# ══════════════════════════════════════════════════════════════════════
NAVY     = colors.HexColor("#0D1B2A")
ACCENT   = colors.HexColor("#1565C0")
ACCENT2  = colors.HexColor("#1976D2")
LIGHT_BG = colors.HexColor("#F0F4F8")
ALT_ROW  = colors.HexColor("#E8F0FE")
RED_TEXT = colors.HexColor("#B71C1C")
GRN_TEXT = colors.HexColor("#1B5E20")
MID_GREY = colors.HexColor("#607D8B")
RULE     = colors.HexColor("#CFD8DC")
WHITE    = colors.white

COMPANY_NAME  = "Arrolite"
COMPANY_FULL  = "Arrolite Group of Companies"
COMPANY_EMAIL = "accounts@arrolite.com"


# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════
def _sty(name, **kw):
    return ParagraphStyle(name, **kw)


def _status_style(status):
    """Return a coloured badge ParagraphStyle based on expense status."""
    colour_map = {
        "PAID":    ("#155724", "#D4EDDA", "#28A745"),
        "PENDING": ("#856404", "#FFF3CD", "#FFC107"),
        "PARTIAL": ("#0C5460", "#D1ECF1", "#17A2B8"),
    }
    txt_c, bg_c, bd_c = colour_map.get(status.upper(), ("#333333", "#EEEEEE", "#AAAAAA"))
    return _sty(
        f"status_{status}",
        fontName="Helvetica-Bold", fontSize=7, leading=9,
        textColor=colors.HexColor(txt_c),
        alignment=TA_CENTER,
        backColor=colors.HexColor(bg_c),
        borderColor=colors.HexColor(bd_c),
        borderWidth=0.5, borderPadding=2, borderRadius=3,
    )


def _parse_date(val):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {val}")


# ══════════════════════════════════════════════════════════════════════
#  VIEW
# ══════════════════════════════════════════════════════════════════════
class ExpenseExportView(View):

    # ── POST entry-point ─────────────────────────────────────────────
    def post(self, request):
        export_type   = request.POST.get("export_type",   "pdf")
        expenses_type = request.POST.get("expenses_type", "").strip()
        due_date_str  = request.POST.get("due_date",      "").strip()

        # Build queryset filters
        filters = {}
        if expenses_type:
            filters["expenses__expenses_type_id"] = expenses_type

        if due_date_str:
            if "to" in due_date_str:
                start_str, end_str = [d.strip() for d in due_date_str.split("to", 1)]
                try:
                    filters["due_date__range"] = (_parse_date(start_str), _parse_date(end_str))
                except ValueError:
                    pass
            else:
                try:
                    filters["due_date"] = _parse_date(due_date_str)
                except ValueError:
                    pass

        qs = (
            Expenses.objects
            .select_related("expenses_type")
            .prefetch_related("items")
            .filter(**filters)
            .order_by("-created_at")
        )

        rows = []
        for exp in qs:
            first_item   = exp.items.first()
            payment_mode = (
                first_item.payment_mode.upper()
                if first_item and first_item.payment_mode else "—"
            )
            rows.append({
                "company_name":   exp.company_name  or "—",
                "product_name":   exp.product_name  or "—",
                "expenses_type":  exp.expenses_type.name if exp.expenses_type else "—",
                "expense_status": (exp.expense_status or "PENDING").upper(),
                "due_date":       str(exp.due_date) if exp.due_date else "—",
                "payment_mode":   payment_mode,
                "amount":         float(exp.amount        or 0),
                "total_paid":     float(exp.total_paid()  or 0),
                "balance":        float(exp.balance_amount() or 0),
            })

        if export_type == "excel":
            return self._excel(rows)
        return self._pdf(rows)

    # ══════════════════════════════════════════════════════════════════
    #  PDF EXPORT
    # ══════════════════════════════════════════════════════════════════
    def _pdf(self, rows):
        buf = io.BytesIO()

        doc = BaseDocTemplate(
            buf,
            pagesize=landscape(A4),
            leftMargin=0.7*cm, rightMargin=0.7*cm,
            topMargin=2.7*cm,  bottomMargin=1.3*cm,
        )
        frame = Frame(
            doc.leftMargin, doc.bottomMargin,
            doc.width, doc.height, id="main",
        )
        doc.addPageTemplates([
            PageTemplate(id="base", frames=frame,
                         onPage=lambda c, d: (self._pdf_header(c, d), self._pdf_footer(c, d)))
        ])

        # ── Paragraph styles ──────────────────────────────────────────
        H_STYLE  = _sty("H",  fontName="Helvetica-Bold", fontSize=8,   textColor=WHITE,    leading=10, alignment=TA_LEFT)
        C_STYLE  = _sty("C",  fontName="Helvetica",      fontSize=8,   textColor=colors.HexColor("#1A1A2E"), leading=10)
        TOT_L    = _sty("TL", fontName="Helvetica-Bold", fontSize=8.5, textColor=WHITE,    alignment=TA_LEFT)
        TOT_R    = _sty("TR", fontName="Helvetica-Bold", fontSize=8.5, textColor=WHITE,    alignment=TA_RIGHT)

        # ── Column widths (must sum to doc.width exactly) ─────────────
        W     = doc.width
        col_w = [W*0.185, W*0.15, W*0.10, W*0.085,
                 W*0.09,  W*0.09, W*0.085, W*0.085, W*0.085]
        col_w[-1] = W - sum(col_w[:-1])          # absorb floating-point rounding

        # ── Table header row ──────────────────────────────────────────
        HDR = ["Company Name", "Product / Service", "Expense Type",
               "Status", "Invoice Date", "Payment Mode",
               "Total (Rs.)", "Paid (Rs.)", "Balance (Rs.)"]
        table_data = [[Paragraph(h, H_STYLE) for h in HDR]]
        row_styles = []

        total_amt = total_paid = total_bal = 0
        ri = 1  # running table-row index (0 = header)

        for ei, row in enumerate(rows):
            bg = ALT_ROW if ei % 2 == 0 else WHITE

            amt_sty = _sty(f"A{ei}", fontName="Helvetica-Bold", fontSize=8,
                           textColor=NAVY,    alignment=TA_RIGHT, leading=10)
            pay_sty = _sty(f"P{ei}", fontName="Helvetica",      fontSize=8,
                           textColor=MID_GREY, alignment=TA_RIGHT, leading=10)
            bal_sty = _sty(f"B{ei}", fontName="Helvetica-Bold", fontSize=8,
                           textColor=RED_TEXT if row["balance"] > 0 else GRN_TEXT,
                           alignment=TA_RIGHT, leading=10)

            table_data.append([
                Paragraph(f"<b>{row['company_name']}</b>",      C_STYLE),
                Paragraph(row["product_name"],                   C_STYLE),
                Paragraph(row["expenses_type"],                  C_STYLE),
                Paragraph(row["expense_status"], _status_style(row["expense_status"])),
                Paragraph(row["due_date"],                       C_STYLE),
                Paragraph(row["payment_mode"],                   C_STYLE),
                Paragraph(f"Rs.{row['amount']:,.2f}",            amt_sty),
                Paragraph(f"Rs.{row['total_paid']:,.2f}",        pay_sty),
                Paragraph(f"Rs.{row['balance']:,.2f}",           bal_sty),
            ])
            row_styles += [
                ("BACKGROUND", (0, ri), (-1, ri), bg),
                ("LINEBELOW",  (0, ri), (-1, ri), 0.4, RULE),
            ]
            ri += 1
            total_amt  += row["amount"]
            total_paid += row["total_paid"]
            total_bal  += row["balance"]

        # ── Grand-total footer row ─────────────────────────────────────
        table_data.append([
            Paragraph("GRAND TOTAL",                      TOT_L),
            Paragraph("",                                  TOT_L),
            Paragraph("",                                  TOT_L),
            Paragraph("",                                  TOT_L),
            Paragraph(f"{len(rows)} expenses",             TOT_L),
            Paragraph("",                                  TOT_L),
            Paragraph(f"Rs.{total_amt:,.2f}",              TOT_R),
            Paragraph(f"Rs.{total_paid:,.2f}",             TOT_R),
            Paragraph(f"Rs.{total_bal:,.2f}",              TOT_R),
        ])
        row_styles.append(("BACKGROUND", (0, ri), (-1, ri), NAVY))

        # ── Assemble TableStyle ────────────────────────────────────────
        tbl_style = TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  ACCENT),
            ("LINEBELOW",     (0, 0), (-1, 0),  1.5, ACCENT2),
            ("GRID",          (0, 0), (-1, -1), 0.3, RULE),
            ("BOX",           (0, 0), (-1, -1), 1.0, NAVY),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ("TOPPADDING",    (0, 0), (-1,  0), 7),
            ("BOTTOMPADDING", (0, 0), (-1,  0), 7),
        ] + row_styles)

        main_tbl = Table(table_data, colWidths=col_w, repeatRows=1)
        main_tbl.setStyle(tbl_style)

        # ── Summary KPI cards (above table) ───────────────────────────
        collection_rate = (total_paid / total_amt * 100) if total_amt else 0
        kpi_data = [[
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Expenses</font><br/>"
                f"<font size='13' color='#0D1B2A'><b>{len(rows)}</b></font>",
                C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Amount</font><br/>"
                f"<font size='11' color='#0D1B2A'><b>Rs.{total_amt:,.2f}</b></font>",
                C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Paid</font><br/>"
                f"<font size='11' color='#1B5E20'><b>Rs.{total_paid:,.2f}</b></font>",
                C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Outstanding Balance</font><br/>"
                f"<font size='11' color='#B71C1C'><b>Rs.{total_bal:,.2f}</b></font>",
                C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Collection Rate</font><br/>"
                f"<font size='11' color='#1565C0'><b>{collection_rate:.1f}%</b></font>",
                C_STYLE),
        ]]
        sw = W / 5
        kpi_tbl = Table(kpi_data, colWidths=[sw] * 5)
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BG),
            ("BOX",           (0, 0), (-1, -1), 0.8, NAVY),
            ("LINEBEFORE",    (1, 0), (-1, -1), 0.5, RULE),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))

        doc.build([kpi_tbl, Spacer(0, 0.35*cm), main_tbl])
        buf.seek(0)

        return HttpResponse(
            buf,
            content_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="arrolite_expense_report.pdf"'},
        )

    # ── PDF Header ────────────────────────────────────────────────────
    def _pdf_header(self, canv, doc):
        canv.saveState()
        pw = doc.pagesize[0]
        ph = doc.pagesize[1]

        # Navy top bar
        canv.setFillColor(NAVY)
        canv.rect(0, ph - 2.2*cm, pw, 2.2*cm, stroke=0, fill=1)

        # Blue left accent stripe
        canv.setFillColor(ACCENT2)
        canv.rect(0, ph - 2.2*cm, 0.55*cm, 2.2*cm, stroke=0, fill=1)

        # White company badge
        bx, by, bw, bh = 0.85*cm, ph - 1.75*cm, 3.8*cm, 1.2*cm
        canv.setFillColor(WHITE)
        canv.roundRect(bx, by, bw, bh, 4, stroke=0, fill=1)
        canv.setFont("Helvetica-Bold", 11)
        canv.setFillColor(NAVY)
        canv.drawCentredString(bx + bw / 2, by + 0.35*cm, COMPANY_NAME.upper())
        canv.setFont("Helvetica", 6)
        canv.setFillColor(ACCENT)
        # canv.drawCentredString(bx + bw / 2, by + 0.12*cm, "GROUP OF COMPANIES")

        # Report title
        canv.setFont("Helvetica-Bold", 15)
        canv.setFillColor(WHITE)
        canv.drawString(5.3*cm, ph - 1.25*cm, "EXPENSE REPORT")

        # Subtitle
        canv.setFont("Helvetica", 8)
        canv.setFillColor(colors.HexColor("#B0BEC5"))
        canv.drawString(5.3*cm, ph - 1.75*cm, "Financial Summary  ·  All Expense Entries")

        # Top-right: date & page
        canv.setFont("Helvetica", 8)
        canv.setFillColor(colors.HexColor("#90A4AE"))
        canv.drawRightString(pw - 0.6*cm, ph - 1.10*cm,
                             f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
        canv.drawRightString(pw - 0.6*cm, ph - 1.60*cm, f"Page {doc.page}")

        # Bottom accent line
        canv.setFillColor(ACCENT)
        canv.rect(0, ph - 2.2*cm, pw, 0.12*cm, stroke=0, fill=1)

        canv.restoreState()

    # ── PDF Footer ────────────────────────────────────────────────────
    def _pdf_footer(self, canv, doc):
        canv.saveState()
        pw = doc.pagesize[0]

        canv.setFillColor(NAVY)
        canv.rect(0, 0, pw, 0.9*cm, stroke=0, fill=1)

        canv.setFillColor(ACCENT2)
        canv.rect(0, 0, 0.55*cm, 0.9*cm, stroke=0, fill=1)

        canv.setFont("Helvetica", 7)
        canv.setFillColor(colors.HexColor("#90A4AE"))
        canv.drawString(0.85*cm, 0.3*cm,
                        f"System-generated report. Queries: {COMPANY_EMAIL}")
        canv.drawRightString(pw - 0.6*cm, 0.3*cm,
                             f"© {datetime.now().year} {COMPANY_FULL}")

        canv.restoreState()

    # ══════════════════════════════════════════════════════════════════
    #  EXCEL EXPORT
    # ══════════════════════════════════════════════════════════════════
    def _excel(self, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Expenses"

        # ── Palette ──
        C_DARK   = "0D1B2A"
        C_ACCENT = "1565C0"
        C_RED    = "B71C1C"
        C_GREEN  = "1B5E20"
        C_LIGHT  = "F0F4F8"
        C_ALT    = "E8F0FE"
        C_WHITE  = "FFFFFF"
        C_GREY   = "CFD8DC"
        C_MID    = "607D8B"

        thin   = Side(style="thin",   color=C_GREY)
        medium = Side(style="medium", color=C_DARK)
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        thick  = Border(left=medium, right=medium, top=medium, bottom=medium)

        # ── Column widths ──
        col_widths = [28, 22, 16, 12, 14, 14, 15, 15, 15]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # ── Row 1: Title ──
        ws.merge_cells("A1:I1")
        c = ws["A1"]
        c.value     = f"{COMPANY_FULL.upper()}  —  EXPENSE REPORT"
        c.font      = Font(name="Calibri", bold=True, size=14, color=C_WHITE)
        c.fill      = PatternFill("solid", fgColor=C_DARK)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 38

        # ── Row 2: Generated date ──
        ws.merge_cells("A2:I2")
        c = ws["A2"]
        c.value     = f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
        c.font      = Font(name="Calibri", italic=True, size=9, color="888888")
        c.fill      = PatternFill("solid", fgColor=C_LIGHT)
        c.alignment = Alignment(horizontal="right")
        ws.row_dimensions[2].height = 16

        # ── Row 3: KPI summary ──
        total_amt  = sum(r["amount"]     for r in rows)
        total_paid = sum(r["total_paid"] for r in rows)
        total_bal  = sum(r["balance"]    for r in rows)
        rate       = (total_paid / total_amt * 100) if total_amt else 0

        kpi_labels = [
            ("Total Expenses",    str(len(rows)),           C_DARK),
            ("Total Amount",      f"Rs.{total_amt:,.2f}",   C_DARK),
            ("Total Paid",        f"Rs.{total_paid:,.2f}",  C_GREEN),
            ("Outstanding",       f"Rs.{total_bal:,.2f}",   C_RED),
            ("Collection Rate",   f"{rate:.1f}%",           C_ACCENT),
        ]
        # Merge pairs of columns for each KPI card (9 cols / 5 ≈ use single cols)
        kpi_cols  = [1, 2, 4, 6, 8]   # starting columns for each card
        kpi_spans = [1, 2, 2, 2, 2]   # how many cols each card spans

        for ki, (label, value, val_color) in enumerate(kpi_labels):
            col = kpi_cols[ki]
            span = kpi_spans[ki]
            end_col = col + span - 1
            if span > 1:
                ws.merge_cells(
                    start_row=3, start_column=col,
                    end_row=3,   end_column=end_col
                )
            cell = ws.cell(row=3, column=col)
            cell.value = f"{label}: {value}"
            cell.font  = Font(name="Calibri", bold=True, size=9, color=val_color)
            cell.fill  = PatternFill("solid", fgColor=C_ALT)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        ws.row_dimensions[3].height = 20

        # ── Row 4: Column headers ──
        headers = ["Company Name", "Product / Service", "Expense Type", "Status",
                   "Invoice Date", "Payment Mode",
                   "Total (Rs.)", "Paid (Rs.)", "Balance (Rs.)"]
        for ci, header in enumerate(headers, 1):
            c = ws.cell(row=4, column=ci, value=header)
            c.font      = Font(name="Calibri", bold=True, size=10, color=C_WHITE)
            c.fill      = PatternFill("solid", fgColor=C_ACCENT)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border    = border
        ws.row_dimensions[4].height = 22
        ws.freeze_panes = "A5"

        # ── Status colour map ──
        status_colors = {
            "PAID":    ("155724", "D4EDDA"),
            "PENDING": ("856404", "FFF3CD"),
            "PARTIAL": ("0C5460", "D1ECF1"),
        }

        cur_row = 5
        for ei, row in enumerate(rows):
            is_even  = (ei % 2 == 0)
            bg       = C_ALT if is_even else C_WHITE
            exp_fill = PatternFill("solid", fgColor=bg)

            values = [
                row["company_name"],
                row["product_name"],
                row["expenses_type"],
                row["expense_status"],
                row["due_date"],
                row["payment_mode"],
                row["amount"],
                row["total_paid"],
                row["balance"],
            ]
            for ci, value in enumerate(values, 1):
                c        = ws.cell(row=cur_row, column=ci, value=value)
                c.fill   = exp_fill
                c.border = border
                c.alignment = Alignment(
                    vertical="center",
                    horizontal="right" if ci >= 7 else "left",
                )

                # Company name – bold
                if ci == 1:
                    c.font = Font(name="Calibri", bold=True, size=9)
                # Status badge colours
                elif ci == 4:
                    txt_c, bg_c = status_colors.get(
                        str(value).upper(), ("333333", "EEEEEE")
                    )
                    c.font = Font(name="Calibri", bold=True, size=9, color=txt_c)
                    c.fill = PatternFill("solid", fgColor=bg_c)
                    c.alignment = Alignment(horizontal="center", vertical="center")
                # Amount columns
                elif ci in (7, 8, 9):
                    c.number_format = '"Rs."#,##0.00'
                    if ci == 9 and isinstance(value, (int, float)):
                        c.font = Font(
                            name="Calibri", bold=True, size=9,
                            color=(C_RED if value > 0 else C_GREEN),
                        )
                    else:
                        c.font = Font(name="Calibri", bold=(ci == 7), size=9)
                else:
                    c.font = Font(name="Calibri", size=9)

            ws.row_dimensions[cur_row].height = 18
            cur_row += 1

        # ── Grand Total row ──
        tot_fill = PatternFill("solid", fgColor=C_DARK)
        tot_vals = [
            "GRAND TOTAL", "", "", "",
            f"{len(rows)} expenses", "",
            total_amt, total_paid, total_bal,
        ]
        for ci, value in enumerate(tot_vals, 1):
            c = ws.cell(row=cur_row, column=ci, value=value)
            c.font = Font(name="Calibri", bold=True, size=10, color=C_WHITE)
            c.fill = tot_fill
            c.border = thick
            c.alignment = Alignment(
                vertical="center",
                horizontal="right" if ci >= 7 else "left",
            )
            if ci in (7, 8, 9):
                c.number_format = '"Rs."#,##0.00'
        ws.row_dimensions[cur_row].height = 22

        ws.auto_filter.ref = f"A4:I{cur_row - 1}"

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        return HttpResponse(
            buf,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="arrolite_expense_report.xlsx"'},
        )