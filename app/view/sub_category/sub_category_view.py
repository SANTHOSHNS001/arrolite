from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect

from app.forms.sub_category.sub_category_form import SubCategoryCreateForm
from app.models.category.category_model import Category
from app.models.sub_category.sub_category_model import SubCategory
# from app.forms.category.category_form import CategoryCreateForm
# from app.models.category.category_model import Category
 
 
class SubCategoryListView(View):
    template="pages/sub_category/sub_category.html"
    def get(self, request):
        subcategories = SubCategory.active_objects.all()
        categories = Category.active_objects.all()
        context = {
            'subcategories': subcategories,
            'categories' :categories
        }
        return render(request, self.template, context)
    def post(self, request):
        form = SubCategoryCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('sub_category_list')  # name of this view in your URLconf
        # If not valid, re-render with errors
        sub_categories = SubCategory.active_objects.all()
        return render(request, self.template, {
            'form': form,
            'subcategories': sub_categories
        })
 

class SubCategoryEditView(View):
   def post(self, request, pk):
        subcategory = get_object_or_404(SubCategory, pk=pk)
        form = SubCategoryCreateForm(request.POST, instance=subcategory)
        if form.is_valid():
            updated_category = form.save()

            return JsonResponse({
                'success': True,
                'message': 'SubCategory updated successfully.',
                'data': {
                   
                }
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)

 