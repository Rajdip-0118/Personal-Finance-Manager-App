from django.urls import path
from . import views

urlpatterns = [
    path("", views.budget_list, name="budget_list"),
    path("add/", views.add_budget, name="add_budget"),
    path("edit/<int:budget_id>/", views.edit_budget, name="edit_budget"),
    path("<int:budget_id>/", views.budget_detail, name="budget_detail"),
    path("<int:budget_id>/add-category/", views.add_category, name="add_category"),
    path('category/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path("delete-selected/", views.delete_selected_budgets, name="delete_selected_budgets"),
    path("delete-all/", views.bulk_delete_budget, name="bulk_delete_budget"),
    path("delete-categories/", views.bulk_delete_categories, name="bulk_delete_categories"),
    path("delete-selected-categories/", views.delete_selected_categories, name="delete_selected_categories"),
]
