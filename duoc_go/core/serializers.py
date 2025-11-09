# core/serializers.py

from rest_framework import serializers
from .models import PagoJunaebOrder
import json

class PagoJunaebOrderSerializer(serializers.ModelSerializer):
    # Campo personalizado para mostrar el detalle del carrito como un objeto
    # Si lo guardaste como JSON string, debes parsearlo antes de enviarlo
    detalle_carrito_parsed = serializers.SerializerMethodField()

    class Meta:
        model = PagoJunaebOrder
        # Campos que la API va a exponer
        fields = (
            'id', 
            'numero_orden', 
            'estado', 
            'hora_retiro', 
            'rut', 
            'clave_dinamica',
            'total', 
            'user_identifier', 
            'fecha_creacion',
            'detalle_carrito_parsed' # Usaremos el método que creamos abajo
        )
        # Opcional: puedes usar fields = '__all__' si quieres exponer todos.

    def get_detalle_carrito_parsed(self, obj):
        # Deserializa la cadena JSON guardada en detalle_carrito para que sea un objeto JSON válido
        try:
            return json.loads(obj.detalle_carrito)
        except (TypeError, json.JSONDecodeError):
            return {"error": "Detalle de carrito no válido."}