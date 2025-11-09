from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import re
from django.conf import settings
from products_a.models import Product as ProductA
from products_b.models import Product as ProductB
import uuid
import json # Necesario para guardar el carrito como texto

# Validador de RUT
def validar_rut(value):
    patron = r'^\d{7,8}-[\dkK]$'
    if not re.match(patron, value):
        raise ValidationError("El RUT debe tener 7 u 8 dígitos seguidos de '-' y un verificador (0-9 o k).")

# Manager personalizado
# core/models.py

class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, rut=None, password=None, username=None, rol="estudiante", **extra_fields): # <-- 1. Añadir username
        if not email and not rut:
            raise ValueError("Debes ingresar un correo o un RUT")
        if not username: # <-- 2. Añadir validación
            raise ValueError("El nombre de usuario es obligatorio")
        
        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, rut=rut, username=username, tipo_usuario=rol, **extra_fields) # <-- 3. Añadir username
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, rut=None, password=None, username=None, **extra_fields): # <-- 4. Añadir username
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        
        # 5. Pasar username a create_user
        return self.create_user(email, rut, password, username, rol="profesor", **extra_fields)

# Modelo de usuario
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True)
    rut = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        validators=[validar_rut]
    )
    
    username = models.CharField(max_length=100, unique=True, verbose_name="Nombre de Usuario")
    
    tipo_usuario = models.CharField(
        max_length=10,
        choices=[("estudiante", "Estudiante"), ("profesor", "Profesor")],
        default="estudiante"
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email if self.email else self.rut

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100)
    product_image = models.URLField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_image = models.URLField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)


class PagoJunaebOrder(models.Model):
    # Campo para la API/Local: Número de orden único (contenido del QR)
    numero_orden = models.CharField(max_length=50, unique=True, editable=False) 
    
    # Campo para la imagen QR. Necesita que el settings.MEDIA_ROOT esté configurado.
    qr_code = models.ImageField(upload_to='qrcodes/junaeb/', blank=True, null=True)

    # Datos del pago
    # 🚨 CORRECCIÓN CLAVE: Referencia al modelo de usuario personalizado 🚨
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    user_identifier = models.CharField(max_length=100, default='Invitado')
    rut = models.CharField(max_length=12)
    clave_dinamica = models.CharField(max_length=4)
    hora_retiro = models.CharField(max_length=5) # Ejemplo: 10:30
    total = models.DecimalField(max_digits=10, decimal_places=0)

    # Detalle de la orden (guarda el carrito como JSON)
    detalle_carrito = models.TextField()

    # Estado de la orden
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Retiro'),
        ('RETIRADO', 'Producto Retirado'),
        ('CANCELADO', 'Cancelado')
    ]
    estado = models.CharField(max_length=10, choices=ESTADOS, default='PENDIENTE')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Generar numero_orden si es una nueva instancia
        if not self.numero_orden:
            # Generar un código corto basado en UUID (Ej: F8E9A1C5)
            self.numero_orden = str(uuid.uuid4()).replace('-', '')[:8].upper() 
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden Junaeb #{self.numero_orden} - {self.user_identifier}"

# core/models.py (Añadir esta nueva clase al final)

class WebpayOrder(models.Model):
    # Campos compartidos
    numero_orden = models.CharField(max_length=50, unique=True, editable=False)
    qr_code = models.ImageField(upload_to='qrcodes/webpay/', blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_identifier = models.CharField(max_length=100, default='Invitado')
    total = models.DecimalField(max_digits=10, decimal_places=0)
    detalle_carrito = models.TextField()
    
    # Reutilizamos los ESTADOS definidos en PagoJunaebOrder
    estado = models.CharField(max_length=10, choices=PagoJunaebOrder.ESTADOS, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Campo específico de Webpay: la hora se añade DESPUÉS del pago
    hora_retiro = models.CharField(max_length=5, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.numero_orden:
            self.numero_orden = str(uuid.uuid4()).replace('-', '')[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Webpay Orden #{self.numero_orden} - {self.user_identifier}"