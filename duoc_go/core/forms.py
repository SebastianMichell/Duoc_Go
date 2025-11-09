from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import re

# Formulario de registro
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


# Formulario de login
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



from django import forms
from django.core.exceptions import ValidationError
import re

class PagoJunaebForm(forms.Form):
    """Formulario para ingresar datos de pago con Tarjeta Junaeb (Beca BAES)."""
    
    # Campo AÑADIDO: Se llenará con las opciones generadas en la vista
    hora_retiro = forms.ChoiceField(
        label="Hora de Retiro Aproximada",
        choices=[], # Las opciones se definen en __init__
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Campo para el RUT (Ej: 12345678-K)
    rut = forms.CharField(
        label="RUT (Sin puntos ni guiones)",
        max_length=9,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: 12345678K'})
    )

    # Campo para la clave dinámica de 4 dígitos
    clave_dinamica = forms.CharField(
        label="Clave Dinámica (4 dígitos)",
        max_length=4,
        widget=forms.PasswordInput(attrs={'placeholder': 'Ej: 1234'})
    )
    
    # Método __init__ para permitir la inyección de las opciones de hora
    def __init__(self, *args, **kwargs):
        hora_choices = kwargs.pop('hora_choices', None)
        super().__init__(*args, **kwargs)
        if hora_choices:
            self.fields['hora_retiro'].choices = hora_choices

    # ... (Los métodos clean_rut y clean_clave_dinamica se mantienen iguales)
    # ...

    def clean_rut(self):
        rut = self.cleaned_data.get('rut').upper()
        
        # 1. Validación de formato general
        if not re.match(r'^\d{8}[0-9K]$', rut):
            raise ValidationError(
                "El formato de RUT debe ser: 8 dígitos numéricos, seguidos de un dígito verificador (número o K)."
            )

        # 2. Validación de dígito verificador
        digito_verificador = rut[-1]
        
        if len(rut) != 9:
             raise ValidationError("El RUT debe tener exactamente 9 caracteres (8 dígitos + verificador).")
        
        if not (digito_verificador.isdigit() and 1 <= int(digito_verificador) <= 9 or digito_verificador == 'K'):
            raise ValidationError("El dígito verificador debe ser un número del 1 al 9 o la letra K.")
            
        return rut

    def clean_clave_dinamica(self):
        clave = self.cleaned_data.get('clave_dinamica')
        
        # 1. Validación de longitud y tipo
        if not clave.isdigit() or len(clave) != 4:
            raise ValidationError("La clave dinámica debe ser de 4 dígitos numéricos.")
            
        return clave