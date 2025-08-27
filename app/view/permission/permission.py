from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import Group, Permission
from app.models.customer_model.customer_model import CustomUser
from app.templatetags.custom_tags import get_sidebar_menu
from django.contrib import messages
from django.urls import reverse
from django.db.models import Count

class PermissionSetting(View):
    template = "pages/permission/permission.html"
    
    def get(self, request):  
         
        groups_list = Group.objects.annotate(user_count=Count("user"))
        context = {
            'groups': groups_list,
        }
 
        return render(request, self.template, context)
class PermissionAdd(View):
    template = "pages/permission/permission_add.html"
    def get(self, request):    
        
        context = {         
            'permission_pages': get_sidebar_menu(),
        }
        return render(request, self.template, context)
    def post(self, request):
        group_name = request.POST.get("name")
        perm_codenames = request.POST.getlist("permissions")  # list of "app_label.codename"

        # Create the group
        group, created = Group.objects.get_or_create(name=group_name)

        # Add permissions to group
        for full_code in perm_codenames:
            try:
                app_label, codename = full_code.split(".")
                permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                group.permissions.add(permission)
            except Permission.DoesNotExist:
                continue  # ignore invalid entries

        messages.success(request, "Group created and permissions assigned.")
        return redirect(reverse("permission_setting"))  # change this to your success URL name
    
    
    
class GroupUpdateView(View):
    template_name = "pages/permission/permission_update.html"

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        selected_perms = group.permissions.values_list('content_type__app_label', 'codename')
        selected_perms = [f"{app}.{code}" for app, code in selected_perms]

        context = {
            "group": group,
            "selected_perms": selected_perms,
            "permission_pages": get_sidebar_menu() ,  
            # app.can_manager_access Name =Managemat Acesss
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        group = get_object_or_404(Group, id=pk)
        new_name = request.POST.get("name")
        perm_codenames = request.POST.getlist("permissions")

        if new_name:
            group.name = new_name
            group.save()

        group.permissions.clear()

        for code in perm_codenames:
            try:
                app_label, codename = code.split(".")
                perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                group.permissions.add(perm)
            except Permission.DoesNotExist:
                continue

        messages.success(request, "Group updated successfully.")
        return redirect(reverse("permission_setting"))
    
    
class GroupUserAddorUpdateView(View):
    template_name = "pages/permission/permission_adduser.html"

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        users_in_group = CustomUser.active_objects.filter(groups=group).distinct()
        users_without_group = CustomUser.active_objects.exclude(groups=group).filter(groups__isnull=True).distinct()

        context = {
            "group": group,
            "users_in_group": users_in_group,
            "users_without_group": users_without_group,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        
        group = get_object_or_404(Group, pk=pk)
        selected_add_user_ids = request.POST.getlist("add_user_ids")
        selected_remove_user_ids = request.POST.getlist("remove_user_ids")

        # Add selected users to the group
        for user_id in selected_add_user_ids:
            try:
                user = CustomUser.active_objects.get(id=user_id)
                if user.groups.exists():
                    messages.warning(request, f"User '{user.get_full_name()}' already belongs to a group.")
                    continue
                user.groups.add(group)
            except CustomUser.DoesNotExist:
                continue

        # Remove selected users from the group
        for user_id in selected_remove_user_ids:
            try:
                user = CustomUser.active_objects.get(id=user_id)
                user.groups.remove(group)
            except CustomUser.DoesNotExist:
                continue

        messages.success(request, f"Users updated successfully for group: {group.name}")
        return redirect("group_user_add", pk=pk)