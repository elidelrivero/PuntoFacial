from flask import Flask, request, jsonify, send_from_directory, session
from dotenv import load_dotenv
from dbutils.pooled_db import PooledDB
from functools import wraps
from time import time
import hmac
import pymysql
import pymysql.cursors
from datetime import datetime
import json
import numpy as np
import os
import random

load_dotenv()

# Flask sirve el frontend completo desde la misma carpeta del proyecto.
# Accede por http://localhost:5000 en lugar de abrir index.html como archivo.
# Frontend y API comparten el mismo origen — no se necesita CORS entre sitios,
# y habilitarlo junto con cookies de sesión sería un riesgo (ver MEJORAS.md #6).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
app.secret_key = os.environ['SECRET_KEY']
# Defensa adicional: evita que la cookie de sesión se envíe en peticiones
# cross-site iniciadas por otros sitios (fetch/formularios).
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

# Configuración de la base de datos (ver .env.example)
db_config = {
    'host': os.environ['DB_HOST'],
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PASSWORD'],
    'database': os.environ['DB_NAME'],
    'cursorclass': pymysql.cursors.DictCursor
}

ADMIN_PASSWORD = os.environ['ADMIN_PASSWORD']
LOGIN_USER     = os.environ['LOGIN_USER']
LOGIN_PASSWORD = os.environ['LOGIN_PASSWORD']

# ================================================================
# AUTENTICACIÓN DEL PANEL
# Sesión única de administrador (cookie firmada con SECRET_KEY).
# Protege todos los endpoints de la API salvo login/session-check.
# ================================================================

