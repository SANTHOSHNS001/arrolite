from django.http import FileResponse, JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from app.forms.product.product_form import ProductCreateForm
from app.models.category.category_model import Category
from app.models.invoice_model.invoice_model import default_report_config
from app.models.product.product_model import Product
from app.models.product.quotation_model import Quotation
from app.models.sub_category.sub_category_model import SubCategory
from app.models.unit.unit_model import Unit
from django.contrib import messages
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle 
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, Image,KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
from django.contrib.staticfiles import finders
from django.db import transaction 
import json,os,io

from app.view.report_config.report_config import get_config


def get_static_asset_path(*parts):
    """Resolve static asset path using staticfiles finders, then STATIC_ROOT or BASE_DIR/static."""
    relative_path = os.path.join(*parts)
    resolved = finders.find(relative_path)
    if resolved:
        return resolved
    candidates = [
        os.path.join(settings.STATIC_ROOT, relative_path),
        os.path.join(settings.BASE_DIR, 'static', relative_path),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        f"Static asset not found: {relative_path}. "
        "Ensure the file exists in STATICFILES_DIRS or STATIC_ROOT, and run collectstatic if needed."
    )

class ProductListView(View):
    template="pages/product/product.html"
    def get(self, request):
        subcategories = SubCategory.active_objects.all()
        categories = Category.active_objects.all()
        Products = Product.active_objects.all()
        units = Unit.active_objects.all()
        context = {
            'subcategories': subcategories,
            'categories' :categories,
            'Products':Products,
            'units':units
        }
        return render(request, self.template, context)
    def post(self, request):
        form = ProductCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list')  # name of this view in your URLconf
        # If not valid, re-render with errors
        sub_categories = Product.active_objects.all()
        return render(request, self.template, {
            'form': form,
            'subcategories': sub_categories
        })
 
class ProductEditView(View):
   def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
   
        form = ProductCreateForm(request.POST, instance=product)
        if form.is_valid():
            form.save() 
            return JsonResponse({
                'success': True,
                'message': 'Product updated successfully.',
                'data': {}
                }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)   
    
class ProductDelete(View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        try:
            with transaction.atomic():
                product.delete(user=request.user)  # soft delete using your CustomBase method
            return JsonResponse({
                'success': True,
                'message': 'Product deleted successfully.'
            }, status=200)

        except ValueError as e:
            # Raised when there are related non-deleted objects
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"An unexpected error occurred: {str(e)}"
            }, status=500)
                
 

