-- ============================================
-- TABLA: usuarios
-- ============================================
CREATE TABLE usuarios (
    id_usuario INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('admin', 'repartidor') NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLA: vehiculos
-- ============================================
CREATE TABLE vehiculos (
    id_vehiculo INT PRIMARY KEY AUTO_INCREMENT,
    tipo ENUM('gasolina', 'hibrido', 'electrico') NOT NULL,
    nombre_modelo VARCHAR(100) NOT NULL,
    consumo_gasolina FLOAT,          -- L por 100km
    consumo_electrico FLOAT,         -- kWh por 100km
    precio_gasolina FLOAT,           -- $ por litro
    precio_kwh FLOAT,                -- $ por kWh
    capacidad_carga_kg FLOAT,
    capacidad_carga_m3 FLOAT,
    autonomia_km FLOAT,
    factor_emisiones_gasolina FLOAT DEFAULT 2.31,
    factor_emisiones_electrico FLOAT DEFAULT 0.45,
    velocidad_promedio_kmh FLOAT DEFAULT 25.0
);

-- ============================================
-- TABLA: pedidos
-- ============================================
CREATE TABLE pedidos (
    id_pedido INT PRIMARY KEY AUTO_INCREMENT,
    id_usuario_admin INT NOT NULL,
    id_vehiculo INT,
    direccion_destino VARCHAR(255) NOT NULL,  -- Dirección textual
    destino_lat DECIMAL(10, 8),               -- Opcional: guardar coordenadas
    destino_lng DECIMAL(11, 8),               -- si MapQuest las devuelve
    peso_kg DECIMAL(8, 2) NOT NULL,
    volumen_m3 DECIMAL(8, 4) NOT NULL,
    descripcion TEXT,
    estado ENUM('pendiente', 'asignado', 'en_ruta', 'entregado', 'cancelado') DEFAULT 'pendiente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Campos para ruteo (calculados por MapQuest)
    distancia_km DECIMAL(8, 3),
    tiempo_estimado_min DECIMAL(8, 2),
    -- Campos para resultados de cálculo
    costo_estimado DECIMAL(8, 2),
    emisiones_co2_kg DECIMAL(8, 2),
    energia_consumida DECIMAL(8, 2),
    
    FOREIGN KEY (id_usuario_admin) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id_vehiculo) ON DELETE SET NULL
);

-- ============================================
-- TABLA: entregas
-- ============================================
CREATE TABLE entregas (
    id_entrega INT PRIMARY KEY AUTO_INCREMENT,
    id_pedido INT NOT NULL,
    id_usuario_repartidor INT NOT NULL,
    estado ENUM('asignado', 'en_ruta', 'entregado') DEFAULT 'asignado',
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega TIMESTAMP NULL,
    observaciones TEXT,
    
    FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario_repartidor) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);