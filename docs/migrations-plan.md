# Plan y Diagrama de Migración · Base de Datos MySQL / Amazon RDS

## 1. Diagrama Entidad-Relación Ampliado (Práctica 4.3)

```mermaid
erDiagram
    USUARIOS ||--o{ VEHICULOS : "posee (propietario_id)"
    USUARIOS ||--o{ DEMOS : "crea (privadas)"
    USUARIOS ||--o{ AUDITORIA : "registra acción"
    MODELOS_VEHICULO ||--o{ VEHICULOS : "instancia física (id_modelo)"
    MODELOS_VEHICULO ||--o{ MODELOS_COMANDOS : "define capacidades"
    MODELOS_VEHICULO ||--o{ DEMOS : "compatible con"
    VEHICULOS ||--o{ COMANDOS : "tiene asignados"
    VEHICULOS ||--o| ESTADOS : "estado actual"
    VEHICULOS ||--o{ HISTORIAL : "registra movimientos"
    VEHICULOS ||--o{ SESIONES_INVITADO : "reserva exclusiva"
    VEHICULOS ||--o{ DEMOS : "contiene demos"
    DEMOS ||--o{ DEMO_MOVIMIENTOS : "secuencia ordenada de pasos"
    COMANDOS ||--o{ DEMO_MOVIMIENTOS : "ejecuta en paso"
    COMANDOS ||--o{ HISTORIAL : "registrado en"

    USUARIOS {
        int id_usuario PK
        string username UK
        string email UK
        string password_hash
        string nombre_completo
        enum rol "ADMINISTRADOR, USUARIO, INVITADO"
        boolean activo
    }

    MODELOS_VEHICULO {
        int id_modelo PK
        string nombre UK
        string codigo_modelo UK
        string descripcion
        string categoria
        string imagen_url
        boolean activo
    }

    MODELOS_COMANDOS {
        int id_modelo_comando PK
        int id_modelo FK
        string nombre_comando
        int codigo_comando
        boolean es_critico
    }

    VEHICULOS {
        int id_vehiculo PK
        string nombre
        string modelo
        string descripcion
        string microcontrolador
        boolean activo
        int id_modelo FK
        int propietario_id FK
        enum estado_comercial "disponible, vendido, exhibicion, inactivo"
        string numero_serie UK
        boolean soporte_autorizado
    }

    SESIONES_INVITADO {
        int id_sesion PK
        int id_vehiculo FK
        string alias_invitado
        string token_sesion UK
        timestamp iniciada_en
        timestamp expira_en
        int duracion_segundos
        boolean activa
        enum finalizada_por
    }

    AUDITORIA {
        int id_auditoria PK
        int id_usuario FK
        string username_actor
        string rol_actor
        string accion
        string recurso
        text detalle
        enum resultado "EXITO, DENEGADO, FALLO"
        timestamp fecha_hora
    }
```

## 2. Inventario de Tablas y Estrategia de Migración

| Tabla | Estado | Justificación |
|---|---|---|
| `vehiculos` | **Conservada y Alterada** | Se conservan todos los campos y registros para compatibilidad de los 21 Stored Procedures. Se agregan columnas opcionales: `id_modelo`, `propietario_id`, `estado_comercial`, `numero_serie` y `soporte_autorizado`. |
| `comandos` | **Conservada intacta** | Mantiene los códigos y comandos que operan en los microcontroladores y endpoints. |
| `estados` | **Conservada intacta** | Mantiene el estado en tiempo real actualizado por movimientos y demos. |
| `historial` | **Conservada intacta** | Preserva íntegramente los datos históricos registrados en las prácticas 4.1 y 4.2. |
| `demos` | **Conservada y Alterada** | Se agregan campos opcionales (`tipo`: `FABRICA`/`PRIVADA`, `id_usuario`, `id_modelo`) sin alterar los SPs que la consultan. |
| `demo_movimientos` | **Conservada intacta** | Almacena los pasos, orden, duración y pausa de cada demo. |
| `usuarios` | **Nueva** | Manejo de RBAC: `ADMINISTRADOR`, `USUARIO` (comprador) e `INVITADO`. |
| `modelos_vehiculo` | **Nueva** | Catálogo comercial para separar el modelo de catálogo de la unidad física particular. |
| `modelos_comandos` | **Nueva** | Validación de capacidades de hardware por modelo. |
| `sesiones_invitado` | **Nueva** | Control de concurrencia y tiempo de prueba limitado en unidades de exhibición. |
| `auditoria` | **Nueva** | Trazabilidad de operaciones sensibles (altas, reasignaciones, cambios de rol, cancelaciones). |

## 3. Consideraciones de MySQL / Amazon RDS y DDL

> **ADVERTENCIA CRÍTICA: Commit Implícito en MySQL:**
> En MySQL, cualquier sentencia DDL (`ALTER TABLE`, `CREATE TABLE`, `DROP TABLE`, `CREATE INDEX`) provoca un **COMMIT implícito** de cualquier transacción abierta.
> 
> Por lo tanto, no es posible envolver la migración en un `START TRANSACTION ... ROLLBACK`. La ejecución debe realizarse mediante scripts versionados probados previamente, verificando conteos antes y después.

### Pasos de Aplicación en Servidor:
1. **Respaldo previo:**
   ```bash
   mysqldump -h <RDS_ENDPOINT> -u <DB_USER> -p --routines --triggers --single-transaction vehiculo_iot > backup_pre_v3.sql
   ```
2. **Verificación previa:**
   ```bash
   mysql -h <RDS_ENDPOINT> -u <DB_USER> -p vehiculo_iot < migrations/001_initial_backup_verification.sql
   ```
3. **Aplicación UP:**
   ```bash
   mysql -h <RDS_ENDPOINT> -u <DB_USER> -p vehiculo_iot < migrations/002_migration_up_v3.sql
   ```
4. **Verificación posterior:**
   Comprobar que el conteo en `vehiculos`, `comandos`, `estados` e `historial` permanezca idéntico al diagnóstico previo.
