from django.urls import path,include
from .views import home, registro, login_view, logout_view,seleccionar_hora_webpay
from rest_framework import routers
from . import views

# Inicializa el Router de DRF
router = routers.DefaultRouter()
# Registra el ViewSet con el prefijo 'junaeb-ordenes'
router.register(r'junaeb-ordenes', views.OrdenesPendientesViewSet, basename='junaeb-ordenes')


urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('auth-options/', views.auth_options, name='auth_options'),
    path('usuario/', views.user_redirect_view, name='usuario_redirect'),
    path('carrito/', views.ver_carrito, name='carrito'),
    path('agregar-carrito/<str:origen>/<int:producto_id>/', views.agregar_al_carrito, name='agregar_carrito'),
    path('carrito/eliminar/<str:unique_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('pago/junaeb/', views.pago_junaeb, name='pago_junaeb'),
    path('pago/junaeb/exito/', views.pago_exitoso_junaeb, name='pago_exitoso_junaeb'),
    path('api/', include(router.urls)), 


    path('pago/', views.iniciar_pago, name='iniciar_pago'),
    path('pago/exito/', views.pago_exito, name='pago_exito'),
    path('pago/seleccionar-hora/', views.seleccionar_hora_webpay, name='seleccionar_hora_webpay'),


    path('panel/', include('Local.urls')),
]