class QuotationReportPdfView(View):
    def __init__(self, **kwargs):
        self.company_name = "ARROLITE"
        super().__init__(**kwargs)

    # ── POST ─────────────────────────────────────────────────────────────────
    def post(self, request):
        try:
            data        = json.loads(request.body)
            document_id = data.get("document_id")
            qns         = Quotation.active_objects.get(id=document_id)
            data        = []
            for qs in qns.items.all():
                data.append({
                    "product":     qs.product.name,
                    "quantity":    qs.quantity,
                    "unit_price":  float(qs.product.price),
                    "total_cost":  round(qs.unit_cost, 2),
                    "unit":        qs.unit or "-",
                    "description": qs.description or '',   # ✅ fixed typo
                })

            if not data:
                return JsonResponse({"error": "No data found"}, status=404)

            buf = self.download_pdf_report(qns, data)
            return FileResponse(
                buf,
                as_attachment=True,
                filename=f"{qns.invoice_number}.pdf",
                content_type="application/pdf"
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    # ── HEADER ───────────────────────────────────────────────────────────────
    def header(self, canvas, doc, quotation):
        canvas.saveState()

        # ✅ Only fonts that actually exist on your disk
        font_montserrat  = get_static_asset_path('fonts', 'montserrat', 'Montserrat-Black.ttf')
        font_gotham_bold = get_static_asset_path('fonts', 'montserrat', 'Gotham-Bold.ttf')   # big "hello"
        font_gotham_bld2 = get_static_asset_path('fonts', 'montserrat', 'GothamBold.ttf')   # labels / numbers
        font_gotham_book = get_static_asset_path('fonts', 'montserrat', 'GothamBook.ttf')   # subtitle / address

        pdfmetrics.registerFont(TTFont("Montserrat-Black", font_montserrat))
        pdfmetrics.registerFont(TTFont("Gotham-Bold",      font_gotham_bold))  # ✅ correct file
        pdfmetrics.registerFont(TTFont("GothamBold",       font_gotham_bld2))  # ✅ correct file
        pdfmetrics.registerFont(TTFont("GothamBook",       font_gotham_book))  # ✅ replaces missing GothamLight

        # ── Paragraph styles ─────────────────────────────────────────────────
        title_style = ParagraphStyle(
            "title",
            fontName="Gotham-Bold",     # ✅ big red "hello"
            fontSize=90,
            textColor=colors.red,
            leading=87,
        )
        subtitle_style = ParagraphStyle(
            "subtitle",
            fontName="GothamBook",      # ✅ "this is your quotation"
            fontSize=23,
            textColor=colors.black,
            backColor=colors.white,
            leading=30,
        )
        label_style = ParagraphStyle(
            "label",
            fontName="GothamBold",
            fontSize=8,
            textColor=colors.black,
        )
        value_style = ParagraphStyle(
            "value",
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.red,
        )
        address_style = ParagraphStyle(
            "addr",
            fontName="GothamBook",      # ✅ GothamBook for address
            fontSize=11,
            textColor=colors.black,
        )
        number_style = ParagraphStyle(
            "number",
            fontName="GothamBold",
            fontSize=11,
            textColor=colors.black,
        )

        # ── Left block: "hello" + subtitle ───────────────────────────────────
        hello    = Paragraph("<b>hello</b>", title_style)
        subtitle = Paragraph(
            'this is your <font color="red"><b>quotation</b></font>',
            subtitle_style
        )
        care = Paragraph(
            '<b>Customer care:</b> <font color="red"><b>+65 8193 0246</b></font>',
            number_style
        )

        left_block = Table([[hello], [subtitle]], colWidths=[12 * cm], style=[
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), -12),
        ])

        # ── Right block: logo + address + care ───────────────────────────────
        logo_path = get_static_asset_path('img', 'logos', 'LOGO.png')
        logo      = Image(logo_path, width=8.3 * cm, height=1.4 * cm)
        address   = Paragraph(
            "#01-21 Centrum Square 320 Serangoon Rd, Singapore 218108",
            address_style
        )

        right_block = Table([[logo], [address], [care]], colWidths=[10 * cm], style=[
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ])

        # ── Top row ──────────────────────────────────────────────────────────
        top_row = Table([[left_block, right_block]], colWidths=[11 * cm, 10 * cm], style=[
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ])

        # ── Info tables ──────────────────────────────────────────────────────
        def make_info_table(data):
            rows = []
            for label, value in data:
                rows.append([Paragraph(label, label_style)])
                rows.append([Paragraph(value, value_style)])
            return Table(rows, colWidths=[8.5 * cm], style=[
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])

        invoice_table = make_info_table([
            ("invoice no.", f"{quotation.invoice_number}"),
            ("date", quotation.request_date.strftime('%d %B %Y').upper()),
        ])
        contact_table = make_info_table([
            ("contact", "+65 8 54321 92"),
            ("email",   "hello@arrolitesg.com"),
        ])

        info_row = Table([[invoice_table, contact_table]], colWidths=[11 * cm, 10 * cm], style=[
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ])

        # ── Combine & draw ───────────────────────────────────────────────────
        full_header = Table(
            [[top_row], [info_row]],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING",  (0, 1), (0, 1),   0),
            ]
        )

        w, h = full_header.wrap(doc.width, doc.topMargin)
        full_header.drawOn(canvas, doc.leftMargin, doc.height + doc.bottomMargin - h)
        canvas.restoreState()

    # ── FOOTER ───────────────────────────────────────────────────────────────
    def footer(self, canvas, doc, quotation, quotationitems):
        canvas.saveState()

        # === Calculate Totals ===
        total           = sum(item["total_cost"] for item in quotationitems)
        discount        = quotation.discount or 0
        discount_amount = total * discount / 100
        grand_total     = total - discount_amount

        # === Styles ===
        for_style         = ParagraphStyle("ForLabel",    fontName="Helvetica-Bold", fontSize=10, textColor=colors.red)
        company_style     = ParagraphStyle("CompanyName", fontName="Helvetica-Bold", fontSize=12, textColor=colors.HexColor("#7B6F6F"))
        address_style     = ParagraphStyle("Address",     fontName="Helvetica",      fontSize=10, textColor=colors.HexColor("#666666"), leading=10)
        total_label_style = ParagraphStyle("TotalLabel",  fontName="Helvetica-Bold", fontSize=9,  textColor=colors.whitesmoke)
        total_value_style = ParagraphStyle("TotalValue",  fontName="Helvetica-Bold", fontSize=12, textColor=colors.whitesmoke, alignment=2)

        # === FOR block (left) ===
        left_cell = [
            Paragraph("for", for_style),
            Paragraph(f"{quotation.customer.name}", company_style),
            Spacer(1, 5),
            Paragraph(f"{quotation.customer.address}", address_style),
        ]

        # === TOTAL block (right) ===
        right_cell = [
            Paragraph("total", total_label_style),
            Paragraph(f"${grand_total:,.2f}", total_value_style),
        ]

        summary_table = Table(
            [[left_cell, right_cell]],
            colWidths=[13.2 * cm, 6.3 * cm],
            style=[
                ("BACKGROUND",    (0, 0), (0, 0), colors.whitesmoke),
                ("BACKGROUND",    (1, 0), (1, 0), colors.HexColor("#231f20")),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 12),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
                ("TOPPADDING",    (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ],
        )

        w, h = summary_table.wrap(doc.width, doc.bottomMargin)
        summary_table.drawOn(canvas, doc.leftMargin, 6 * cm)

        # "thank you!"
        canvas.setFont("Helvetica-Bold", 40)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin, 4 * cm, "thank you!")

        # Grey payment strip background
        canvas.setFillColorRGB(0.95, 0.95, 0.95)
        canvas.rect(
            doc.leftMargin - 0.5 * cm, 0.9 * cm,
            doc.width + 1 * cm, 2.1 * cm,
            stroke=0, fill=1
        )

        # OCBC logo
        ocbc_img_path = get_static_asset_path('ac-imgs', 'ocbc_logo.png')
        canvas.drawImage(ocbc_img_path, doc.leftMargin, 1.3 * cm,
                         width=1.3 * cm, height=1.3 * cm, mask='auto')

        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin + 1.5 * cm, 2.3 * cm, "bank transfer")

        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.black)
        canvas.drawString(doc.leftMargin + 1.5 * cm, 1.9 * cm, "current AC")
        canvas.drawString(doc.leftMargin + 1.5 * cm, 1.5 * cm, "595-28881-2001")

        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin + 5 * cm, 2.0 * cm, "or")

        # PayNow logo
        paynow_img_path = get_static_asset_path('ac-imgs', 'paynow.png')
        canvas.drawImage(paynow_img_path, doc.leftMargin + 7 * cm, 1.5 * cm,
                         width=1.3 * cm, height=1 * cm, mask='auto')

        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(colors.black)
        canvas.drawString(doc.leftMargin + 8.7 * cm, 2.3 * cm, "uen")
        canvas.drawString(doc.leftMargin + 8.7 * cm, 2.0 * cm, "202313034H")

        canvas.setFont("Helvetica", 6)
        canvas.drawString(doc.leftMargin + 8.7 * cm, 1.7 * cm, "ARROLITE PTE. LTD.")

        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin + 12.2 * cm, 2.0 * cm, "or")

        # Scan Me
        scan_img_path = get_static_asset_path('ac-imgs', 'scan_me.png')
        canvas.drawImage(scan_img_path, doc.leftMargin + 14 * cm, 1.4 * cm,
                         width=2 * cm, height=1.6 * cm, mask='auto')

        # QR code
        qr_img_path = get_static_asset_path('ac-imgs', 'qr_img.jpeg')
        canvas.drawImage(qr_img_path, doc.leftMargin + 16 * cm, 0.6 * cm,
                         width=3 * cm, height=3 * cm, mask='auto')

        # Disclaimer
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.red)
        canvas.drawString(
            doc.leftMargin, 0.6 * cm,
            "This is a computer generated and no signature is required."
        )

        canvas.restoreState()

    # ── DOWNLOAD PDF ─────────────────────────────────────────────────────────
    def download_pdf_report(self, quotation, quotationitems):
        buffer = io.BytesIO()

        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1 * cm,
            rightMargin=1 * cm,
            topMargin=0.7 * cm,
            bottomMargin=3 * cm,
        )

        # ── Config flags ─────────────────────────────────────────────────────
        config                = get_config().label or default_report_config()
        show_design_note      = config.get("show_design_note",      True)
        show_deposit_note     = config.get("show_deposit_note",     True)
        show_discount_product = config.get("show_discount_product", True)
        design_note_text      = config.get("design_note",  "DESIGN PROVIDED BY YOU")
        deposit_note_text     = config.get("deposit_note", "50% deposit required")

        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')

        def header_with_data(canvas, doc):
            self.header(canvas, doc, quotation)

        def footer_with_data(canvas, doc):
            self.footer(canvas, doc, quotation, quotationitems)

        doc.addPageTemplates([PageTemplate(
            id='quote',
            frames=frame,
            onPage=header_with_data,
            onPageEnd=footer_with_data,
        )])

        # ── Styles ───────────────────────────────────────────────────────────
        normal_style   = ParagraphStyle(
            "normal",
            fontName="Helvetica",
            fontSize=8,
            leading=14,
            textColor=colors.HexColor("#74666a"),
        )
        header_style   = ParagraphStyle(
            "header_style",
            fontName="Helvetica-Bold",
            fontSize=7,
            textColor=colors.white,
            spaceAfter=6,
        )
        for_desc_style = ParagraphStyle(
            "for_desc",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.HexColor("#74666a"),
        )

        # ── Body table ───────────────────────────────────────────────────────
        table_data = [[
            Paragraph("<b>description</b>", header_style),
            Paragraph("<b>unit price</b>",  header_style),
            Paragraph("<b>quantity</b>",    header_style),
            Paragraph("<b>price</b>",       header_style),
        ]]

        for item in quotationitems:
            product_text = (
                f"<b>{item['product']}</b><br/>"
                f'<font size="7" color="#9e9e9e">- {item.get("description", "")}</font>'
            )
            table_data.append([
                Paragraph(product_text,            normal_style),
                Paragraph(f"${item['unit_price']}", normal_style),
                Paragraph(f"{item['quantity']}",    normal_style),
                Paragraph(f"${item['total_cost']}", normal_style),
            ])

        body_table = Table(
            table_data,
            colWidths=[10 * cm, 3 * cm, 3 * cm, 3 * cm],
            repeatRows=1,
        )
        body_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.black),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("ALIGN",      (1, 1), (-1, -1), "RIGHT"),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE",   (0, 1), (-1, -1), 10),
            ("GRID",       (0, 0), (-1, -1), 1, colors.white),
        ]))

        # ── Totals ───────────────────────────────────────────────────────────
        total           = sum(item["total_cost"] for item in quotationitems)
        discount        = quotation.discount or 0
        discount_amount = total * discount / 100
        grand_total     = total - discount_amount

        # ── Build elements ───────────────────────────────────────────────────
        elements = [
            Spacer(1, 6 * cm),
            body_table,
            Spacer(1, 0.5 * cm),
        ]

        # ✅ FIXED: create table first, then append separately
        if show_discount_product:
            total_table = Table([
                [f"Discount ({discount}%)", f"-${discount_amount:.2f}"],
            ], colWidths=[14 * cm, 1 * cm], style=[
                ("ALIGN",        (0, 0), (0, -1), "LEFT"),
                ("ALIGN",        (1, 0), (1, -1), "RIGHT"),
                ("FONTSIZE",     (0, 0), (-1, -1), 8),
                ("TEXTCOLOR",    (0, 0), (-1, -1), colors.HexColor("#74666a")),
                ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ])
            elements.append(total_table)

        if show_design_note:
            desc_table = Table(
                [[[Paragraph(f"*{design_note_text}", for_desc_style)]]],
                style=[("FONTSIZE", (0, 0), (-1, -1), 8)]
            )
            elements.append(desc_table)

        if show_deposit_note:
            desc_table2 = Table(
                [[[Paragraph(f"- {deposit_note_text}", for_desc_style)]]],
                style=[("FONTSIZE", (0, 0), (-1, -1), 8)]
            )
            elements.append(desc_table2)

        doc.build(elements)
        buffer.seek(0)
        return buffer