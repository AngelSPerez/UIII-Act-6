from django.urls import path
from . import views

urlpatterns = [
    # Ruta raíz
    path('', views.inicio, name='inicio'), 
    
    # --- RUTAS DE PRODUCTOS ---
    path('productos/', views.ver_productos, name='ver_productos'), 
    path('productos/agregar/', views.agregar_producto, name='agregar_producto'),
    path('productos/<int:producto_id>/editar/', views.actualizar_producto, name='actualizar_producto'),
    path('productos/<int:producto_id>/borrar/', views.borrar_producto, name='borrar_producto'),

    # --- RUTAS DE CATEGORIAS ---
    path('categorias/', views.ver_categorias, name='ver_categorias'),
    path('categorias/agregar/', views.agregar_categoria, name='agregar_categoria'),
    path('categorias/<int:categoria_id>/editar/', views.actualizar_categoria, name='actualizar_categoria'),
    path('categorias/<int:categoria_id>/borrar/', views.borrar_categoria, name='borrar_categoria'),

    # --- RUTAS DE PROVEEDORES ---
    path('proveedores/', views.ver_proveedores, name='ver_proveedores'),
    path('proveedores/agregar/', views.agregar_proveedor, name='agregar_proveedor'),
    path('proveedores/<int:proveedor_id>/editar/', views.actualizar_proveedor, name='actualizar_proveedor'),
    path('proveedores/<int:proveedor_id>/borrar/', views.borrar_proveedor, name='borrar_proveedor'),

    # --- RUTAS DE VENTAS ---
    path('ventas/', views.ver_ventas, name='ver_ventas'),
    path('ventas/agregar/', views.agregar_venta, name='agregar_venta'),
    path('ventas/<int:venta_id>/editar/', views.actualizar_venta, name='actualizar_venta'),
    path('ventas/<int:venta_id>/borrar/', views.borrar_venta, name='borrar_venta'),

    # --- RUTAS DE CLIENTES ---
    path('clientes/', views.ver_clientes, name='ver_clientes'),
    path('clientes/agregar/', views.agregar_cliente, name='agregar_cliente'),
    path('clientes/<int:cliente_id>/editar/', views.actualizar_cliente, name='actualizar_cliente'),
    path('clientes/<int:cliente_id>/borrar/', views.borrar_cliente, name='borrar_cliente'),

    # --- RUTAS DE EMPLEADOS ---
    path('empleados/', views.ver_empleados, name='ver_empleados'),
    path('empleados/agregar/', views.agregar_empleado, name='agregar_empleado'),
    path('empleados/<int:empleado_id>/editar/', views.actualizar_empleado, name='actualizar_empleado'),
    path('empleados/<int:empleado_id>/borrar/', views.borrar_empleado, name='borrar_empleado'),

    # --- RUTAS DE INVENTARIO ---
    path('inventario/', views.ver_movimientos_inventario, name='ver_movimientos_inventario'),
    path('inventario/agregar/', views.agregar_movimiento_inventario, name='agregar_movimiento_inventario'),
    path('inventario/<int:movimiento_id>/editar/', views.actualizar_movimiento, name='actualizar_movimiento'),
    path('inventario/<int:movimiento_id>/borrar/', views.borrar_movimiento, name='borrar_movimiento'),
]