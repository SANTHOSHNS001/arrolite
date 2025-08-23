 

from decimal import Decimal
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from app.models.customer_model.customer_model import CustomUser, Customer
from app.models.invoice_model.invoice_model import Invoice, InvoiceItem
from app.models.iso_series.iso_series_model import ISOSize
from app.models.product.product_model import Product
from app.models.product.quotation_model import Quotation, QuotationItem
from app.models.unit.unit_model import Unit
from django.contrib import messages 
from django.http import FileResponse, JsonResponse
import json
 
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
 
from decimal import Decimal, InvalidOperation

class InvoiceListView(View):
  
    template = "pages/invoice/invoice_list.html"
    def get(self, request):
        quotation = Invoice.active_objects.all()  
        context = {
            'quotations':quotation,
  
        }
        return render(request, self.template, context) 

class InvoiceRequestView(View):
 
    template = "pages/invoice/invoice_form.html"
    def get(self, request):
        products = Product.active_objects.all()
        units = Unit.active_objects.all()
        customer = Customer.active_objects.all() 
        iso_sizes = ISOSize.active_objects.all() 
        
        context = {
             
            'products': products,
            'units': units,
            'users': customer,
            "iso_sizes":iso_sizes
        }
 
        return render(request, self.template, context)

    def post(self, request):
        requite_date = request.POST.get("requite_date")
        user_id = request.POST.get("user")
        description = request.POST.get("description")
        iso_size = request.POST.get("iso_size")
           
        if not requite_date or not user_id:
            messages.error(request, "Request date and user are required.")
            return self.render_with_context(request)

        user = get_object_or_404(Customer.active_objects, id=user_id)
        iso_size = get_object_or_404(ISOSize.active_objects, id=iso_size)
        items = self.extract_valid_items(request.POST)

        if not items:
            messages.error(request, "At least one product must be added to create a Products.")
            return self.render_with_context(request)

        # ✅ Create quotation
        invoice = Invoice.objects.create(
            invoice_number=self.generate_quotation_number(),
            request_date=requite_date,
            approver_status ="pending",
            approver = self.request.user,
            description=description,
            isosize = iso_size,
            customer=user
        )
    
        # ✅ Save valid items
        print("items--099",items)
        for item in items:
            InvoiceItem.objects.create(invoice=invoice, **item)

        messages.success(request, "Invoice created successfully.")
        return redirect('quotation_invoice')

    def generate_quotation_number(self):
        last_quotation = Invoice.active_objects.order_by('-id').first()
        if last_quotation and last_quotation.invoice_number:
            last_number = int(last_quotation.invoice_number.replace('Q', ''))
            new_number = last_number + 1
        else:
            new_number = 1
        return f"Q{new_number:04d}"

    def extract_valid_items(self, post_data):
        items = []
        counter = 1
        while True:
            product_id = post_data.get(f'product_{counter}')
            if not product_id:
                break
            try:
                product = Product.objects.get(id=product_id)
                qty = float(post_data.get(f'qty_{counter}', 0))
                width = float(post_data.get(f'width_{counter}', 0) or 0)
                height = float(post_data.get(f'height_{counter}', 0) or 0)
                unit_cost = float(post_data.get(f'unit_cost_{counter}', 0) or 0)
                unit_id = post_data.get(f'unit_{counter}')    
                unit = Unit.active_objects.get(id=unit_id) if unit_id else None

                if qty > 0:
                    items.append({
                        'product': product,
                        'quantity': qty,
                        'width': width,
                        'height': height,
                        'unit_cost': unit_cost,
                        'unit': unit,
                         
                    })
            except (Product.DoesNotExist, Unit.DoesNotExist, ValueError):
                pass  # skip this row if anything is invalid

            counter += 1
        return items

    def render_with_context(self, request):
        quotations = Quotation.active_objects.all()
        products = Product.active_objects.all()
        units = Unit.active_objects.all()
        users = CustomUser.active_objects.all()
        context = {
            'quotations': quotations,
            'products': products,
            'units': units,
            'users': users
        }
        return render(request, self.template, context)
    
