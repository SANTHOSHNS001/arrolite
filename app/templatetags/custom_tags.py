from django import template

register = template.Library()
@register.simple_tag
def get_sidebar_menu():
    
    return [
        {"url": "home", "name": "Dashboard", "icon": "home"},  
        {"url": "user_list", "name": "Users", "icon": "manage_accounts", "perm": "app.can_manage_isosize"},
        {"url": "category_list", "name": "Category", "icon": "category", "perm": "app.manage_category"},
        {"url": "sub_category_list", "name": "Sub-Category", "icon": "interests", "perm": "app.manage_subcategory"},
        {"url": "product_list", "name": "Product", "icon": "inventory_2", "perm": "app.can_manage_product"},
        {"url": "quotation_list", "name": "Quotation", "icon": "request_quote", "perm": "app.can_manage_quotaion"},
        {"url": "quotation_waiting", "name": "Approved", "icon": "pending_actions", "perm": "app.can_approve_quotation"},
        {"url": "quotation_invoice", "name": "Invoice", "icon": "receipt", "perm": "app.can_assign_approver_quotation"}, 
        {"url": "permission_setting", "name": "Permission", "icon": "admin_panel_settings", "perm": "app.can_assign_approver_quotation"},
        {"url": "quotaion_report", "name": "Report", "icon": "assignment", "perm": "app.can_assign_approver_quotation"},

        
        {"url": "unit_list", "name": "Unit", "icon": "ac_unit", "perm": "app.manage_unit"},
        {"url": "iso_list", "name": "ISO-Size", "icon": "apps", "perm": "app.can_manage_isosize"},
        # {"url": "logout", "name": "Logout", "icon": "logout"},  
        
        # {"url": "Sheet", "name": "Sheet-Size", "icon": "user", "perm": "app.can_manage_isosize"},
        
        # {"url": "unit", "name": "Unit", "icon": "user", "perm": "app.manage_unit"}, 
    ]
@register.filter
def has_perm(user, perm_name):
    return user.has_perm(perm_name)