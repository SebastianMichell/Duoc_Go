# duoc_go/core/views.py (COMPLETO Y DEFINITIVO)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm, LoginForm, PagoJunaebForm, ContactoForm, InscripcionLocalForm
from products_a.models import Product as ProductA
from products_b.models import Product as ProductB
from django.http import JsonResponse, HttpResponseBadRequest
import uuid
from django.conf import settings
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from .models import PagoJunaebOrder, WebpayOrder, Favorite 
import qrcode
import io
import json
import random 
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from .serializers import PagoJunaebOrderSerializer 
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.error.transaction_commit_error import TransactionCommitError
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage
import os
from django.urls import reverse
from itertools import chain 
from operator import attrgetter 
from .models import CarouselItem
from .models import LocalProfile

def obtener_nombre_local(origen): 
    try:
        perfil = LocalProfile.objects.get(local_id=origen)
        return perfil.nombre_local
    except LocalProfile.DoesNotExist:
        return "Local 1" if origen == 'a' else "Local 2"

def home(request):
    hoy = timezone.now().date()
    
    try:
        perfil_a = LocalProfile.objects.get(local_id='a')
        nombre_local_a = perfil_a.nombre_local
    except LocalProfile.DoesNotExist:
        perfil_a = None
        nombre_local_a = "Local 1"

    try:
        perfil_b = LocalProfile.objects.get(local_id='b')
        nombre_local_b = perfil_b.nombre_local
    except LocalProfile.DoesNotExist:
        perfil_b = None
        nombre_local_b = "Local 2"

    productos_a = ProductA.objects.all()
    productos_b = ProductB.objects.using('secondary').all() 
    
    todos_productos = []
    
    for p in productos_a:
        precio_final = p.price
        precio_orig = None
        en_oferta = False
        
        if p.precio_especial and p.fecha_inicio_especial and p.fecha_fin_especial:
            if p.fecha_inicio_especial <= hoy <= p.fecha_fin_especial:
                precio_final = p.precio_especial
                precio_orig = p.price
                en_oferta = True

        todos_productos.append({
            'id': p.id, 
            'nombre': p.name, 
            'descripcion': p.description,
            'precio': precio_final, 
            'precio_original': precio_orig, 
            'en_oferta': en_oferta,
            'imagen': p.image.url if p.image else '/static/img/default.png',
            'origen': 'a', 
            'local': nombre_local_a, 
            'stock': p.stock
        })
        
    for p in productos_b:
        precio_final = p.price
        precio_orig = None
        en_oferta = False
        
        if p.precio_especial and p.fecha_inicio_especial and p.fecha_fin_especial:
            if p.fecha_inicio_especial <= hoy <= p.fecha_fin_especial:
                precio_final = p.precio_especial
                precio_orig = p.price
                en_oferta = True

        todos_productos.append({
            'id': p.id, 
            'nombre': p.name, 
            'descripcion': p.description,
            'precio': precio_final, 
            'precio_original': precio_orig, 
            'en_oferta': en_oferta,
            'imagen': p.image.url if p.image else '/static/img/default.png',
            'origen': 'b', 
            'local': nombre_local_b, 
            'stock': p.stock
        })

    productos_oferta = [p for p in todos_productos if p['en_oferta']]
    
    if len(todos_productos) > 4:
        productos_nuevos = todos_productos[-4:] 
    else:
        productos_nuevos = todos_productos

    carrusel_items = CarouselItem.objects.filter(activo=True).order_by('-fecha_creacion')

    context = {
        'productos': todos_productos,   
        'ofertas': productos_oferta,    
        'nuevos': productos_nuevos,
        'carrusel_items': carrusel_items,
        'perfil_a': perfil_a, 
        'perfil_b': perfil_b,
    }
    return render(request, 'home.html', context)


