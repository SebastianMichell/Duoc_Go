from django.contrib.auth.backends import ModelBackend
from .models import CustomUser


class EmailOrRUTBackend(ModelBackend):
    """
    Permite login con correo o RUT
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Primero buscar por correo
            user = CustomUser.objects.filter(email=username).first()
            if not user:
                # Si no existe, buscar por RUT
                user = CustomUser.objects.filter(rut=username.lower()).first()

            if user and user.check_password(password):
                return user
        except CustomUser.DoesNotExist:
            return None
        return None
