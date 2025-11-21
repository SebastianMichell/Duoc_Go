# Local/views.py (ACTUALIZADO CON LÓGICA DE ENTREGA SEPARADA)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q 
import json 

from core.models import PagoJunaebOrder, WebpayOrder
from products_a.models import Product as ProductA
from products_b.models import Product as ProductB
from core.forms import ProductAForm, ProductBForm 
from core.views import enviar_correo_retiro


@login_required(login_url='login')
def panel_local(request):
    
    # 1. Seguridad y setup
    if request.user.tipo_usuario != 'local':
        messages.error(request, 'Acceso denegado. No eres un usuario de tipo "Local".')
        return redirect('home')
    if not request.user.local_asignado:
        messages.error(request, 'No tienes un local asignado. Contacta a un administrador.')
        return redirect('home')

    local_id = request.user.local_asignado # 'a' o 'b'
    local_nombre = ""
    
    # 2. Lógica de Productos (Sin cambios)
    query = request.GET.get('q', '')       
    ordenar_por = request.GET.get('ordenar', 'nombre_asc') 

    if local_id == 'a':
        productos_qs = ProductA.objects.all() 
        local_nombre = "Local 1"
    else: 
        productos_qs = ProductB.objects.using('secondary').all()
        local_nombre = "Local 2"

    if query:
        productos_qs = productos_qs.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    # ... (resto de filtros de producto sin cambios) ...
    if ordenar_por == 'stock_desc':
        productos_qs = productos_qs.order_by('-stock')
    elif ordenar_por == 'stock_asc':
        productos_qs = productos_qs.order_by('stock')
    elif ordenar_por == 'precio_desc':
        productos_qs = productos_qs.order_by('-price')
    elif ordenar_por == 'precio_asc':
        productos_qs = productos_qs.order_by('price')
    else: 
        productos_qs = productos_qs.order_by('name')
    productos = productos_qs

    # 3. Lógica de Estadísticas (Ventas Completadas) (Sin cambios)
    ganancias_totales = 0
    productos_vendidos_totales = 0 
    items_vendidos_recientes = []
    ESTADO_VENTA_COMPLETA = 'RETIRADO' 
    ordenes_junaeb_completadas = PagoJunaebOrder.objects.filter(estado=ESTADO_VENTA_COMPLETA)
    for orden in ordenes_junaeb_completadas:
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id:
                    cantidad_item = item.get('cantidad', 1)
                    precio_item = item['precio'] * cantidad_item
                    ganancias_totales += precio_item
                    productos_vendidos_totales += cantidad_item 
                    items_vendidos_recientes.append({
                        'orden_id': orden.numero_orden, 'fecha': orden.fecha_creacion,
                        'nombre': item['nombre'], 'precio_total': precio_item,
                    })
        except: pass 
    ordenes_webpay_completadas = WebpayOrder.objects.filter(estado=ESTADO_VENTA_COMPLETA) 
    for orden in ordenes_webpay_completadas:
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id:
                    cantidad_item = item.get('cantidad', 1)
                    precio_item = item['precio'] * cantidad_item
                    ganancias_totales += precio_item
                    productos_vendidos_totales += cantidad_item 
                    items_vendidos_recientes.append({
                        'orden_id': orden.numero_orden, 'fecha': orden.fecha_creacion,
                        'nombre': item['nombre'], 'precio_total': precio_item,
                    })
        except: pass 
    total_productos_distintos = productos.count()
    items_vendidos_recientes.sort(key=lambda x: x['fecha'], reverse=True)

    # --- 4. LÓGICA DE ÓRDENES PENDIENTES (MODIFICADA) ---
    ordenes_pendientes_list = []
    ESTADO_PENDIENTE_LOCAL = 'PENDIENTE' # <- Usamos el estado local

    # --- CAMBIO AQUÍ: Filtramos por estado_local_a o estado_local_b ---
    if local_id == 'a':
        ordenes_junaeb_pendientes = PagoJunaebOrder.objects.filter(estado_local_a=ESTADO_PENDIENTE_LOCAL)
        ordenes_webpay_pendientes = WebpayOrder.objects.filter(estado_local_a=ESTADO_PENDIENTE_LOCAL)
        local_nombre = "Local 1"
    else: # local_id == 'b'
        ordenes_junaeb_pendientes = PagoJunaebOrder.objects.filter(estado_local_b=ESTADO_PENDIENTE_LOCAL)
        ordenes_webpay_pendientes = WebpayOrder.objects.filter(estado_local_b=ESTADO_PENDIENTE_LOCAL)
        local_nombre = "Local 2"
    # --- FIN CAMBIO ---

    # 4.1. Procesar órdenes Junaeb PENDIENTES (para este local)
    for orden in ordenes_junaeb_pendientes:
        items_del_local = []
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id: 
                    items_del_local.append(item)
        except: pass
        
        # Ya no necesitamos "if items_del_local:" porque el filtro de BD ya lo hizo
        ordenes_pendientes_list.append({
            'orden': orden,
            'items': items_del_local,
            'tipo_pago': 'Junaeb',
            'tipo_orden_str': 'PagoJunaebOrder', 
        })

    # 4.2. Procesar órdenes Webpay PENDIENTES (para este local)
    for orden in ordenes_webpay_pendientes:
        items_del_local = []
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id:
                    items_del_local.append(item)
        except: pass
        
        ordenes_pendientes_list.append({
            'orden': orden,
            'items': items_del_local,
            'tipo_pago': 'Webpay',
            'tipo_orden_str': 'WebpayOrder',
        })

    # 4.3. Ordenar la lista final
    ordenes_pendientes_list.sort(key=lambda x: x['orden'].hora_retiro or '99:99')
    
    # 5. Preparar el Contexto (Sin cambios)
    context = {
        'productos': productos,
        'local_nombre': local_nombre,
        'ganancias_totales': ganancias_totales,
        'productos_vendidos_totales': productos_vendidos_totales,
        'total_productos_distintos': total_productos_distintos, 
        'items_vendidos': items_vendidos_recientes[:10],
        'query_actual': query,
        'orden_actual': ordenar_por,
        'ordenes_pendientes': ordenes_pendientes_list
    }
    
    return render(request, 'Local/panel_local.html', context)


