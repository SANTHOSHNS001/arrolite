from django.views import View
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import transaction, DatabaseError
from django.core.exceptions import ValidationError
from datetime import datetime
from django.db.models import Prefetch
from app.forms.expenses.expenses_form import ExpensesForm, ExpensesItemsForm, ExpensesTypesForm
from app.models.expenses.expenses_model import Expenses, ExpensesItems, ExpensesTypes
from django.utils import timezone
# ──────────────────────────────────────────────
# EXPENSES TYPE VIEWS
# ──────────────────────────────────────────────

class ExpensesTypeDetail(View):
    template = "pages/expenses/expenses_type_list.html"

    def get(self, request):
        context = {
            'expenses': Expenses.objects.select_related('expenses_type').all(),
            'expensestypes': ExpensesTypes.objects.filter(active=True),
        }
        return render(request, self.template, context)


class ExpensesTypesCreate(View):
    def post(self, request):
        form = ExpensesTypesForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.active = True
            obj.creator = request.user
            obj.save()
            return JsonResponse({'success': True, 'message': 'Expense type created successfully.'}, status=200)
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)


class ExpensesTypesUpdate(View):
    def post(self, request, pk):
        instance = get_object_or_404(ExpensesTypes, pk=pk)
        form = ExpensesTypesForm(request.POST, instance=instance)

        if form.is_valid():
            obj = form.save(commit=False) 
            obj.active = True
            obj.updated_by = request.user   # make sure field exists
            obj.updated_at = timezone.now() 
            obj.save()

            return JsonResponse({
                'success': True,
                'message': 'Expense type updated successfully.'
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


class ExpensesTypesDelete(View):
    def post(self, request, pk):
        instance = get_object_or_404(ExpensesTypes, pk=pk)
        try:
            with transaction.atomic():
                instance.delete(user=request.user)
            return JsonResponse({'success': True, 'message': 'Expense type deleted successfully.'}, status=200)
        except ValueError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Unexpected error: {str(e)}"}, status=500)


# ──────────────────────────────────────────────
# EXPENSES VIEWS
# ──────────────────────────────────────────────

class ExpensesViewList(View):
    template = "pages/expenses/expenses_list.html"

    def get(self, request):
        context = {
            'expenses': Expenses.objects.select_related('expenses_type').all().order_by("-created_at"),
            'expensestypes': ExpensesTypes.objects.filter(active=True),
        }
        return render(request, self.template, context) 

    def post(self, request):
        try:
            filters = {}

            expenses_type = request.POST.get("expenses_type", "").strip()
            due_date_str  = request.POST.get("due_date", "").strip()

            item_filters = {}

            if expenses_type:
                filters["expenses_type_id"] = expenses_type

            def parse_date(val):
                for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
                    try:
                        return datetime.strptime(val, fmt).date()
                    except ValueError:
                        continue
                raise ValueError("Invalid date")

            if due_date_str:
                if "to" in due_date_str:
                    start_str, end_str = [d.strip() for d in due_date_str.split("to", 1)]
                    try:
                        start_date = parse_date(start_str)
                        end_date = parse_date(end_str)

                        # ✅ parent filter
                        filters["items__due_date__range"] = (start_date, end_date)

                        # ✅ child filter (IMPORTANT FIX)
                        item_filters["due_date__range"] = (start_date, end_date)

                    except ValueError:
                        pass
                else:
                    try:
                        single_date = parse_date(due_date_str)

                        filters["items__due_date"] = single_date
                        item_filters["due_date"] = single_date

                    except ValueError:
                        pass

            # ✅ Apply filtered prefetch
            qs = (
                Expenses.objects
                .select_related('expenses_type')
                .prefetch_related(
                    Prefetch(
                        'items',
                        queryset=ExpensesItems.objects.filter(**item_filters)
                    )
                )
                .filter(**filters)
                .distinct()   # 🔥 IMPORTANT to avoid duplicates
                .order_by('-created_at')
            )
            data = []
            for expense in qs:
                payments = [
                    {
                        "id": item.id,
                        "amount": item.amount,
                        "invoice_number": item.invoice_number or "",
                        "due_date": str(item.due_date) if item.due_date else "",
                        "payment_mode": item.payment_mode or "",
                        "description": item.description or "",
                        "receipt": item.receipt.url if item.receipt else "",
                    }
                    for item in expense.items.all()   # ✅ now filtered
                ]

                data.append({
                    "id": expense.id,
                    "expenses_type": expense.expenses_type.name if expense.expenses_type else "",
                    "amount": expense.amount,
                    "company_name": expense.company_name or "",
                    "product_name": expense.product_name or "",
                    "description": expense.description or "",
                    "due_date": str(expense.due_date) if expense.due_date else "",
                    "expense_status": expense.expense_status,
                    "total_paid": expense.total_paid(),
                    "balance": expense.balance_amount(),
                    "payments": payments,
                })

            return JsonResponse({"success": True, "count": len(data), "data": data})

        except ValueError as e:
            return JsonResponse({"error": f"Invalid date format: {str(e)}"}, status=400)
        except DatabaseError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


class ExpensesCreate(View):
    def post(self, request):
        try:
            form = ExpensesForm(request.POST, request.FILES)
            if not form.is_valid():
                return JsonResponse({"success": False, "errors": form.errors.get_json_data()}, status=400)

            with transaction.atomic():
                expense = form.save(commit=False)
                expense.creator = request.user
                expense.save()

                # Always create a payment item.
                # deposit defaults to 0 if the user left it blank (meaning the expense is recorded but not yet paid).
                deposit = request.POST.get("deposit", "").strip()
                deposit_amount = float(deposit) if deposit else 0.0

                ExpensesItems.objects.create(
                    expenses       = expense,
                    amount         = deposit_amount,
                    invoice_number = request.POST.get("invoice_number", "").strip() or None,
                    due_date       = request.POST.get("due_date")  or None,
                    payment_mode   = request.POST.get("payment_mode", "upi"),
                    receipt        = request.FILES.get("receipt"),
                    description    = request.POST.get("description", "").strip() or None,
                )

                # Update status based on the new payment
                expense.update_status()

            return JsonResponse({
                "success": True,
                "message": "Expense created successfully.",
                "data": {
                    "id":       expense.id,
                    "total":    expense.amount,
                    "paid":     expense.total_paid(),
                    "balance":  expense.balance_amount(),
                    "status":   expense.expense_status,
                }
            }, status=201)

        except ValidationError as e:
            return JsonResponse({"success": False, "errors": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

# Add ExpensesItems
class ExpensesItemsCreate(View):
    def post(self, request):
        try:
            expense_id = request.POST.get("expense_id", "").strip()
            if not expense_id:
                return JsonResponse(
                    {"success": False, "errors": "expense_id is required."},
                    status=400
                )
 
            expense = get_object_or_404(Expenses, pk=expense_id)
 
            # Pass expense= so form.clean_amount() can check the balance
            form = ExpensesItemsForm(
                request.POST,
                request.FILES,
                expense=expense,
            )
 
            if not form.is_valid():
                return JsonResponse(
                    {"success": False, "errors": form.errors.get_json_data()},
                    status=400
                )
 
            with transaction.atomic():
                item          = form.save(commit=False)  # expenses not set yet — that's fine
                item.expenses = expense                  # set it NOW, before .save()
                item.creator  = request.user
                item.save()                              # model.clean() runs here, expenses_id is set
 
            return JsonResponse({
                "success": True,
                "message": "Payment added successfully.",
                "data": {
                    "expense_id": expense.id,
                    "total":      expense.amount,
                    "paid":       expense.total_paid(),
                    "balance":    expense.balance_amount(),
                    "status":     expense.expense_status,
                    "new_item": {
                        "id":             item.id,
                        "amount":         item.amount,
                        "invoice_number": item.invoice_number or "",
                        "due_date":       str(item.due_date) if item.due_date else "",
                        "payment_mode":   item.payment_mode  or "",
                        "description":    item.description   or "",
                        "receipt":        item.receipt.url   if item.receipt else "",
                    },
                },
            }, status=201)
 
        except ValidationError as e:
            return JsonResponse({"success": False, "errors": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
        
class ExpensesUpdate(View):
    def post(self, request, pk):
        expense = get_object_or_404(Expenses, pk=pk)
        form = ExpensesForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Expense updated successfully.'}, status=200)
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)


class ExpensesDelete(View):
    def post(self, request, pk):
        expense = get_object_or_404(Expenses, pk=pk)
        try:
            with transaction.atomic():
                expense.delete(user=request.user)
            return JsonResponse({'success': True, 'message': 'Expense deleted successfully.'}, status=200)
        except ValueError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Unexpected error: {str(e)}"}, status=500)