def detalle_producto(request, origen, producto_id):
    if origen == 'a':
        producto = get_object_or_404(ProductA, id=producto_id)
        local_nombre = "Local 1"
    else:
        producto = get_object_or_404(ProductB.objects.using('secondary'), id=producto_id)
        local_nombre = "Local 2"

    hoy = timezone.now().date()
    precio_a_mostrar = producto.price
    precio_original = None
    en_oferta = False

    local_nombre = obtener_nombre_local(origen)

    if producto.precio_especial and producto.fecha_inicio_especial and producto.fecha_fin_especial:
        if producto.fecha_inicio_especial <= hoy <= producto.fecha_fin_especial:
            precio_a_mostrar = producto.precio_especial
            precio_original = producto.price
            en_oferta = True

    todos_productos = []
    
    prods_a = ProductA.objects.all()
    for p in prods_a:
        if not (origen == 'a' and p.id == producto.id):
            todos_productos.append({'obj': p, 'origen': 'a', 'local': 'Local 1'})

    prods_b = ProductB.objects.using('secondary').all()
    for p in prods_b:
        if not (origen == 'b' and p.id == producto.id):
            todos_productos.append({'obj': p, 'origen': 'b', 'local': 'Local 2'})

    random.shuffle(todos_productos)
    recomendados_raw = todos_productos[:4]
    
    recomendados = []
    for item in recomendados_raw:
        p = item['obj']
        p_precio = p.price
        p_orig = None
        p_oferta = False
        
        if p.precio_especial and p.fecha_inicio_especial and p.fecha_fin_especial:
            if p.fecha_inicio_especial <= hoy <= p.fecha_fin_especial:
                p_precio = p.precio_especial
                p_orig = p.price
                p_oferta = True
        
        recomendados.append({
            'id': p.id,
            'nombre': p.name,
            'imagen': p.image.url if p.image else '/static/img/default.png',
            'precio': p_precio,
            'precio_original': p_orig,
            'en_oferta': p_oferta,
            'origen': item['origen'],
            'local': item['local']
        })

    context = {
        'p': producto,
        'origen': origen,
        'local_nombre': local_nombre,
        'precio_final': precio_a_mostrar,
        'precio_original': precio_original,
        'en_oferta': en_oferta,
        'recomendados': recomendados
    }
    return render(request, 'core/detalle_producto.html', context)

