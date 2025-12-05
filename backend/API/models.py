from sqlalchemy import Column, Integer, String, Float, DECIMAL, TIMESTAMP, Enum, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .dependencies import Base  # Importa Base de dependencies.py

# Modelo para usuarios
class Usuario(Base):
    __tablename__ = 'usuarios'
    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum('admin', 'repartidor'), nullable=False)
    fecha_registro = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')

# Modelo para vehiculos
class Vehiculo(Base):
    __tablename__ = 'vehiculos'
    id_vehiculo = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(Enum('gasolina', 'hibrido', 'electrico'), nullable=False)
    nombre_modelo = Column(String(100), nullable=False)
    consumo_gasolina = Column(Float)
    consumo_electrico = Column(Float)
    precio_gasolina = Column(Float)
    precio_kwh = Column(Float)
    capacidad_carga_kg = Column(Float)
    capacidad_carga_m3 = Column(Float)
    autonomia_km = Column(Float)
    factor_emisiones_gasolina = Column(Float, default=2.31)
    factor_emisiones_electrico = Column(Float, default=0.45)
    rendimiento_gasolina = Column(Float)
    rendimiento_electrico = Column(Float)
    costo_mantenimiento_km = Column(Float)
    valor_aproximado = Column(Float)
    velocidad_promedio_kmh = Column(Float, default=25.0)

# Modelo para nodos_del_mapa
class NodoMapa(Base):
    __tablename__ = 'nodos_del_mapa'
    id_nodo = Column(Integer, primary_key=True, autoincrement=True)
    latitud = Column(DECIMAL(10, 8), nullable=False)
    longitud = Column(DECIMAL(11, 8), nullable=False)
    nombre = Column(String(100))
    tipo = Column(Enum('almacen', 'cliente', 'interseccion', 'punto_interes'), nullable=False)
    direccion = Column(Text)
    fecha_creacion = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')

# Modelo para conexiones_mapa
class ConexionMapa(Base):
    __tablename__ = 'conexiones_mapa'
    id_conexion = Column(Integer, primary_key=True, autoincrement=True)
    id_nodo_origen = Column(Integer, ForeignKey('nodos_del_mapa.id_nodo'), nullable=False)
    id_nodo_destino = Column(Integer, ForeignKey('nodos_del_mapa.id_nodo'), nullable=False)
    distancia_km = Column(DECIMAL(8, 3), nullable=False)
    tiempo_min = Column(DECIMAL(8, 2), nullable=False)
    tipo_via = Column(Enum('autopista', 'avenida', 'calle', 'atajo'), default='calle')
    trafico_promedio = Column(DECIMAL(3, 2), default=0.0)

# Modelo para pedidos
class Pedido(Base):
    __tablename__ = 'pedidos'
    id_pedido = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario_admin = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    id_vehiculo = Column(Integer, ForeignKey('vehiculos.id_vehiculo'))
    destino_lat = Column(DECIMAL(10, 8), nullable=False)
    destino_lng = Column(DECIMAL(11, 8), nullable=False)
    peso_kg = Column(DECIMAL(8, 2), nullable=False)
    volumen_m3 = Column(DECIMAL(8, 4), nullable=False)
    descripcion = Column(Text)
    estado = Column(Enum('pendiente', 'asignado', 'en_ruta', 'entregado', 'cancelado'), default='pendiente')
    fecha_creacion = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')

# Modelo para entregas
class Entrega(Base):
    __tablename__ = 'entregas'
    id_entrega = Column(Integer, primary_key=True, autoincrement=True)
    id_pedido = Column(Integer, ForeignKey('pedidos.id_pedido'), nullable=False)
    id_usuario_repartidor = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    estado = Column(Enum('asignado', 'en_ruta', 'entregado'), default='asignado')
    fecha_asignacion = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')
    fecha_entrega = Column(TIMESTAMP)

# Modelo para rutas_optimizadas
class RutaOptimizada(Base):
    __tablename__ = 'rutas_optimizadas'
    id_ruta = Column(Integer, primary_key=True, autoincrement=True)
    id_pedido = Column(Integer, ForeignKey('pedidos.id_pedido'), nullable=False)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    id_vehiculo = Column(Integer, ForeignKey('vehiculos.id_vehiculo'), nullable=False)
    origen_lat = Column(DECIMAL(10, 8), nullable=False)
    origen_lng = Column(DECIMAL(11, 8), nullable=False)
    ruta_calculada = Column(JSON)
    distancia_km = Column(DECIMAL(8, 3), nullable=False)
    tiempo_estimado_min = Column(DECIMAL(8, 2), nullable=False)
    energia_usada_kwh = Column(DECIMAL(8, 2))
    energia_usada_litros = Column(DECIMAL(8, 2))
    costo_estimado = Column(DECIMAL(8, 2), nullable=False)
    emisiones_co2_kg = Column(DECIMAL(8, 2))
    modo = Column(Enum('simulacion', 'real'), nullable=False)
    fecha_calculo = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')