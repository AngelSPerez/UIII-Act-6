from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError, transaction
from django.forms import inlineformset_factory, ModelForm, TextInput, Select 
from decimal import Decimal 
import json  # <-- AGREGAR ESTE IMPORT

# Importamos todos los modelos necesarios
from .models import (
    Producto, Categoria, Proveedor, 
    Ventas, Inventario, DetalleVenta
)


# =======================================================================
# --- FORMS Y FORMSETS (LÓGICA DE VENTA) ---
# =======================================================================

class DetalleVentaBaseForm(ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ('producto', 'cantidad_vendida', 'precio_unitario', 'descuento_porcentaje')
        
        widgets = {
            'producto': Select(attrs={'class': 'form-control producto-select'}),
            'cantidad_vendida': TextInput(attrs={'class': 'form-control', 'type': 'number', 'min': '1', 'value': '1'}),
            'precio_unitario': TextInput(attrs={'class': 'form-control precio-unitario-input', 'type': 'number', 'step': '0.01', 'readonly': 'readonly'}),
            'descuento_porcentaje': TextInput(attrs={'class': 'form-control', 'type': 'number', 'step': '0.01', 'value': '0', 'min': '0', 'max': '100'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'producto' in self.fields:
            self.fields['producto'].empty_label = "Seleccione un Producto"


DetalleVentaFormSet = inlineformset_factory(
    Ventas,
    DetalleVenta,
    form=DetalleVentaBaseForm, 
    extra=1,  # Esto crea UNA fila vacía visible por defecto
    can_delete=True
)


# =======================================================================
# --- VISTAS DE VENTAS (CRUD) ---
# =======================================================================

def ver_ventas(request):
    """Muestra la lista de transacciones de venta."""
    ventas = Ventas.objects.all().order_by('-fecha_venta')
    return render(request, 'venta/ver_ventas.html', {'ventas': ventas})


@transaction.atomic
def agregar_venta(request):
    """Permite registrar una nueva Venta (cabecera + detalles) en un solo paso."""
    
    metodos_pago = Ventas.METODOS_PAGO 
    venta_instance = Ventas()
    
    # Obtenemos todos los productos con su precio_venta para el JavaScript
    productos = Producto.objects.all().values('id', 'precio_venta')
    # IMPORTANTE: Convertimos Decimal a string para serialización JSON
    productos_list = [{'id': p['id'], 'precio_venta': str(p['precio_venta'])} for p in productos]
    productos_json = json.dumps(productos_list)
    
    if request.method == 'POST':
        formset = DetalleVentaFormSet(request.POST, instance=venta_instance)
        
        nombre_cliente = request.POST.get('nombre_cliente')
        metodo_pago = request.POST.get('metodo_pago')
        vendedor = request.POST.get('vendedor', '')
        
        if nombre_cliente and metodo_pago and formset.is_valid():
            
            venta_obj = Ventas.objects.create(
                nombre_cliente=nombre_cliente,
                metodo_pago=metodo_pago,
                vendedor=vendedor,
            )
            
            formset.instance = venta_obj 
            detalles_guardados = formset.save(commit=False)
            
            for detalle in detalles_guardados:
                try:
                    producto = Producto.objects.get(id=detalle.producto_id)
                    
                    if producto.stock < detalle.cantidad_vendida:
                        raise IntegrityError(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}")

                    producto.stock -= detalle.cantidad_vendida
                    producto.save()
                    
                    Inventario.objects.create(
                        producto=producto,
                        tipo_movimiento='SAL', 
                        cantidad=detalle.cantidad_vendida,
                        razon=f"Venta a cliente {nombre_cliente} (Venta #{venta_obj.id})",
                        responsable=vendedor or "Sistema"
                    )
                except Producto.DoesNotExist:
                    pass 
                
                detalle.venta = venta_obj
                detalle.save()
            
            formset.save_m2m()
            
            return redirect('ver_ventas')
        else:
            # Debug: Imprime errores del formset
            print("Errores del formset:", formset.errors)
            print("Errores non_form:", formset.non_form_errors())
        
    else:
        formset = DetalleVentaFormSet(instance=venta_instance)
        
    context = {
        'metodos_pago': metodos_pago,
        'formset': formset,
        'productos_json': productos_json  # <-- Cambiamos el nombre
    }
    return render(request, 'venta/agregar_venta.html', context)


@transaction.atomic 
def actualizar_venta(request, venta_id):
    """Actualiza la cabecera de una venta Y sus detalles usando un Formset."""
    venta = get_object_or_404(Ventas, id=venta_id)
    metodos_pago = Ventas.METODOS_PAGO 
    productos = Producto.objects.all().values('id', 'precio_venta')
    # IMPORTANTE: Convertimos Decimal a string para serialización JSON
    productos_list = [{'id': p['id'], 'precio_venta': str(p['precio_venta'])} for p in productos]
    productos_json = json.dumps(productos_list)
    
    original_detalles = {d.id: (d.producto_id, d.cantidad_vendida) for d in venta.detalleventa.all()}

    if request.method == 'POST':
        formset = DetalleVentaFormSet(request.POST, instance=venta)
        
        if formset.is_valid():
            venta.nombre_cliente = request.POST.get('nombre_cliente', venta.nombre_cliente)
            venta.metodo_pago = request.POST.get('metodo_pago', venta.metodo_pago)
            venta.vendedor = request.POST.get('vendedor', venta.vendedor)
            venta.esta_pagada = request.POST.get('esta_pagada') == 'on'
            venta.notas = request.POST.get('notas', venta.notas)
            venta.save()
            
            detalles_guardados = formset.save(commit=False)
            
            for form in formset.deleted_forms:
                if form.instance.pk:
                    original = original_detalles.get(form.instance.pk)
                    if original:
                        producto = Producto.objects.get(pk=original[0])
                        cantidad_a_revertir = original[1]
                        
                        producto.stock += cantidad_a_revertir
                        producto.save()
                        
                        form.instance.delete()
                        
            for detalle in detalles_guardados:
                producto = detalle.producto
                cantidad_nueva = detalle.cantidad_vendida
                
                cantidad_original = original_detalles.get(detalle.pk, (None, Decimal('0.00')))[1]
                diferencia_stock = cantidad_nueva - cantidad_original 
                
                if detalle.pk:
                    producto.stock -= diferencia_stock
                else:
                    producto.stock -= cantidad_nueva

                if producto.stock < 0:
                    raise IntegrityError(f"Stock insuficiente para {producto.nombre} después de la actualización.")
                            
                producto.save()
                
                detalle.venta = venta
                detalle.save()

            if not detalles_guardados:
                 venta.update_monto_total()

            return redirect('ver_ventas')
            
        else:
            pass
            
    else:
        formset = DetalleVentaFormSet(instance=venta)

    context = {
        'venta': venta,
        'metodos_pago': metodos_pago,
        'formset': formset,
        'productos_json': productos_json
    }
    return render(request, 'venta/actualizar_venta.html', context)


@transaction.atomic
def borrar_venta(request, venta_id):
    """Borra una venta y revierte el stock de los productos vendidos."""
    venta = get_object_or_404(Ventas, id=venta_id)
    
    if request.method == 'POST':
        for detalle in venta.detalleventa.all():
            try:
                producto = detalle.producto
                producto.stock += detalle.cantidad_vendida
                producto.save()
                
                Inventario.objects.create(
                    producto=producto,
                    tipo_movimiento='ENT', 
                    cantidad=detalle.cantidad_vendida,
                    razon=f"Reversión por borrado de Venta #{venta.id}",
                    responsable="Sistema"
                )
            except Producto.DoesNotExist:
                pass

        venta.delete()
        return redirect('ver_ventas')
        
    return render(request, 'venta/borrar_venta.html', {'venta': venta})


# =======================================================================
# --- VISTA BASE ---
# =======================================================================

def inicio(request):
    """Renderiza la página de inicio."""
    return render(request, 'inicio.html')


# =======================================================================
# --- VISTAS DE PRODUCTO (CRUD) ---
# =======================================================================

def ver_productos(request):
    productos = Producto.objects.all()
    return render(request, 'producto/ver_productos.html', {'productos': productos})

def agregar_producto(request):
    categorias = Categoria.objects.all()
    proveedores = Proveedor.objects.all()

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        precio_venta = request.POST.get('precio_venta')
        stock = request.POST.get('stock', 0)
        codigo_barras = request.POST.get('codigo_barras', '')
        categoria_id = request.POST.get('categoria')
        
        producto = Producto.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            precio_venta=precio_venta,
            stock=stock,
            codigo_barras=codigo_barras,
            categoria_id=categoria_id
        )
        proveedores_ids = request.POST.getlist('proveedores')
        producto.proveedores.set(proveedores_ids)

        return redirect('ver_productos')
    
    return render(request, 'producto/agregar_producto.html', {'categorias': categorias, 'proveedores': proveedores})

def actualizar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    categorias = Categoria.objects.all()
    proveedores = Proveedor.objects.all()

    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre', producto.nombre)
        producto.descripcion = request.POST.get('descripcion', producto.descripcion)
        producto.precio_venta = request.POST.get('precio_venta', producto.precio_venta)
        producto.stock = request.POST.get('stock', producto.stock)
        producto.codigo_barras = request.POST.get('codigo_barras', producto.codigo_barras)
        producto.categoria_id = request.POST.get('categoria', producto.categoria_id)
        producto.save()
        
        proveedores_ids = request.POST.getlist('proveedores')
        producto.proveedores.set(proveedores_ids)
        
        return redirect('ver_productos')
        
    return render(request, 'producto/actualizar_producto.html', {'producto': producto, 'categorias': categorias, 'proveedores': proveedores})

def borrar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        return redirect('ver_productos')
    return render(request, 'producto/borrar_producto.html', {'producto': producto})


# =======================================================================
# --- VISTAS DE CATEGORIA (CRUD) ---
# =======================================================================

def ver_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, 'categoria/ver_categorias.html', {'categorias': categorias})

def agregar_categoria(request):
    if request.method == 'POST':
        Categoria.objects.create(
            nombre=request.POST.get('nombre'),
            descripcion=request.POST.get('descripcion', ''),
            pasillo=request.POST.get('pasillo', None),
            responsable_area=request.POST.get('responsable_area', ''),
            activa=request.POST.get('activa') == 'on' 
        )
        return redirect('ver_categorias')
    return render(request, 'categoria/agregar_categoria.html')

def actualizar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        categoria.nombre = request.POST.get('nombre', categoria.nombre)
        categoria.descripcion = request.POST.get('descripcion', categoria.descripcion)
        categoria.pasillo = request.POST.get('pasillo', categoria.pasillo)
        categoria.responsable_area = request.POST.get('responsable_area', categoria.responsable_area)
        categoria.activa = request.POST.get('activa') == 'on'
        categoria.save()
        return redirect('ver_categorias')
    return render(request, 'categoria/actualizar_categoria.html', {'categoria': categoria})

def borrar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        categoria.delete()
        return redirect('ver_categorias')
    return render(request, 'categoria/borrar_categoria.html', {'categoria': categoria})


# =======================================================================
# --- VISTAS DE PROVEEDOR (CRUD) ---
# =======================================================================

def ver_proveedores(request):
    proveedores = Proveedor.objects.all()
    return render(request, 'proveedor/ver_proveedores.html', {'proveedores': proveedores})

def agregar_proveedor(request):
    if request.method == 'POST':
        Proveedor.objects.create(
            nombre_empresa=request.POST.get('nombre_empresa'),
            nombre_contacto=request.POST.get('nombre_contacto', ''),
            telefono=request.POST.get('telefono', ''),
            telefono_empresa=request.POST.get('telefono_empresa', ''),
            email=request.POST.get('email', ''),
            direccion=request.POST.get('direccion', '')
        )
        return redirect('ver_proveedores')
    return render(request, 'proveedor/agregar_proveedor.html')

def actualizar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    if request.method == 'POST':
        proveedor.nombre_empresa = request.POST.get('nombre_empresa', proveedor.nombre_empresa)
        proveedor.nombre_contacto = request.POST.get('nombre_contacto', proveedor.nombre_contacto)
        proveedor.telefono = request.POST.get('telefono', proveedor.telefono)
        proveedor.telefono_empresa = request.POST.get('telefono_empresa', proveedor.telefono_empresa) 
        proveedor.email = request.POST.get('email', proveedor.email)
        proveedor.direccion = request.POST.get('direccion', proveedor.direccion)
        proveedor.save()
        return redirect('ver_proveedores')
    return render(request, 'proveedor/actualizar_proveedor.html', {'proveedor': proveedor})

def borrar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    if request.method == 'POST':
        proveedor.delete()
        return redirect('ver_proveedores')
    return render(request, 'proveedor/borrar_proveedor.html', {'proveedor': proveedor})


# =======================================================================
# --- VISTAS DE INVENTARIO (CRUD) ---
# =======================================================================

def ver_movimientos_inventario(request):
    movimientos = Inventario.objects.all().order_by('-fecha_movimiento')
    return render(request, 'inventario/ver_inventario.html', {'movimientos': movimientos})

@transaction.atomic
def agregar_movimiento_inventario(request):
    productos = Producto.objects.all()
    tipos_movimiento = Inventario.TIPO_MOVIMIENTO
    
    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        tipo_movimiento = request.POST.get('tipo_movimiento')
        
        try:
            cantidad = int(request.POST.get('cantidad', 0))
        except ValueError:
            cantidad = 0
            
        razon = request.POST.get('razon')
        responsable = request.POST.get('responsable')

        if cantidad <= 0:
             return render(request, 'inventario/agregar_movimiento.html', {
                'productos': productos,
                'tipos_movimiento': tipos_movimiento,
                'error': 'La cantidad debe ser un número positivo.'
            })

        producto = get_object_or_404(Producto, id=producto_id)
        
        if tipo_movimiento == 'ENT':
            producto.stock += cantidad
        elif tipo_movimiento == 'SAL':
            if producto.stock < cantidad:
                return render(request, 'inventario/agregar_movimiento.html', {
                    'productos': productos,
                    'tipos_movimiento': tipos_movimiento,
                    'error': f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}'
                })
            producto.stock -= cantidad
        
        producto.save()
        
        Inventario.objects.create(
            producto=producto,
            tipo_movimiento=tipo_movimiento,
            cantidad=cantidad,
            razon=razon,
            responsable=responsable
        )
        
        return redirect('ver_movimientos_inventario')
    
    context = {
        'productos': productos,
        'tipos_movimiento': tipos_movimiento,
    }
    return render(request, 'inventario/agregar_movimiento.html', context)

def actualizar_movimiento(request, movimiento_id):
    movimiento = get_object_or_404(Inventario, id=movimiento_id)
    productos = Producto.objects.all()
    tipos_movimiento = Inventario.TIPO_MOVIMIENTO
    
    if request.method == 'POST':
        movimiento.producto_id = request.POST.get('producto', movimiento.producto_id)
        movimiento.tipo_movimiento = request.POST.get('tipo_movimiento', movimiento.tipo_movimiento)
        movimiento.cantidad = request.POST.get('cantidad', movimiento.cantidad)
        movimiento.razon = request.POST.get('razon', movimiento.razon)
        movimiento.responsable = request.POST.get('responsable', movimiento.responsable)
        
        movimiento.save()
        return redirect('ver_movimientos_inventario')
        
    context = {
        'movimiento': movimiento,
        'productos': productos,
        'tipos_movimiento': tipos_movimiento,
    }
    return render(request, 'inventario/actualizar_movimiento.html', context)

@transaction.atomic
def borrar_movimiento(request, movimiento_id):
    movimiento = get_object_or_404(Inventario, id=movimiento_id)
    
    if request.method == 'POST':
        producto = movimiento.producto
        cantidad = movimiento.cantidad
        tipo_movimiento = movimiento.tipo_movimiento
        
        if tipo_movimiento == 'ENT':
            if producto.stock < cantidad:
                 return render(request, 'inventario/borrar_movimiento.html', {
                    'movimiento': movimiento,
                    'error': f'No se puede borrar. El stock de {producto.nombre} quedaría negativo.'
                })
            producto.stock -= cantidad
        elif tipo_movimiento == 'SAL':
            producto.stock += cantidad
        
        producto.save()
        movimiento.delete()
            
        return redirect('ver_movimientos_inventario')
    
    return render(request, 'inventario/borrar_movimiento.html', {'movimiento': movimiento})