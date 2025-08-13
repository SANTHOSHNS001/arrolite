from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from app.models.customer_model.customer_model import CustomUser, Customer
from app.models.product.product_model import Product
from app.models.product.quotation_model import Quotation, QuotationItem
from app.models.unit.unit_model import Unit
from django.contrib import messages
 
class QuotationView(View):
    template = "pages/product/quotationitems.html"

    def get(self, request,pk):
        quotation = get_object_or_404(Quotation.active_objects, id=pk)
        quotation_items = QuotationItem.active_objects.filter(quotation=quotation)     
        context = {
            'quotation':quotation,
            'quotationsitems': quotation_items,
        }
 
        return render(request, self.template, context)
    
class QuotationApprovalView(View):
    template = "pages/quotation/quotation_approval_list.html"
    def get(self, request):
        quotation = Quotation.active_objects.filter(approver = self.request.user,approver_status__in =['Pending','pending'])  
        context = {
            'quotations':quotation,
  
        }
        return render(request, self.template, context)
 
class QuotationListView(View):
    template = "pages/quotation/quotation_list.html"

    def get(self, request):
        if request.user.is_superuser:
            quotations = Quotation.active_objects.all().order_by('-created_at')
        else :
            quotations = Quotation.active_objects.filter(approver = request.user).order_by('-created_at')
            
        products = Product.active_objects.all()
        units = Unit.active_objects.all()
        customer = Customer.active_objects.all()
        
        context = {
            'quotations': quotations,
            'products': products,
            'units': units,
            'users': customer,
        }
 
        return render(request, self.template, context)
 
    
class QuotationRequestView(View):
    template = "pages/quotation/quotation_form.html"
    def get(self, request):
        products = Product.active_objects.all()
        units = Unit.active_objects.all()
        customer = Customer.active_objects.all() 
        context = {
             
            'products': products,
            'units': units,
            'users': customer,
        }
 
        return render(request, self.template, context)

    def post(self, request):
        requite_date = request.POST.get("requite_date")
        user_id = request.POST.get("user")
        description = request.POST.get("description")
        
        if not requite_date or not user_id:
            messages.error(request, "Request date and user are required.")
            return self.render_with_context(request)

        user = get_object_or_404(Customer.active_objects, id=user_id)
        items = self.extract_valid_items(request.POST)

        if not items:
            messages.error(request, "At least one product must be added to create a quotation.")
            return self.render_with_context(request)

        # ✅ Create quotation
        quotation = Quotation.objects.create(
            invoice_number=self.generate_quotation_number(),
            request_date=requite_date,
            approver_status ="pending",
            approver = self.request.user,
            description=description
        
        )
        quotation.customer.add(user)

        # ✅ Save valid items
        for item in items:
            QuotationItem.objects.create(quotation=quotation, **item)

        messages.success(request, "Quotation created successfully.")
        return redirect('quotation_list')

    def generate_quotation_number(self):
        last_quotation = Quotation.active_objects.order_by('-id').first()
        if last_quotation and last_quotation.invoice_number:
            last_number = int(last_quotation.invoice_number.replace('#Q', ''))
            new_number = last_number + 1
        else:
            new_number = 1
        return f"#Q{new_number:04d}"

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
 
 
class QuotationApprove(View):
    template = "pages/quotation/quotation_approval_form.html"

    def get(self, request, pk):
        quotation = get_object_or_404(Quotation.active_objects, id=pk)
        quotation_items = QuotationItem.active_objects.filter(quotation=quotation)
        
        context = {
            'quotation': quotation,
            'quotationsitems': quotation_items,
        }
        return render(request, self.template, context)

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, id=pk)
        discount = request.POST.get('discount')
        status = request.POST.get('status')
        # Validation
        if not status:
            quotation_items = QuotationItem.objects.filter(quotation=quotation)
            context = {
                'quotation': quotation,
                'quotationsitems': quotation_items,
                'error': 'Status is required.',
            }
            return render(request, self.template, context)

        # Handle discount input
        if discount:
            try:
                discount_value = float(discount)
                if not (0 <= discount_value <= 100):
                    context = {
                        'quotation': quotation,
                        'quotationsitems': QuotationItem.objects.filter(quotation=quotation),
                        'error': 'Discount must be between 0 and 100.',
                    }
                    return render(request, self.template, context)
                quotation.discount = discount_value
            except ValueError:
                context = {
                    'quotation': quotation,
                    'quotationsitems': QuotationItem.objects.filter(quotation=quotation),
                    'error': 'Invalid discount format.',
                }
                return render(request, self.template, context)

        # Approver permission check
        if quotation.approver == request.user and quotation.approver_status == 'pending':
            quotation.approver_status = status
            quotation.save()
            return redirect('quotation_waiting')  # ✅ Use correct URL name

        # Unauthorized access
        quotation_items = QuotationItem.objects.filter(quotation=quotation)
        context = {
            'quotation': quotation,
            'quotationsitems': quotation_items,
            'error': 'You are not allowed to update this quotation.',
        }
        return render(request, self.template, context)
    
    
class QuotationInvoiceView(View):
    template = "pages/quotation/quotation_approval_list.html"
    def get(self, request):
        quotation = Quotation.active_objects.filter(approver = self.request.user,approver_status__in =['Approved','approved'])  
        context = {
            'quotations':quotation,
  
        }
        return render(request, self.template, context)    
    