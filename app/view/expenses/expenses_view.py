
import calendar
from datetime import datetime
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from app.forms.expenses.expenses_form import ExpensesForm, ExpensesTypesForm
from app.models.expenses.expenses_model import Expenses, ExpensesTypes


class ExpensesTypeDetail(View):
    
    template="pages/expenses/expenses_type_list.html"
    def get(self, request):
        expenses = Expenses.active_objects.all()
        expensestypes = ExpensesTypes.active_objects.all()
        # pending_list=RecycleEence_datas()
        context = {
            'expenses': expenses,
            'expensestypes':expensestypes,
            # 'expenses_pending':pending_list
        }
        return render(request, self.template, context)

class ExpensesTypesCreate(View):
    
    def post(self, request):
        form = ExpensesTypesForm(request.POST)
       
        if form.is_valid():
            expensestypes = form.save(commit=False)
            expensestypes.active = True  
            expensestypes.creator = request.user 
            # Set status here
            expensestypes.save()
            return JsonResponse({
                'success': True,
                'message': 'ExpensesTypes Create successfully.',
                'data': {
                     
                }
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)
     
class ExpensesTypesUpdate(View):
    def post(self, request,pk):
        expensestype = get_object_or_404(ExpensesTypes, pk=pk)
        form = ExpensesTypesForm(request.POST, instance=expensestype)
        if form.is_valid():
            expensestypes = form.save(commit=False)
            expensestypes.active = True              # Set status here
            expensestypes.save()
            return JsonResponse({
                'success': True,
                'message': 'ExpensesTypes Update successfully.',
                'data': {}
                
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)

class ExpensesTypesDelete(View):
    def post(self, request):
        form = ExpensesForm(request.POST)
        if form.is_valid():
            expensestypes = form.save( )
             
            return JsonResponse({
                'success': True,
                'message': 'Expenses Create successfully.',
                'data': {
                     
                }
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)

class ExpensesCreate(View):
    def post(self, request):
        form = ExpensesForm(request.POST,request.FILES)
        if form.is_valid():
            expensestypes = form.save(commit=False)
            expensestypes.creator = request.user 
            # Set status here
            expensestypes.save()
            return JsonResponse({
                'success': True,
                'message': 'Expenses Create successfully.',
                'data': {  
                }
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)
     
class ExpensesUpdate(View):
    def post(self, request,pk):
        expense = get_object_or_404(Expenses, pk=pk)
        form = ExpensesTypesForm(request.POST, instance=expense)
        if form.is_valid():
            expensestypes = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Expenses Update successfully.',
                'data': {}
                
            }, status=200)

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)
class ExpensesViewList(View):
    template="pages/expenses/expenses_list.html"
    def get(self, request):
        expenses = Expenses.active_objects.all()
        expensestypes = ExpensesTypes.active_objects.all()
        # pending_list=RecycleEence_datas()
        context = {
            'expenses': expenses,
            'expensestypes':expensestypes,
            # 'expenses_pending':pending_list
        }
        return render(request, self.template, context)
    def post(self, request):
        try:
            filters = {}
            print("Post -List",request.POST)
            expenses_type = request.POST.get("expenses_type")
            quotation_ids = request.POST.getlist("quotation")
            request_date_str = request.POST.get("due_date")
            if quotation_ids:
                quotation_ids = quotation_ids
                filters["id__in"] = quotation_ids
                
            if expenses_type:
                filters["expenses_type"] = expenses_type
             

            
            if request_date_str:
                try:
                
                    if isinstance(request_date_str, list):
                        request_date_str = request_date_str[0]

                    request_date_str = request_date_str.strip()

                    if "to" in request_date_str:  # Date range case: "01-09-2025 to 06-09-2025"
                        start_str, end_str = [d.strip() for d in request_date_str.split("to")]
                        filters["due_date__range"] = (
                            datetime.strptime(start_str, "%d-%m-%Y").date(),
                            datetime.strptime(end_str, "%d-%m-%Y").date()
                        )
                    else:  # Single date case: "2025-09-06"
                        filters["due_date"] = datetime.strptime(request_date_str, "%Y-%m-%d").date()

                except ValueError:
                    return JsonResponse(
                        {"error": "Invalid date format. Use YYYY-MM-DD or DD-MM-YYYY to DD-MM-YYYY"},
                        status=400
                    )

            # Query database
            expenses_qs = (Expenses.active_objects.filter(**filters))     
                                          
            data = [
                    {
                        "id": q.id,
                        "expenses_type":q.expenses_type.name,
                        "amount":q.amount,
                        "due_date":q.due_date,
                        "receipt":q.receipt.url if q.receipt else '',
                        "description":q.description
                        
                    }
                        for q in expenses_qs
            ]
            return JsonResponse({
                "message": "Invoice fetched successfully",
                "count": len(data),
                "data": data
            })

        except DatabaseError as db_err:
            return JsonResponse({"error": f"Database error: {str(db_err)}"}, status=500)
        
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

class ExpensesDelete(View):
    pass


import datetime
from django.db.models import Q
 

def RecycleEence_datas():
    today = datetime.date.today()
    current_year, current_month, current_day = today.year, today.month, today.day
    current_weekday = today.weekday()

    result = {}

    expenses_types = ExpensesTypes.active_objects.filter(is_recurring=True).distinct()

    for et in expenses_types:
        recurrence_type = et.recurrence_type
        recurrence_day = et.recurrence_day
        start_date, end_date = et.reminder_start, et.reminder_end

        # default
        status, due_date = "No Recurrence", None

        # check reminder range
        if start_date and today < start_date:
            result[et.name] = {"status": "Not Started", "due_date": str(start_date)}
            continue
        if end_date and today > end_date:
            result[et.name] = {"status": "Expired", "due_date": str(end_date)}
            continue

        # ---------------- Due date calculation ----------------
        if recurrence_type == "daily":
            due_date = today

        elif recurrence_type == "weekly":
            days_ahead = (recurrence_day - current_weekday) % 7
            due_date = today + datetime.timedelta(days=days_ahead)

        elif recurrence_type == "monthly":
            try:
                due_date = datetime.date(current_year, current_month, recurrence_day)
            except ValueError:
                last_day = calendar.monthrange(current_year, current_month)[1]
                due_date = datetime.date(current_year, current_month, last_day)

        elif recurrence_type == "yearly":
            recurrence_month = recurrence_day or current_month
            due_date = datetime.date(current_year, recurrence_month, 1)

        # ---------------- Expense check ----------------
        if due_date:
            exists = Expenses.active_objects.filter(
                expenses_type=et,
                due_date=due_date
            ).exists()

            if exists:
                status = "Complete"
            else:
                if due_date < today:
                    status = "Pending"
                elif due_date == today:
                    status = "Pending"
                else:
                    status = "Upcoming"

        result[et.name] = {"status": status, "due_date": str(due_date) if due_date else None}

    return result
# sample 
# # "EMI":{"status:"pending"","due_date":"date"}
# }