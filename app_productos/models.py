from django.db import models
from decimal import Decimal # <--- IMPORTACIÓN NECESARIA

# ====================================
# MODELOS NUEVOS: CLIENTE Y EMPLEADO
# ====================================

# Modelo NUEVO: Cliente
class Cliente(models.Model):
    nombre_completo = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_completo

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre_completo']


# Modelo NUEVO: Empleado
class Empleado(models.Model):
    PUESTOS = [
        ('VEN', 'Vendedor'),
        ('CAJ', 'Cajero'),
        ('ALM', 'Almacenista'),
        ('GER', 'Gerente'),
        ('SUP', 'Supervisor'),
        ('OTR', 'Otro'),
    ]
    
    nombre_completo = models.CharField(max_length=150)
    puesto = models.CharField(max_length=3, choices=PUESTOS, default='VEN')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    fecha_contratacion = models.DateField()
    salario = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre_completo} - {self.get_puesto_display()}"

    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ['nombre_completo']


# ====================================
# MODELOS EXISTENTES
# ====================================

# Modelo 1: Categoria
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    pasillo = models.IntegerField(blank=True, null=True)
    responsable_area = models.CharField(max_length=100, blank=True, null=True)
    fecha_creacion = models.DateField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


# Modelo 2: Proveedor
class Proveedor(models.Model):
    nombre_empresa = models.CharField(max_length=150, unique=True)
    nombre_contacto = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    telefono_empresa = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_empresa


# Modelo 3: Producto
class Producto(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2) # El precio de venta base
    stock = models.IntegerField(default=0)
    codigo_barras = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    # Relaciones
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)
    proveedores = models.ManyToManyField(Proveedor, blank=True)

    def __str__(self):
        return self.nombre


# Modelo 4: Ventas (Cabecera de la Venta)
class Ventas(models.Model):
    METODOS_PAGO = [
        ('EFE', 'Efectivo'),
        ('TAR', 'Tarjeta de Crédito/Débito'),
        ('TRA', 'Transferencia Bancaria'),
        ('OTR', 'Otro'),
    ]

    fecha_venta = models.DateTimeField(auto_now_add=True)
    
    # ✅ RELACIÓN CON CLIENTE (ForeignKey)
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ventas',
        verbose_name='Cliente'
    )
    # Campo antiguo mantenido para compatibilidad con ventas existentes
    nombre_cliente = models.CharField(max_length=150, blank=True, null=True, help_text='(Obsoleto - usar campo Cliente)')
    
    metodo_pago = models.CharField(max_length=3, choices=METODOS_PAGO, default='EFE')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # ✅ RELACIÓN CON EMPLEADO (ForeignKey)
    empleado_vendedor = models.ForeignKey(
        Empleado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas_realizadas',
        verbose_name='Vendedor (Empleado)'
    )
    # Campo antiguo mantenido para compatibilidad con ventas existentes
    vendedor = models.CharField(max_length=100, blank=True, null=True, help_text='(Obsoleto - usar campo Empleado Vendedor)')
    
    esta_pagada = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)
    
    def __str__(self):
        # Priorizar el cliente de ForeignKey sobre nombre_cliente
        if self.cliente:
            return f"Venta #{self.id} - Cliente: {self.cliente.nombre_completo}"
        return f"Venta #{self.id} - Cliente: {self.nombre_cliente or 'N/A'}"
    
    def get_nombre_cliente_display(self):
        """Método auxiliar para obtener el nombre del cliente (nuevo o antiguo)"""
        if self.cliente:
            return self.cliente.nombre_completo
        return self.nombre_cliente or 'N/A'
    
    def get_nombre_vendedor_display(self):
        """Método auxiliar para obtener el nombre del vendedor (nuevo o antiguo)"""
        if self.empleado_vendedor:
            return self.empleado_vendedor.nombre_completo
        return self.vendedor or 'N/A'
        
    def update_monto_total(self):
        # Calcula la suma de los subtotales de todos los detalles de esta venta
        total_agregado = self.detalleventa.aggregate(total=models.Sum('subtotal'))['total']
        self.monto_total = total_agregado or Decimal('0.00')
        self.save() # Guarda la cabecera con el nuevo total

# Modelo 5: DetalleVenta (Línea de Producto en la Venta)
class DetalleVenta(models.Model):
    venta = models.ForeignKey(Ventas, on_delete=models.CASCADE, related_name='detalleventa')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_vendida = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) 
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00')) 
    
    class Meta:
        unique_together = ('venta', 'producto') 
    
    def __str__(self):
        return f"{self.cantidad_vendida} x {self.producto.nombre} en Venta #{self.venta.id}"

    # MÉTODO SAVE CORREGIDO PARA EVITAR EL TypeError
    def save(self, *args, **kwargs):
        # 1. Asegurarse de que todos los valores numéricos sean Decimal antes de operar
        try:
            # Convertimos la cantidad a Decimal para operaciones seguras
            cantidad = Decimal(self.cantidad_vendida) 
            precio = self.precio_unitario
            # Convertimos el porcentaje (0-100) a un factor de descuento (0-1)
            descuento_pct = self.descuento_porcentaje / Decimal(100) 
            
            # 2. Calcular Subtotal: (Cantidad * Precio) * (1 - Descuento%)
            base = cantidad * precio
            self.subtotal = base * (Decimal(1) - descuento_pct)
            
        except Exception:
            # En caso de error (e.g., campo vacío), asigna un valor seguro
            self.subtotal = Decimal('0.00')

        # 3. Guardar el detalle
        super().save(*args, **kwargs)
        
        # 4. Actualizar el monto total de la venta (cabecera)
        # Esto se ejecuta DESPUÉS de guardar el detalle
        self.venta.update_monto_total() 
        

# Modelo 6: Inventario
class Inventario(models.Model):
    TIPO_MOVIMIENTO = [
        ('ENT', 'Entrada'),
        ('SAL', 'Salida'),
        ('AJU', 'Ajuste'),
    ]
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    tipo_movimiento = models.CharField(max_length=3, choices=TIPO_MOVIMIENTO)
    cantidad = models.IntegerField()
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    razon = models.CharField(max_length=255, blank=True, null=True)
    responsable = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"Movimiento {self.tipo_movimiento} de {self.cantidad} de {self.producto.nombre}"