def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password1"])
            user.save()

            email = form.cleaned_data.get("email")
            rut = form.cleaned_data.get("rut")
            password = form.cleaned_data.get("password1")

            user = authenticate(request, username=email or rut, password=password)

            if user is not None:
                login(request, user, backend='core.backends.EmailOrRUTBackend') 
                return redirect("home")
            else:
                messages.error(request, "Usuario registrado, pero error al iniciar sesión.")
                return redirect("login")
    else:
        form = RegistroForm()
    return render(request, "registro.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.tipo_usuario == "estudiante" and user.email and user.email.endswith("@profesor.duoc"):
                        messages.error(request, "Los alumnos no pueden usar un correo @profesor.duoc.")
                        return render(request, "login.html", {"form": form})

                login(request, user)
                
                if user.tipo_usuario == 'local':
                    return redirect('local:panel')
                else:
                    return redirect("home")
            else:
                messages.error(request, "Correo/RUT o contraseña incorrectos.")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def user_redirect_view(request):
    if request.user.is_authenticated:
        return redirect('perfil') 
    else:
        return redirect('auth_options') 


@login_required(login_url='login')
def perfil(request):
    if not request.user.is_authenticated:
        return redirect('auth_options')

    ordenes_junaeb = PagoJunaebOrder.objects.filter(user=request.user)

    for o in ordenes_junaeb:
        o.tipo_pago = 'Junaeb'

    ordenes_webpay = WebpayOrder.objects.filter(user=request.user)
    for o in ordenes_webpay:
        o.tipo_pago = 'Webpay'
    historial_ordenes = sorted(
        chain(ordenes_junaeb, ordenes_webpay),
        key=attrgetter('fecha_creacion'),
        reverse=True
    )
    context = {
        'historial': historial_ordenes
    }
    return render(request, 'perfil.html', context)


def auth_options(request):
    return render(request, 'auth_options.html')

def agregar_al_carrito(request, origen, producto_id):
    if origen == 'a':
        producto = get_object_or_404(ProductA, id=producto_id)
        local = "Local 1"
        db_to_use = 'default'
    else:
        producto = get_object_or_404(ProductB.objects.using('secondary'), id=producto_id)
        local = "Local 2"
        db_to_use = 'secondary'

    if hasattr(producto, 'stock') and producto.stock <= 0:
        return JsonResponse({'status': 'error', 'msg': 'Sin stock disponible'})
    
    local_nombre = obtener_nombre_local(origen)
    
    unique_id = f"{origen}-{producto.id}"
    carrito = request.session.get('carrito', [])

    for item in carrito:
        qty = item.get('cantidad', 0)
        if isinstance(qty, (list, tuple)):
            item['cantidad'] = int(qty[0])
        else:
            item['cantidad'] = int(qty)
    
    hoy = timezone.now().date()
    precio_a_usar = producto.price 
    
    if producto.precio_especial is not None and producto.fecha_inicio_especial and producto.fecha_fin_especial:
        if producto.fecha_inicio_especial <= hoy <= producto.fecha_fin_especial:
            precio_a_usar = producto.precio_especial
    
    try:
        cantidad_solicitada = int(request.GET.get('cantidad', 1))
    except (ValueError, TypeError):
        cantidad_solicitada = 1

    item_encontrado = False
    for item in carrito:
        if item.get('unique_id') == unique_id:
            item['cantidad'] += cantidad_solicitada
            item_encontrado = True
            break 

    if not item_encontrado:
        carrito.append({
            'unique_id': unique_id,
            'id': producto.id,
            'nombre': producto.name,
            'precio': float(precio_a_usar), 
            'origen': origen,
            'local': local_nombre,
            'cantidad': cantidad_solicitada,
            'imagen': producto.image.url if producto.image else '/static/img/default.png'
        })
    
    request.session['carrito'] = carrito

    if hasattr(producto, 'stock'):
        if producto.stock >= cantidad_solicitada:
            producto.stock -= cantidad_solicitada
            producto.save(using=db_to_use)
        else:
             return JsonResponse({'status': 'error', 'msg': 'No hay suficiente stock'})

    total_items_cantidad = sum(int(item.get('cantidad', 0)) for item in carrito)
    
    return JsonResponse({
        'status': 'ok', 
        'total_items': total_items_cantidad,
        'product_name': producto.name
    })


def ver_carrito(request):
    carrito = request.session.get('carrito', [])
    
    for item in carrito:
        qty = item.get('cantidad', 0)
        if isinstance(qty, (list, tuple)):
            item['cantidad'] = int(qty[0])
        else:
            item['cantidad'] = int(qty)

    total = sum(item['precio'] * int(item.get('cantidad', 1)) for item in carrito) 
    return render(request, 'carrito.html', {'carrito': carrito, 'total': total})


def eliminar_del_carrito(request, unique_id):
    carrito = request.session.get('carrito', [])
    item_eliminado = None
    
    for item in carrito:
        if item.get('unique_id') == unique_id:
            item_eliminado = item
            break

    if item_eliminado:
        qty = item_eliminado.get('cantidad', 1)
        if isinstance(qty, (list, tuple)):
            cantidad_a_devolver = int(qty[0])
        else:
            cantidad_a_devolver = int(qty)

        try:
            origen, producto_id = item_eliminado['unique_id'].split('-')
            producto_id = int(producto_id)
            
            if origen == 'a':
                producto = ProductA.objects.get(id=producto_id)
                producto.stock += cantidad_a_devolver
                producto.save()
            elif origen == 'b':
                producto = ProductB.objects.using('secondary').get(id=producto_id)
                producto.stock += cantidad_a_devolver
                producto.save(using='secondary')
                
        except Exception as e:
            print(f"Error al devolver stock: {e}")

    carrito = [item for item in carrito if item.get('unique_id') != unique_id]
    request.session['carrito'] = carrito
    return redirect('carrito')



def generar_opciones_hora():
    now_utc = timezone.now() 
    start_time_utc = now_utc + timedelta(minutes=15) 
    minute = start_time_utc.minute
    minute_round = ((minute // 5) * 5) + 5
    
    if minute_round >= 60:
        start_time_utc = start_time_utc.replace(minute=0) + timedelta(hours=1)
    else:
        start_time_utc = start_time_utc.replace(minute=minute_round)
    
    opciones = []
    current_time_utc = start_time_utc
    max_time_utc = now_utc + timedelta(minutes=30)
    
    while current_time_utc <= max_time_utc:
        local_time = timezone.localtime(current_time_utc)
        time_str = local_time.strftime("%H:%M") 
        opciones.append((time_str, time_str))
        current_time_utc += timedelta(minutes=5)
        
    return opciones


def enviar_correo_confirmacion(request, orden):
    destinatario = orden.user_identifier
    if 'Invitado' in destinatario:
        lista_destinatarios = ['jexfryxd@gmail.com']
    else:
        lista_destinatarios = [destinatario, 'jexfryxd@gmail.com']

    asunto = f"Confirmación de Orden #{orden.numero_orden} (DUOC GO)"
    
    context = {
        'orden': orden,
        'qr_url': request.build_absolute_uri(orden.qr_code.url)
    }

    html_message = render_to_string('core/confirmacion_orden.html', context)
    plain_message = strip_tags(html_message)
    
    email = EmailMultiAlternatives(
        subject=asunto,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=lista_destinatarios
    )
    
    email.attach_alternative(html_message, "text/html")

    try:
        if orden.qr_code:
            with open(orden.qr_code.path, 'rb') as f:
                qr_image = MIMEImage(f.read())
                qr_image.add_header('Content-ID', '<qr_code>') 
                qr_image.add_header('Content-Disposition', 'inline')
                email.attach(qr_image)
    except Exception as e:
        print(f"Error al adjuntar QR al correo: {e}")

    email.send(fail_silently=False)


def enviar_correo_retiro(request, orden):
    destinatario = orden.user_identifier
    if 'Invitado' in destinatario:
        lista_destinatarios = ['jexfryxd@gmail.com'] 
    else:
        lista_destinatarios = [destinatario, 'jexfryxd@gmail.com'] 

    asunto = f"¡Tu Orden #{orden.numero_orden} ha sido Retirada! (DUOC GO)"
    
    context = {'orden': orden}
    html_message = render_to_string('core/confirmacion_retiro.html', context)
    plain_message = strip_tags(html_message)
    
    email = EmailMultiAlternatives(
        subject=asunto,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=lista_destinatarios
    )
    
    email.attach_alternative(html_message, "text/html")
    
    email.send(fail_silently=False)

def pago_junaeb(request):
    carrito = request.session.get('carrito', [])
    if not carrito:
        messages.error(request, "El carrito está vacío.")
        return redirect('carrito')

    total = sum(item['precio'] * int(item.get('cantidad', 1)) for item in carrito)
    user_identifier = request.user.email if request.user.is_authenticated else 'Invitado'
    hora_choices = generar_opciones_hora()
    
    if request.method == 'POST':
        form = PagoJunaebForm(request.POST, hora_choices=hora_choices)
        
        if form.is_valid():
            rut = form.cleaned_data['rut']
            clave_dinamica = form.cleaned_data['clave_dinamica']
            hora_retiro = form.cleaned_data['hora_retiro']
            
            try:
                nueva_orden = PagoJunaebOrder.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    user_identifier=user_identifier,
                    rut=rut,
                    clave_dinamica=clave_dinamica,
                    hora_retiro=hora_retiro,
                    total=total,
                    detalle_carrito=json.dumps(carrito)
                )
            except Exception as e:
                messages.error(request, f"Error al guardar la orden: {e}")
                return redirect('carrito')

            qr_data = nueva_orden.numero_orden
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            
            file_name = f'junaeb_qr_{nueva_orden.numero_orden}.png'
            nueva_orden.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)
            
            try:
                enviar_correo_confirmacion(request, nueva_orden)
                messages.success(request, f"Datos de pago Junaeb enviados. Revisa tu correo.")
                
            except Exception as e:
                messages.error(request, f"Error al enviar el correo. Detalle: {e}. La orden N° {nueva_orden.numero_orden} ha sido guardada.")
            
            request.session['carrito'] = []
            request.session['ultima_orden_junaeb'] = nueva_orden.numero_orden 
            return redirect('pago_exitoso_junaeb') 

        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
            
    else:
        form = PagoJunaebForm(hora_choices=hora_choices)

    context = {
        'form': form,
        'carrito': carrito,
        'total': total,
        'user_identifier': user_identifier
    }
    return render(request, 'core/pago_junaeb.html', context)


def pago_exitoso_junaeb(request):
    numero_orden_junaeb = request.session.pop('ultima_orden_junaeb', None)
    
    orden = None
    if numero_orden_junaeb:
        try:
            orden = PagoJunaebOrder.objects.get(numero_orden=numero_orden_junaeb)
            messages.success(request, f"¡Solicitud Junaeb aceptada! Orden N° {orden.numero_orden} generada.")
        except PagoJunaebOrder.DoesNotExist:
            messages.error(request, "Error: No se encontró la orden de pago Junaeb.")
    else:
        messages.info(request, "Tu solicitud fue procesada.")
        
    return render(request, 'core/pago_exitoso.html', {'orden': orden})


def iniciar_pago(request):
    if request.method != "POST":
        return redirect('carrito')
        
    carrito = request.session.get('carrito', [])
    if not carrito:
        messages.error(request, "El carrito está vacío.")
        return redirect('carrito')

    total = int(sum(item['precio'] * int(item.get('cantidad', 1)) for item in carrito))
    
    buy_order = str(uuid.uuid4()).replace('-', '')[:10]
    session_id = str(uuid.uuid4()).replace('-', '')[:10]
    
    request.session['transbank_data'] = {
        'buy_order': buy_order,
        'session_id': session_id,
        'total': total
    }
    
    return_url = request.build_absolute_uri(reverse('pago_exito')) 

    tx = Transaction.build_for_integration(
        IntegrationCommerceCodes.WEBPAY_PLUS, 
        IntegrationApiKeys.WEBPAY
    )
    
    response = tx.create(buy_order, session_id, total, return_url)
    return redirect(response['url'] + '?token_ws=' + response['token'])


def pago_exito(request):
    token = request.POST.get('token_ws') or request.GET.get('token_ws')
    transbank_data = request.session.pop('transbank_data', None)
    
    carrito = request.session.get('carrito', [])

    if not token or not transbank_data or not carrito:
        messages.error(request, "Error al procesar el pago. Faltan datos de la sesión.")
        return redirect('carrito') 

    tx = Transaction.build_for_integration(
        IntegrationCommerceCodes.WEBPAY_PLUS, 
        IntegrationApiKeys.WEBPAY
    )

    try:
        response = tx.commit(token) 
        
        if response['response_code'] == 0:

            try:
                nueva_orden = WebpayOrder.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    user_identifier=request.user.email if request.user.is_authenticated else 'Invitado (Webpay)',
                    total=transbank_data['total'],
                    detalle_carrito=json.dumps(carrito),
                    estado='PENDIENTE',
                    hora_retiro=None
                )
                
                request.session['orden_webpay_id'] = nueva_orden.id
                request.session['carrito'] = [] 
                
                messages.success(request, "¡Pago Webpay exitoso! Ahora selecciona tu hora de retiro.")
                return redirect('seleccionar_hora_webpay')

            except Exception as e:
                print("\n\n--- 🚨 ERROR AL GUARDAR ORDEN WEBPAY 🚨 ---")
                print(f"Tipo de Error: {type(e)}")
                print(f"Detalle: {e}")
                print("------------------------------------------\n\n")
                messages.error(request, f"Pago exitoso, pero hubo un error al guardar tu orden. Revisa la consola.")
                return redirect('home')
        else:
            messages.error(request, f"Pago rechazado por el banco. Código: {response['response_code']}")
            return render(request, 'core/pago_fallido.html')

    except TransactionCommitError as e:
        messages.error(request, f"Error de comunicación con el sistema de pago: {e}")
        return render(request, 'core/pago_fallido.html')
    except Exception as e:
        messages.error(request, f"Error inesperado durante el pago: {e}")
        return render(request, 'core/pago_fallido.html')


