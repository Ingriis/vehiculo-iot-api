-- =============================================================================
-- MIGRACIÓN 4.3 · PASO 1: VERIFICACIÓN PREVIA Y DIAGNÓSTICO DE RESPALDO
-- Archivo: 001_initial_backup_verification.sql
-- Propósito: Auditar el estado actual de MySQL/RDS antes de cualquier cambio DDL.
-- =============================================================================

-- 1. Instrucciones de Respaldo Obligatorio en Servidor / Terminal
-- Ejecutar en PowerShell/Bash antes de aplicar cualquier migración:
-- mysqldump -h <DB_HOST> -u <DB_USER> -p --routines --triggers --single-transaction vehiculo_iot > backup_vehiculo_iot_pre_v3.sql

-- 2. Conteo de registros existentes (Línea Base)
SELECT 'vehiculos' AS tabla, COUNT(*) AS total_registros FROM vehiculos
UNION ALL
SELECT 'comandos' AS tabla, COUNT(*) AS total_registros FROM comandos
UNION ALL
SELECT 'estados' AS tabla, COUNT(*) AS total_registros FROM estados
UNION ALL
SELECT 'historial' AS tabla, COUNT(*) AS total_registros FROM historial
UNION ALL
SELECT 'demos' AS tabla, COUNT(*) AS total_registros FROM demos
UNION ALL
SELECT 'demo_movimientos' AS tabla, COUNT(*) AS total_registros FROM demo_movimientos;

-- 3. Verificación de existencia de Stored Procedures de 4.1 y 4.2
SELECT ROUTINE_NAME, ROUTINE_TYPE, CREATED
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = DATABASE()
  AND ROUTINE_NAME IN (
    'sp_actualizar_comando', 'sp_actualizar_demo', 'sp_actualizar_estado',
    'sp_actualizar_movimiento_demo', 'sp_actualizar_vehiculo', 'sp_agregar_movimiento_demo',
    'sp_crear_comando', 'sp_crear_demo', 'sp_crear_vehiculo', 'sp_eliminar_comando',
    'sp_eliminar_demo', 'sp_eliminar_movimiento_demo', 'sp_eliminar_vehiculo',
    'sp_obtener_comandos_vehiculo', 'sp_obtener_demos', 'sp_obtener_estado',
    'sp_obtener_historial', 'sp_obtener_movimientos_demo', 'sp_obtener_vehiculo',
    'sp_obtener_vehiculos', 'sp_registrar_historial'
  )
ORDER BY ROUTINE_NAME;

-- 4. Verificación de integridad de llaves foráneas actuales
SELECT 
    TABLE_NAME, 
    COLUMN_NAME, 
    CONSTRAINT_NAME, 
    REFERENCED_TABLE_NAME, 
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() 
  AND REFERENCED_TABLE_NAME IS NOT NULL;
