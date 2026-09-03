from django.urls import path

from . import views

urlpatterns = [
    path('', views.seat_map, name='seat_map'),
    path('api/availability/', views.availability, name='availability'),
    path('api/reservation/', views.reserve, name='reserve'),
    path('api/reservation/checkout/', views.checkout, name='checkout'),
]