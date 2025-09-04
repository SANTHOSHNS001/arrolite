from django import template

register = template.Library()



parant_menus = {
    1: "Quotation",
    2: "Invoice",
    3: "Calculation"
}

@register.simple_tag
def get_sidebar_menu():
      return [
        {"url": "home", "name": "Dashboard", "icon": "fa fa-dashboard", "class": "sidebar", "parent": None},  
        {"perm": "app.can_manager_access", "name": "Management Access", "icon": "fa fa-key", "permission_only": True, "parent": None},

        {"url": "user_list", "name": "Users", "icon": "fa fa-users", "perm": "app.client_role_access", "parent": None},
        {"url": "category_list", "name": "Category", "icon": "fa fa-list", "perm": "app.manage_category", "parent": None},
        {"url": "sub_category_list", "name": "Sub-Category", "icon": "fa fa-sitemap", "perm": "app.manage_subcategory", "parent": None},
        # Setting
        {"url": "permission_setting", "name": "Permission", "icon": "fa fa-cog", "perm": "app.client_manege_access", "parent": "Setting"},
        {"url": "unit_list", "name": "Unit", "icon": "fa fa-ruler", "perm": "app.manage_unit", "parent": "Setting"},
        {"url": "iso_list", "name": "ISO-Size", "icon": "fa fa-cubes", "perm": "app.can_manage_isosize", "parent": "Setting"},
        # Product (single menu, not grouped)
        {"url": "invoice_product_report", "name": "Product-Report", "icon": "fa fa-shopping-cart", "perm": "app.can_report_invoice", "parent": "Product"},
        {"url": "product_list", "name": "Product", "icon": "fa fa-box", "perm": "app.can_manage_product", "parent": "Product"},
        

        # QUOTATIONS
        {"url": "quotation_list", "name": "Quotation", "icon": "fa fa-file", "perm": "app.can_manage_quotaion", "parent": "Quotation"},
        {"url": "quotation_waiting", "name": "Approved", "icon": "fa fa-check", "perm": "app.can_approve_quotation", "parent": "Quotation"}, 
        {"url": "quotaion_report", "name": "Quotaion Report", "icon": "fa fa-file-alt", "perm": "app.can_reports_quotaion", "parent": "Quotation"},

        # Invoice
        {"url": "quotation_invoice", "name": "Invoice", "icon": "fa fa-receipt", "perm": "app.can_assign_approver_quotation", "parent": "Invoice"}, 
        {"url": "invoice_report", "name": "Invoice Report", "icon": "fa fa-file-invoice", "perm": "app.can_report_invoice", "parent": "Invoice"},
       # Expenses (single menu, not grouped)
        {"url": "expenses_list", "name": "Expenses", "icon": "fa fa-wallet", "perm": "app.expense_manage_permission", "parent": "Expenses"},
 
        {"url": "customer_list", "name": "Customer", "icon": "fa fa-user", "perm": "app.client_manege_permission", "parent": None},
    ]
 
 
 
@register.filter
def has_perm(user, perm_name):
    return user.has_perm(perm_name)