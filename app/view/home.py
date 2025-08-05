from django.views import View
from django.shortcuts import render

from app.models.category.category_model import Category
from app.models.customer_model.customer_model import Customer
from app.models.product.product_model import Product
from app.models.sub_category.sub_category_model import SubCategory
 
class HomePageView(View):
    template_name = 'pages/dashboard/dashboard.html'
    def get(self, request):
        subcategories = SubCategory.active_objects.all()
        categories = Category.active_objects.all()
        Products = Product.active_objects.all()
        Customers=Customer.active_objects.all()
       
        context = {
            'categories' :categories,
            'categories_total' :categories.count(),
            'subcategories': subcategories,
            'subcategories_total': subcategories.count(),
            'Products':Products,
            'Products_total':Products.count(),
            'customers':Customers,
            'customers_total':Customers.count()
 
        }
        return render(request, self.template_name,context)

    def post(self, request):
         
        return render(request, self.template_name)