# --- VISTAS DEL CRUD (Sin cambios) ---

@login_required(login_url='login')
def producto_crear(request):
    if request.user.tipo_usuario != 'local' or not request.user.local_asignado:
        messages.error(request, 'Acceso denegado.')
        return redirect('home')
    
    local_id = request.user.local_asignado
    FormularioProducto = ProductAForm if local_id == 'a' else ProductBForm
    db_alias = 'default' if local_id == 'a' else 'secondary'
    template_name = 'Local/producto_form.html' 

    if request.method == 'POST':
        form = FormularioProducto(request.POST, request.FILES)
        if form.is_valid():
            producto_nuevo = form.save(commit=False)
            producto_nuevo.save(using=db_alias)    
            messages.success(request, 'Producto agregado exitosamente.')
            return redirect('local:panel') 
    else:
        form = FormularioProducto()

    return render(request, template_name, {'form': form, 'titulo': 'Agregar Nuevo Producto'})


@login_required(login_url='login')
def producto_editar(request, pk): 
    if request.user.tipo_usuario != 'local' or not request.user.local_asignado:
        messages.error(request, 'Acceso denegado.')
        return redirect('home')

    local_id = request.user.local_asignado
    
    if local_id == 'a':
        ModeloProducto = ProductA
        FormularioProducto = ProductAForm
        db_alias = 'default'
    else: 
        ModeloProducto = ProductB
        FormularioProducto = ProductBForm
        db_alias = 'secondary'
        
    template_name = 'Local/producto_form.html'
    producto = get_object_or_404(ModeloProducto.objects.using(db_alias), pk=pk)

    if request.method == 'POST':
        form = FormularioProducto(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto_editado = form.save(commit=False)
            producto_editado.save(using=db_alias)    
            messages.success(request, 'Producto actualizado exitosamente.')
            return redirect('local:panel')
    else:
        form = FormularioProducto(instance=producto)

    return render(request, template_name, {'form': form, 'titulo': f'Editar Producto: {producto.name}'})


@login_required(login_url='login')
def producto_eliminar(request, pk):
    if request.user.tipo_usuario != 'local' or not request.user.local_asignado:
        messages.error(request, 'Acceso denegado.')
        return redirect('home')

    local_id = request.user.local_asignado
    
    if local_id == 'a':
        ModeloProducto = ProductA
        db_alias = 'default'
    else: 
        ModeloProducto = ProductB
        db_alias = 'secondary'
        
    template_name = 'Local/producto_confirm_delete.html' 
    producto = get_object_or_404(ModeloProducto.objects.using(db_alias), pk=pk)

    if request.method == 'POST':
        producto.delete(using=db_alias) 
        messages.success(request, 'Producto eliminado exitosamente.')
        return redirect('local:panel')
    
    return render(request, template_name, {'producto': producto})


# --- VISTA 'MARCAR_ENTREGADO' (MODIFICADA) ---
@login_required(login_url='login')
def marcar_entregado(request):
    if request.method != 'POST':
        messages.error(request, 'Método no permitido.')
        return redirect('local:panel')

    # 1. Seguridad y obtener el ID del local ('a' o 'b')
    if request.user.tipo_usuario != 'local' or not request.user.local_asignado:
        messages.error(request, 'Acceso denegado.')
        return redirect('home')
    local_id = request.user.local_asignado # 'a' o 'b'

    try:
        # 2. Obtenemos los datos del formulario
        orden_id = request.POST.get('orden_id')
        orden_tipo = request.POST.get('orden_tipo') 
        orden_a_actualizar = None

        # 3. Buscamos la orden en el modelo correcto
        if orden_tipo == 'PagoJunaebOrder':
            orden_a_actualizar = get_object_or_404(PagoJunaebOrder, id=orden_id)
        elif orden_tipo == 'WebpayOrder':
            orden_a_actualizar = get_object_or_404(WebpayOrder, id=orden_id)
        else:
            raise Exception("Tipo de orden desconocido.")

        # 4. --- LÓGICA DE ENTREGA SEPARADA ---
        # Actualizamos solo la parte que corresponde a ESTE local
        if local_id == 'a':
            orden_a_actualizar.estado_local_a = 'RETIRADO'
        elif local_id == 'b':
            orden_a_actualizar.estado_local_b = 'RETIRADO'
        
        orden_a_actualizar.save() # Guardamos el estado parcial

        # 5. --- REVISIÓN DE ORDEN COMPLETA ---
        # Verificamos si AMBAS partes (A y B) ya NO están 'PENDIENTE'
        # (Pueden ser 'RETIRADO' o 'NA')
        local_a_listo = (orden_a_actualizar.estado_local_a != 'PENDIENTE')
        local_b_listo = (orden_a_actualizar.estado_local_b != 'PENDIENTE')

        if local_a_listo and local_b_listo:
            # ¡Ambos locales entregaron!
            # Ahora sí, marcamos la orden general como RETIRADA
            orden_a_actualizar.estado = 'RETIRADO'
            orden_a_actualizar.save() # Guardamos el estado general
            
            # Y enviamos el correo de confirmación final
            enviar_correo_retiro(request, orden_a_actualizar)
            
            messages.success(request, f"¡Orden #{orden_a_actualizar.numero_orden} completada! Cliente notificado.")
        
        else:
            # Aún falta que el otro local entregue su parte
            messages.success(request, f"Tu parte de la orden #{orden_a_actualizar.numero_orden} fue marcada como ENTREGADA.")

    except Exception as e:
        messages.error(request, f"Error al marcar la orden como entregada: {e}")

    return redirect('local:panel')
# --- FIN DE LA VISTA 'MARCAR_ENTREGADO' ---