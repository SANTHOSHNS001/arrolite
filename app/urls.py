
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from app.view.home import HomePageView
from app.view.iso_series.iso_view import ISOSizeDelete, ISOSizeEditView, ISOSizeListView
from app.view.permission.permission import GroupUpdateView, GroupUserAddorUpdateView, PermissionAdd, PermissionSetting
from app.view.product.product_view import ProductDelete, ProductEditView, ProductListView, QuotationReportPdfView
from app.view.quotation.quotation_view import QuotationApprovalView, QuotationInvoiceView, QuotationListView, QuotationReportView, QuotationRequestView, QuotationView,QuotationApprove
from app.view.sub_category.sub_category_view import SubCategoryDelete, SubCategoryEditView, SubCategoryListView
from app.view.category.category_view import CategoryDelete, CategoryEditView, CategoryListView
from app.view.customer.customer_view import CustomUserRegister, CustomUserUpdate, CustomerRegister, CustomuserList, Login, UserLogoutView
from app.view.unit.unit_view import UnitDelete, UnitEditView, UnitListView
 
urlpatterns = [
  
                path("login/", Login.as_view(), name="login"),
                path("logout/", UserLogoutView.as_view(), name="logout"),
                path("", HomePageView.as_view(), name="home"),
                # User Path
                path("user_add/", CustomUserRegister.as_view(), name="user_add"),
                path("users/<int:pk>/edit/", CustomUserUpdate.as_view(), name="user_update"),
                path("user_list/", CustomuserList.as_view(), name="user_list"),
                # Category Path
                path("category-list/", CategoryListView.as_view(), name="category_list"),    
                path("category-edit/<int:pk>/", CategoryEditView.as_view(), name="category_edit"),
                path("category-delete/<int:pk>/", CategoryDelete.as_view(), name="category_delete"),
                # Sub-Category Path
                path("sub-category-list/", SubCategoryListView.as_view(), name="sub_category_list"),    
                path("sub-category-edit/<int:pk>/", SubCategoryEditView.as_view(), name="sub_category_edit"),
                path("sub-category-delete/<int:pk>/", SubCategoryDelete.as_view(), name="sub_category_delete"),    
                # Product Path
                path("product-list/", ProductListView.as_view(), name="product_list"),
                path("product-edit/<int:pk>/", ProductEditView.as_view(), name="product_edit") , 
                path("product-delete/<int:pk>/", ProductDelete.as_view(), name="product_delete") , 
                # Quotation Path
                path("quotation-list/", QuotationListView.as_view(), name="quotation_list"),
                path("quotation-awaiting/", QuotationApprovalView.as_view(), name="quotation_waiting"),
                path("quotation-request/", QuotationRequestView.as_view(), name="quotation_request"),
                path("quotation-invoice/", QuotationInvoiceView.as_view(), name="quotation_invoice"),  
                path("quotation-test/", QuotationReportPdfView.as_view(), name="quotation_test"),
                path("quotation-items/<int:pk>/", QuotationView.as_view(), name="quotation_items"), 
                path("quotaion-approval/<int:pk>/", QuotationApprove.as_view(), name="quotaion_approval") , 
                path("quotaion-report/", QuotationReportView.as_view(), name="quotaion_report") , 

                
                # Permission Path
                path("permission-setting", PermissionSetting.as_view(), name="permission_setting"),
                path("permission-add", PermissionAdd.as_view(), name="permission_add"), 
                path("permission/<int:pk>/edit/", GroupUpdateView.as_view(), name="permission_update"),
                path("permission/<int:pk>/add-users/", GroupUserAddorUpdateView.as_view(), name="group_user_add"),      
                path('register-customer/', CustomerRegister.as_view(), name='register-customer'),            
                # unit Path
                path("unit-list", UnitListView.as_view(), name="unit_list"),
                path("unit-edit/<int:pk>", UnitEditView.as_view(), name="unit_edit"),
                path("unit-delete/<int:pk>", UnitDelete.as_view(), name="unit_delete"),              
                # ISO Path
                path("iso-list", ISOSizeListView.as_view(), name="iso_list"),
                path("iso-edit/<int:pk>", ISOSizeEditView.as_view(), name="iso_edit"),
                path("iso-delete/<int:pk>", ISOSizeDelete.as_view(), name="iso_delete"),
                    
                         
              ]  
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)