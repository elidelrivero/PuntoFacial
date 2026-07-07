-- ================================================================
-- MIGRACIÓN: SISTEMA BIOMÉTRICO FACIAL
-- POLÍTICA DE PRIVACIDAD: Solo se almacenan vectores matemáticos.
-- NUNCA se guarda ninguna imagen (.jpg, .png, blob, base64).
-- ================================================================
USE sistema_asistencia;

-- Columna de estado en la tabla existente
ALTER TABLE empleados
    ADD COLUMN IF NOT EXISTS bio_enrolado BOOLEAN DEFAULT FALSE
    COMMENT 'TRUE si el empleado tiene biometría registrada';

-- Tabla exclusiva para vectores faciales (sin imágenes)
CREATE TABLE IF NOT EXISTS biometria_facial (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id          INT NOT NULL UNIQUE,

    -- ✅ ÚNICO dato almacenado: el vector numérico de 128 dimensiones
    -- ❌ PROHIBIDO por diseño: imágenes, capturas de pantalla, base64
    face_embedding       JSON NOT NULL
                         COMMENT 'Vector facial Float32[128] - face-api.js faceRecognitionNet. SIN imágenes.',

    fecha_enrolamiento   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion  DATETIME     ON UPDATE CURRENT_TIMESTAMP,
    activo               BOOLEAN      DEFAULT TRUE,

    FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
    INDEX idx_empleado_activo (empleado_id, activo)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Biometría facial — exclusivamente vectores numéricos. Política: cero almacenamiento de imágenes.';
