from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Rutas de seguridad
    path('login/', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Tus rutas existentes
    path('', views.dashboard_home, name='dashboard_home'), 
    path('estudiantes/', views.lista_estudiantes, name='estudiantes'),
    path('alertas/', views.dashboard_alertas, name='alertas_ia'),
    path('estadisticas/', views.estadisticas, name='estadisticas'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('exportar-estudiantes/', views.exportar_estudiantes, name='exportar_estudiantes'),
    
    # --- NUEVA RUTA PARA CREAR ESTUDIANTE ---
    path('estudiantes/nuevo/', views.nuevo_estudiante, name='nuevo_estudiante'),
]