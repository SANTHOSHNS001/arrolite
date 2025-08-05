import datetime
from django.http import FileResponse, JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from app import models
from app.forms.product.product_form import ProductCreateForm
from app.models.category.category_model import Category
from app.models.customer_model.customer_model import CustomUser, Customer
from app.models.product.product_model import Product
from app.models.product.quotation_model import Quotation, QuotationItem
from app.models.sub_category.sub_category_model import SubCategory
from app.models.unit.unit_model import Unit
from django.contrib import messages
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, Image,KeepTogether
)
import io

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
            updated_category = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Product updated successfully.',
                'data': {}
                }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)        
                
 
    

import os
from django.conf import settings
import json
class QuotationReportPdfView(View):
    def __init__(self, **kwargs):
        self.company_name = "ARROLITE"
        super().__init__(**kwargs)
    def post(self, request):
        try:      
            # discount = request.POST.get('discount')
            # qns = Quotation.active_objects.get(id=17,approver_status = "approved")
            data = json.loads(request.body)
           
            document_id = data.get("document_id")
            print("get user-id",type(document_id),document_id)
            qns = Quotation.active_objects.get(id=document_id)
            print("jsdhjsdj",qns)
            data = []
            for qs in qns.items.all():
                data.append({
                    "product": qs.product.name,
                    "quantity": qs.quantity,
                    "unit_price" :float(qs.product.price),
                    "total_cost" : round(qs.unit_cost, 2),
                    "unit": qs.unit or "-",  # Default to dash if None
                    "descriptioan":qs.description or '',    
                })
       
            if not data:
                return JsonResponse({"error": "No data found"}, status=404)

            buf = self.download_pdf_report(qns,data)
            return FileResponse(buf, as_attachment=True, filename=f"{qns.invoice_number}.pdf", content_type="application/pdf")

        except Exception as e:
            print(f"{e}")
            return JsonResponse({"error": str(e)}, status=400) 
 
    def header(self, canvas, doc,quotation):
        canvas.saveState()
      
        title_style = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=90, textColor=colors.red, leading=80)
        subtitle_style = ParagraphStyle("subtitle", fontName="Helvetica", fontSize=20, textColor=colors.black, backColor=colors.white)
        label_style = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=10, textColor=colors.black)
        value_style = ParagraphStyle("value", fontName="Helvetica", fontSize=12, textColor=colors.red)
        address_style = ParagraphStyle("addr", fontName="Helvetica", fontSize=11, textColor=colors.black)
        # Left Block
        hello = Paragraph("<b>hello</b>", title_style)
        subtitle = Paragraph('this is your <font color="red"><b>quotation</b></font>', subtitle_style)
        left_block = Table([[hello], [subtitle]], colWidths=[10 * cm], style=[
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), -4),
        ])

        # Right Block
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logos', 'arrolite.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=6 * cm, height=1.5 * cm)
        else:
            logo = Paragraph("<b>ARROLITE</b>", title_style)

        address = Paragraph("#01-21 Centrum Square 320 Serangoon Rd, Singapore 218108", address_style)
        right_block = Table([[logo], [address]], colWidths=[9 * cm], style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ])

        # Combined Header
        top_table = Table([[left_block, right_block]], colWidths=[10 * cm, 9.5 * cm], style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ])
        w, h = top_table.wrap(doc.width, doc.topMargin)
        top_table.drawOn(canvas, doc.leftMargin, doc.height + doc.bottomMargin - h)

        # Info Tables
        def make_info_table(data):
            return Table(
                [[Paragraph(label, label_style), Paragraph(value, value_style)] for label, value in data],
                colWidths=[3 * cm, 6 * cm],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )

        invoice_table = make_info_table([
            ("invoice no.", f"{quotation.invoice_number}"),
           ("date", f"{quotation.request_date.strftime('%d-%m-%Y')}"),
        ])

        contact_table = make_info_table([
            ("contact", "+65 8 54321 92"),
            ("email", "hello@arrolitesg.com"),
        ])

        bottom_info = Table([[invoice_table, contact_table]], colWidths=[9 * cm, 9.5 * cm], style=[
            ("TOPPADDING", (0, 0), (-1, -1), 10),
        ])

        w2, h2 = bottom_info.wrap(doc.width, doc.bottomMargin)
        bottom_info.drawOn(canvas, doc.leftMargin, doc.height + doc.bottomMargin - h - h2)

        canvas.restoreState()

    def footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 40)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin, 1.8 * cm, "thank you!")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(doc.leftMargin, 1.3 * cm, "This is a computer generated and no signature is required.")
        canvas.restoreState()

    def download_pdf_report(self,quotation,quotationitems):
        buffer = io.BytesIO()

        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1 * cm,
            rightMargin=1 * cm,
            topMargin=1 * cm,
            bottomMargin=3 * cm,
        )

        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
        def header_with_data(canvas, doc):
            self.header(canvas, doc, quotation)
        doc.addPageTemplates([PageTemplate(id='quote', frames=frame, onPage=header_with_data, onPageEnd=self.footer)])

        # Styles
        normal_style = ParagraphStyle("normal", fontName="Helvetica", fontSize=10, leading=14)
        header_style = ParagraphStyle("header_style", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white, spaceAfter=6)
        total_style = ParagraphStyle("total", fontName="Helvetica-Bold", fontSize=12, alignment=2)

        # Sample data
        body_data =  quotationitems

        table_data = [[
            Paragraph("<b>description</b>", header_style),
            Paragraph("<b>unit price</b>", header_style),
            Paragraph("<b>quantity</b>", header_style),
            Paragraph("<b>price</b>", header_style),
        ]]

        for item in body_data:
            table_data.append([
                Paragraph(item["product"], normal_style),
                Paragraph(f"${item['unit_price']}", normal_style),
                Paragraph(f"{item['quantity']}", normal_style),
                Paragraph(f"${item['total_cost']}", normal_style),
            ])
        print(f"total table{table_data}")
        body_table = Table(table_data, colWidths=[10 * cm, 3 * cm, 3 * cm, 3 * cm], repeatRows=1)
        body_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.black),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 1, colors.white),
        ]))

        total = sum(item["total_cost"] for item in quotationitems)
        discount = quotation.discount or 0
        discount_amount = total * discount / 100
        grand_total = total - discount_amount

        total_table = Table([
            
            [f"Discount ({discount}%)", f"-${discount_amount:.2f}"],
           
        ], colWidths=[13 * cm, 4.5 * cm], style=[
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ])

        # FOR / TOTAL block
        for_label_style = ParagraphStyle("for_label", fontName="Helvetica-Bold", fontSize=9, textColor=colors.red)
        for_name_style = ParagraphStyle("for_name", fontName="Helvetica-Bold", fontSize=12, textColor=colors.black)
        for_address_style = ParagraphStyle("for_address", fontName="Helvetica", fontSize=10, textColor=colors.gray)
        total_label_style = ParagraphStyle("total_label", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)
        total_value_style = ParagraphStyle("total_value", fontName="Helvetica-Bold", fontSize=12, textColor=colors.white, alignment=2)

        for_section = [
            Paragraph("for", for_label_style),
            Paragraph("HN CONSTRUCTION PTE LTD", for_name_style),
            Paragraph("39 Woodlands close, MEGA@woodlands #08-84<br/>Singapore 737856", for_address_style)
        ]
        total_section = [
            Paragraph("total", total_label_style),
            Paragraph(f"${grand_total:,.2f}", total_value_style)
        ]
        summary_table = Table([
            [for_section, total_section]
        ], colWidths=[13.2 * cm, 6.3 * cm], style=[
            ("BACKGROUND", (0, 0), (0, 0), colors.whitesmoke),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#231f20")),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])

        elements = [
            Spacer(1, 6 * cm),
            body_table,
            Spacer(1, 0.5 * cm),
            KeepTogether(total_table),
            Spacer(1, 1 * cm),
            KeepTogether(summary_table),
        ]

        doc.build(elements)
        buffer.seek(0)
        return buffer
 
 
    # def download_pdf_report(self, data, invoice_number, request_date):
    #     buffer = io.BytesIO()
    #     doc = BaseDocTemplate(
    #         buffer,
    #         pagesize=A4,
    #         leftMargin=1 * cm,
    #         rightMargin=1 * cm,
    #         topMargin=1 * cm,
    #         bottomMargin=1.5 * cm
    #     )
    #     styles = getSampleStyleSheet()
    #     elements = []
    #     # Title and subtitle
    #     title_style = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=38, textColor=colors.red)
    #     subtitle_style = ParagraphStyle("subtitle", fontName="Helvetica", fontSize=14, textColor=colors.black)

    #     title = Paragraph("hello", title_style)
    #     subtitle = Paragraph("this is your <b><font color='red'>quotation</font></b>", subtitle_style)
    #     elements.append(Table([[title], [subtitle]], colWidths=[doc.width]))
    #     elements.append(Spacer(1, 0.3 * cm))

    #     # Invoice and contact info
    #     left_info = [
    #         ["<b>Invoice No.</b>", f"<font color='red'>{invoice_number}</font>"],
    #         ["<b>Date</b>", f"<font color='red'>{request_date}</font>"]
    #     ]
    #     right_info = [
    #         ["<b>Contact</b>", "<font color='red'>+65 8 54321 92</font>"],
    #         ["<b>Email</b>", "<font color='red'>hello@arrolitesg.com</font>"]
    #     ]

    #     def format_table(data):
    #         return Table(data, colWidths=[3.5 * cm, 6 * cm], hAlign="LEFT", style=[
    #             ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    #             ("FONTSIZE", (0, 0), (-1, -1), 10),
    #             ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    #         ])

    #     elements.append(
    #         Table(
    #             [[format_table(left_info), format_table(right_info)]],
    #             colWidths=[doc.width / 2, doc.width / 2],
    #             style=[("VALIGN", (0, 0), (-1, -1), "TOP")]
    #         )
    #     )
    #     elements.append(Spacer(1, 0.6 * cm))

    #     # Table headers
    #     table_header = ["description", "unit price", "quantity", "price"]
    #     table_data = [table_header]

    #     wrap_style = ParagraphStyle("wrap", fontName="Helvetica", fontSize=9, leading=11)

    #     # Add table rows from data
    #     for row in data:
    #         try:
    #             desc = Paragraph(
    #                 f"<b>{row.get('product', '')}</b><br/>- Hoarding installation<br/>- with sticker print with matte lamination & installation",
    #                 wrap_style
    #             )
    #             unit_price = "$2730"
    #             qty = str(row.get("quantity", "0"))
    #             total_price = "$2730.00"

    #             table_row = [desc, unit_price, qty, total_price]

    #             if len(table_row) != 4:
    #                 raise ValueError(f"Invalid row length: {table_row}")

    #             table_data.append(table_row)
    #         except Exception as e:
    #             print(f"Skipping row due to error: {e}")

    #     # Optional discount row
    #     discount_row = [Paragraph("<b>Discount</b>", wrap_style), "", "", "-$230.00"]
    #     table_data.append(discount_row)

    #     # Final column widths
    #     col_widths = [doc.width * 0.5, doc.width * 0.2, doc.width * 0.15, doc.width * 0.15]

    #     # Table with styling
    #     try:
    #         tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    #         tbl.setStyle(TableStyle([
    #             ("BACKGROUND", (0, 0), (-1, 0), colors.black),
    #             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    #             ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    #             ("VALIGN", (0, 0), (-1, -1), "TOP"),
    #             ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    #             ("FONTSIZE", (0, 0), (-1, -1), 9),
    #             ("GRID", (0, 0), (-1, -1), 0.25, colors.gray),
    #             ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    #         ]))
    #         elements.append(tbl)
    #     except Exception as e:
    #         elements.append(Paragraph(f"<b>Error creating table: {e}</b>", wrap_style))

    #     # Footer address
    #     elements.append(Spacer(1, 1 * cm))
    #     address = Paragraph("#01-21 Centrum Square 320 Serangoon Rd,<br/>Singapore 218108", wrap_style)
    #     elements.append(address)

    #     try:
    #         doc.build(elements)
    #     except Exception as e:
    #         print(f"PDF build failed: {e}")
    #         raise

    #     buffer.seek(0)
    #     return buffer

