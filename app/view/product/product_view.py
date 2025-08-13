from django.http import FileResponse, JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from app.forms.product.product_form import ProductCreateForm
from app.models.category.category_model import Category
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
import io
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings
import json

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
        print("Form Data,",request.POST)
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
from django.db import transaction     
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
    def post(self, request):
        try:      
            # discount = request.POST.get('discount')
            # qns = Quotation.active_objects.get(id=17,approver_status = "approved")
            data = json.loads(request.body)
           
            document_id = data.get("document_id")
    
            qns = Quotation.active_objects.get(id=document_id)
          
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
 
    def header(self, canvas, doc, quotation):
        canvas.saveState()
        # Register custom font
        font_new = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'montserrat', 'Montserrat-Black.ttf')
 
        pdfmetrics.registerFont(
            TTFont("Montserrat-Black", font_new)
        )

        # Define Styles
        title_style = ParagraphStyle(
            "title", fontName="Montserrat-Black", fontSize=95, textColor=colors.red, leading=80
        )
        subtitle_style = ParagraphStyle(
            "subtitle", fontName="Helvetica", fontSize=20, textColor=colors.black, backColor=colors.white, leading=30
        )
        label_style = ParagraphStyle(
            "label", fontName="Helvetica-Bold", fontSize=8, textColor=colors.black
        )
        value_style = ParagraphStyle(
            "value", fontName="Helvetica", fontSize=10, textColor=colors.red
        )
        address_style = ParagraphStyle(
            "addr", fontName="Helvetica", fontSize=11, textColor=colors.black
        )

        # Left Block (hello + subtitle)
        hello = Paragraph("<b>hello</b>", title_style)
        subtitle = Paragraph('this is your <font color="red"><b>quotation</b></font>', subtitle_style)

        left_block = Table([[hello], [subtitle]], colWidths=[10 * cm], style=[
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])

        # Right Block (logo + address)
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logos', 'arrolite.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=6 * cm, height=1.5 * cm)
        else:
            logo = Paragraph("<b>ARROLITE</b>", title_style)

        address = Paragraph("#01-21 Centrum Square 320 Serangoon Rd, Singapore 218108", address_style)

        right_block = Table([[logo], [address]], colWidths=[9 * cm], style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ])

        # Top row (hello + logo block)
        top_row = Table([[left_block, right_block]], colWidths=[10 * cm, 9.5 * cm], style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ])

        def make_info_table(data):
            rows = []
            for label, value in data:
                rows.append([Paragraph(label, label_style)])
                rows.append([Paragraph(value, value_style)])
            return Table(rows, colWidths=[8.5 * cm], style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])

        # Left and right info blocks
        invoice_table = make_info_table([
            ("invoice no.", f"{quotation.invoice_number}"),
            ("date", quotation.request_date.strftime('%d %B %Y').upper()),
        ])

        contact_table = make_info_table([
            ("contact", "+65 8 54321 92"),
            ("email", "hello@arrolitesg.com"),
        ])

        # Bottom info row (2 columns)
        info_row = Table([[invoice_table, contact_table]], colWidths=[9 * cm, 9.5 * cm], style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ])

        # Combine top row and info row
        full_header = Table(
            [[top_row], [info_row]],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 1), (0, 1), 0),  # spacing between top and bottom
            ]
        )

        # Draw the final layout
        w, h = full_header.wrap(doc.width, doc.topMargin)
        full_header.drawOn(canvas, doc.leftMargin, doc.height + doc.bottomMargin - h)

        canvas.restoreState()

    def footer(self, canvas, doc):
        canvas.saveState()

        # Set red "thank you!"
        canvas.setFont("Helvetica-Bold", 40)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin, 4 * cm, "thank you!")

        # Draw a light grey background rectangle (very slim)
        canvas.setFillColorRGB(0.95, 0.95, 0.95)  # #f2f2f2
        canvas.rect(doc.leftMargin - 0.5 * cm, 0.9 * cm, doc.width + 1 * cm, 2.1 * cm, stroke=0, fill=1)

        # OCBC Logo
        ocbc_img_path = os.path.join(settings.BASE_DIR, 'static', 'ac-imgs', 'ocbc-bank-logo.png')
        canvas.drawImage(ocbc_img_path, doc.leftMargin, 1.3 * cm, width=1.3 * cm, height=1.3 * cm, mask='auto')

        # OCBC Bank Text
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin + 1.5 * cm, 2.3 * cm, "bank transfer")

        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.black)
        canvas.drawString(doc.leftMargin + 1.5 * cm, 1.9 * cm, "current AC")

        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(doc.leftMargin + 1.5 * cm, 1.5 * cm, "595-28881-2001")

        # First separator "or"
        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin + 6 * cm, 2.0 * cm, "or")

        # PayNow logo
        paynow_img_path = os.path.join(settings.BASE_DIR, 'static', 'ac-imgs', 'paynow.png')
        canvas.drawImage(paynow_img_path, doc.leftMargin + 7 * cm, 1.5 * cm, width=1.1 * cm, height=1 * cm, mask='auto')

        # UEN and company name
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(colors.black)
        canvas.drawString(doc.leftMargin + 8.7 * cm, 2.3 * cm, "uen")
        canvas.drawString(doc.leftMargin + 8.7 * cm, 2.0 * cm, "202313034H")

        canvas.setFont("Helvetica", 6)
        canvas.drawString(doc.leftMargin + 8.7 * cm, 1.7 * cm, "ARROLITE PTE. LTD.")

        # Second separator "or"
        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin + 13.3 * cm, 2.0 * cm, "or")

        # Scan Me image
        # scan_img_path = os.path.join(settings.BASE_DIR, 'static', 'ac-imgs', 'scanme.png')
        # canvas.drawImage(scan_img_path, doc.leftMargin + 14.8 * cm, 2.0 * cm, width=2 * cm, height=1.5 * cm, mask='auto')

        # QR code
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.black)
        canvas.drawString(doc.leftMargin + 14 * cm, 1.7 * cm, "Scan me")
        qr_img_path = os.path.join(settings.BASE_DIR, 'static', 'ac-imgs', 'ocbc-qr.png')
        canvas.drawImage(qr_img_path, doc.leftMargin + 16 * cm, 0.4 * cm, width=3 * cm, height=3 * cm, mask='auto')

        # Disclaimer
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.red)
        canvas.drawString(doc.leftMargin, 0.6 * cm, "This is a computer generated and no signature is required.")

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
        normal_style = ParagraphStyle("normal", fontName="Helvetica", fontSize=8, leading=14,textColor=colors.HexColor("#74666a"))
        header_style = ParagraphStyle("header_style", fontName="Helvetica-Bold", fontSize=7, textColor=colors.white, spaceAfter=6)
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
           
        ], colWidths=[14 * cm, 4* cm], style=[
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#74666a")),
        ])
         
         
        # FOR / TOTAL block
        for_label_style = ParagraphStyle("for_label", fontName="Helvetica-Bold", fontSize=9, textColor=colors.red)
        for_desc_style = ParagraphStyle("for_label", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#74666a"))
        for_name_style = ParagraphStyle("for_name", fontName="Helvetica-Bold", fontSize=12, textColor=colors.HexColor("#74666a"))
        for_address_style = ParagraphStyle("for_address", fontName="Helvetica", fontSize=10, textColor=colors.gray)
        total_label_style = ParagraphStyle("total_label", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)
        total_value_style = ParagraphStyle("total_value", fontName="Helvetica-Bold", fontSize=12, textColor=colors.white, alignment=2)

        for_section = [
            Paragraph("for", for_label_style),
            Paragraph("HN CONSTRUCTION PTE LTD<br/>", for_name_style),
            Spacer(1, 5), 
            Paragraph("39 Woodlands close, MEGA@woodlands #08-84<br/>Singapore 737856", for_address_style)
        ]
        total_section = [
            Paragraph("total", total_label_style),
            Paragraph(f"${grand_total:,.2f}", total_value_style)
        ]
        desc_section = [
            Paragraph("*DESIGN PROVIDED BY YOU", for_desc_style),
        ]
        desc_des_section = [
            Paragraph("- 50% deposit require for order confirmation", for_desc_style),
        ]
        desc_table = Table([
            [desc_section],
        ], style=[
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#74666a")),
        ])
        desc_table2 = Table([
            [desc_des_section],
        ], style=[
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#74666a")),
        ])
         
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
            Spacer(1, 0.5 * cm),
            desc_table,
            desc_table2,
            Spacer(1, 1 * cm),
            KeepTogether(summary_table),
        ]

        doc.build(elements)
        buffer.seek(0)
        return buffer
 