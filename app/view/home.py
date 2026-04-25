from django.views import View
from django.shortcuts import render
from app.models.category.category_model import Category
from app.models.customer_model.customer_model import Customer
from app.models.invoice_model.invoice_model import Invoice
from app.models.product.product_model import Product
from app.models.product.quotation_model import Quotation
from app.models.sub_category.sub_category_model import SubCategory
from django.utils import timezone
 
from django.views import View
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q


class HomePageView(View):
    template_name = 'pages/dashboard/dashboard.html'
    limit_quotations = 10
    limit_invoices = 10


    def get(self, request):
        today = timezone.now().date()
        first_day_this_month = today.replace(day=1)

        # 🔹 Base filters
        base_filter = Q(request_date__date__range=(first_day_this_month, today))

        if not request.user.is_superuser:
            base_filter &= Q(approver=request.user)

        # 🔹 Aggregated Quotation Stats (ONE QUERY)
        quotation_stats = Quotation.active_objects.filter(base_filter).aggregate(
            total=Count('id'),
            approved=Count('id', filter=Q(approver_status='approved')),
            rejected=Count('id', filter=Q(approver_status='rejected')),
            pending=Count('id', filter=Q(approver_status='pending')),
        )

        # 🔹 Aggregated Invoice Stats (ONE QUERY)
        invoice_stats = Invoice.active_objects.filter(base_filter).aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(approver_status='pending')),
            payment_pending=Count('id', filter=Q(approver_status='pending_payment')),
            paid=Count('id', filter=Q(approver_status='paid')),
        )

        # 🔹 Only fetch lists if needed (LIMIT them)
        quotations = Quotation.active_objects.filter(base_filter).order_by('-request_date')[:10]
        invoices = Invoice.active_objects.filter(base_filter).order_by('-request_date')[:10]

        context = {
            # 🔹 Counts only (no full querysets)
            'categories_total': Category.active_objects.count(),
            'subcategories_total': SubCategory.active_objects.count(),
            'products_total': Product.active_objects.count(),
            'customers_total': Customer.active_objects.count(),

            # 🔹 Aggregated data
            'qus': {
                'list_quotations': quotation_stats['total'],
                'quotations_invoice': quotation_stats['approved'],
                'quotations_reject': quotation_stats['rejected'],
                'quotations_pending': quotation_stats['pending'],
            },

            'invoice': {
                'list_invoice': invoice_stats['total'],
                'pending_invoice': invoice_stats['pending'],
                'payment_pending_invoice': invoice_stats['payment_pending'],
                'paid_invoices': invoice_stats['paid'],
            },

            # 🔹 Recent items only (not full table!)
            'current_month_quotations': quotations,
            'current_month_invoices': invoices,

            'current_month_start': first_day_this_month,
            'current_month_end': today,
            'pending_invoice_list': self.pending_invoice(request),
            
        } 

        return render(request, self.template_name, context)
    def pending_invoice(self, request):
        limit = getattr(self, "limit_invoices", 10)

        if request.user.has_perm('app.can_manage_invoice'):
            invoices = Invoice.active_objects.filter(
                approver_status="sent_to_manager"
            ).select_related('customer')[:limit]

            result = [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "request_date": inv.request_date.strftime("%Y-%m-%d") if inv.request_date else None,
                    "customer": inv.customer.name if inv.customer else None,
                    "customer_email": inv.customer.email if inv.customer else None,
                    "total_cost":int(inv.total_cost), 
                }
                for inv in invoices
            ] 
            return result

        else:
            return []
 

 