def login_required(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if not session.get('autenticado'):
            return jsonify({'success': False, 'mensaje': 'Sesión no iniciada.'}), 401
        return f(*args, **kwargs)
    return decorada

# Límite simple de intentos fallidos de login (en memoria — un solo admin,
# un solo proceso). No sustituye un sistema de cuentas real, pero evita
# fuerza bruta trivial contra la contraseña.
MAX_INTENTOS_LOGIN    = 5
VENTANA_INTENTOS_SEG  = 300
_intentos_fallidos_login = []

@app.route('/api/login', methods=['POST'])
def login():
    ahora = time()
    _intentos_fallidos_login[:] = [t for t in _intentos_fallidos_login if ahora - t < VENTANA_INTENTOS_SEG]
    if len(_intentos_fallidos_login) >= MAX_INTENTOS_LOGIN:
        return jsonify({'success': False, 'mensaje': 'Demasiados intentos fallidos. Intenta de nuevo en unos minutos.'}), 429

    datos = request.json or {}
    usuario_ok  = hmac.compare_digest(str(datos.get('usuario', '')), LOGIN_USER)
    password_ok = hmac.compare_digest(str(datos.get('password', '')), LOGIN_PASSWORD)

    if usuario_ok and password_ok:
        _intentos_fallidos_login.clear()
        session['autenticado'] = True
        return jsonify({'success': True})

    _intentos_fallidos_login.append(ahora)
    return jsonify({'success': False, 'mensaje': 'Usuario o contraseña incorrectos.'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('autenticado', None)
    return jsonify({'success': True})

@app.route('/api/session-check', methods=['GET'])
def session_check():
    return jsonify({'autenticado': bool(session.get('autenticado'))})

# Pool de conexiones: reutiliza hasta 5 conexiones en vez de abrir una nueva
# por cada request. get_db_connection() y conn.close() se usan igual en todo
# el código; PooledDB intercepta el close() y devuelve la conexión al pool.
connection_pool = PooledDB(
    creator=pymysql,
    maxconnections=5,
    **db_config
)

def get_db_connection():
    return connection_pool.connection()

# --- ENDPOINT 1: Obtener el reporte de hoy y el directorio ---
@app.route('/api/datos-iniciales', methods=['GET'])
@login_required
def obtener_datos():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.codigo_empleado as id, e.nombre_completo as nombre, d.nombre as depto
        FROM empleados e JOIN departamentos d ON e.departamento_id = d.id
        WHERE e.activo = TRUE OR e.activo IS NULL
    """)
    directorio = cursor.fetchall()

    cursor.execute("""
        SELECT 
            e.codigo_empleado AS id_emp,
            e.nombre_completo AS Empleado,
            d.nombre AS Departamento,
            CONCAT(TIME_FORMAT(d.hora_entrada, '%H:%i'), ' a ', TIME_FORMAT(d.hora_salida, '%H:%i')) AS Horario,
            IFNULL(TIME_FORMAT(a.hora_entrada, '%H:%i:%s'), '--:--:--') AS Entrada,
            CASE 
                WHEN a.minutos_retraso > 0 THEN CONCAT('Sí (+', a.minutos_retraso, ' min)')
                WHEN a.hora_entrada IS NOT NULL THEN 'No'
                ELSE '--'
            END AS Retraso,
            IFNULL(TIME_FORMAT(a.hora_salida, '%H:%i:%s'), '--:--:--') AS Salida,
            CASE 
                WHEN a.diferencia_salida > 0 THEN CONCAT('+', a.diferencia_salida, ' min (Tarde)')
                WHEN a.diferencia_salida < 0 THEN CONCAT(a.diferencia_salida, ' min (Antes)')
                WHEN a.hora_salida IS NOT NULL THEN 'Exacto'
                ELSE '--'
            END AS Dif_Salida,
            IFNULL(a.estado, 'Sin registro') AS Estado,
            IFNULL(a.puerta,   '--') AS Puerta,
            IFNULL(a.sucursal, '--') AS Sucursal
        FROM empleados e
        JOIN departamentos d ON e.departamento_id = d.id
        LEFT JOIN asistencia a ON e.id = a.empleado_id AND a.fecha = CURDATE()
        WHERE e.activo = TRUE OR e.activo IS NULL;
    """)
    reporte_hoy = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return jsonify({'directorio': directorio, 'reporte': reporte_hoy})

# --- ENDPOINT 2: Registrar un nuevo empleado ---
@app.route('/api/empleados', methods=['POST'])
@login_required
def registrar_empleado():
    datos  = request.json or {}
    nombre = (datos.get('nombre') or '').strip()
    depto  = datos.get('depto')

    deptos = {"Recursos Humanos": 1, "Tecnología": 2, "Ventas": 3, "Operaciones": 4}
    if not nombre or depto not in deptos:
        return jsonify({'success': False, 'error': f"Nombre requerido y depto debe ser uno de: {', '.join(deptos)}."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Generar ID único aleatorio de exactamente 7 dígitos (1000000-9999999)
        while True:
            nuevo_codigo = str(random.randint(1000000, 9999999))
            cursor.execute("SELECT id FROM empleados WHERE codigo_empleado = %s", (nuevo_codigo,))
            if not cursor.fetchone():
                break  # ID confirmado como único

        depto_id = deptos[depto]

        cursor.execute(
            "INSERT INTO empleados (codigo_empleado, nombre_completo, departamento_id) VALUES (%s, %s, %s)",
            (nuevo_codigo, nombre, depto_id)
        )
        conn.commit()
        return jsonify({'success': True, 'nuevo_id': nuevo_codigo, 'nombre': nombre}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# --- ENDPOINT 3: Registrar Entrada / Salida ---
@app.route('/api/asistencia', methods=['POST'])
@login_required
def registrar_asistencia():
    datos      = request.json or {}
    codigo_emp = datos.get('id')
    tipo       = datos.get('tipo')

    if not codigo_emp or tipo not in ('Entrada', 'Salida'):
        return jsonify({'success': False, 'mensaje': "Faltan campos requeridos: 'id' y 'tipo' ('Entrada' o 'Salida')."}), 400

    # Metadatos de acceso (solo para Entrada; Salida los ignora)
    puerta   = datos.get('puerta',   None)
    sucursal = datos.get('sucursal', None)

    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT e.id, e.nombre_completo, d.hora_entrada, d.hora_salida
            FROM empleados e JOIN departamentos d ON e.departamento_id = d.id
            WHERE e.codigo_empleado = %s AND (e.activo = TRUE OR e.activo IS NULL)
        """, (codigo_emp,))
        empleado = cursor.fetchone()

        if not empleado:
            return jsonify({'success': False, 'mensaje': 'ID no encontrado o empleado dado de baja'}), 404

        emp_id          = empleado['id']
        ahora           = datetime.now()
        hora_actual_str = ahora.strftime('%H:%M:%S')
        minutos_actuales = ahora.hour * 60 + ahora.minute
        min_entrada_depto = empleado['hora_entrada'].seconds // 60
        min_salida_depto  = empleado['hora_salida'].seconds // 60

        if tipo == 'Entrada':
            retraso = max(0, minutos_actuales - min_entrada_depto)
            estado  = 'Retardo' if retraso > 0 else 'Presente'
            # Guardar junto con puerta y sucursal seleccionadas por el empleado
            cursor.execute("""
                INSERT INTO asistencia
                    (empleado_id, fecha, hora_entrada, minutos_retraso, estado, puerta, sucursal)
                VALUES (%s, CURDATE(), %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    hora_entrada    = VALUES(hora_entrada),
                    minutos_retraso = VALUES(minutos_retraso),
                    estado          = VALUES(estado),
                    puerta          = VALUES(puerta),
                    sucursal        = VALUES(sucursal)
            """, (emp_id, hora_actual_str, retraso, estado, puerta, sucursal))

        elif tipo == 'Salida':
            dif_salida = minutos_actuales - min_salida_depto
            cursor.execute("""
                UPDATE asistencia
                SET hora_salida = %s, diferencia_salida = %s, estado = 'Jornada Finalizada'
                WHERE empleado_id = %s AND fecha = CURDATE()
            """, (hora_actual_str, dif_salida, emp_id))

            if cursor.rowcount == 0:
                return jsonify({'success': False, 'mensaje': 'Debe registrar entrada primero.'}), 400

        conn.commit()
        return jsonify({'success': True, 'nombre': empleado['nombre_completo'], 'hora': hora_actual_str})
        
    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'mensaje': 'Error en el servidor'}), 500
    finally:
        cursor.close()
        conn.close()

