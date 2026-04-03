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
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics

# Excel
import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

from app.models.expenses.expenses_model import Expenses, ExpensesItems


# ── Company constants (replace with your actual values) ──────────────
COMPANY_NAME  = "Arrolite"
COMPANY_FULL  = "Arrolite Group of Companies"
COMPANY_EMAIL = "accounts@arrolite.com"
 
# ── Colour palette ───────────────────────────────────────────────────
WHITE     = colors.white
NAVY      = colors.HexColor("#0D1B2A")
ACCENT    = colors.HexColor("#1565C0")
ACCENT2   = colors.HexColor("#FFA000")
ALT_ROW   = colors.HexColor("#EEF2F7")
LIGHT_BG  = colors.HexColor("#F5F7FA")
RULE      = colors.HexColor("#CFD8DC")
MID_GREY  = colors.HexColor("#546E7A")
RED_TEXT  = colors.HexColor("#B71C1C")
GRN_TEXT  = colors.HexColor("#1B5E20")
 
 
# ── Helpers ──────────────────────────────────────────────────────────
def _parse_date(s):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            from datetime import datetime as dt
            return dt.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date: {s!r}")
 
 
def _sty(name, **kw):
    return ParagraphStyle(name, **kw)
 
 
def _status_style(status):
    colour_map = {
        "PAID":    colors.HexColor("#1B5E20"),
        "PENDING": colors.HexColor("#E65100"),
        "OVERDUE": colors.HexColor("#B71C1C"),
    }
    c = colour_map.get(status, MID_GREY)
    return _sty(f"ST_{status}", fontName="Helvetica-Bold", fontSize=7,
                textColor=c, leading=10)
 
 
