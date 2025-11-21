# Local/urls.py (ACTUALIZADO)
from django.urls import path
from . import views # Importa las vistas de esta app

# Esto es crucial para que {% url 'local:panel' %} funcione
# Usamos 'local' en minúscula por convención para el namespace.
app_name = 'local' 

urlpatterns = [
    # La URL base (ej: /panel/) apuntará a la vista panel_local
    path('', views.panel_local, name='panel'), 

    # Las URLs del CRUD (Crear, Editar, Eliminar)
    path('producto/agregar/', views.producto_crear, name='producto_crear'),
    path('producto/<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('producto/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),

    # --- AÑADE ESTA LÍNEA ---
    # Esta es la URL que usará el botón "Marcar Entregado"
    path('marcar-entregado/', views.marcar_entregado, name='marcar_entregado'),
]