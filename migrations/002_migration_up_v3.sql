-- =============================================================================
-- MIGRACIÓN 4.3 · PASO 2: APLICACIÓN DE CAMBIOS (UP MIGRATION)
-- Archivo: 002_migration_up_v3.sql
-- Propósito: Ampliación relacional para Administración IoT preservando el historial
-- =============================================================================

-- IMPORTANTE SOBRE DDL EN MYSQL:
-- Las sentencias ALTER TABLE y CREATE TABLE producen COMMIT IMPLÍCITO en MySQL.
-- No confíes en ROLLBACK si una sentencia DDL falla a la mitad. Ejecutar paso a paso.

-- -----------------------------------------------------------------------------
-- 1. Tabla de Usuarios y Roles (RBAC)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(120) NOT NULL,
    rol ENUM('ADMINISTRADOR', 'USUARIO', 'INVITADO') NOT NULL DEFAULT 'USUARIO',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_usuario_rol (rol),
    INDEX idx_usuario_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 2. Tabla de Modelos Comerciales (Catálogo)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelos_vehiculo (
    id_modelo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    codigo_modelo VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255) NOT NULL,
    categoria VARCHAR(50) NOT NULL DEFAULT 'Montacargas',
    imagen_url VARCHAR(255) NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_modelo_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 3. Tabla de Capacidades y Comandos Permitidos por Modelo
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelos_comandos (
    id_modelo_comando INT AUTO_INCREMENT PRIMARY KEY,
    id_modelo INT NOT NULL,
    nombre_comando VARCHAR(60) NOT NULL,
    codigo_comando INT NOT NULL,
    descripcion VARCHAR(255) NULL,
    es_critico BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_mc_modelo FOREIGN KEY (id_modelo) REFERENCES modelos_vehiculo(id_modelo) ON DELETE CASCADE,
    UNIQUE KEY uk_modelo_codigo (id_modelo, codigo_comando)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 4. Extensión NO DESTRUCTIVA de la tabla existente `vehiculos` (Unidades Físicas)
-- -----------------------------------------------------------------------------
-- Agregamos columnas sólo si no existen mediante procedimiento auxiliar seguro

DELIMITER $$
DROP PROCEDURE IF EXISTS sp_migrar_columnas_vehiculos$$
CREATE PROCEDURE sp_migrar_columnas_vehiculos()
BEGIN
    -- id_modelo
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vehiculos' AND COLUMN_NAME = 'id_modelo'
    ) THEN
        ALTER TABLE vehiculos ADD COLUMN id_modelo INT NULL AFTER microcontrolador;
    END IF;

    -- propietario_id
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vehiculos' AND COLUMN_NAME = 'propietario_id'
    ) THEN
        ALTER TABLE vehiculos ADD COLUMN propietario_id INT NULL AFTER id_modelo;
    END IF;

    -- estado_comercial
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vehiculos' AND COLUMN_NAME = 'estado_comercial'
    ) THEN
        ALTER TABLE vehiculos ADD COLUMN estado_comercial ENUM('disponible', 'vendido', 'exhibicion', 'inactivo') NOT NULL DEFAULT 'disponible' AFTER propietario_id;
    END IF;

    -- numero_serie
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vehiculos' AND COLUMN_NAME = 'numero_serie'
    ) THEN
        ALTER TABLE vehiculos ADD COLUMN numero_serie VARCHAR(100) NULL AFTER estado_comercial;
    END IF;

    -- soporte_autorizado
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vehiculos' AND COLUMN_NAME = 'soporte_autorizado'
    ) THEN
        ALTER TABLE vehiculos ADD COLUMN soporte_autorizado BOOLEAN NOT NULL DEFAULT FALSE AFTER numero_serie;
    END IF;
END$$
DELIMITER ;

CALL sp_migrar_columnas_vehiculos();
DROP PROCEDURE IF EXISTS sp_migrar_columnas_vehiculos;

-- Índices y Llaves Foráneas en vehiculos (compatibles con registros existentes)
DELIMITER $$
DROP PROCEDURE IF EXISTS sp_agregar_fks_vehiculos$$
CREATE PROCEDURE sp_agregar_fks_vehiculos()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.TABLE_CONSTRAINTS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vehiculos' AND CONSTRAINT_NAME = 'fk_vehiculos_modelo'
    ) THEN
        ALTER TABLE vehiculos ADD CONSTRAINT fk_vehiculos_modelo FOREIGN KEY (id_modelo) REFERENCES modelos_vehiculo(id_modelo) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT * FROM information_schema.TABLE_CONSTRAINTS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vehiculos' AND CONSTRAINT_NAME = 'fk_vehiculos_propietario'
    ) THEN
        ALTER TABLE vehiculos ADD CONSTRAINT fk_vehiculos_propietario FOREIGN KEY (propietario_id) REFERENCES usuarios(id_usuario) ON DELETE SET NULL;
    END IF;
