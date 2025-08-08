from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from app.forms.category.category_form import CategoryCreateForm
from app.models.category.category_model import Category
 

class CategoryListView(View):
    template="pages/category/category_view.html"
    def get(self, request):
        categories = Category.active_objects.all()
        context = {
            'categories': categories
        }
        return render(request, self.template, context)
    def post(self, request):
        print(request.POST)
        form = CategoryCreateForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.status = True              # Set status here
            category.save()
            return redirect('category_list')  # name of this view in your URLconf
        # If not valid, re-render with errors
        categories = Category.objects.all()
        return render(request, self.template, {
            'form': form,
            'categories': categories
        })
 

class CategoryEditView(View):
   def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        form = CategoryCreateForm(request.POST, instance=category)
        if form.is_valid():
            updated_category = form.save()

            return JsonResponse({
                'success': True,
                'message': 'Category updated successfully.',
                'data': {
                    'id': updated_category.id,
                    'name': updated_category.name,
                    'description': updated_category.description,
                    'product_code': updated_category.product_code,
                    'status': updated_category.status,
                }
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)

 