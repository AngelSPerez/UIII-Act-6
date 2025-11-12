from django.db import models
from decimal import Decimal # <--- IMPORTACIÓN NECESARIA

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
    nombre_cliente = models.CharField(max_length=150, blank=True, null=True)
    metodo_pago = models.CharField(max_length=3, choices=METODOS_PAGO, default='EFE')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    vendedor = models.CharField(max_length=100, blank=True, null=True)
    esta_pagada = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Venta #{self.id} - Cliente: {self.nombre_cliente or 'N/A'}"
        
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