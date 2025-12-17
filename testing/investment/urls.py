from django.urls import path
from . import views

urlpatterns = [
    path('', views.investment_list, name='investment_list'),
    path('add/', views.add_investment, name='add_investment'),
    path('edit/<int:id>/', views.edit_investment, name='edit_investment'),
    path('delete/<int:id>/', views.delete_investment, name='delete_investment'),
    path("portfolio/", views.investment_portfolio, name="investment_portfolio"),
    path('get-expected-return/', views.get_expected_return, name='get_expected_return'),
    path('delete-all/', views.delete_all_investments, name='delete_all_investments'),

]
