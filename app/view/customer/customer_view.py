import json

from django.http import JsonResponse
from app.forms.customer.customer_form import CustomerRegisterFrom, CustomerUserRegisterForm
from app.models.customer_model.customer_model import CustomUser, Customer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, UpdateView
from django.contrib import messages
from django.forms.models import model_to_dict
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
 
class Login(View):  # ✅ inherit from View
    template_name = "pages/customer/login.html"

    def get(self, request):
        return render(request, self.template_name)
    def post(self, request):
        email = request.POST.get("email")
        password = request.POST.get("password")
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, self.template_name)
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, "Login successful.")
                return redirect("home")  # replace with your actual URL name
            else:
                messages.error(request, "Account is inactive. Contact admin.")
        else:
            messages.error(request, "Invalid login credentials.")            
        return render(request, self.template_name)

class UserLogoutView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        logout(request)
        response = redirect("home")
        request.session.flush()
        for cookie in request.COOKIES:
            response.delete_cookie(cookie)
        return response
    
class CustomUserRegister(LoginRequiredMixin, CreateView):
    model = CustomUser
    form_class = CustomerUserRegisterForm
    template_name = "pages/customer/customer_register.html"
    success_url = reverse_lazy("home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_add_user_modal"] = True
        context["current_user"] = self.request.user
        return context

    def form_invalid(self, form):
         
        messages.error(self.request, form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.save(commit=False)
        raw_password = form.cleaned_data.get("password")

        if raw_password:
            user.set_password(raw_password)  # ensures password is hashed
        user.save()
        if hasattr(form, 'save_m2m'):
            form.save_m2m()
        messages.success(
            self.request,
            f'User {form.cleaned_data["email"]} has been added successfully',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("user_list")
   
# Edit user
class CustomUserUpdate(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomerUserRegisterForm
    template_name = "pages/customer/customer_register.html"

    def form_invalid(self, form):
        print("Form is invalid. Errors:", form.errors)
        messages.error(self.request, form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.save(commit=False)
        raw_password = form.cleaned_data.get("password")
        if raw_password and len(raw_password) < 3:  
            # only hash & update if changing password
            print("as")
            user.set_password(raw_password)
        user.save()
        form.save_m2m()
        messages.success(
            self.request,
            f'User {form.cleaned_data["email"]} has been updated successfully',
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_action"] = reverse("user_update", kwargs={"pk": self.object.pk})
        context["is_update"] = True
        return context

    def get_success_url(self):
        return reverse("user_list")
   
   
   
    
@method_decorator(csrf_exempt, name='dispatch')  
class CustomerRegister(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerRegisterFrom

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
 

        form = self.form_class(data)

        if form.is_valid():
            customer = form.save()
            return JsonResponse({
                "status": "success",
                "message": "Customer registered successfully.",
                "data": model_to_dict(customer)
            }, status=201)
        else:
            return JsonResponse({
                "status": "error",
                "message": "Validation failed",
               "errors": {
                        field: errors[0]["message"]
                        for field, errors in form.errors.get_json_data().items()
                    }
            }, status=400)
            
            
     
class CustomuserList(View):
    template_name = "pages/customer/user_list.html"
    def get(self, request):
        users = CustomUser.active_objects.all()
        return render(request, self.template_name, {'users': users})
    