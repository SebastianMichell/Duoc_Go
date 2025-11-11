from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm, LoginForm,PagoJunaebForm
from products_a.models import Product as ProductA
from products_b.models import Product as ProductB
from django.http import JsonResponse, HttpResponseBadRequest
import uuid
from django.conf import settings
from django.http import HttpResponse
from django.core.mail import send_mail
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from .models import PagoJunaebOrder
import qrcode
import io
import json
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

# Vistas de Productos
def home(request):
    productos_a = ProductA.objects.all()
    productos_b = ProductB.objects.using('secondary').all() 

    productos = []
    
    # Carga y combina productos de Local 1 (origen 'a')
    for p in productos_a:
        productos.append({
            'id': p.id,
            'nombre': p.name,
            'descripcion': p.description,
            'precio': p.price,
            'imagen': p.image.url if p.image else '/static/img/default.png',
            'origen': 'a',  # Código para productos de Local 1
            'local': 'Local 1',
            'stock': p.stock
        })
        
    # Carga y combina productos de Local 2 (origen 'b')
    for p in productos_b:
        productos.append({
            'id': p.id,
            'nombre': p.name,
            'descripcion': p.description,
            'precio': p.price,
            'imagen': p.image.url if p.image else '/static/img/default.png',
            'origen': 'b',  # Código para productos de Local 2
            'local': 'Local 2',
            'stock': p.stock
        })

    return render(request, 'home.html', {'productos': productos})


# Vistas de Autenticación
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
                 # Esto solo debería pasar si hay un error muy raro después del save
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
                if user.tipo_usuario == "profesor" and not (user.email and user.email.endswith("@profesor.duoc")):
                     messages.error(request, "Los profesores deben usar un correo @profesor.duoc para ingresar.")
                     return render(request, "login.html", {"form": form})
                
                elif user.tipo_usuario == "estudiante" and user.email and user.email.endswith("@profesor.duoc"):
                     messages.error(request, "Los alumnos no pueden usar un correo @profesor.duoc.")
                     return render(request, "login.html", {"form": form})

                login(request, user)
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
    return render(request, 'perfil.html')

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

    unique_id = f"{origen}-{producto.id}"
    carrito = request.session.get('carrito', [])

    item_encontrado = False
    for item in carrito:
        if item.get('unique_id') == unique_id:
            item['cantidad'] = item.get('cantidad', 0) + 1 
            item_encontrado = True
            break # Salir del bucle

    if not item_encontrado:
        # NO está en el carrito, agregarlo con cantidad 1
        carrito.append({
            'unique_id': unique_id,
            'id': producto.id,
            'nombre': producto.name,
            'precio': float(producto.price),
            'origen': origen,
            'local': local,
            'cantidad': 1  # <-- Añadir la cantidad inicial
        })
    
    request.session['carrito'] = carrito

    # Descontar el stock
    if hasattr(producto, 'stock'):
        producto.stock -= 1
        producto.save(using=db_to_use)

    # Devolvemos la cantidad total de todos los productos para el ícono del carrito
    total_items_cantidad = sum(item.get('cantidad', 0) for item in carrito)
    return JsonResponse({'status': 'ok', 'total_items': total_items_cantidad})

def ver_carrito(request):
    carrito = request.session.get('carrito', [])
    # Multiplicar precio por cantidad
    total = sum(item['precio'] * item.get('cantidad', 1) for item in carrito) 
    return render(request, 'carrito.html', {'carrito': carrito, 'total': total})