class InvoiceDetails(View):
    template = "pages/invoice/invoice_details.html"

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice.active_objects, id=pk)
        quotation_items = InvoiceItem.active_objects.filter(invoice=invoice)
        context = {
            'quotation': invoice,
            'quotationsitems': quotation_items,
        }
        return render(request, self.template, context)

    def post(self, request, pk):
        quotation = get_object_or_404(Invoice, id=pk)
        print("request.POST", request.POST)

        # Read inputs
        status_str   = request.POST.get('status')
        discount_str = request.POST.get('discount')
        deposit_str  = request.POST.get('deposit')
        is_disc_flag = request.POST.get('is_discount', 'off') == 'on'

        # Validate status present
        if not status_str:
            quotation_items = InvoiceItem.objects.filter(invoice=quotation)  # <-- FIXED: use invoice=
            return render(request, self.template, {
                'quotation': quotation,
                'quotationsitems': quotation_items,
                'error': 'Status is required.',
            })

        # Parse numbers safely as Decimal
        try:
            advance = Decimal(str(deposit_str or 0))
        except (InvalidOperation, TypeError, ValueError):
            quotation_items = InvoiceItem.objects.filter(invoice=quotation)
            return render(request, self.template, {
                'quotation': quotation,
                'quotationsitems': quotation_items,
                'error': 'Invalid deposit amount.',
            })

        # Handle discount (optional)
        if discount_str not in (None, ""):
            try:
                discount_val = Decimal(str(discount_str))
            except (InvalidOperation, TypeError, ValueError):
                quotation_items = InvoiceItem.objects.filter(invoice=quotation)
                return render(request, self.template, {
                    'quotation': quotation,
                    'quotationsitems': quotation_items,
                    'error': 'Invalid discount format.',
                })

            # Validate discount bounds
            if is_disc_flag:
                if not (Decimal("0") <= discount_val <= Decimal("100")):
                    quotation_items = InvoiceItem.objects.filter(invoice=quotation)
                    return render(request, self.template, {
                        'quotation': quotation,
                        'quotationsitems': quotation_items,
                        'error': 'Percentage discount must be between 0 and 100.',
                    })
            else:
                if discount_val < 0:
                    quotation_items = InvoiceItem.objects.filter(invoice=quotation)
                    return render(request, self.template, {
                        'quotation': quotation,
                        'quotationsitems': quotation_items,
                        'error': 'Fixed discount must be 0 or higher.',
                    })

            quotation.discount = discount_val
            quotation.is_percentage = is_disc_flag

        # --- Add new deposit (CRITICAL: do NOT overwrite; accumulate) ---
        if advance > 0:
            quotation.advance_amount = (quotation.advance_amount or Decimal("0.00")) + advance
            quotation.save(update_fields=["advance_amount", "discount", "is_percentage"])
            quotation.refresh_from_db()

        # Recompute after any changes
        balance_due = quotation.balance_due
        print("quotation.balance_due", balance_due)
        print("advance just received", advance)
        print("total paid so far", quotation.total_paid)

        # --- Status logic ---
        # If user set "paid":
        if status_str == 'paid':
            if balance_due <= 0:
                quotation.approver_status = 'paid'
            else:
                quotation.approver_status = 'pending_payment'
        else:
            # Otherwise accept requested status as-is
            quotation.approver_status = status_str

        # Optional: protect against unauthorized edits
        if not (quotation.approver == request.user and quotation.approver_status in ['pending', 'pending_payment', 'paid', status_str]):
            quotation_items = InvoiceItem.objects.filter(invoice=quotation)
            return render(request, self.template, {
                'quotation': quotation,
                'quotationsitems': quotation_items,
                'error': 'You are not allowed to update this quotation.',
            })

        quotation.save(update_fields=["approver_status", "discount", "is_percentage"])
        return redirect('quotation_invoice')
    
    
    
    
    
