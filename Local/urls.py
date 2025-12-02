# Local/urls.py (ACTUALIZADO)
from django.urls import path
from . import views 

app_name = 'local' 

urlpatterns = [
    path('', views.panel_local, name='panel'), 
    path('producto/agregar/', views.producto_crear, name='producto_crear'),
    path('producto/<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('producto/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('marcar-entregado/', views.marcar_entregado, name='marcar_entregado'),
    path('configuracion/', views.configuracion_local, name='configuracion_local'),
    path('carrusel/', views.gestion_carrusel, name='gestion_carrusel'),
    path('carrusel/eliminar/<int:pk>/', views.eliminar_promo, name='eliminar_promo'),
    path('historial/', views.historial_ventas, name='historial_ventas'),
]

