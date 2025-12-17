from django.urls import path
from . import views

urlpatterns = [
    path("predict_expense_category/", views.predict_expense_category, name="predict_expense_category"),
    path("predict_income_category/", views.predict_income_category, name="predict_income_category"),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('add_expense/', views.add_expense, name='add_expense'),
    path('add_income/', views.add_income, name='add_income'),
    
    path('income/edit/<int:id>/', views.edit_income, name='edit_income'),
    path('income/delete/<int:id>/', views.delete_income, name='delete_income'),

    path('expense/edit/<int:id>/', views.edit_expense, name='edit_expense'),
    path('expense/delete/<int:id>/', views.delete_expense, name='delete_expense'),

    path('expense_log/', views.expense_log, name='expense_log'),
    path('income_history/', views.income_history, name='income_history'),
    path('recurring_expense/', views.recurring_expense, name='recurring_expense'),
    path('recurring_income/', views.recurring_income, name='recurring_income'),
    
    path('recurring-expense/edit/<int:id>/', views.edit_recurring_expense, name='edit_recurring_expense'),
    path('recurring-expense/delete/<int:id>/', views.delete_recurring_expense, name='delete_recurring_expense'),
    path('recurring-income/edit/<int:id>/', views.edit_recurring_income, name='edit_recurring_income'),
    path('recurring-income/delete/<int:id>/', views.delete_recurring_income, name='delete_recurring_income'),

    path('upload_expense_csv/', views.upload_expense_csv, name='upload_expense_csv'),
    path('upload_income_csv/', views.upload_income_csv, name='upload_income_csv'),
    path('upload_bank_statement/', views.upload_bank_statement, name='upload_bank_statement'),
    path("income/bulk-delete/", views.bulk_delete_income, name="bulk_delete_income"),
    path("income/delete-selected/", views.delete_selected_incomes, name="delete_selected_incomes"),
    path("expense/bulk-delete/", views.bulk_delete_expense, name="bulk_delete_expense"),
    path("expense/delete-selected/", views.delete_selected_expenses, name="delete_selected_expenses"),

]
