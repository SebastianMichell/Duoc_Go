from django import template

register = template.Library()

@register.filter
def clp(value):
    """
    Formatea un número al estilo Peso Chileno:
    - Sin decimales.
    - Con punto como separador de miles.
    Ejemplo: 1400 -> 1.400
    """
    try:
        # Convertimos a entero para eliminar cualquier decimal (,00)
        value = int(float(value))
        # Formateamos con coma como separador de miles (1,400)
        formateado = "{:,}".format(value)
        # Reemplazamos la coma por punto (1.400)
        return formateado.replace(",", ".")
    except (ValueError, TypeError):
        # Si algo falla (ej: es texto), devolvemos el valor original
        return value