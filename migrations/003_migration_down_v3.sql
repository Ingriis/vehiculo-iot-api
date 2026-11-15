-- =============================================================================
-- MIGRACIÓN 4.3 · PASO 3: REVERSIÓN RAZONABLE (DOWN MIGRATION)
-- Archivo: 003_migration_down_v3.sql
-- Propósito: Restaurar el esquema anterior para ambientes de prueba sin perder datos históricos
-- =============================================================================

-- IMPORTANTE:
-- Este script es exclusivo para entornos de prueba o contingencia.
-- NUNCA elimina las tablas originales ni los datos históricos de vehiculos,
-- comandos, estados, historial, demos ni demo_movimientos.

-- 1. Eliminar llaves foráneas creadas en vehiculos y demos
ALTER TABLE vehiculos DROP FOREIGN KEY IF EXISTS fk_vehiculos_modelo;
ALTER TABLE vehiculos DROP FOREIGN KEY IF EXISTS fk_vehiculos_propietario;
ALTER TABLE demos DROP FOREIGN KEY IF EXISTS fk_demos_usuario;
ALTER TABLE demos DROP FOREIGN KEY IF EXISTS fk_demos_modelo;

-- 2. Eliminar columnas agregadas a vehiculos
ALTER TABLE vehiculos 
    DROP COLUMN IF EXISTS soporte_autorizado,
    DROP COLUMN IF EXISTS numero_serie,
    DROP COLUMN IF EXISTS estado_comercial,
    DROP COLUMN IF EXISTS propietario_id,
    DROP COLUMN IF EXISTS id_modelo;

-- 3. Eliminar columnas agregadas a demos
ALTER TABLE demos 
    DROP COLUMN IF EXISTS id_modelo,
    DROP COLUMN IF EXISTS id_usuario,
    DROP COLUMN IF EXISTS tipo;

-- 4. Eliminar tablas agregadas en orden inverso de dependencias
DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS sesiones_invitado;
DROP TABLE IF EXISTS modelos_comandos;
DROP TABLE IF EXISTS modelos_vehiculo;
DROP TABLE IF EXISTS usuarios;