END$$
DELIMITER ;

CALL sp_agregar_fks_vehiculos();
DROP PROCEDURE IF EXISTS sp_agregar_fks_vehiculos;

-- -----------------------------------------------------------------------------
-- 5. Extensión NO DESTRUCTIVA de la tabla existente `demos`
-- -----------------------------------------------------------------------------
DELIMITER $$
DROP PROCEDURE IF EXISTS sp_migrar_columnas_demos$$
CREATE PROCEDURE sp_migrar_columnas_demos()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'demos' AND COLUMN_NAME = 'tipo'
    ) THEN
        ALTER TABLE demos ADD COLUMN tipo ENUM('FABRICA', 'PRIVADA') NOT NULL DEFAULT 'FABRICA' AFTER activo;
    END IF;

    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'demos' AND COLUMN_NAME = 'id_usuario'
    ) THEN
        ALTER TABLE demos ADD COLUMN id_usuario INT NULL AFTER tipo;
    END IF;

    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'demos' AND COLUMN_NAME = 'id_modelo'
    ) THEN
        ALTER TABLE demos ADD COLUMN id_modelo INT NULL AFTER id_usuario;
    END IF;
END$$
DELIMITER ;

CALL sp_migrar_columnas_demos();
DROP PROCEDURE IF EXISTS sp_migrar_columnas_demos;

DELIMITER $$
DROP PROCEDURE IF EXISTS sp_agregar_fks_demos$$
CREATE PROCEDURE sp_agregar_fks_demos()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.TABLE_CONSTRAINTS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'demos' AND CONSTRAINT_NAME = 'fk_demos_usuario'
    ) THEN
        ALTER TABLE demos ADD CONSTRAINT fk_demos_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT * FROM information_schema.TABLE_CONSTRAINTS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'demos' AND CONSTRAINT_NAME = 'fk_demos_modelo'
    ) THEN
        ALTER TABLE demos ADD CONSTRAINT fk_demos_modelo FOREIGN KEY (id_modelo) REFERENCES modelos_vehiculo(id_modelo) ON DELETE SET NULL;
    END IF;
END$$
DELIMITER ;

CALL sp_agregar_fks_demos();
DROP PROCEDURE IF EXISTS sp_agregar_fks_demos;

