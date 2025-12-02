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

from core.models import LocalProfile, CarouselItem
from core.forms import LocalProfileForm, CarouselItemForm

@login_required(login_url='login')
def panel_local(request):
    
    if request.user.tipo_usuario != 'local':
        messages.error(request, 'Acceso denegado. No eres un usuario de tipo "Local".')
        return redirect('home')
    if not request.user.local_asignado:
        messages.error(request, 'No tienes un local asignado. Contacta a un administrador.')
        return redirect('home')

    local_id = request.user.local_asignado 
    
    try:
        perfil = LocalProfile.objects.get(local_id=local_id)
        local_nombre = perfil.nombre_local
    except LocalProfile.DoesNotExist:
        local_nombre = "Local 1" if local_id == 'a' else "Local 2"

    query = request.GET.get('q', '')       
    ordenar_por = request.GET.get('ordenar', 'nombre_asc') 

    if local_id == 'a':
        productos_qs = ProductA.objects.all() 
    else: 
        productos_qs = ProductB.objects.using('secondary').all()

    if query:
        productos_qs = productos_qs.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

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

    ganancias_totales = 0
    productos_vendidos_totales = 0 
    items_vendidos_recientes = []
    ESTADO_VENTA_COMPLETA = 'RETIRADO' 

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    qs_junaeb = PagoJunaebOrder.objects.filter(estado=ESTADO_VENTA_COMPLETA)
    qs_webpay = WebpayOrder.objects.filter(estado=ESTADO_VENTA_COMPLETA)

    if fecha_inicio and fecha_fin:
        qs_junaeb = qs_junaeb.filter(fecha_creacion__date__range=[fecha_inicio, fecha_fin])
        qs_webpay = qs_webpay.filter(fecha_creacion__date__range=[fecha_inicio, fecha_fin])

    for orden in qs_junaeb:
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id:
                    cantidad_item = int(item.get('cantidad', 1))
                    precio_item = int(item['precio']) * cantidad_item
                    ganancias_totales += precio_item
                    productos_vendidos_totales += cantidad_item 
                    items_vendidos_recientes.append({
                        'orden_id': orden.numero_orden, 'fecha': orden.fecha_creacion,
                        'nombre': item['nombre'], 'precio_total': precio_item,
                    })
        except: pass 

    for orden in qs_webpay:
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id:
                    cantidad_item = int(item.get('cantidad', 1))
                    precio_item = int(item['precio']) * cantidad_item
                    ganancias_totales += precio_item
                    productos_vendidos_totales += cantidad_item 
                    items_vendidos_recientes.append({
                        'orden_id': orden.numero_orden, 'fecha': orden.fecha_creacion,
                        'nombre': item['nombre'], 'precio_total': precio_item,
                    })
        except: pass 

    total_productos_distintos = productos.count()
    items_vendidos_recientes.sort(key=lambda x: x['fecha'], reverse=True)

    ordenes_pendientes_list = []
    ESTADO_PENDIENTE_LOCAL = 'PENDIENTE' 

    if local_id == 'a':
        ordenes_junaeb_pendientes = PagoJunaebOrder.objects.filter(estado_local_a=ESTADO_PENDIENTE_LOCAL)
        ordenes_webpay_pendientes = WebpayOrder.objects.filter(estado_local_a=ESTADO_PENDIENTE_LOCAL)
    else: 
        ordenes_junaeb_pendientes = PagoJunaebOrder.objects.filter(estado_local_b=ESTADO_PENDIENTE_LOCAL)
        ordenes_webpay_pendientes = WebpayOrder.objects.filter(estado_local_b=ESTADO_PENDIENTE_LOCAL)

    for orden in ordenes_junaeb_pendientes:
        items_del_local = []
        total_a_cobrar_local = 0 
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id: 
                    items_del_local.append(item)
                    precio = int(item.get('precio', 0))
                    cantidad = int(item.get('cantidad', 1))
                    total_a_cobrar_local += (precio * cantidad)
        except: pass
        
        ordenes_pendientes_list.append({
            'orden': orden,
            'items': items_del_local,
            'tipo_pago': 'Junaeb',
            'tipo_orden_str': 'PagoJunaebOrder',
            'total_local': total_a_cobrar_local 
        })

    ordenes_pendientes_list.sort(key=lambda x: x['orden'].hora_retiro or '99:99')
    
    items_vendidos_recientes.sort(key=lambda x: x['fecha'], reverse=True)
    
    context = {
        'productos': productos,
        'local_nombre': local_nombre,
        'ganancias_totales': ganancias_totales,
        'productos_vendidos_totales': productos_vendidos_totales,
        'total_productos_distintos': total_productos_distintos, 
        
        'items_vendidos': items_vendidos_recientes[:13], 
        
        'query_actual': query,
        'orden_actual': ordenar_por,
        'ordenes_pendientes': ordenes_pendientes_list,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'Local/panel_local.html', context)


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
            try:
                producto_editado = form.save(commit=False)
                
                producto_editado.save(using=db_alias)
                
                messages.success(request, 'Producto actualizado exitosamente.')
                return redirect('local:panel')
            except Exception as e:
                messages.error(request, f"Error al guardar en base de datos: {e}")
        else:
            messages.error(request, 'Error al actualizar. Revisa los campos.')
            print(form.errors) 
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


