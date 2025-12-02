# core/serializers.py

from rest_framework import serializers
from .models import PagoJunaebOrder
import json

class PagoJunaebOrderSerializer(serializers.ModelSerializer):
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
            'detalle_carrito_parsed' 
        )

    def get_detalle_carrito_parsed(self, obj):
        try:
            return json.loads(obj.detalle_carrito)
        except (TypeError, json.JSONDecodeError):
            return {"error": "Detalle de carrito no válido."}