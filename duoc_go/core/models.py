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
import json 

def validar_rut(value):
    patron = r'^\d{7,8}-[\dkK]$'
    if not re.match(patron, value):
        raise ValidationError("El RUT debe tener 7 u 8 dígitos seguidos de '-' y un verificador (0-9 o k).")

class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, rut=None, password=None, username=None, rol="estudiante", **extra_fields): 
        if not email and not rut:
            raise ValueError("Debes ingresar un correo o un RUT")
        if not username: 
            raise ValueError("El nombre de usuario es obligatorio")
        
        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, rut=rut, username=username, tipo_usuario=rol, **extra_fields) 
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, rut=None, password=None, username=None, **extra_fields): 
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, rut, password, username, rol="local", **extra_fields)

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
    
    TIPO_USUARIO_CHOICES = [
        ("estudiante", "Estudiante"),
        ("local", "Local"),
    ]
    tipo_usuario = models.CharField(
        max_length=10,
        choices=TIPO_USUARIO_CHOICES, 
        default="estudiante"
    )

    LOCAL_ASIGNADO_CHOICES = [
        ('a', 'Local 1 (Base de Datos A)'),
        ('b', 'Local 2 (Base de Datos B)'),
    ]
    local_asignado = models.CharField(
        max_length=1,
        choices=LOCAL_ASIGNADO_CHOICES,
        null=True,
        blank=True 
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

    product_id = models.IntegerField(default=0) 
    origin = models.CharField(max_length=1, default='a') 
    
    product_name = models.CharField(max_length=100)
    product_image = models.CharField(max_length=255, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product_id', 'origin') 

    def __str__(self):
        return f"{self.user.username} - {self.product_name}"

class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_image = models.URLField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)


ESTADOS_ORDEN = [
    ('PENDIENTE', 'Pendiente de Retiro'),
    ('RETIRADO', 'Producto Retirado'),
    ('CANCELADO', 'Cancelado')
]


ESTADOS_ITEM_LOCAL = [
    ('PENDIENTE', 'Pendiente'),
    ('RETIRADO', 'Retirado'),
    ('NA', 'No Aplica'), 
]



class PagoJunaebOrder(models.Model):
    numero_orden = models.CharField(max_length=50, unique=True, editable=False) 
    qr_code = models.ImageField(upload_to='qrcodes/junaeb/', blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    user_identifier = models.CharField(max_length=100, default='Invitado')
    rut = models.CharField(max_length=12)
    clave_dinamica = models.CharField(max_length=4)
    hora_retiro = models.CharField(max_length=5)
    total = models.DecimalField(max_digits=10, decimal_places=0)
    detalle_carrito = models.TextField()
    
    estado = models.CharField(max_length=10, choices=ESTADOS_ORDEN, default='PENDIENTE')
    
    estado_local_a = models.CharField(
        max_length=10, 
        choices=ESTADOS_ITEM_LOCAL, 
        default='NA', 
        verbose_name="Estado Local A"
    )
    estado_local_b = models.CharField(
        max_length=10, 
        choices=ESTADOS_ITEM_LOCAL, 
        default='NA', 
        verbose_name="Estado Local B"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.numero_orden:
            self.numero_orden = str(uuid.uuid4()).replace('-', '')[:8].upper() 
        
        if self.pk is None and self.detalle_carrito:
            try:
                carrito = json.loads(self.detalle_carrito)
                tiene_local_a = any(item.get('origen') == 'a' for item in carrito)
                tiene_local_b = any(item.get('origen') == 'b' for item in carrito)
                
                if tiene_local_a:
                    self.estado_local_a = 'PENDIENTE'
                if tiene_local_b:
                    self.estado_local_b = 'PENDIENTE'
            except json.JSONDecodeError:
                pass 
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden Junaeb #{self.numero_orden} - {self.user_identifier}"


class WebpayOrder(models.Model):
    numero_orden = models.CharField(max_length=50, unique=True, editable=False)
    qr_code = models.ImageField(upload_to='qrcodes/webpay/', blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_identifier = models.CharField(max_length=100, default='Invitado')
    total = models.DecimalField(max_digits=10, decimal_places=0)
    detalle_carrito = models.TextField()
    
    estado = models.CharField(max_length=10, choices=ESTADOS_ORDEN, default='PENDIENTE')
    
    estado_local_a = models.CharField(
        max_length=10, 
        choices=ESTADOS_ITEM_LOCAL, 
        default='NA', 
        verbose_name="Estado Local A"
    )
    estado_local_b = models.CharField(
        max_length=10, 
        choices=ESTADOS_ITEM_LOCAL, 
        default='NA', 
        verbose_name="Estado Local B"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    hora_retiro = models.CharField(max_length=5, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.numero_orden:
            self.numero_orden = str(uuid.uuid4()).replace('-', '')[:8].upper()
            
        if self.pk is None and self.detalle_carrito:
            try:
                carrito = json.loads(self.detalle_carrito)
                tiene_local_a = any(item.get('origen') == 'a' for item in carrito)
                tiene_local_b = any(item.get('origen') == 'b' for item in carrito)
                
                if tiene_local_a:
                    self.estado_local_a = 'PENDIENTE'
                if tiene_local_b:
                    self.estado_local_b = 'PENDIENTE'
            except json.JSONDecodeError:
                pass 
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Webpay Orden #{self.numero_orden} - {self.user_identifier}"



class LocalProfile(models.Model):
    local_id = models.CharField(max_length=1, unique=True, choices=CustomUser.LOCAL_ASIGNADO_CHOICES)
    nombre_local = models.CharField(max_length=100, default="Mi Local")
    descripcion = models.TextField(blank=True, default="Descripción del local...")
    logo = models.ImageField(upload_to='logos_locales/', blank=True, null=True)

    color_banner = models.CharField(max_length=7, default="#004aad")
    
    def __str__(self):
        return f"Perfil de {self.get_local_id_display()}"

class CarouselItem(models.Model):
    # Quién subió la promo
    local_id = models.CharField(max_length=1, choices=CustomUser.LOCAL_ASIGNADO_CHOICES)
    
    imagen = models.ImageField(upload_to='carrusel_promos/')
    titulo = models.CharField(max_length=100, blank=True)
    subtitulo = models.CharField(max_length=200, blank=True)
    
    # Lógica del Link
    TIPO_LINK_CHOICES = [
        ('tienda', 'Ir a mi Tienda'),
        ('producto', 'Ir a un Producto Específico'),
    ]
    tipo_link = models.CharField(max_length=10, choices=TIPO_LINK_CHOICES, default='tienda')
    producto_id = models.IntegerField(default=0, help_text="ID del producto (solo si eliges 'Producto Específico')", blank=True)
    
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Promo {self.titulo} ({self.local_id})"