# --- ENDPOINT 4: Registrar Novedad ---
@app.route('/api/novedades', methods=['POST'])
@login_required
def registrar_novedad():
    datos = request.json or {}
    empleado_input = datos.get('empleado')  # Puede ser el ID (003) o el Nombre (Samuel)
    tipo           = datos.get('tipo')
    fecha_inicio   = datos.get('fecha_inicio')
    fecha_fin      = datos.get('fecha_fin')

    if not all([empleado_input, tipo, fecha_inicio, fecha_fin]):
        return jsonify({'success': False, 'mensaje': 'Faltan campos requeridos: empleado, tipo, fecha_inicio y fecha_fin.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Buscar primero coincidencia exacta (código o nombre completo)
        cursor.execute("""
            SELECT id, nombre_completo FROM empleados
            WHERE codigo_empleado = %s OR nombre_completo = %s
        """, (empleado_input, empleado_input))
        empleado = cursor.fetchone()

        # 2. Si no hubo coincidencia exacta, buscar por nombre parcial —
        #    pero solo se acepta si es INEQUÍVOCA (un único resultado).
        #    Evita asignar la novedad al empleado equivocado cuando varios
        #    nombres comparten una misma subcadena (ej. "Ana" / "Mariana").
        if not empleado:
            cursor.execute("""
                SELECT id, nombre_completo FROM empleados WHERE nombre_completo LIKE %s
            """, (f"%{empleado_input}%",))
            candidatos = cursor.fetchall()

            if len(candidatos) == 1:
                empleado = candidatos[0]
            elif len(candidatos) > 1:
                nombres = ', '.join(c['nombre_completo'] for c in candidatos)
                return jsonify({
                    'success': False,
                    'mensaje': f'"{empleado_input}" coincide con varios empleados ({nombres}). Especifica con el ID.'
                }), 400

        if not empleado:
            return jsonify({'success': False, 'mensaje': 'Empleado no encontrado. Verifique el ID o Nombre.'}), 404

        emp_id = empleado['id']

        # 2. Insertar en la tabla novedades
        cursor.execute("""
            INSERT INTO novedades (empleado_id, tipo_novedad, fecha_inicio, fecha_fin) 
            VALUES (%s, %s, %s, %s)
        """, (emp_id, tipo, fecha_inicio, fecha_fin))

        conn.commit()
        return jsonify({
            'success': True, 
            'mensaje': f"Novedad registrada exitosamente para {empleado['nombre_completo']}"
        })

    except Exception as e:
        print("Error al registrar novedad:", e)
        return jsonify({'success': False, 'mensaje': 'Error en la base de datos.'}), 500
    finally:
        cursor.close()
        conn.close()

# ================================================================
# ENDPOINTS BIOMÉTRICOS
# Política: el navegador extrae el embedding y DESCARTA la imagen.
# Solo el vector numérico (128 floats) viaja y se almacena aquí.
# ================================================================

@app.route('/api/biometria/enrolar', methods=['POST'])
@login_required
def enrolar_biometria():
    datos = request.json or {}
    codigo_empleado = datos.get('codigo_empleado')

    # ✅ PRIVACIDAD: Se recibe únicamente el vector numérico.
    # La imagen fue procesada y DESCARTADA en el navegador del cliente.
    embedding = datos.get('face_embedding')  # Lista de 128 floats

    if not embedding or len(embedding) != 128:
        return jsonify({'success': False, 'mensaje': 'Vector facial inválido (se esperan 128 dimensiones)'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, nombre_completo FROM empleados WHERE codigo_empleado = %s",
            (codigo_empleado,)
        )
        emp = cursor.fetchone()
        if not emp:
            return jsonify({'success': False, 'mensaje': 'Empleado no encontrado'}), 404

        # ✅ ALMACENAMIENTO: Solo el JSON del vector — nunca un archivo de imagen
        cursor.execute("""
            INSERT INTO biometria_facial (empleado_id, face_embedding, activo)
            VALUES (%s, %s, TRUE)
            ON DUPLICATE KEY UPDATE
                face_embedding      = VALUES(face_embedding),
                fecha_actualizacion = NOW(),
                activo              = TRUE
        """, (emp['id'], json.dumps(embedding)))

        cursor.execute(
            "UPDATE empleados SET bio_enrolado = TRUE WHERE id = %s",
            (emp['id'],)
        )
        conn.commit()
        return jsonify({'success': True, 'mensaje': f"Biometría de {emp['nombre_completo']} registrada correctamente"})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'mensaje': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# --- ENDPOINT: Baja de Empleado (requiere contraseña administrativa) ---
@app.route('/api/empleados/baja', methods=['POST'])
@login_required
def dar_baja_empleado():
    datos           = request.json or {}
    codigo_empleado = datos.get('codigo_empleado')
    password        = datos.get('password', '')

    if not hmac.compare_digest(str(password), ADMIN_PASSWORD):
        return jsonify({'success': False, 'mensaje': 'Contraseña incorrecta. Acción denegada.'}), 403

    conn   = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, nombre_completo FROM empleados WHERE codigo_empleado = %s AND activo = TRUE",
            (codigo_empleado,)
        )
        emp = cursor.fetchone()
        if not emp:
            return jsonify({'success': False, 'mensaje': 'Empleado no encontrado o ya dado de baja'}), 404

        # Baja lógica: desactiva empleado y su biometría sin borrar historial
        cursor.execute("UPDATE empleados       SET activo = FALSE WHERE id = %s", (emp['id'],))
        cursor.execute("UPDATE biometria_facial SET activo = FALSE WHERE empleado_id = %s", (emp['id'],))
        conn.commit()
        return jsonify({'success': True, 'mensaje': f"{emp['nombre_completo']} dado de baja correctamente."})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'mensaje': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/biometria/verificar', methods=['POST'])
@login_required
def verificar_biometria():
    """
    Verificación 1:1 estricta.
    Recibe un ID de 7 dígitos + el vector del rostro capturado en vivo.
    Busca ÚNICAMENTE el vector del empleado con ese ID específico y compara.
    Si el ID no existe o el rostro no coincide → acceso denegado.
    """
    datos = request.json or {}
    codigo_empleado = datos.get('codigo_empleado')

    # ✅ PRIVACIDAD: Solo se recibe el vector del frame — NUNCA la imagen
    embedding_nuevo = np.array(datos.get('face_embedding'), dtype=np.float64)

    # distancia < 0.45 ≈ ≥90 % de confianza (calibrado para face-api.js)
    UMBRAL_DISTANCIA = 0.45

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1:1 → traemos SOLO el vector del empleado cuyo ID fue ingresado
        cursor.execute("""
            SELECT b.face_embedding, e.nombre_completo
            FROM biometria_facial b
            JOIN empleados e ON b.empleado_id = e.id
            WHERE e.codigo_empleado = %s AND b.activo = TRUE
        """, (codigo_empleado,))
        registro = cursor.fetchone()

        if not registro:
            return jsonify({
                'verificado': False,
                'mensaje': f'El ID {codigo_empleado} no tiene biometría registrada.'
            }), 200

        # ✅ Comparación matemática entre los dos vectores (solo estos dos, 1:1)
        embedding_db = np.array(json.loads(registro['face_embedding']), dtype=np.float64)
        distancia    = float(np.linalg.norm(embedding_nuevo - embedding_db))

        if distancia <= UMBRAL_DISTANCIA:
            confianza = round(max(0.0, (1.0 - distancia / 1.5)) * 100, 1)
            return jsonify({
                'verificado': True,
                'nombre':     registro['nombre_completo'],
                'confianza':  confianza,
                'distancia':  round(distancia, 4)
            })
        else:
            return jsonify({
                'verificado': False,
                'mensaje':    'El rostro no coincide con el ID ingresado. Acceso denegado.'
            })

    except Exception as e:
        print("Error en verificación 1:1:", e)
        return jsonify({'verificado': False, 'mensaje': 'Error interno del servidor'}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    # Por defecto False: el debugger interactivo de Flask permite ejecución
    # remota de código si queda activo fuera de una máquina de desarrollo.
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, port=5000)