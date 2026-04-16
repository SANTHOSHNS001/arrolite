from django.views import View
from django.shortcuts import render
from app.models.category.category_model import Category
from app.models.customer_model.customer_model import Customer
from app.models.invoice_model.invoice_model import Invoice
from app.models.product.product_model import Product
from app.models.product.quotation_model import Quotation
from app.models.sub_category.sub_category_model import SubCategory
from django.utils import timezone
 
class HomePageView(View):
    template_name = 'pages/dashboard/dashboard.html'

    def get(self, request):
        today = timezone.now().date()
        first_day_this_month = today.replace(day=1)

        subcategories = SubCategory.active_objects.all()
        categories = Category.active_objects.all()
        products = Product.active_objects.all()
        customers = Customer.active_objects.all()

        month_filters = {
            'request_date__date__range': (first_day_this_month, today)
        }
        quotations = Quotation.active_objects.filter(**month_filters)
        invoices = Invoice.active_objects.filter(**month_filters)

        if not request.user.is_superuser:
            quotations = quotations.filter(approver=request.user)
            invoices = invoices.filter(approver=request.user)

        qus = {
            'list_quotations': quotations.count(),
            'quotations_invoice': quotations.filter(approver_status='approved').count(),
            'quotations_reject': quotations.filter(approver_status='rejected').count(),
            'quotations_pending': quotations.filter(approver_status='pending').count(),
        }
        ins = {
            'list_invoice': invoices.count(),
            'pending_invoice': invoices.filter(approver_status='pending').count(),
            'payment_pending_invoice': invoices.filter(approver_status='pending_payment').count(),
            'paid_invoices': invoices.filter(approver_status='paid').count(),
        }

        context = {
            'categories': categories,
            'categories_total': categories.count(),
            'subcategories': subcategories,
            'subcategories_total': subcategories.count(),
            'products': products,
            'products_total': products.count(),
            'customers': customers,
            'customers_total': customers.count(),
            'qus': qus,
            'invoice': ins,
            'current_month_quotations': quotations.order_by('-request_date'),
            'current_month_invoices': invoices.order_by('-request_date'),
            'current_month_start': first_day_this_month,
            'current_month_end': today,
        }
        
        return render(request, self.template_name, context)

 

 
