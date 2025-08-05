from django.contrib import admin
from app.models.category.category_model import Category
from app.models.customer_model.customer_model import CustomUser, Customer
from app.models.iso_series.iso_series_model import ISOSize
from app.models.product.product_model import Product, ProductImage
from app.models.product.quotation_model import Quotation, QuotationItem
from app.models.sub_category.sub_category_model import SubCategory
from app.models.unit.unit_model import Unit

# Register your models here.


admin.site.register(CustomUser)
admin.site.register(Customer)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Quotation)
admin.site.register(QuotationItem)


admin.site.register(Unit)
admin.site.register(ISOSize)









