from django.urls import path

from . import views

urlpatterns = [
  path('', views.home, name='home'),
  path('inscription/', views.register_view, name='register'),
  path('connexion/', views.login_view, name='login'),
  path('deconnexion/', views.logout_view, name='logout'),
  path('dashboard/', views.dashboard_view, name='dashboard'),
  path('cultures/nouvelle/', views.exploitation_create_view, name='exploitation_create'),
  path('cultures/<int:pk>/analyser/', views.exploitation_analyse_view, name='exploitation_analyse'),
  path('analyses/', views.analyses_list_view, name='analyses_list'),
  path('analyses/<int:pk>/', views.analyse_detail_view, name='analyse_detail'),
]
