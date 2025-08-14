from django.views import View
from django.shortcuts import render

from app.models.category.category_model import Category
from app.models.customer_model.customer_model import Customer
from app.models.product.product_model import Product
from app.models.product.quotation_model import Quotation
from app.models.sub_category.sub_category_model import SubCategory
 
class HomePageView(View):
    template_name = 'pages/dashboard/dashboard.html'
    def get(self, request):
        subcategories = SubCategory.active_objects.all()
        categories = Category.active_objects.all()
        Products = Product.active_objects.all()
        Customers=Customer.active_objects.all()
        quotations = Quotation.active_objects.all() 
        if not request.user.is_superuser:
            quotations = quotations.filter(approver =request.user)
        else:
            quotations = quotations

        qus={
            "list_quotations":quotations.count(),
            "quotations_invoice":quotations.filter(approver_status="approved").count(),
            "quotations_reject":quotations.filter(approver_status="rejected").count(),
            "quotations_pending":quotations.filter(approver_status="pending").count(),
        }
        context = {
            'categories' :categories,
            'categories_total' :categories.count(),
            'subcategories': subcategories,
            'subcategories_total': subcategories.count(),
            'Products':Products,
            'Products_total':Products.count(),
            'customers':Customers,
            'customers_total':Customers.count(),
            'qus':qus
        }
        return render(request, self.template_name,context)

 
