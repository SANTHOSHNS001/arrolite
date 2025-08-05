from django.views import View
from django.shortcuts import get_object_or_404, render

from app.models.product.quotation_model import Quotation, QuotationItem

class PermissionSetting(View):
    template = "pages/permission/permission.html"
 
    def get(self, request):
       
         
        context = {
             
            'quotationsitems': "quotation_items",
        }
 
        return render(request, self.template, context)
class PermissionAdd(View):
    template = "pages/permission/permission_add.html"
 
    def get(self, request):
       
         
        context = {
             
            'quotationsitems': "quotation_items",
        }
 
        return render(request, self.template, context)