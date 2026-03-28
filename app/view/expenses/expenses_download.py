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

from app.models.expenses.expenses_model import Expenses


class ExpenseExportView(View):
    def post(self, request):
        export_type   = request.POST.get("export_type", "pdf")
        expenses_type = request.POST.get("expenses_type", "").strip()
        due_date_str  = request.POST.get("due_date", "").strip()

        filters = {}
        if expenses_type:
            filters["expenses_type_id"] = expenses_type
        if due_date_str:
            try:
                filters["due_date"] = datetime.strptime(due_date_str, "%Y-%m-%d").date()
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
            # ── child payment items ──
            payments = [
                {
                    "invoice_number": item.invoice_number or "—",
                    "due_date":       str(item.due_date) if item.due_date else "—",
                    "amount":         float(item.amount or 0),
                    "payment_mode":   (item.payment_mode or "—").upper(),
                    "description":    item.description or "—",
                }
                for item in exp.items.all()
            ]

            rows.append({
                "company_name":   exp.company_name  or "—",
                "product_name":   exp.product_name  or "—",
                "expenses_type":  exp.expenses_type.name if exp.expenses_type else "—",
                "expense_status": (exp.expense_status or "pending").upper(),
                "due_date":       str(exp.due_date) if exp.due_date else "—",
                "amount":         float(exp.amount or 0),
                "total_paid":     float(exp.total_paid() or 0),
                "balance":        float(exp.balance_amount() or 0),
                "payments":       payments,   # ← child rows
            })

        if export_type == "excel":
            return self._excel(rows)
        return self._pdf(rows)

     
    # ══════════════════════════════════════════════════════════════
    #  PDF
    # ══════════════════════════════════════════════════════════════
    def _pdf(self, rows):
        buf = io.BytesIO()

        doc = BaseDocTemplate(
            buf, pagesize=landscape(A4),
            leftMargin=1.2*cm, rightMargin=1.2*cm,
            topMargin=1.5*cm, bottomMargin=2*cm,
        )
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")

        def on_page(canv, doc):
            self._pdf_header(canv, doc)
            self._pdf_footer(canv, doc)

        doc.addPageTemplates([PageTemplate(id="base", frames=frame, onPage=on_page)])

        # ── styles ──
        h_style  = ParagraphStyle("h",  fontName="Helvetica-Bold", fontSize=7.5, textColor=colors.white)
        c_style  = ParagraphStyle("c",  fontName="Helvetica",      fontSize=8,   textColor=colors.HexColor("#333333"), leading=11)
        r_style  = ParagraphStyle("r",  fontName="Helvetica",      fontSize=8,   textColor=colors.HexColor("#333333"), leading=11, alignment=2)
        pm_style = ParagraphStyle("pm", fontName="Helvetica-Oblique", fontSize=7.5, textColor=colors.HexColor("#555555"), leading=10)
        pm_r     = ParagraphStyle("pr", fontName="Helvetica-Oblique", fontSize=7.5, textColor=colors.HexColor("#555555"), leading=10, alignment=2)
        pm_h     = ParagraphStyle("ph", fontName="Helvetica-Bold",    fontSize=7,   textColor=colors.HexColor("#777777"))

        col_w = [5*cm, 4.5*cm, 3*cm, 2.5*cm, 3*cm, 3.5*cm, 3.5*cm, 3.5*cm]

        # ── main header row ──
        headers = ["Company", "Product", "Type", "Status",
                "Invoice Date", "Total (₹)", "Paid (₹)", "Balance (₹)"]
        table_data  = [[Paragraph(h, h_style) for h in headers]]
        row_styles  = []   # extra per-row TableStyle commands

        total_amt = total_paid_sum = total_bal = 0
        data_row_index = 1   # track actual table row index (header = 0)

        for exp_idx, row in enumerate(rows):
            is_even  = (exp_idx % 2 == 0)
            bg_color = colors.white if is_even else colors.HexColor("#f5f5f5")

            bal_color = "#cc0000" if row["balance"] > 0 else "#2e7d32"
            bal_style = ParagraphStyle("bal", fontName="Helvetica-Bold", fontSize=8,
                                    textColor=colors.HexColor(bal_color), alignment=2)

            # ── parent expense row ──
            table_data.append([
                Paragraph(row["company_name"],  c_style),
                Paragraph(row["product_name"],  c_style),
                Paragraph(row["expenses_type"], c_style),
                Paragraph(row["expense_status"], c_style),
                Paragraph(row["due_date"],       c_style),
                Paragraph(f"₹{row['amount']:,.2f}",     r_style),
                Paragraph(f"₹{row['total_paid']:,.2f}", r_style),
                Paragraph(f"₹{row['balance']:,.2f}",    bal_style),
            ])
            row_styles.append(("BACKGROUND", (0, data_row_index), (-1, data_row_index), bg_color))
            row_styles.append(("FONTSIZE",   (0, data_row_index), (-1, data_row_index), 8))
            data_row_index += 1

            # ── child payment rows ──
            if row["payments"]:
                # sub-header
                table_data.append([
                    Paragraph("  ↳ Invoice No", pm_h),
                    Paragraph("Date",           pm_h),
                    Paragraph("Mode",           pm_h),
                    Paragraph("Description",    pm_h),
                    Paragraph("",              pm_h),
                    Paragraph("",              pm_h),
                    Paragraph("",              pm_h),
                    Paragraph("Amount (₹)",    pm_h),
                ])
                row_styles.append(("BACKGROUND", (0, data_row_index), (-1, data_row_index),
                                    colors.HexColor("#eeeeee")))
                row_styles.append(("TOPPADDING",    (0, data_row_index), (-1, data_row_index), 2))
                row_styles.append(("BOTTOMPADDING", (0, data_row_index), (-1, data_row_index), 2))
                data_row_index += 1

                for pmt in row["payments"]:
                    table_data.append([
                        Paragraph(f"  {pmt['invoice_number']}", pm_style),
                        Paragraph(pmt["due_date"],              pm_style),
                        Paragraph(pmt["payment_mode"],          pm_style),
                        Paragraph(pmt["description"],           pm_style),
                        Paragraph("", pm_style),
                        Paragraph("", pm_style),
                        Paragraph("", pm_style),
                        Paragraph(f"₹{pmt['amount']:,.2f}",    pm_r),
                    ])
                    row_styles.append(("BACKGROUND", (0, data_row_index), (-1, data_row_index),
                                        colors.HexColor("#fafafa")))
                    row_styles.append(("TOPPADDING",    (0, data_row_index), (-1, data_row_index), 2))
                    row_styles.append(("BOTTOMPADDING", (0, data_row_index), (-1, data_row_index), 3))
                    row_styles.append(("LINEBELOW", (0, data_row_index), (-1, data_row_index),
                                        0.3, colors.HexColor("#dddddd")))
                    data_row_index += 1

            # separator after each expense block
            row_styles.append(("LINEBELOW", (0, data_row_index - 1), (-1, data_row_index - 1),
                                1, colors.HexColor("#cccccc")))

            total_amt       += row["amount"]
            total_paid_sum  += row["total_paid"]
            total_bal       += row["balance"]

        # ── totals footer row ──
        tot_l = ParagraphStyle("tl", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)
        tot_r = ParagraphStyle("tr", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=2)
        table_data.append([
            Paragraph("TOTAL", tot_l),
            Paragraph("", tot_l),
            Paragraph("", tot_l),
            Paragraph("", tot_l),
            Paragraph(f"{len(rows)} expenses", tot_l),
            Paragraph(f"₹{total_amt:,.2f}",       tot_r),
            Paragraph(f"₹{total_paid_sum:,.2f}",   tot_r),
            Paragraph(f"₹{total_bal:,.2f}",        tot_r),
        ])
        row_styles.append(("BACKGROUND", (0, data_row_index), (-1, data_row_index),
                            colors.HexColor("#1a1a2e")))

        # ── build table ──
        base_style = [
            ("BACKGROUND",    (0, 0), (-1, 0),   colors.HexColor("#1a1a2e")),
            ("GRID",          (0, 0), (-1, -1),   0.3, colors.HexColor("#dddddd")),
            ("VALIGN",        (0, 0), (-1, -1),   "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, 0),    6),
            ("BOTTOMPADDING", (0, 0), (-1, 0),    6),
            ("LEFTPADDING",   (0, 0), (-1, -1),   5),
            ("RIGHTPADDING",  (0, 0), (-1, -1),   5),
        ] + row_styles

        body_table = Table(table_data, colWidths=col_w, repeatRows=1)
        body_table.setStyle(TableStyle(base_style))

        elements = [Spacer(1, 1.2*cm), body_table]
        doc.build(elements)
        buf.seek(0)

        return HttpResponse(
            buf,
            content_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="expenses_report.pdf"'}
        )
    def _pdf_header(self, canv, doc):
        canv.saveState()
        # Red accent bar
        canv.setFillColor(colors.HexColor("#c62828"))
        canv.rect(doc.leftMargin, doc.height + doc.bottomMargin + 0.3*cm,
                  doc.width, 0.35*cm, stroke=0, fill=1)

        canv.setFont("Helvetica-Bold", 16)
        canv.setFillColor(colors.HexColor("#1a1a2e"))
        canv.drawString(doc.leftMargin, doc.height + doc.bottomMargin + 0.8*cm, "Expense Report")

        canv.setFont("Helvetica", 9)
        canv.setFillColor(colors.HexColor("#555555"))
        canv.drawRightString(
            doc.width + doc.leftMargin,
            doc.height + doc.bottomMargin + 0.8*cm,
            f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
        )
        canv.restoreState()

    def _pdf_footer(self, canv, doc):
        canv.saveState()
        canv.setStrokeColor(colors.HexColor("#dddddd"))
        canv.setLineWidth(0.5)
        canv.line(doc.leftMargin, 1.5*cm, doc.width + doc.leftMargin, 1.5*cm)

        canv.setFont("Helvetica", 7.5)
        canv.setFillColor(colors.HexColor("#888888"))
        canv.drawString(doc.leftMargin, 1.0*cm, "This is a computer-generated report.")
        canv.drawRightString(
            doc.width + doc.leftMargin, 1.0*cm,
            f"Page {doc.page}"
        )
        canv.restoreState()

    # ══════════════════════════════════════════════════════════════
    #  EXCEL
    # ══════════════════════════════════════════════════════════════
    def _excel(self, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Expenses"

        DARK  = "1A1A2E"
        RED   = "C62828"
        LIGHT = "F5F5F5"
        WHITE = "FFFFFF"
        GREY  = "DDDDDD"
        SUB   = "EEEEEE"   # payment sub-row bg
        GREEN = "2E7D32"

        thin   = Side(style="thin",   color=GREY)
        medium = Side(style="medium", color=DARK)
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        col_widths = [22, 20, 15, 12, 14, 14, 14, 14]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # ── Title ──
        ws.merge_cells("A1:H1")
        c = ws["A1"]
        c.value     = "EXPENSE REPORT"
        c.font      = Font(name="Calibri", bold=True, size=16, color=WHITE)
        c.fill      = PatternFill("solid", fgColor=DARK)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 36

        ws.merge_cells("A2:H2")
        c = ws["A2"]
        c.value     = f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
        c.font      = Font(name="Calibri", italic=True, size=9, color="888888")
        c.fill      = PatternFill("solid", fgColor=LIGHT)
        c.alignment = Alignment(horizontal="right")
        ws.row_dimensions[2].height = 18

        # ── Column headers ──
        headers = ["Company", "Product", "Type", "Status",
                "Invoice Date", "Total (₹)", "Paid (₹)", "Balance (₹)"]
        for col_idx, header in enumerate(headers, 1):
            c = ws.cell(row=3, column=col_idx, value=header)
            c.font      = Font(name="Calibri", bold=True, size=10, color=WHITE)
            c.fill      = PatternFill("solid", fgColor=RED)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border    = border
        ws.row_dimensions[3].height = 22
        ws.freeze_panes = "A4"

        cur_row = 4
        total_amt = total_paid_sum = total_bal = 0

        for exp_idx, row in enumerate(rows):
            is_even = (exp_idx % 2 == 0)
            bg      = LIGHT if is_even else WHITE
            exp_fill = PatternFill("solid", fgColor=bg)

            # ── parent expense row ──
            values = [
                row["company_name"],
                row["product_name"],
                row["expenses_type"],
                row["expense_status"],
                row["due_date"],
                row["amount"],
                row["total_paid"],
                row["balance"],
            ]
            for col_idx, value in enumerate(values, 1):
                c        = ws.cell(row=cur_row, column=col_idx, value=value)
                c.font   = Font(name="Calibri", bold=True, size=9)
                c.fill   = exp_fill
                c.border = border
                c.alignment = Alignment(vertical="center",
                                        horizontal="right" if col_idx >= 6 else "left")
                if col_idx in (6, 7, 8):
                    c.number_format = '₹#,##0.00'
                if col_idx == 8 and isinstance(value, (int, float)):
                    c.font = Font(name="Calibri", bold=True, size=9,
                                color=(RED if value > 0 else GREEN))
            ws.row_dimensions[cur_row].height = 18
            cur_row += 1

            # ── payment sub-rows ──
            if row["payments"]:
                # sub-header
                sub_headers = ["  ↳ Invoice No", "Pay Date", "Mode",
                            "Description", "", "", "", "Amount (₹)"]
                sub_fill = PatternFill("solid", fgColor=SUB)
                for col_idx, sh in enumerate(sub_headers, 1):
                    c        = ws.cell(row=cur_row, column=col_idx, value=sh)
                    c.font   = Font(name="Calibri", bold=True, size=8, color="666666")
                    c.fill   = sub_fill
                    c.border = border
                    c.alignment = Alignment(vertical="center",
                                            horizontal="right" if col_idx == 8 else "left")
                ws.row_dimensions[cur_row].height = 15
                cur_row += 1

                pmt_fill = PatternFill("solid", fgColor="FAFAFA")
                for pmt in row["payments"]:
                    pmt_values = [
                        f"  {pmt['invoice_number']}",
                        pmt["due_date"],
                        pmt["payment_mode"],
                        pmt["description"],
                        "", "", "",
                        pmt["amount"],
                    ]
                    for col_idx, value in enumerate(pmt_values, 1):
                        c        = ws.cell(row=cur_row, column=col_idx, value=value)
                        c.font   = Font(name="Calibri", italic=True, size=8, color="555555")
                        c.fill   = pmt_fill
                        c.border = border
                        c.alignment = Alignment(vertical="center",
                                                horizontal="right" if col_idx == 8 else "left")
                        if col_idx == 8:
                            c.number_format = '₹#,##0.00'
                    ws.row_dimensions[cur_row].height = 15
                    cur_row += 1

            total_amt      += row["amount"]
            total_paid_sum += row["total_paid"]
            total_bal      += row["balance"]

        # ── Totals row ──
        tot_fill   = PatternFill("solid", fgColor=DARK)
        tot_border = Border(left=Side(style="medium", color=DARK),
                            right=Side(style="medium", color=DARK),
                            top=Side(style="medium", color=DARK),
                            bottom=Side(style="medium", color=DARK))
        tot_vals = ["TOTAL", "", "", "", f"{len(rows)} expenses",
                    total_amt, total_paid_sum, total_bal]
        for col_idx, value in enumerate(tot_vals, 1):
            c        = ws.cell(row=cur_row, column=col_idx, value=value)
            c.font   = Font(name="Calibri", bold=True, size=10, color=WHITE)
            c.fill   = tot_fill
            c.border = tot_border
            c.alignment = Alignment(vertical="center",
                                    horizontal="right" if col_idx >= 6 else "left")
            if col_idx in (6, 7, 8):
                c.number_format = '₹#,##0.00'
        ws.row_dimensions[cur_row].height = 22

        ws.auto_filter.ref = f"A3:H{cur_row - 1}"

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        return HttpResponse(
            buf,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="expenses_report.xlsx"'}
        )