-- -----------------------------------------------------------------------------
-- 6. Tabla de Sesiones Temporales de Invitados (Control Concurrencia)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sesiones_invitado (
    id_sesion INT AUTO_INCREMENT PRIMARY KEY,
    id_vehiculo INT NOT NULL,
    alias_invitado VARCHAR(80) NOT NULL,
    token_sesion VARCHAR(64) NOT NULL UNIQUE,
    iniciada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expira_en TIMESTAMP NOT NULL,
    duracion_segundos INT NOT NULL DEFAULT 180,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    finalizada_por ENUM('TIEMPO', 'USUARIO', 'DETENER_EMERGENCIA', 'DESCONEXION') NULL,
    CONSTRAINT fk_sesion_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id_vehiculo) ON DELETE CASCADE,
    INDEX idx_sesion_activa (id_vehiculo, activa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 7. Tabla de Auditoría del Sistema
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auditoria (
    id_auditoria INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NULL,
    username_actor VARCHAR(50) NOT NULL,
    rol_actor VARCHAR(30) NOT NULL,
    accion VARCHAR(60) NOT NULL,
    recurso VARCHAR(60) NOT NULL,
    detalle TEXT NULL,
    ip_origen VARCHAR(45) NULL,
    resultado ENUM('EXITO', 'DENEGADO', 'FALLO') NOT NULL DEFAULT 'EXITO',
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_auditoria_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    INDEX idx_auditoria_fecha (fecha_hora),
    INDEX idx_auditoria_actor (username_actor),
    INDEX idx_auditoria_accion (accion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 8. Inserción de Datos Iniciales y Vinculación con Datos Existentes
-- -----------------------------------------------------------------------------

-- 8.1 Modelo inicial para el Montacargas IoT existente
INSERT INTO modelos_vehiculo (id_modelo, nombre, codigo_modelo, descripcion, categoria, activo)
VALUES (1, 'Montacargas IoT Arcade', 'MOD_FORKLIFT_01', 'Montacargas industrial a escala con tracción diferencial y elevador de horquillas', 'Montacargas', TRUE)
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

-- 8.2 Modelo complementario para catálogo comercial (Batman Tumbler)
INSERT INTO modelos_vehiculo (id_modelo, nombre, codigo_modelo, descripcion, categoria, activo)
VALUES (2, 'Batman Tumbler IoT', 'MOD_TUMBLER_01', 'Vehículo todoterreno de alta velocidad con sonido y luces turbo', 'Deportivo', TRUE)
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

-- 8.3 Capacidades del Montacargas (comandos permitidos)
INSERT IGNORE INTO modelos_comandos (id_modelo, nombre_comando, codigo_comando, descripcion, es_critico) VALUES
(1, 'AVANZAR', 1, 'Tracción hacia adelante', FALSE),
(1, 'RETROCEDER', 2, 'Tracción hacia atrás con alarma sonora', FALSE),
(1, 'GIRAR_IZQUIERDA', 3, 'Giro hacia la izquierda', FALSE),
(1, 'GIRAR_DERECHA', 4, 'Giro hacia la derecha', FALSE),
(1, 'SUBIR_HORQUILLAS', 5, 'Elevación de carga', FALSE),
(1, 'BAJAR_HORQUILLAS', 6, 'Descenso de carga', FALSE),
(1, 'CAMBIAR_VELOCIDAD', 7, 'Conmutador de velocidad lenta/rápida', FALSE),
(1, 'LUCES', 8, 'Alternador de luces frontales', FALSE),
(1, 'DETENER', 9, 'Parada inmediata prioritaria de seguridad', TRUE),
(1, 'ENCENDER_AUTO', 10, 'Arranque del sistema de tracción', FALSE),
(1, 'SONIDO', 11, 'Bocina / alarma', FALSE),
(1, 'ACTIVAR_CRUCERO', 12, 'Control de crucero automático', FALSE);

-- 8.4 Capacidades del Batman Tumbler
INSERT IGNORE INTO modelos_comandos (id_modelo, nombre_comando, codigo_comando, descripcion, es_critico) VALUES
(2, 'AVANZAR', 1, 'Impulso hacia adelante', FALSE),
(2, 'RETROCEDER', 2, 'Retroceso estándar', FALSE),
(2, 'GIRAR_IZQUIERDA', 3, 'Giro cerrado izquierda', FALSE),
(2, 'GIRAR_DERECHA', 4, 'Giro cerrado derecha', FALSE),
(2, 'LUCES', 8, 'Faros LED de combate', FALSE),
(2, 'DETENER', 9, 'Freno de emergencia prioritario', TRUE),
(2, 'SONIDO', 11, 'Sirena de combate', FALSE);

-- 8.5 Usuarios de Demostración Semilla (Contraseña 'Admin123!' hasheada con bcrypt o formato seguro)
-- Contraseña temporal para desarrollo: 'Pass1234!' (hash de ejemplo compatible con passlib / bcrypt)
INSERT INTO usuarios (id_usuario, username, email, password_hash, nombre_completo, rol, activo)
VALUES 
(1, 'admin', 'admin@empresa-iot.com', '$2b$12$e6xU7Wb6QjV7KjO9m2Z5Ou9ZzQzJ/BqZ9/3D6VfT4qXwB7rN6b9qy', 'Administrador General', 'ADMINISTRADOR', TRUE),
(2, 'comprador1', 'cliente1@correo.com', '$2b$12$e6xU7Wb6QjV7KjO9m2Z5Ou9ZzQzJ/BqZ9/3D6VfT4qXwB7rN6b9qy', 'Juan Pérez (Cliente)', 'USUARIO', TRUE),
(3, 'comprador2', 'cliente2@correo.com', '$2b$12$e6xU7Wb6QjV7KjO9m2Z5Ou9ZzQzJ/BqZ9/3D6VfT4qXwB7rN6b9qy', 'María López (Cliente)', 'USUARIO', TRUE)
ON DUPLICATE KEY UPDATE nombre_completo = VALUES(nombre_completo);

-- 8.6 Asignar el vehículo existente (id_vehiculo = 1) al modelo montacargas y dejarlo disponible/exhibición
UPDATE vehiculos 
SET id_modelo = 1, 
    estado_comercial = 'exhibicion', 
    numero_serie = 'SN-FORKLIFT-001',
    soporte_autorizado = FALSE
WHERE id_vehiculo = 1;

-- 8.7 Auditoría inicial del evento de migración
INSERT INTO auditoria (id_usuario, username_actor, rol_actor, accion, recurso, detalle, resultado)
VALUES (1, 'sistema', 'ADMINISTRADOR', 'MIGRACION_SCHEMA', 'base_de_datos:vehiculo_iot', 'Migración UP 4.3 aplicada con éxito', 'EXITO');