# ════════════════════════════════════════════════════════════════════
class ExpenseExportView(View):
 
    # ── POST entry-point ─────────────────────────────────────────────
    def post(self, request):
               # adjust import path
 
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
                "company_name":   expense.company_name   or "—",
                "product_name":   expense.product_name   or "—",
                "invoice_number": expense.invoice_number or "—",
                # ── FIX: invoice_date was missing from the dict ──
                "invoice_date":   str(expense.due_date) if getattr(expense, "due_date", None) else "—",
                "paid_date":      str(exp.due_date)  if exp.due_date  else "—",
                "expense_status": (expense.expense_status or "PENDING").upper(),
                "expense_type":   expense.expenses_type.name if expense.expenses_type else "—",
                "payment_mode":   (exp.payment_mode or "—").upper(),
                "amount":         float(exp.amount       or 0),   # item amount
                "total_amount":   float(expense.amount   or 0),   # expense total
                "total_paid":     float(expense.total_paid()      or 0),
                "balance":        float(expense.balance_amount()  or 0),
            })
 
        if export_type == "excel":
            return self._excel(rows)
        return self._pdf(rows)
 
    # ════════════════════════════════════════════════════════════════
    #  PDF EXPORT
    # ════════════════════════════════════════════════════════════════
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
 
        # ── Paragraph styles ──────────────────────────────────────
        H_STYLE = _sty("H",  fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE,    leading=10, alignment=TA_LEFT)
        C_STYLE = _sty("C",  fontName="Helvetica",      fontSize=7.5, textColor=colors.HexColor("#1A1A2E"), leading=10)
        TOT_L   = _sty("TL", fontName="Helvetica-Bold", fontSize=8,   textColor=WHITE,    alignment=TA_LEFT)
        TOT_R   = _sty("TR", fontName="Helvetica-Bold", fontSize=8,   textColor=WHITE,    alignment=TA_RIGHT)
 
        # ── 11 columns — widths must sum exactly to doc.width ─────
        #
        #  #   Column                %
        #  1   Company Name         13 %
        #  2   Product Name         11 %
        #  3   Invoice Number       10 %
        #  4   Invoice Date          8 %
        #  5   Status                7 %
        #  6   Paid Date             7 %
        #  7   Payment Mode          7 %
        #  8   Item Total (Rs.)      8 %
        #  9   Expense Total (Rs.)   9 %
        # 10   Paid (Rs.)            8 %
        # 11   Balance (Rs.)        12 %  ← absorbs rounding remainder
        #
        W = doc.width
        col_w = [
            W * 0.13,   # 1  Company Name
            W * 0.11,   # 2  Product Name
            W * 0.10,   # 3  Invoice Number
            W * 0.08,   # 4  Invoice Date
            W * 0.07,   # 5  Status
            W * 0.07,   # 6  Paid Date
            W * 0.07,   # 7  Payment Mode
            W * 0.08,   # 8  Item Total
            W * 0.09,   # 9  Expense Total
            W * 0.08,   # 10 Paid
            W * 0.08,   # 11 Balance  ← last col absorbs rounding
        ]
        col_w[-1] = W - sum(col_w[:-1])
 
        # ── FIX: 11 header strings, each correctly comma-separated ─
        HDR = [
            "Company Name",         # 1
            "Product Name",         # 2
            "Invoice Number",       # 3
            "Invoice Date",         # 4
            "Status",               # 5
            "Paid Date",            # 6
            "Payment Mode",         # 7
            "Paid Amount ",     # 8
            "Invoice Amount",  # 9
            "Paid",           # 10
            "Balance ",        # 11
        ]
        table_data = [[Paragraph(h, H_STYLE) for h in HDR]]
        row_styles = []
 
        total_item_amt = total_exp_amt = total_paid = total_bal = 0
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
 
            # ── FIX: 11 cells in the same order as HDR ────────────
            table_data.append([
                Paragraph(f"<b>{row['company_name']}</b>",         C_STYLE),                        # 1
                Paragraph(row["product_name"],                      C_STYLE),                        # 2
                Paragraph(row["invoice_number"],                    C_STYLE),                        # 3
                Paragraph(row["invoice_date"],                      C_STYLE),                        # 4
                Paragraph(row["expense_status"], _status_style(row["expense_status"])),              # 5
                Paragraph(row["paid_date"],                         C_STYLE),                        # 6
                Paragraph(row["payment_mode"],                      C_STYLE),                        # 7
                Paragraph(f"Rs.{row['amount']:,.2f}",               amt_sty),                        # 8
                Paragraph(f"Rs.{row['total_amount']:,.2f}",         amt_sty),                        # 9
                Paragraph(f"Rs.{row['total_paid']:,.2f}",           pay_sty),                        # 10
                Paragraph(f"Rs.{row['balance']:,.2f}",              bal_sty),                        # 11
            ])
            row_styles += [
                ("BACKGROUND", (0, ri), (-1, ri), bg),
                ("LINEBELOW",  (0, ri), (-1, ri), 0.4, RULE),
            ]
            ri += 1
            total_item_amt += row["amount"]
            total_exp_amt  += row["total_amount"]
            total_paid     += row["total_paid"]
            total_bal      += row["balance"]
 
        # ── Grand-total footer row — 11 cells ─────────────────────
        table_data.append([
            Paragraph("GRAND TOTAL",                              TOT_L),   # 1
            Paragraph("",                                          TOT_L),   # 2
            Paragraph("",                                          TOT_L),   # 3
            Paragraph("",                                          TOT_L),   # 4
            Paragraph(f"{len(rows)} items",                        TOT_L),   # 5
            Paragraph("",                                          TOT_L),   # 6
            Paragraph("",                                          TOT_L),   # 7
            Paragraph(f"Rs.{total_item_amt:,.2f}",                 TOT_R),   # 8
            Paragraph(f"Rs.{total_exp_amt:,.2f}",                  TOT_R),   # 9
            Paragraph(f"Rs.{total_paid:,.2f}",                     TOT_R),   # 10
            Paragraph(f"Rs.{total_bal:,.2f}",                      TOT_R),   # 11
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
 
        # ── KPI summary cards (4 cards) ───────────────────────────
        collection_rate = (total_paid / total_item_amt * 100) if total_item_amt else 0
        kpi_data = [[
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Items</font><br/>"
                f"<font size='13' color='#0D1B2A'><b>{len(rows)}</b></font>", C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Item Amount</font><br/>"
                f"<font size='11' color='#0D1B2A'><b>Rs.{total_item_amt:,.2f}</b></font>", C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Total Paid</font><br/>"
                f"<font size='11' color='#1B5E20'><b>Rs.{total_paid:,.2f}</b></font>", C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Outstanding Balance</font><br/>"
                f"<font size='11' color='#B71C1C'><b>Rs.{total_bal:,.2f}</b></font>", C_STYLE),
            Paragraph(
                f"<font size='7' color='#607D8B'>Collection Rate</font><br/>"
                f"<font size='11' color='#1565C0'><b>{collection_rate:.1f}%</b></font>", C_STYLE),
        ]]
        # ── FIX: 5 KPI cells → colWidths=[W/5]*5 ─────────────────
        kpi_tbl = Table(kpi_data, colWidths=[W / 5] * 5)
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
 
        canv.setFont("Helvetica-Bold", 15)
        canv.setFillColor(WHITE)
        canv.drawString(5.3*cm, ph - 1.25*cm, "EXPENSE REPORT")
 
        canv.setFont("Helvetica", 8)
        canv.setFillColor(colors.HexColor("#B0BEC5"))
        canv.drawString(5.3*cm, ph - 1.75*cm, "Financial Summary  ·  All Expense Entries")
 
        canv.setFont("Helvetica", 8)
        canv.setFillColor(colors.HexColor("#90A4AE"))
        canv.drawRightString(pw - 0.6*cm, ph - 1.10*cm,
                             f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
        canv.drawRightString(pw - 0.6*cm, ph - 1.60*cm, f"Page {doc.page}")
 
        canv.setFillColor(ACCENT2)
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
 
    # ════════════════════════════════════════════════════════════════
    #  EXCEL EXPORT  (complete & corrected)
    # ════════════════════════════════════════════════════════════════
    def _excel(self, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Expense Report"
 
        # ── Colour helpers ────────────────────────────────────────
        C_NAVY    = "0D1B2A"
        C_ACCENT  = "1565C0"
        C_ACCENT2 = "FFA000"
        C_WHITE   = "FFFFFF"
        C_ALT     = "EEF2F7"
        C_LIGHT   = "F5F7FA"
        C_RED     = "B71C1C"
        C_GREEN   = "1B5E20"
        C_GREY    = "607D8B"
        C_MID     = "546E7A"
 
        def fill(hex_):  return PatternFill("solid", fgColor=hex_)
        def font(hex_, bold=False, sz=10): return Font(name="Arial", size=sz, bold=bold, color=hex_)
        def align(h="left", v="center", wrap=True):
            return Alignment(horizontal=h, vertical=v, wrap_text=wrap)
        def border_thin():
            s = Side(style="thin", color="CFD8DC")
            return Border(left=s, right=s, top=s, bottom=s)
        def border_medium():
            s = Side(style="medium", color=C_NAVY)
            return Border(left=s, right=s, top=s, bottom=s)
 
        # ══════════════════════════════════════════════════════════
        # ROW 1 — Company banner
        # ══════════════════════════════════════════════════════════
        ws.merge_cells("A1:K1")
        c = ws["A1"]
        c.value    = f"{COMPANY_NAME.upper()}  ·  EXPENSE REPORT"
        c.font     = font(C_WHITE, bold=True, sz=14)
        c.fill     = fill(C_NAVY)
        c.alignment= align("center")
        ws.row_dimensions[1].height = 28
 
        # ══════════════════════════════════════════════════════════
        # ROW 2 — Sub-title / generated date
        # ══════════════════════════════════════════════════════════
        ws.merge_cells("A2:K2")
        c = ws["A2"]
        c.value    = (f"Financial Summary  ·  All Expense Entries  ·  "
                      f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
        c.font     = font("B0BEC5", sz=9)
        c.fill     = fill(C_NAVY)
        c.alignment= align("center")
        ws.row_dimensions[2].height = 16
 
        # ══════════════════════════════════════════════════════════
        # ROW 3 — blank spacer
        # ══════════════════════════════════════════════════════════
        ws.row_dimensions[3].height = 6
        for col in range(1, 12):
            ws.cell(row=3, column=col).fill = fill(C_LIGHT)
 
        # ══════════════════════════════════════════════════════════
        # ROW 4 — KPI cards (merged pairs)
        # ══════════════════════════════════════════════════════════
        total_item_amt = sum(r["amount"]       for r in rows)
        total_exp_amt  = sum(r["total_amount"] for r in rows)
        total_paid     = sum(r["total_paid"]   for r in rows)
        total_bal      = sum(r["balance"]      for r in rows)
        rate = (total_paid / total_item_amt * 100) if total_item_amt else 0
 
        kpis = [
            ("Total Items",        str(len(rows)),              C_NAVY),
            ("Total Item Amount",  f"Rs.{total_item_amt:,.2f}", C_ACCENT),
            ("Total Paid",         f"Rs.{total_paid:,.2f}",     C_GREEN),
            ("Outstanding",        f"Rs.{total_bal:,.2f}",      C_RED),
            ("Collection Rate",    f"{rate:.1f}%",               C_ACCENT),
        ]
        # 5 KPI cards across 11 columns — columns A-B, C-D, E-F, G-H, I-J (K spare)
        kpi_cols = [(1,2), (3,4), (5,6), (7,8), (9,10)]
        ws.row_dimensions[4].height = 13
        ws.row_dimensions[5].height = 22
        ws.row_dimensions[6].height = 8
 
        for (sc, ec), (label, value, vc) in zip(kpi_cols, kpis):
            # label row
            lc = ws.cell(row=4, column=sc, value=label)
            lc.font      = font(C_GREY, sz=8)
            lc.fill      = fill(C_LIGHT)
            lc.alignment = align("center")
            ws.merge_cells(start_row=4, start_column=sc, end_row=4, end_column=ec)
            # value row
            vc_ = ws.cell(row=5, column=sc, value=value)
            vc_.font      = font(vc, bold=True, sz=12)
            vc_.fill      = fill(C_LIGHT)
            vc_.alignment = align("center")
            ws.merge_cells(start_row=5, start_column=sc, end_row=5, end_column=ec)
            # bottom border accent
            bc = ws.cell(row=6, column=sc)
            bc.fill = fill(C_LIGHT)
            ws.merge_cells(start_row=6, start_column=sc, end_row=6, end_column=ec)
 
        # draw box around KPI area
        for row_ in range(4, 7):
            for col_ in range(1, 12):
                ws.cell(row=row_, column=col_).border = border_thin()
 
        # ══════════════════════════════════════════════════════════
        # ROW 7 — spacer
        # ══════════════════════════════════════════════════════════
        ws.row_dimensions[7].height = 4
 
        # ══════════════════════════════════════════════════════════
        # ROW 8 — Column headers
        # ══════════════════════════════════════════════════════════
        HEADERS = [
            "Company Name",         # A  col 1
            "Product Name",         # B  col 2
            "Invoice Number",       # C  col 3
            "Invoice Date",         # D  col 4
            "Status",               # E  col 5
            "Paid Date",            # F  col 6
            "Payment Mode",         # G  col 7
            "Paid Amount",     # H  col 8
            "Invoice Amount",  # I  col 9
            "Paid",           # J  col 10
            "Balance ",        # K  col 11
        ]
        HDR_ROW = 8
        ws.row_dimensions[HDR_ROW].height = 22
        for ci, h in enumerate(HEADERS, 1):
            c = ws.cell(row=HDR_ROW, column=ci, value=h)
            c.font      = font(C_WHITE, bold=True, sz=9)
            c.fill      = fill(C_ACCENT)
            c.alignment = align("center")
            c.border    = border_thin()
 
        # ══════════════════════════════════════════════════════════
        # ROWS 9+ — Data rows
        # ══════════════════════════════════════════════════════════
        DATA_START = HDR_ROW + 1
        money_fmt  = '#,##0.00'
 
        STATUS_COLOURS = {
            "PAID":    ("1B5E20", "E8F5E9"),
            "PENDING": ("E65100", "FFF3E0"),
            "OVERDUE": ("B71C1C", "FFEBEE"),
        }
 
        for ri, row in enumerate(rows):
            r = DATA_START + ri
            bg = C_ALT if ri % 2 == 0 else C_WHITE
            ws.row_dimensions[r].height = 18
 
            def wc(col, val, *, h="left", bold=False, fmt=None, fcolor=None):
                cell = ws.cell(row=r, column=col, value=val)
                cell.font      = font(fcolor or C_NAVY, bold=bold, sz=9)
                cell.fill      = fill(bg)
                cell.alignment = align(h)
                cell.border    = border_thin()
                if fmt:
                    cell.number_format = fmt
                return cell
 
            wc(1,  row["company_name"],  bold=True)                    # A Company
            wc(2,  row["product_name"])                                 # B Product
            wc(3,  row["invoice_number"])                               # C Invoice No
            wc(4,  row["invoice_date"])                                 # D Invoice Date
            # E Status — coloured text
            st_fc, st_bg = STATUS_COLOURS.get(row["expense_status"], (C_MID, bg))
            sc = ws.cell(row=r, column=5, value=row["expense_status"])
            sc.font      = font(st_fc, bold=True, sz=9)
            sc.fill      = fill(st_bg)
            sc.alignment = align("center")
            sc.border    = border_thin()
 
            wc(6,  row["paid_date"])                                    # F Paid Date
            wc(7,  row["payment_mode"], h="center")                     # G Payment Mode
            wc(8,  row["amount"],        h="right", fmt=money_fmt)      # H Item Total
            wc(9,  row["total_amount"],  h="right", fmt=money_fmt)      # I Expense Total
            wc(10, row["total_paid"],    h="right", fmt=money_fmt,
               fcolor=C_MID)                                            # J Paid
            bal_color = C_RED if row["balance"] > 0 else C_GREEN
            wc(11, row["balance"],       h="right", fmt=money_fmt,
               bold=True, fcolor=bal_color)                             # K Balance
 
        # ══════════════════════════════════════════════════════════
        # Grand Total row
        # ══════════════════════════════════════════════════════════
        TOTAL_ROW = DATA_START + len(rows)
        ws.row_dimensions[TOTAL_ROW].height = 20
 
        def tc(col, val, *, h="left", fmt=None):
            c = ws.cell(row=TOTAL_ROW, column=col, value=val)
            c.font      = font(C_WHITE, bold=True, sz=9)
            c.fill      = fill(C_NAVY)
            c.alignment = align(h)
            c.border    = border_medium()
            if fmt:
                c.number_format = fmt
            return c
 
        tc(1,  "GRAND TOTAL")
        tc(2,  "")
        tc(3,  "")
        tc(4,  "")
        tc(5,  f"{len(rows)} items", h="center")
        tc(6,  "")
        tc(7,  "")
        tc(8,  total_item_amt, h="right", fmt=money_fmt)
        tc(9,  total_exp_amt,  h="right", fmt=money_fmt)
        tc(10, total_paid,     h="right", fmt=money_fmt)
        tc(11, total_bal,      h="right", fmt=money_fmt)
 
        # ── Use Excel SUM formulas instead of hardcoded Python totals ──
        fr, lr = DATA_START, DATA_START + len(rows) - 1
        if rows:
            for col, letter in [(8, "H"), (9, "I"), (10, "J"), (11, "K")]:
                ws.cell(row=TOTAL_ROW, column=col).value = (
                    f"=SUM({letter}{fr}:{letter}{lr})"
                )
 
        # ══════════════════════════════════════════════════════════
        # Column widths
        # ══════════════════════════════════════════════════════════
        COL_WIDTHS = {
            "A": 22,   # Company Name
            "B": 18,   # Product Name
            "C": 16,   # Invoice Number
            "D": 13,   # Invoice Date
            "E": 11,   # Status
            "F": 13,   # Paid Date
            "G": 14,   # Payment Mode
            "H": 16,   # Item Total
            "I": 18,   # Expense Total
            "J": 16,   # Paid
            "K": 16,   # Balance
        }
        for col_letter, width in COL_WIDTHS.items():
            ws.column_dimensions[col_letter].width = width
 
        # ── Freeze panes below header ─────────────────────────────
        ws.freeze_panes = f"A{DATA_START}"
 
        # ── Auto-filter on header row ─────────────────────────────
        ws.auto_filter.ref = f"A{HDR_ROW}:K{HDR_ROW}"
 
        # ── Output ────────────────────────────────────────────────
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
 
        return HttpResponse(
            buf,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="arrolite_expense_report.xlsx"'},
        )