def eliminar_del_carrito(request, unique_id):
    carrito = request.session.get('carrito', [])
    item_eliminado = None
    
    # Buscar el item a eliminar
    for item in carrito:
        if item.get('unique_id') == unique_id:
            item_eliminado = item
            break

    if item_eliminado:
        # Obtener la cantidad a devolver
        cantidad_a_devolver = item_eliminado.get('cantidad', 1) 
        
        try:
            origen, producto_id = item_eliminado['unique_id'].split('-')
            producto_id = int(producto_id)
            
            if origen == 'a':
                producto = ProductA.objects.get(id=producto_id)
                producto.stock += cantidad_a_devolver # <-- Usar cantidad correcta
                producto.save()
            elif origen == 'b':
                producto = ProductB.objects.using('secondary').get(id=producto_id)
                producto.stock += cantidad_a_devolver # <-- Usar cantidad correcta
                producto.save(using='secondary')
                
        except Exception as e:
            print(f"Error al devolver stock: {e}")

    # Eliminar el ítem de la lista del carrito
    carrito = [item for item in carrito if item.get('unique_id') != unique_id]
    request.session['carrito'] = carrito
    return redirect('carrito')


def generar_opciones_hora():
    """Genera las opciones de hora de retiro en formato (value, label)."""
    
    # 1. Obtiene la hora actual (en UTC, ej: 22:04 UTC)
    now_utc = timezone.now() 
    
    # 2. Calcula el inicio y el fin del rango en UTC
    start_time_utc = now_utc + timedelta(minutes=15) 
    
    minute = start_time_utc.minute
    minute_round = ((minute // 5) * 5) + 5
    
    if minute_round >= 60:
        start_time_utc = start_time_utc.replace(minute=0) + timedelta(hours=1)
    else:
        start_time_utc = start_time_utc.replace(minute=minute_round)

    # (ej: start_time_utc es 22:20 UTC)
    
    opciones = []
    
    current_time_utc = start_time_utc
    max_time_utc = now_utc + timedelta(minutes=30)
    
    while current_time_utc <= max_time_utc:
        
        # 3. 🚨 CORRECCIÓN 🚨
        # Convierte la hora UTC a la zona horaria local (America/Santiago)
        local_time = timezone.localtime(current_time_utc)
        
        # 4. Formatea la hora local
        # (ej: 22:20 UTC se convierte en 19:20 local)
        time_str = local_time.strftime("%H:%M") 
        
        opciones.append((time_str, time_str))
        current_time_utc += timedelta(minutes=5)
        
    return opciones


def enviar_correo_confirmacion(request, orden):
    """
    Construye y envía un correo HTML con el QR adjunto.
    Funciona tanto para PagoJunaebOrder como para WebpayOrder.
    """
    
    # Determinar el destinatario
    destinatario = orden.user_identifier
    if 'Invitado' in destinatario:
        # Si es invitado, no tenemos su correo, enviamos solo al admin
        lista_destinatarios = ['jexfryxd@gmail.com']
    else:
        # Envía al usuario Y al admin
        lista_destinatarios = [destinatario, 'jexfryxd@gmail.com']

    asunto = f"Confirmación de Orden #{orden.numero_orden} (DUOC GO)"
    
    # Contexto para la plantilla HTML
    context = {
        'orden': orden,
        'qr_url': request.build_absolute_uri(orden.qr_code.url)
    }

    # 1. Renderizar el HTML
    html_message = render_to_string('core/confirmacion_orden.html', context)
    
    # 2. Crear el fallback de texto plano
    plain_message = strip_tags(html_message)
    
    # 3. Crear el mensaje de correo
    email = EmailMultiAlternatives(
        subject=asunto,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=lista_destinatarios
    )
    
    # 4. Adjuntar la versión HTML
    email.attach_alternative(html_message, "text/html")

    # 5. Adjuntar la imagen QR
    try:
        # Abrimos la imagen QR que guardamos en el modelo
        with open(orden.qr_code.path, 'rb') as f:
            qr_image = MIMEImage(f.read())
            # 'qr_code' debe coincidir con el 'cid:qr_code' en el HTML
            qr_image.add_header('Content-ID', '<qr_code>') 
            qr_image.add_header('Content-Disposition', 'inline')
            email.attach(qr_image)
    except Exception as e:
        print(f"Error al adjuntar QR al correo: {e}")
        # El correo se enviará sin el QR adjunto si falla la lectura

    # 6. Enviar (a la consola, si settings está en 'console')
    email.send(fail_silently=False)


# --- VISTA DE PAGO (JUNAEB) ---

def pago_junaeb(request):
    carrito = request.session.get('carrito', [])
    if not carrito:
        messages.error(request, "El carrito está vacío.")
        return redirect('carrito')

    # Multiplicar precio por cantidad
    total = sum(item['precio'] * item.get('cantidad', 1) for item in carrito)
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

            # --- GENERAR Y GUARDAR CÓDIGO QR ---
            qr_data = nueva_orden.numero_orden
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            
            file_name = f'junaeb_qr_{nueva_orden.numero_orden}.png'
            nueva_orden.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)
            
            # --- 3. ENVIAR CORREO (CON QR) ---
            try:
                enviar_correo_confirmacion(request, nueva_orden)
                messages.success(request, f"Datos de pago Junaeb enviados. Revisa tu correo.")
                
            except Exception as e:
                messages.error(request, f"Error al enviar el correo. Detalle: {e}. La orden N° {nueva_orden.numero_orden} ha sido guardada.")
            
            # --- 4. REDIRECCIÓN DE ÉXITO ---
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
    """
    Vista de éxito para Junaeb. Busca la orden para mostrar el QR.
    (Esta vista se reutiliza para ambos flujos al final)
    """
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


# --- VISTAS DE PAGO (WEBPAY/TRANSBANK) ---

def iniciar_pago(request):
    if request.method != "POST":
        return redirect('carrito')
        
    carrito = request.session.get('carrito', [])
    if not carrito:
        messages.error(request, "El carrito está vacío.")
        return redirect('carrito')

    # Multiplicar precio por cantidad
    total = int(sum(item['precio'] * item.get('cantidad', 1) for item in carrito))
    
    buy_order = str(uuid.uuid4()).replace('-', '')[:10]
    session_id = str(uuid.uuid4()).replace('-', '')[:10]
    
    request.session['transbank_data'] = {
        'buy_order': buy_order,
        'session_id': session_id,
        'total': total
    }
    
    return_url = request.build_absolute_uri(reverse('pago_exito')) # Usar reverse() es más seguro

    tx = Transaction.build_for_integration(
        IntegrationCommerceCodes.WEBPAY_PLUS, 
        IntegrationApiKeys.WEBPAY
    )
    
    response = tx.create(buy_order, session_id, total, return_url)
    return redirect(response['url'] + '?token_ws=' + response['token'])


def pago_exito(request):
    token = request.POST.get('token_ws') or request.GET.get('token_ws')
    transbank_data = request.session.pop('transbank_data', None)
    
    from .models import WebpayOrder # Importar modelo Webpay
    
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
            # PAGO EXITOSO
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
    
    from .models import WebpayOrder
    
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

        # 1. ACTUALIZAR LA ORDEN WEBPAY CON LA HORA
        orden.hora_retiro = hora_retiro
        
        # 2. GENERAR Y GUARDAR EL QR
        qr_data = orden.numero_orden
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')

        file_name = f'webpay_qr_{orden.numero_orden}.png'
        orden.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)
        
        # --- 3. ENVIAR CORREO (CON QR) ---
        try:
            enviar_correo_confirmacion(request, orden)
            messages.success(request, f"¡Orden N° {orden.numero_orden} confirmada! Revisa tu correo.")

        except Exception as e:
            messages.error(request, f"Error al enviar el correo. Detalle: {e}. La orden N° {orden.numero_orden} ha sido guardada.")
        
        del request.session['orden_webpay_id']
        
        # 4. MOSTRAR LA PANTALLA DE ÉXITO FINAL
        return render(request, 'core/pago_exitoso.html', {'orden': orden})

    return render(request, 'core/seleccionar_hora_webpay.html', {'hora_choices': hora_choices})
# --- VISTA DE API (DRF) ---
class OrdenesPendientesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para exponer las órdenes Junaeb PENDIENTES.
    """
    queryset = PagoJunaebOrder.objects.filter(estado='PENDIENTE').order_by('hora_retiro')
    serializer_class = PagoJunaebOrderSerializer
    permission_classes = [AllowAny]