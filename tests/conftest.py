import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Las pruebas usan una base de datos separada — nunca la real. Se fija ANTES
# de importar app.py para que el pool de conexiones se inicialice apuntando
# directamente a sistema_asistencia_test.
os.environ['DB_NAME'] = 'sistema_asistencia_test'

import pytest
import pymysql
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / '.env')  # completa DB_HOST/DB_USER/... (no pisa DB_NAME)

from app import app as flask_app, db_config  # noqa: E402 (import intencional tras fijar DB_NAME)

SCHEMA_SQL = """
CREATE DATABASE IF NOT EXISTS sistema_asistencia_test;
USE sistema_asistencia_test;

DROP TABLE IF EXISTS biometria_facial;
DROP TABLE IF EXISTS novedades;
DROP TABLE IF EXISTS asistencia;
DROP TABLE IF EXISTS empleados;
DROP TABLE IF EXISTS departamentos;

CREATE TABLE departamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    hora_entrada TIME NOT NULL,
    hora_salida TIME NOT NULL
);

CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_empleado VARCHAR(10) UNIQUE NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    departamento_id INT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bio_enrolado BOOLEAN DEFAULT FALSE,
    activo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
);

CREATE TABLE asistencia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT NOT NULL,
    fecha DATE NOT NULL,
    hora_entrada TIME NULL,
    hora_salida TIME NULL,
    minutos_retraso INT DEFAULT 0,
    diferencia_salida INT DEFAULT 0,
    estado VARCHAR(50) DEFAULT 'Sin registro',
    puerta VARCHAR(60) DEFAULT NULL,
    sucursal VARCHAR(60) DEFAULT NULL,
    FOREIGN KEY (empleado_id) REFERENCES empleados(id),
    UNIQUE(empleado_id, fecha)
);

CREATE TABLE novedades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT NOT NULL,
    tipo_novedad ENUM('Permiso Personal', 'Vacaciones', 'Incapacidad Médica') NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    notas TEXT,
    estado ENUM('Pendiente', 'Aprobado', 'Rechazado') DEFAULT 'Aprobado',
    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
);

CREATE TABLE biometria_facial (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT NOT NULL UNIQUE,
    face_embedding JSON NOT NULL,
    fecha_enrolamiento DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME ON UPDATE CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
);

INSERT INTO departamentos (nombre, hora_entrada, hora_salida) VALUES
    ('Recursos Humanos', '08:00:00', '17:00:00'),
    ('Tecnología', '09:00:00', '18:00:00'),
    ('Ventas', '10:00:00', '19:00:00'),
    ('Operaciones', '07:00:00', '16:00:00');
"""


def _conexion_sin_bd():
    cfg = dict(db_config)
    cfg.pop('database', None)
    return pymysql.connect(**cfg)


@pytest.fixture(scope='session', autouse=True)
def setup_test_database():
    """Crea sistema_asistencia_test con el esquema completo, una vez por sesión de pruebas."""
    conn = _conexion_sin_bd()
    try:
        with conn.cursor() as cur:
            for statement in SCHEMA_SQL.strip().split(';'):
                statement = statement.strip()
                if statement:
                    cur.execute(statement)
        conn.commit()
    finally:
        conn.close()
    yield


@pytest.fixture(autouse=True)
def limpiar_datos():
    """Antes de cada prueba, vacía las tablas dependientes (departamentos se conserva)."""
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for tabla in ('biometria_facial', 'novedades', 'asistencia', 'empleados'):
                cur.execute(f"TRUNCATE TABLE {tabla}")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
    finally:
        conn.close()
    yield


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture
def auth_client(client):
    """Cliente de pruebas con sesión de administrador ya iniciada."""
    res = client.post('/api/login', json={
        'usuario':  os.environ['LOGIN_USER'],
        'password': os.environ['LOGIN_PASSWORD'],
    })
    assert res.status_code == 200
    return client
