from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from app.models.category.category_model import Category
from django import forms

from app.models.unit.unit_model import Unit
 
class UnitListView(View):
    template="pages/unit/unit_view.html"
    def get(self, request):
        units = Unit.active_objects.all()
     
        context = {
            'units': units
        }
        return render(request, self.template, context)
    def post(self, request):
        print(request.POST)
        form = UnitCreateForm(request.POST)
        if form.is_valid():
            units = form.save(commit=False)
            units.status = True              # Set status here
            units.save()
            return redirect('unit_list')  # name of this view in your URLconf
        # If not valid, re-render with errors
        categories = Category.objects.all()
        return render(request, self.template, {
            'form': form,
            'categories': categories
        })
 

class UnitEditView(View):
   def post(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        form = UnitCreateForm(request.POST, instance=unit)
        if form.is_valid():
            unit = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Category updated successfully.',
                'data': {
                    'id': unit.id,
                    'name': unit.name,
                    'symbol': unit.symbol,
                    'status': unit.status,
                }
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)
        
        
        

class UnitCreateForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ['name', 'symbol','status']