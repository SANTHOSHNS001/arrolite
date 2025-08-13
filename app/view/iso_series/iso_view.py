from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from django import forms

from app.models.iso_series.iso_series_model import ISOSize
 
 
class ISOSizeListView(View):
    template="pages/iso_series/iso_size_view.html"
    def get(self, request):
        isosizes = ISOSize.active_objects.all()
     
        context = {
            'isosizes': isosizes,
            'series_choices': ISOSize.SERIES_CHOICES
        }
        return render(request, self.template, context)
    def post(self, request):
        print(request.POST)
        post_data = request.POST.copy()
        post_data['status'] = True
        form = IsoSizeCreateForm(post_data)
        if form.is_valid():
            units = form.save()
            return redirect('iso_list')  # name of this view in your URLconf
        # If not valid, re-render with errors
        isosizes = ISOSize.active_objects.all()
        return render(request, self.template, {
            'form': form,
            'isosizes': isosizes
        })
 

class ISOSizeEditView(View):
   def post(self, request, pk):
        isosize = get_object_or_404(ISOSize, pk=pk)
        form = IsoSizeCreateForm(request.POST, instance=isosize)
        if form.is_valid():
            isosize = form.save()
            return JsonResponse({
                'success': True,
                'message': 'ISOSize updated successfully.',
                'data': {}
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)
        
        
        

class IsoSizeCreateForm(forms.ModelForm):
    class Meta:
        model = ISOSize
        fields = ['name', 'series','width_mm','height_mm','status']