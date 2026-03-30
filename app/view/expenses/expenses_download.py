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
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════
COMPANY_NAME  = "Arrolite"
COMPANY_FULL  = "Arrolite Group of Companies"
COMPANY_EMAIL = "accounts@arrolite.com"

# ── Brand colours ──
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


# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════
def _sty(name, **kw):
    return ParagraphStyle(name, **kw)


def _status_style(status):
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
            ExpensesItems.objects
            .select_related("expenses", "expenses__expenses_type")
            .filter(**filters)
            .order_by("-created_at")
        )

        rows = []
        for exp in qs:
            expense = exp.expenses
            rows.append({
                "company_name":   expense.company_name or "—",
                "product_name":   expense.product_name or "—",
                "expenses_type":  expense.expenses_type.name if expense.expenses_type else "—",
                "expense_status": (expense.expense_status or "PENDING").upper(),
                "invoice_number": exp.invoice_number or "—",
                "due_date":       str(exp.due_date) if exp.due_date else "—",
                "payment_mode":   (exp.payment_mode or "—").upper(),
                "amount":         float(exp.amount or 0),
                "total_amount":         float(expense.amount or 0),
                
                "total_paid":     float(expense.total_paid() or 0),
                "balance":        float(expense.balance_amount() or 0),
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
            PageTemplate(
                id="base", frames=frame,
                onPage=lambda c, d: (self._pdf_header(c, d), self._pdf_footer(c, d))
            )
        ])

        # ── Paragraph styles ──
        H_STYLE = _sty("H",  fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE,    leading=10, alignment=TA_LEFT)
        C_STYLE = _sty("C",  fontName="Helvetica",      fontSize=7.5, textColor=colors.HexColor("#1A1A2E"), leading=10)
        TOT_L   = _sty("TL", fontName="Helvetica-Bold", fontSize=8,   textColor=WHITE,    alignment=TA_LEFT)
        TOT_R   = _sty("TR", fontName="Helvetica-Bold", fontSize=8,   textColor=WHITE,    alignment=TA_RIGHT)

        # ── 11 columns — widths must sum exactly to doc.width ──
        #   Col:  1-Company | 2-Product | 3-Type | 4-Status | 5-Invoice No.
        #         6-Date    | 7-Payment | 8-Item | 9-Expense | 10-Paid | 11-Balance
        W = doc.width
        col_w = [
            W * 0.145,  # 1  Company Name
            W * 0.12,   # 2  Product / Service
            W * 0.09,   # 3  Expense Type
            W * 0.065,  # 4  Status
            W * 0.09,   # 5  Invoice No.
            W * 0.075,  # 6  Invoice Date
            W * 0.075,  # 7  Payment Mode
            W * 0.08,   # 8  Item Total (Rs.)
            W * 0.08,   # 9  Expense Total (Rs.)
            W * 0.08,   # 10 Paid (Rs.)
            W * 0.08,   # 11 Balance (Rs.)
        ]
        col_w[-1] = W - sum(col_w[:-1])   # absorb floating-point rounding

        # ── Table header row — 11 columns ──
        HDR = [
            "Company Name", "Product / Service", "Expense Type",
            "Status", "Invoice No.", "Invoice Date",
            "Payment Mode", "Item Total (Rs.)", "Expense Total (Rs.)", "Paid (Rs.)", "Balance (Rs.)",
        ]
        table_data = [[Paragraph(h, H_STYLE) for h in HDR]]
        row_styles = []

        total_amt = total_paid = total_bal = 0
        ri = 1

        for ei, row in enumerate(rows):
            bg = ALT_ROW if ei % 2 == 0 else WHITE

            amt_sty = _sty(f"A{ei}", fontName="Helvetica-Bold", fontSize=7.5,
                           textColor=NAVY,     alignment=TA_RIGHT, leading=10)
            pay_sty = _sty(f"P{ei}", fontName="Helvetica",      fontSize=7.5,
                           textColor=MID_GREY, alignment=TA_RIGHT, leading=10)
            bal_sty = _sty(f"B{ei}", fontName="Helvetica-Bold", fontSize=7.5,
                           textColor=RED_TEXT if row["balance"] > 0 else GRN_TEXT,
                           alignment=TA_RIGHT, leading=10)

            # ── 11 cells — must match col_w exactly ──
            table_data.append([
                Paragraph(f"<b>{row['company_name']}</b>",        C_STYLE),  # 1
                Paragraph(row["product_name"],                     C_STYLE),  # 2
                Paragraph(row["expenses_type"],                    C_STYLE),  # 3
                Paragraph(row["expense_status"], _status_style(row["expense_status"])),  # 4
                Paragraph(row["invoice_number"],                   C_STYLE),  # 5
                Paragraph(row["due_date"],                         C_STYLE),  # 6
                Paragraph(row["payment_mode"],                     C_STYLE),  # 7
                Paragraph(f"Rs.{row['amount']:,.2f}",              amt_sty),  # 8  Item amount
                Paragraph(f"Rs.{row['total_amount']:,.2f}",        amt_sty),  # 9  Expense total
                Paragraph(f"Rs.{row['total_paid']:,.2f}",          pay_sty),  # 10 Paid
                Paragraph(f"Rs.{row['balance']:,.2f}",             bal_sty),  # 11 Balance
            ])
            row_styles += [
                ("BACKGROUND", (0, ri), (-1, ri), bg),
                ("LINEBELOW",  (0, ri), (-1, ri), 0.4, RULE),
            ]
            ri += 1
            total_amt  += row["amount"]
            total_paid += row["total_paid"]
            total_bal  += row["balance"]

        # ── Grand-total footer row — 11 cells ──
        table_data.append([
            Paragraph("GRAND TOTAL",           TOT_L),   # 1
            Paragraph("",                       TOT_L),   # 2
            Paragraph("",                       TOT_L),   # 3
            Paragraph("",                       TOT_L),   # 4
            Paragraph(f"{len(rows)} items",     TOT_L),   # 5
            Paragraph("",                       TOT_L),   # 6
            Paragraph("",                       TOT_L),   # 7
            Paragraph(f"Rs.{total_amt:,.2f}",   TOT_R),   # 8
            Paragraph(f"Rs.{sum(r['total_amount'] for r in rows):,.2f}", TOT_R), # 9
            Paragraph(f"Rs.{total_paid:,.2f}",  TOT_R),   # 10
            Paragraph(f"Rs.{total_bal:,.2f}",   TOT_R),   # 11
        ])
        row_styles.append(("BACKGROUND", (0, ri), (-1, ri), NAVY))

        tbl_style = TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  ACCENT),
            ("LINEBELOW",     (0, 0), (-1, 0),  1.5, ACCENT2),
            ("GRID",          (0, 0), (-1, -1), 0.3, RULE),
            ("BOX",           (0, 0), (-1, -1), 1.0, NAVY),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1,  0), 7),
            ("BOTTOMPADDING", (0, 0), (-1,  0), 7),
        ] + row_styles)

        main_tbl = Table(table_data, colWidths=col_w, repeatRows=1)
        main_tbl.setStyle(tbl_style)

        # ── KPI summary cards ──
        collection_rate = (total_paid / total_amt * 100) if total_amt else 0
        kpi_data = [[
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Items</font><br/>"
                f"<font size='13' color='#0D1B2A'><b>{len(rows)}</b></font>", C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Amount</font><br/>"
                f"<font size='11' color='#0D1B2A'><b>Rs.{total_amt:,.2f}</b></font>", C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Paid</font><br/>"
                f"<font size='11' color='#1B5E20'><b>Rs.{total_paid:,.2f}</b></font>", C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Outstanding Balance</font><br/>"
                f"<font size='11' color='#B71C1C'><b>Rs.{total_bal:,.2f}</b></font>", C_STYLE),
            # Paragraph(
            #     f"<font size='7' color='#607D8B'>Collection Rate</font><br/>"
            #     f"<font size='11' color='#1565C0'><b>{collection_rate:.1f}%</b></font>", C_STYLE),
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

        canv.setFillColor(NAVY)
        canv.rect(0, ph - 2.2*cm, pw, 2.2*cm, stroke=0, fill=1)

        canv.setFillColor(ACCENT2)
        canv.rect(0, ph - 2.2*cm, 0.55*cm, 2.2*cm, stroke=0, fill=1)

        bx, by, bw, bh = 0.85*cm, ph - 1.75*cm, 3.8*cm, 1.2*cm
        canv.setFillColor(WHITE)
        canv.roundRect(bx, by, bw, bh, 4, stroke=0, fill=1)
        canv.setFont("Helvetica-Bold", 11)
        canv.setFillColor(NAVY)
        canv.drawCentredString(bx + bw / 2, by + 0.35*cm, COMPANY_NAME.upper())
        canv.setFont("Helvetica", 6)
        canv.setFillColor(ACCENT)
        # canv.drawCentredString(bx + bw / 2, by + 0.12*cm, "GROUP OF COMPANIES")
        # canv.drawCentredString(bx + bw / 2, by + 0.12*cm, "GROUP OF COMPANIES")

        canv.setFont("Helvetica-Bold", 15)
        canv.setFillColor(WHITE)
        canv.drawString(5.3*cm, ph - 1.25*cm, "EXPENSE REPORT")

        canv.setFont("Helvetica", 8)
        canv.setFillColor(colors.HexColor("#B0BEC5"))
        canv.drawString(5.3*cm, ph - 1.75*cm, "Financial Summary  .  All Expense Entries")

        canv.setFont("Helvetica", 8)
        canv.setFillColor(colors.HexColor("#90A4AE"))
        canv.drawRightString(pw - 0.6*cm, ph - 1.10*cm,
                             f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
        canv.drawRightString(pw - 0.6*cm, ph - 1.60*cm, f"Page {doc.page}")

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
                             f"(c) {datetime.now().year} {COMPANY_FULL}")
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

        thin   = Side(style="thin",   color=C_GREY)
        medium = Side(style="medium", color=C_DARK)
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        thick  = Border(left=medium, right=medium, top=medium, bottom=medium)

        # ── 11 columns A–K ──
        #   A=Company | B=Product | C=Type | D=Status | E=Invoice No.
        #   F=Date    | G=Payment | H=Item Total | I=Expense Total | J=Paid | K=Balance
        col_widths = [26, 20, 15, 11, 14, 12, 13, 12, 12, 13, 13]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # ── Row 1: Title (A1:K1) ──
        ws.merge_cells("A1:J1")
        c = ws["A1"]
        c.value     = f"{COMPANY_FULL.upper()}  -  EXPENSE REPORT"
        c.font      = Font(name="Calibri", bold=True, size=14, color=C_WHITE)
        c.fill      = PatternFill("solid", fgColor=C_DARK)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 38

        # ── Row 2: Generated date (A2:J2) ──
        ws.merge_cells("A2:J2")
        c = ws["A2"]
        c.value     = f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
        c.font      = Font(name="Calibri", italic=True, size=9, color="888888")
        c.fill      = PatternFill("solid", fgColor=C_LIGHT)
        c.alignment = Alignment(horizontal="right")
        ws.row_dimensions[2].height = 16

        # ── Row 3: KPI cards — 5 cards x 2 cols = 10 cols exactly ──
        total_amt  = sum(r["amount"]     for r in rows)
        total_paid = sum(r["total_paid"] for r in rows)
        total_bal  = sum(r["balance"]    for r in rows)
        rate       = (total_paid / total_amt * 100) if total_amt else 0

        kpi_labels = [
            ("Total Items",     str(len(rows)),            C_DARK),
            ("Total Amount",    f"Rs.{total_amt:,.2f}",    C_DARK),
            ("Total Paid",      f"Rs.{total_paid:,.2f}",   C_GREEN),
            ("Outstanding",     f"Rs.{total_bal:,.2f}",    C_RED),
            # ("Collection Rate", f"{rate:.1f}%",            C_ACCENT),
        ]
        for ki, (label, value, val_color) in enumerate(kpi_labels):
            start_col = ki * 2 + 1   # 1, 3, 5, 7, 9
            end_col   = start_col + 1 # 2, 4, 6, 8, 10
            ws.merge_cells(start_row=3, start_column=start_col,
                           end_row=3,   end_column=end_col)
            cell           = ws.cell(row=3, column=start_col)
            cell.value     = f"{label}: {value}"
            cell.font      = Font(name="Calibri", bold=True, size=9, color=val_color)
            cell.fill      = PatternFill("solid", fgColor=C_ALT)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border    = Border(left=thin, right=thin, top=thin, bottom=thin)
        ws.row_dimensions[3].height = 20

        # ── Row 4: Column headers — 11 columns ──
        headers = [
            "Company Name",      # A col 1
            "Product / Service", # B col 2
            "Expense Type",      # C col 3
            "Status",            # D col 4
            "Invoice No.",       # E col 5
            "Invoice Date",      # F col 6
            "Payment Mode",      # G col 7
            "Item Total (Rs.)",  # H col 8
            "Expense Total (Rs.)", # I col 9
            "Paid (Rs.)",        # J col 10
            "Balance (Rs.)",     # K col 11
        ]
        for ci, header in enumerate(headers, 1):
            c           = ws.cell(row=4, column=ci, value=header)
            c.font      = Font(name="Calibri", bold=True, size=10, color=C_WHITE)
            c.fill      = PatternFill("solid", fgColor=C_ACCENT)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border    = border
        ws.row_dimensions[4].height = 22
        ws.freeze_panes = "A5"

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

            # 11 values — same order as headers above
            values = [
                row["company_name"],    # A  col 1
                row["product_name"],    # B  col 2
                row["expenses_type"],   # C  col 3
                row["expense_status"],  # D  col 4
                row["invoice_number"],  # E  col 5
                row["due_date"],        # F  col 6
                row["payment_mode"],    # G  col 7
                row["amount"],          # H  col 8
                row["total_amount"],    # I  col 9
                row["total_paid"],      # J  col 10
                row["balance"],         # K  col 11
            ]
            for ci, value in enumerate(values, 1):
                c           = ws.cell(row=cur_row, column=ci, value=value)
                c.fill      = exp_fill
                c.border    = border
                c.alignment = Alignment(
                    vertical="center",
                    horizontal="right"  if ci >= 9 else
                               "center" if ci in (4, 5, 6, 7) else "left",
                )
                if ci == 1:    # Company — bold
                    c.font = Font(name="Calibri", bold=True, size=9)
                elif ci == 4:  # Status badge
                    txt_c, bg_c = status_colors.get(str(value).upper(), ("333333", "EEEEEE"))
                    c.font  = Font(name="Calibri", bold=True, size=9, color=txt_c)
                    c.fill  = PatternFill("solid", fgColor=bg_c)
                elif ci in (8, 9, 10, 11):  # Amount columns
                    c.number_format = '"Rs."#,##0.00'
                    if ci == 11 and isinstance(value, (int, float)):
                        c.font = Font(name="Calibri", bold=True, size=9,
                                      color=(C_RED if value > 0 else C_GREEN))
                    else:
                        c.font = Font(name="Calibri", bold=(ci == 8), size=9)
                else:
                    c.font = Font(name="Calibri", size=9)

            ws.row_dimensions[cur_row].height = 18
            cur_row += 1

        # ── Grand Total row — 11 cells ──
        tot_fill = PatternFill("solid", fgColor=C_DARK)
        tot_vals = [
            "GRAND TOTAL", "", "", "",          # A–D  cols 1–4
            f"{len(rows)} items", "", "",        # E–G  cols 5–7
            total_amt, sum(r["total_amount"] for r in rows), total_paid, total_bal,    # H–K  cols 8–11
        ]
        for ci, value in enumerate(tot_vals, 1):
            c           = ws.cell(row=cur_row, column=ci, value=value)
            c.font      = Font(name="Calibri", bold=True, size=10, color=C_WHITE)
            c.fill      = tot_fill
            c.border    = thick
            c.alignment = Alignment(
                vertical="center",
                horizontal="right" if ci >= 8 else "left",
            )
            if ci in (8, 9, 10, 11):
                c.number_format = '"Rs."#,##0.00'
        ws.row_dimensions[cur_row].height = 22

        ws.auto_filter.ref = f"A4:K{cur_row - 1}"

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        return HttpResponse(
            buf,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="arrolite_expense_report.xlsx"'},
        )