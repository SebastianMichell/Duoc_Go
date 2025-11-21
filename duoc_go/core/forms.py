from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import re
from products_a.models import Product as ProductA
from products_b.models import Product as ProductB


class RegistroForm(UserCreationForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        help_text="Debe tener al menos 8 caracteres, no ser demasiado común, no ser solo números y no ser similar a tu información personal."
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput
    )

    class Meta:
        model = CustomUser
        fields = ['username',"email", "rut", "tipo_usuario", "password1", "password2"]

    def clean_rut(self):
        rut = self.cleaned_data.get("rut")
        if rut:
            rut = rut.lower()
        return rut

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        validate_password(password, self.instance)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden")


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Correo o RUT")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            self.is_profesor_login = username.endswith("@profesor.duoc")
        else:
            self.is_profesor_login = False
        return username


class PagoJunaebForm(forms.Form):
    """Formulario para ingresar datos de pago con Tarjeta Junaeb (Beca BAES)."""
    
    hora_retiro = forms.ChoiceField(
        label="Hora de Retiro Aproximada",
        choices=[], 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    rut = forms.CharField(
        label="RUT (Sin puntos ni guiones)",
        max_length=9,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: 12345678K'})
    )

    clave_dinamica = forms.CharField(
        label="Clave Dinámica (4 dígitos)",
        max_length=4,
        widget=forms.PasswordInput(attrs={'placeholder': 'Ej: 1234'})
    )
    
    def __init__(self, *args, **kwargs):
        hora_choices = kwargs.pop('hora_choices', None)
        super().__init__(*args, **kwargs)
        if hora_choices:
            self.fields['hora_retiro'].choices = hora_choices

    def clean_rut(self):
        rut = self.cleaned_data.get('rut').upper()
        
        if not re.match(r'^\d{8}[0-K]$', rut):
            raise ValidationError(
                "El formato de RUT debe ser: 8 dígitos numéricos, seguidos de un dígito verificador (número o K)."
            )

        digito_verificador = rut[-1]
        
        if len(rut) != 9:
                raise ValidationError("El RUT debe tener exactamente 9 caracteres (8 dígitos + verificador).")
        
        if not (digito_verificador.isdigit() and 1 <= int(digito_verificador) <= 9 or digito_verificador == 'K'):
            raise ValidationError("El dígito verificador debe ser un número del 1 al 9 o la letra K.")
            
        return rut

    def clean_clave_dinamica(self):
        clave = self.cleaned_data.get('clave_dinamica')
        
        if not clave.isdigit() or len(clave) != 4:
            raise ValidationError("La clave dinámica debe ser de 4 dígitos numéricos.")
            
        return clave


class ProductAForm(forms.ModelForm):
    
    class Meta:
        model = ProductA
        fields = [
            'name', 'description', 'price', 'stock', 'image', 
            'precio_especial', 'fecha_inicio_especial', 'fecha_fin_especial'
        ]
        labels = {
            'name': 'Nombre del Producto',
            'description': 'Descripción',
            'price': 'Precio Regular',
            'stock': 'Stock Disponible',
            'image': 'Imagen del Producto',
            'precio_especial': 'Precio de Oferta (Opcional)',
            'fecha_inicio_especial': 'Inicio de la Oferta (Opcional)',
            'fecha_fin_especial': 'Fin de la Oferta (Opcional)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            

            'precio_especial': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_inicio_especial': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), 
            'fecha_fin_especial': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("fecha_inicio_especial")
        fin = cleaned_data.get("fecha_fin_especial")
        precio = cleaned_data.get("precio_especial")

        if precio and (not inicio or not fin):
            self.add_error(None, "Si defines un precio de oferta, debes definir la fecha de inicio y fin.")
        
        if (inicio or fin) and not precio:
            self.add_error(None, "Si defines fechas de oferta, debes definir un precio de oferta.")

        if inicio and fin and fin < inicio:
            self.add_error('fecha_fin_especial', "La fecha de fin de la oferta no puede ser anterior a la fecha de inicio.")
            
        return cleaned_data


class ProductBForm(forms.ModelForm):

    class Meta:
        model = ProductB
        fields = [
            'name', 'description', 'price', 'stock', 'image', 
            'precio_especial', 'fecha_inicio_especial', 'fecha_fin_especial'
        ]
        labels = {
            'name': 'Nombre del Producto',
            'description': 'Descripción',
            'price': 'Precio Regular',
            'stock': 'Stock Disponible',
            'image': 'Imagen del Producto',
            'precio_especial': 'Precio de Oferta (Opcional)',
            'fecha_inicio_especial': 'Inicio de la Oferta (Opcional)',
            'fecha_fin_especial': 'Fin de la Oferta (Opcional)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            
            'precio_especial': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_inicio_especial': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin_especial': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("fecha_inicio_especial")
        fin = cleaned_data.get("fecha_fin_especial")
        precio = cleaned_data.get("precio_especial")

        if precio and (not inicio or not fin):
            self.add_error(None, "Si defines un precio de oferta, debes definir la fecha de inicio y fin.")
        
        if (inicio or fin) and not precio:
            self.add_error(None, "Si defines fechas de oferta, debes definir un precio de oferta.")

        if inicio and fin and fin < inicio:
            self.add_error('fecha_fin_especial', "La fecha de fin de la oferta no puede ser anterior a la fecha de inicio.")
            
        return cleaned_data