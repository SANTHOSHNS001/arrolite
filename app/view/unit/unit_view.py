from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from app.forms.unit.unit_form import UnitForm
from app.models.unit.unit_model import Unit
class UnitcreateView(View):
    template = "pages/unit/unit.html"

    def get(self, request):
        units = Unit.active_objects.all()
        return render(request, self.template, {'units': units})

    def post(self, request):
        name = request.POST.get('name')
        symbol = request.POST.get('symbol')
        if name and symbol:
            Unit.objects.create(name=name, symbol=symbol)
        return redirect('home')



class UnitEditView(View):
    template_name = 'pages/unit/edit_unit.html'

    def get(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        context = {'unit': unit}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        unit.name = request.POST.get('name')
        unit.symbol = request.POST.get('symbol')
        unit.save()
        return redirect('unit_list')  # Make sure this name matches your list view
        

class UnitDeleteView(View):
    def get(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        unit.delete()
        return redirect('unit_list')