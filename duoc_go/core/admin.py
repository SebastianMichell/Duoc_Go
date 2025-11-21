from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, PagoJunaebOrder, WebpayOrder, Favorite, CartItem

# --- Para ver las Órdenes de tu equipo ---
@admin.register(PagoJunaebOrder)
class PagoJunaebOrderAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'user_identifier', 'rut', 'total', 'estado', 'hora_retiro', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion', 'hora_retiro')
    search_fields = ('user_identifier', 'rut', 'numero_orden')
    readonly_fields = ('numero_orden', 'fecha_creacion')

@admin.register(WebpayOrder)
class WebpayOrderAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'user_identifier', 'total', 'estado', 'hora_retiro', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion', 'hora_retiro')
    search_fields = ('user_identifier', 'numero_orden')
    readonly_fields = ('numero_orden', 'fecha_creacion') 

# --- Para ver los Usuarios (con rol "Local") ---
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Campos que se ven en la LISTA
    list_display = ('email', 'rut', 'username', 'tipo_usuario', 'local_asignado', 'is_staff')
    # Campos para FILTRAR
    list_filter = ('tipo_usuario', 'local_asignado', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'rut', 'username')
    ordering = ('email',)

    # (Formulario para EDITAR un usuario)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('email', 'rut')}),
        # --- CAMBIO ---
        ('Roles y Locales', {'fields': ('tipo_usuario', 'local_asignado')}), # <-- Actualizado
        # --- FIN CAMBIO ---
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )

    # (Formulario para AÑADIR un usuario)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'rut', 'password', 'password2', 'tipo_usuario', 'local_asignado', 'is_staff', 'is_superuser'),
        }),
    )

# Registra los otros modelos para que aparezcan en el admin
admin.site.register(Favorite)
admin.site.register(CartItem)