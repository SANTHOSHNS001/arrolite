import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from app.models.invoice_model.invoice_model import QuotationReportGenerator

def get_config():
    obj = QuotationReportGenerator.objects.first()

    if not obj:
        obj = QuotationReportGenerator.objects.create()

    return obj
class QuotationReportConfigView(LoginRequiredMixin, View):

    # ✅ GET (fetch config)
    def get(self, request):
        obj = get_config()

        return JsonResponse({
            "success": True,
            "data": {
                "id": obj.id,
                "is_tagged": obj.is_tagged,
                "label": obj.label
            }
        })

    # ✅ UPDATE ONLY
    def post(self, request):
        try:
            obj = get_config()

            data = json.loads(request.body)

            # 🔹 update is_tagged
            if "is_tagged" in data:
                obj.is_tagged = data.get("is_tagged")

            # 🔹 update label (merge)
            if "label" in data:
                new_label = data.get("label", {})

                if not isinstance(new_label, dict):
                    return JsonResponse({
                        "success": False,
                        "error": "label must be JSON object"
                    }, status=400)

                current = obj.label or {}
                current.update(new_label)
                obj.label = current

            obj.save()

            return JsonResponse({
                "success": True,
                "message": "Updated successfully",
                "data": {
                    "id": obj.id,
                    "is_tagged": obj.is_tagged,
                    "label": obj.label
                }
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=400)