class InvoiceReportPdfView(View):
    def __init__(self, **kwargs):
        self.company_name = "ARROLITE"
        super().__init__(**kwargs)
    def post(self, request):
        try:      
 
            data = json.loads(request.body)
            document_id = data.get("document_id")
            qns = Invoice.active_objects.get(id=document_id)
            data = []
            for qs in qns.invoiceitems.all():
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
          
            return JsonResponse({"error": str(e)}, status=400) 
 
    def header(self, canvas, doc, quotation):
        canvas.saveState()
        font_new = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'montserrat', 'Montserrat-Black.ttf')
        titles_header_fonts = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'montserrat', 'GothamBold.ttf')
        titles_header_fontss = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'montserrat', 'Gotham-Bold.ttf')
        titles_add = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'montserrat', 'GothamLight.ttf')
        pdfmetrics.registerFont(
            TTFont("Montserrat-Black", font_new)
        )
        pdfmetrics.registerFont(
            TTFont("Gotham-Bold", font_new)
        )
        pdfmetrics.registerFont(
            TTFont("GothamLight", titles_add)
        )
        
        pdfmetrics.registerFont(TTFont("GothamBold", titles_header_fonts))


        # Define Styles
        title_style = ParagraphStyle(
            "title", fontName="Gotham-Bold", fontSize=90, textColor=colors.red, leading=87
        )
        subtitle_style = ParagraphStyle(
            "subtitle", fontName="GothamLight", fontSize=25, textColor=colors.black, backColor=colors.white, leading=30
        )
        label_style = ParagraphStyle(
            "label", fontName="GothamBold", fontSize=8, textColor=colors.black
        )
        value_style = ParagraphStyle(
            "value", fontName="Helvetica", fontSize=10, textColor=colors.red
        )
        address_style = ParagraphStyle(
            "addr", fontName="GothamLight", fontSize=11, textColor=colors.black
        )

        # Left Block (hello + subtitle)
        hello = Paragraph("<b>hello</b>", title_style)
        subtitle = Paragraph('this is your <font color="red"><b> invoice</b></font>', subtitle_style)

        left_block = Table([[hello], [subtitle]], colWidths=[12 * cm], style=[
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), -12),
            # ("BACKGROUND", (0, 0), (-1, -1), colors.green),  # ✅ background color

        ])
 
        # Right Block (logo + address)
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logos', 'LOGO.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=8.3 * cm, height=1.4 * cm)
        else:
            logo = Paragraph("<b>ARROLITE</b>", title_style)

        address = Paragraph("#01-21 Centrum Square 320 Serangoon Rd, Singapore 218108", address_style)

        right_block = Table([[logo], [address]], colWidths=[10 * cm], style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
           
        ])

        # Top row (hello + logo block)
        top_row = Table([[left_block, right_block]], colWidths=[11 * cm, 10 * cm], style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),     
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

        # Bottom info row (2 columns)[11 * cm, 10 * cm]
        info_row = Table([[invoice_table, contact_table]], colWidths=[11 * cm, 10 * cm], style=[
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

    def footer(self, canvas, doc,quotation,quotationitems):
        canvas.saveState()
      
       
        #  that add that dection part 
        canvas.setFillColorRGB(0.95, 0.95, 0.95)
        canvas.rect(doc.leftMargin - 0.5 * cm, 0.9 * cm, doc.width + 1 * cm, 2.1 * cm, stroke=0, fill=1)

        # === Calculate Totals ===
        total = sum(item["total_cost"] for item in quotationitems)
        discount = quotation.discount or 0
        discount_amount = total * discount / 100
        grand_total = total - discount_amount

        # === Styles ===
        for_style = ParagraphStyle("ForLabel", fontName="Helvetica-Bold", fontSize=10, textColor=colors.red)
        company_style = ParagraphStyle("CompanyName", fontName="Helvetica-Bold", fontSize=12, textColor=colors.HexColor("#7B6F6F"))
        address_style = ParagraphStyle("Address", fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#666666"), leading=10)
        total_label_style = ParagraphStyle("TotalLabel", fontName="Helvetica-Bold", fontSize=6, textColor=colors.whitesmoke)
        total_value_style = ParagraphStyle("TotalValue", fontName="Helvetica-Bold", fontSize=7, textColor=colors.whitesmoke, alignment=2)

        # === Left (FOR) ===
        customer_add="39 Woodlands closeMEGA@woodlands #08-84 \n Singapore 737856"
        left_cell = [
            Paragraph("for", for_style),
            Paragraph("HN CONSTRUCTION PTE LTD", company_style),
            Spacer(1, 5),
            Paragraph(customer_add.replace("\n", "<br/>"), address_style),
        ]

         # === Right (TOTAL / DEPOSIT / BALANCE) as 2-column inner table ===
        right_inner_table = Table(
            [
                [Paragraph("total", total_label_style),   Paragraph(f"$ {quotation.total_cost:,.2f}", total_value_style)],
                [Paragraph("deposit", total_label_style), Paragraph(f"${quotation.advance_amount:,.2f}", total_value_style)],
                [Paragraph("balance", total_label_style), Paragraph(f"${quotation.balance_due:,.2f}", total_value_style)],
            ],
            colWidths=[2 * cm, 3 * cm],  # adjust widths to balance text/value
            style=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),  # right align values
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ],
        )

        # === Full summary table (Left: FOR, Right: Inner table) ===
        summary_table = Table(
            [[left_cell, right_inner_table]],
            colWidths=[13.2 * cm, 6.3 * cm],
            style=[
                ("BACKGROUND", (0, 0), (0, 0), colors.whitesmoke),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#231f20")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ],
        )

        # === Draw summary box instead of "For" ===
        w, h = summary_table.wrap(doc.width, doc.bottomMargin)
        summary_table.drawOn(canvas, doc.leftMargin, 6 * cm)

        # Set red "thank you!"
        canvas.setFont("Helvetica-Bold", 40)
        canvas.setFillColor(colors.red)
        #  that add that dection part 
        
        canvas.drawString(doc.leftMargin, 4 * cm, "thank you!")

        # Draw a light grey background rectangle (very slim)
        canvas.setFillColorRGB(0.95, 0.95, 0.95)  # #f2f2f2
        canvas.rect(doc.leftMargin - 0.5 * cm, 0.9 * cm, doc.width + 1 * cm, 2.1 * cm, stroke=0, fill=1)

        # OCBC Logo
        ocbc_img_path = os.path.join(settings.BASE_DIR, 'static', 'ac-imgs', 'ocbc_logo.png')
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
        scan_img_path = os.path.join(settings.BASE_DIR, 'static', 'ac-imgs', 'scan_me.png')
        canvas.drawImage(scan_img_path, doc.leftMargin + 14 * cm, 1.4 * cm, width=2* cm, height=1.6 * cm, mask='auto')
 
        qr_img_path = os.path.join(settings.BASE_DIR, 'static', 'ac-imgs', 'qr_img.jpeg')
        canvas.drawImage(qr_img_path, doc.leftMargin + 16 * cm, 0.6 * cm, width=3 * cm, height=3 * cm, mask='auto')

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
            topMargin=0.7 * cm,
            bottomMargin=3 * cm,
        )

        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
        def header_with_data(canvas, doc):
            self.header(canvas, doc, quotation)
        def footer_with_data(canvas, doc):
            self.footer(canvas, doc, quotation,quotationitems)
        doc.addPageTemplates([PageTemplate(id='quote', frames=frame, onPage=header_with_data, onPageEnd=footer_with_data)])

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
            # KeepTogether(total_table),
            # Spacer(1, 0.5 * cm),
            # desc_table,
            # desc_table2,
            Spacer(1, 1 * cm),
            # KeepTogether(summary_table),
        ]

        doc.build(elements)
        buffer.seek(0)
        return buffer