@login_required(login_url='login')
def marcar_entregado(request):
    if request.method != 'POST':
        messages.error(request, 'Método no permitido.')
        return redirect('local:panel')

    if request.user.tipo_usuario != 'local' or not request.user.local_asignado:
        messages.error(request, 'Acceso denegado.')
        return redirect('home')
    local_id = request.user.local_asignado 

    try:
        orden_id = request.POST.get('orden_id')
        orden_tipo = request.POST.get('orden_tipo') 
        orden_a_actualizar = None

        if orden_tipo == 'PagoJunaebOrder':
            orden_a_actualizar = get_object_or_404(PagoJunaebOrder, id=orden_id)
        elif orden_tipo == 'WebpayOrder':
            orden_a_actualizar = get_object_or_404(WebpayOrder, id=orden_id)
        else:
            raise Exception("Tipo de orden desconocido.")

        if local_id == 'a':
            orden_a_actualizar.estado_local_a = 'RETIRADO'
        elif local_id == 'b':
            orden_a_actualizar.estado_local_b = 'RETIRADO'
        
        orden_a_actualizar.save() 

        local_a_listo = (orden_a_actualizar.estado_local_a != 'PENDIENTE')
        local_b_listo = (orden_a_actualizar.estado_local_b != 'PENDIENTE')

        if local_a_listo and local_b_listo:
            orden_a_actualizar.estado = 'RETIRADO'
            orden_a_actualizar.save() 
            
            enviar_correo_retiro(request, orden_a_actualizar)
            
            messages.success(request, f"¡Orden #{orden_a_actualizar.numero_orden} completada! Cliente notificado.")
        
        else:
            messages.success(request, f"Tu parte de la orden #{orden_a_actualizar.numero_orden} fue marcada como ENTREGADA.")

    except Exception as e:
        messages.error(request, f"Error al marcar la orden como entregada: {e}")

    return redirect('local:panel')


@login_required(login_url='login')
def configuracion_local(request):
    if request.user.tipo_usuario != 'local':
        return redirect('home')
    
    local_id = request.user.local_asignado
    
    perfil, created = LocalProfile.objects.get_or_create(local_id=local_id)
    
    if request.method == 'POST':
        form = LocalProfileForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil del local actualizado.')
            return redirect('local:panel')
    else:
        form = LocalProfileForm(instance=perfil)
        
    return render(request, 'Local/configuracion.html', {'form': form})


@login_required(login_url='login')
def gestion_carrusel(request):
    if request.user.tipo_usuario != 'local':
        return redirect('home')
    
    local_id = request.user.local_asignado
    
    promos = CarouselItem.objects.filter(local_id=local_id).order_by('-fecha_creacion')
    
    if request.method == 'POST':
        form = CarouselItemForm(request.POST, request.FILES)
        if form.is_valid():
            promo = form.save(commit=False)
            promo.local_id = local_id 
            promo.save()
            messages.success(request, 'Promoción agregada al carrusel.')
            return redirect('local:gestion_carrusel')
    else:
        form = CarouselItemForm()
        
    return render(request, 'Local/gestion_carrusel.html', {'form': form, 'promos': promos})

@login_required(login_url='login')
def eliminar_promo(request, pk):
    promo = get_object_or_404(CarouselItem, pk=pk, local_id=request.user.local_asignado)
    promo.delete()
    messages.success(request, 'Promoción eliminada.')
    return redirect('local:gestion_carrusel')

@login_required(login_url='login')
def historial_ventas(request):
    if request.user.tipo_usuario != 'local':
        return redirect('home')
    
    local_id = request.user.local_asignado
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    items_vendidos = []
    ESTADO_VENTA_COMPLETA = 'RETIRADO'
    
    qs_junaeb = PagoJunaebOrder.objects.filter(estado=ESTADO_VENTA_COMPLETA)
    qs_webpay = WebpayOrder.objects.filter(estado=ESTADO_VENTA_COMPLETA)

    if fecha_inicio and fecha_fin:
        qs_junaeb = qs_junaeb.filter(fecha_creacion__date__range=[fecha_inicio, fecha_fin])
        qs_webpay = qs_webpay.filter(fecha_creacion__date__range=[fecha_inicio, fecha_fin])

    for orden in qs_junaeb:
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id:
                    cantidad = int(item.get('cantidad', 1))
                    precio = int(item['precio']) * cantidad
                    items_vendidos.append({
                        'orden_id': orden.numero_orden, 'fecha': orden.fecha_creacion,
                        'nombre': item['nombre'], 'precio_total': precio,
                        'tipo': 'Junaeb'
                    })
        except: pass 

    for orden in qs_webpay:
        try:
            carrito = json.loads(orden.detalle_carrito)
            for item in carrito:
                if item.get('origen') == local_id:
                    cantidad = int(item.get('cantidad', 1))
                    precio = int(item['precio']) * cantidad
                    items_vendidos.append({
                        'orden_id': orden.numero_orden, 'fecha': orden.fecha_creacion,
                        'nombre': item['nombre'], 'precio_total': precio,
                        'tipo': 'Webpay'
                    })
        except: pass 

    items_vendidos.sort(key=lambda x: x['fecha'], reverse=True)

    context = {
        'items': items_vendidos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    }
    return render(request, 'Local/historial_ventas.html', context)