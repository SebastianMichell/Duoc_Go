from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products_a/', blank=True, null=True)
    
    # --- AÑADE ESTOS 3 CAMPOS NUEVOS AQUÍ ---
    precio_especial = models.DecimalField(
        max_digits=10, 
        decimal_places=0, # O 2, si quieres centavos en la oferta
        null=True, 
        blank=True, 
        verbose_name="Precio Especial (Oferta)"
    )
    fecha_inicio_especial = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Inicio de la Oferta"
    )
    fecha_fin_especial = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Fin de la Oferta"
    )
    # --- FIN DE CAMPOS NUEVOS ---

    def __str__(self):
        return self.name