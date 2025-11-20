from django.contrib import admin
# Importamos los modelos solicitados
from .models import Producto, Categoria, Proveedor, Ventas, DetalleVenta, Inventario, Cliente, Empleado

# --- REGISTROS PARA CLIENTES ---
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'telefono', 'email', 'activo', 'fecha_registro')
    search_fields = ('nombre_completo', 'telefono', 'email')
    list_filter = ('activo', 'fecha_registro')
    ordering = ['nombre_completo']

# --- REGISTROS PARA EMPLEADOS ---
@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'puesto', 'telefono', 'fecha_contratacion', 'activo')
    search_fields = ('nombre_completo', 'telefono', 'email')
    list_filter = ('puesto', 'activo', 'fecha_contratacion')
    ordering = ['nombre_completo']

# Registros de Producto, Categoria, Proveedor
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_venta', 'stock', 'categoria')
    search_fields = ('nombre', 'codigo_barras')
    list_filter = ('categoria',)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'pasillo', 'responsable_area', 'activa')
    search_fields = ('nombre', 'responsable_area')
    list_filter = ('activa', 'pasillo')

admin.site.register(Proveedor)


# --- REGISTROS PARA VENTAS ---

# Inline para DetalleVenta
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1 
    readonly_fields = ('subtotal',)

@admin.register(Ventas)
class VentasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_cliente', 'fecha_venta', 'monto_total', 'metodo_pago', 'vendedor', 'esta_pagada')
    list_filter = ('fecha_venta', 'metodo_pago', 'esta_pagada')
    search_fields = ('nombre_cliente', 'vendedor')
    readonly_fields = ('monto_total',)
    inlines = [DetalleVentaInline]

# --- REGISTROS PARA INVENTARIO ---

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo_movimiento', 'cantidad', 'fecha_movimiento', 'responsable', 'razon')
    list_filter = ('tipo_movimiento', 'producto__categoria', 'fecha_movimiento')
    search_fields = ('producto__nombre', 'razon', 'responsable')

# Opcional: Registrar DetalleVenta si quieres verlo en la interfaz de admin
# admin.site.register(DetalleVenta)