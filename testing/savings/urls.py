from django.urls import path
from . import views

urlpatterns = [
    path("", views.savings_dashboard, name="savings_dashboard"),

    # Goals Form
    path("goal/form/", views.goal_form, name="add_goal"),
    path("goal/form/<int:id>/", views.goal_form, name="edit_goal"),

    # Delete Goals (with refund)
    path("goal/delete/<int:id>/", views.delete_goal, name="delete_goal"),
    path("delete-selected/", views.delete_selected_goals, name="delete_selected_goals"),
    path("delete-all/", views.delete_all_goals, name="delete_all_goals"),

]