def seleccionar_hora_webpay(request):
    
    orden_id = request.session.get('orden_webpay_id')

    if not orden_id:
        messages.error(request, "No se encontró una orden pendiente para asignar hora.")
        return redirect('home')
    
    try:
        orden = WebpayOrder.objects.get(id=orden_id)
    except WebpayOrder.DoesNotExist:
        messages.error(request, "La orden no existe.")
        return redirect('home')

    hora_choices = generar_opciones_hora()

    if request.method == 'POST':
        hora_retiro = request.POST.get('hora_retiro')
        
        if hora_retiro not in [choice[0] for choice in hora_choices]:
            messages.error(request, "Hora de retiro no válida.")
            return redirect('seleccionar_hora_webpay')

        orden.hora_retiro = hora_retiro
        
        qr_data = orden.numero_orden
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')

        file_name = f'webpay_qr_{orden.numero_orden}.png'
        orden.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)
        
        try:
            enviar_correo_confirmacion(request, orden)
            messages.success(request, f"¡Orden N° {orden.numero_orden} confirmada! Revisa tu correo.")

        except Exception as e:
            messages.error(request, f"Error al enviar el correo. Detalle: {e}. La orden N° {orden.numero_orden} ha sido guardada.")
        
        del request.session['orden_webpay_id']
        
        return render(request, 'core/pago_exitoso.html', {'orden': orden})

    return render(request, 'core/seleccionar_hora_webpay.html', {'hora_choices': hora_choices})

class OrdenesPendientesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para exponer las órdenes Junaeb PENDIENTES.
    """
    queryset = PagoJunaebOrder.objects.filter(estado='PENDIENTE').order_by('hora_retiro')
    serializer_class = PagoJunaebOrderSerializer
    permission_classes = [AllowAny]


def sumar_item_carrito(request, unique_id):
    carrito = request.session.get('carrito', [])
    item_encontrado = None
    
    for item in carrito:
        if item.get('unique_id') == unique_id:
            item_encontrado = item
            break

    if item_encontrado:
        try:
            origen, producto_id = unique_id.split('-')
            producto_id = int(producto_id)
            
            if origen == 'a':
                producto = ProductA.objects.get(id=producto_id)
                db_alias = 'default'
            else:
                producto = ProductB.objects.using('secondary').get(id=producto_id)
                db_alias = 'secondary'

            if producto.stock > 0:
                producto.stock -= 1
                producto.save(using=db_alias)
                
                current_qty = int(item_encontrado.get('cantidad', 1))
                item_encontrado['cantidad'] = current_qty + 1
                request.session['carrito'] = carrito
            else:
                messages.error(request, f"No hay más stock de {producto.name}")

        except Exception as e:
            print(f"Error al sumar: {e}")

    return redirect('carrito')


def restar_item_carrito(request, unique_id):
    carrito = request.session.get('carrito', [])
    item_encontrado = None
    
    for item in carrito:
        if item.get('unique_id') == unique_id:
            item_encontrado = item
            break

    if item_encontrado:
        current_qty = int(item_encontrado.get('cantidad', 1))
        
        if current_qty > 1:
            try:
                origen, producto_id = unique_id.split('-')
                producto_id = int(producto_id)
                
                if origen == 'a':
                    producto = ProductA.objects.get(id=producto_id)
                    db_alias = 'default'
                else:
                    producto = ProductB.objects.using('secondary').get(id=producto_id)
                    db_alias = 'secondary'

                producto.stock += 1
                producto.save(using=db_alias)

                item_encontrado['cantidad'] = current_qty - 1
                request.session['carrito'] = carrito

            except Exception as e:
                print(f"Error al restar: {e}")

    return redirect('carrito')

def api_carrito(request):
    """Devuelve el contenido del carrito en formato JSON para el Mini-Cart"""
    carrito = request.session.get('carrito', [])
    
    total_precio = 0
    total_items = 0
    
    data_carrito = []
    for item in carrito:
        cant = int(item.get('cantidad', 1))
        precio = float(item.get('precio', 0))
        total_precio += precio * cant
        total_items += cant
        
        data_carrito.append({
            'nombre': item.get('nombre'),
            'precio': precio,
            'cantidad': cant,
            'imagen': item.get('imagen', '/static/img/default.png'),
            'unique_id': item.get('unique_id')
        })

    return JsonResponse({
        'carrito': data_carrito,
        'total_precio': total_precio,
        'total_items': total_items
    })

def ver_local(request, local_id):
    """Vista pública para ver el perfil y productos de un local específico"""
    hoy = timezone.now().date()
    productos_procesados = []
    nombre_local = ""
    
    if local_id == 'a':
        productos_raw = ProductA.objects.all()
        nombre_local = "Local 1" 
    elif local_id == 'b':
        productos_raw = ProductB.objects.using('secondary').all()
        nombre_local = "Local 2"
    else:
        return redirect('home')

    for p in productos_raw:
        precio_a_mostrar = p.price
        precio_original = None
        en_oferta = False
        
        if p.precio_especial and p.fecha_inicio_especial and p.fecha_fin_especial:
            if p.fecha_inicio_especial <= hoy <= p.fecha_fin_especial:
                precio_a_mostrar = p.precio_especial
                precio_original = p.price
                en_oferta = True
        
        productos_procesados.append({
            'id': p.id,
            'nombre': p.name,
            'descripcion': p.description,
            'precio': precio_a_mostrar,
            'precio_original': precio_original,
            'en_oferta': en_oferta,
            'imagen': p.image.url if p.image else '/static/img/default.png',
            'origen': local_id, # 'a' o 'b'
            'local': nombre_local,
            'stock': p.stock
        })

    try:
            perfil = LocalProfile.objects.get(local_id=local_id)
            nombre_real = perfil.nombre_local
            descripcion = perfil.descripcion
            logo_url = perfil.logo.url if perfil.logo else None
            color_banner = perfil.color_banner 
    except LocalProfile.DoesNotExist:
            nombre_real = f"Local {1 if local_id=='a' else 2}"
            descripcion = "¡Bienvenidos a nuestra tienda!"
            logo_url = None
            color_banner = "#004aad" # Color por defecto si no hay perfil

    context = {
            'nombre_local': nombre_real,
            'descripcion_local': descripcion,
            'logo_url': logo_url,
            'color_banner': color_banner, # <--- Pasamos el color al HTML
            'local_id': local_id,
            'productos': productos_procesados
        }
    return render(request, 'core/ver_local.html', context)

def contacto(request):
    if request.method == 'POST':
        form = ContactoForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            email = form.cleaned_data['email']
            asunto = form.cleaned_data['asunto']
            mensaje = form.cleaned_data['mensaje']

            full_message = f"Nuevo mensaje de contacto de {nombre} ({email}):\n\nMotivo: {asunto}\n\n{mensaje}"
            
            try:
                send_mail(
                    subject=f"Contacto DuocGo: {asunto}",
                    message=full_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=['jexfryxd@gmail.com'],
                    fail_silently=False,
                )
                messages.success(request, "¡Mensaje enviado! Nos pondremos en contacto contigo pronto.")
                return redirect('home')
            except Exception as e:
                messages.error(request, "Hubo un error al enviar el mensaje. Inténtalo más tarde.")
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'nombre': request.user.username,
                'email': request.user.email
            }
        form = ContactoForm(initial=initial_data)

    return render(request, 'core/contacto.html', {'form': form})

@login_required(login_url='login')
def toggle_favorito(request, origen, producto_id):
    if origen == 'a':
        producto = get_object_or_404(ProductA, id=producto_id)
    else:
        producto = get_object_or_404(ProductB.objects.using('secondary'), id=producto_id)

    favorito_existente = Favorite.objects.filter(
        user=request.user, 
        product_id=producto_id, 
        origin=origen
    ).first()

    if favorito_existente:
        favorito_existente.delete()
        mensaje = "Eliminado de favoritos"
        estado = "removed"
    else:
        img_url = producto.image.url if producto.image else '/static/img/default.png'
        precio_final = producto.price
        hoy = timezone.now().date()
        if producto.precio_especial and producto.fecha_inicio_especial and producto.fecha_fin_especial:
            if producto.fecha_inicio_especial <= hoy <= producto.fecha_fin_especial:
                precio_final = producto.precio_especial

        Favorite.objects.create(
            user=request.user,
            product_id=producto_id,
            origin=origen,
            product_name=producto.name,
            product_image=img_url,
            price=precio_final
        )
        mensaje = "Agregado a favoritos"
        estado = "added"

    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required(login_url='login')
def mis_favoritos(request):
    favoritos = Favorite.objects.filter(user=request.user).order_by('-added_at')
    return render(request, 'core/mis_favoritos.html', {'favoritos': favoritos})

def inscripcion_local(request):
    if request.method == 'POST':
        form = InscripcionLocalForm(request.POST)
        if form.is_valid():
            # Extraer datos
            nombre = form.cleaned_data['nombre_local']
            rut = form.cleaned_data['rut_empresa']
            encargado = form.cleaned_data['nombre_encargado']
            email = form.cleaned_data['email_contacto']
            telefono = form.cleaned_data['telefono']
            mensaje = form.cleaned_data['mensaje_adicional']

            # Construir el correo para el administrador
            asunto = f"Nueva Solicitud de Inscripción de Local: {nombre}"
            cuerpo = f"""
            Se ha recibido una nueva solicitud para inscribir un local en DuocGo.
            
            DATOS DEL LOCAL:
            ----------------
            Nombre Local: {nombre}
            RUT Empresa: {rut}
            
            DATOS DE CONTACTO:
            ------------------
            Encargado: {encargado}
            Correo: {email}
            Teléfono: {telefono}
            
            MENSAJE ADICIONAL:
            ------------------
            {mensaje}
            
            ------------------
            Por favor, contacta al encargado para verificar los datos y crear su cuenta manualmente en el Admin de Django.
            """
            
            try:
                send_mail(
                    subject=asunto,
                    message=cuerpo,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=['jexfryxd@gmail.com'],
                    fail_silently=False,
                )
                messages.success(request, "¡Solicitud enviada! Nos pondremos en contacto contigo para habilitar tu local.")
                return redirect('login') 
            except Exception as e:
                messages.error(request, f"Error al enviar la solicitud: {e}")
    else:
        form = InscripcionLocalForm()

    return render(request, 'core/inscripcion_local.html', {'form': form})