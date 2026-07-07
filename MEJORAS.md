# Registro de mejoras — TimeCheck

Este documento lleva el control de las mejoras propuestas al sistema, su justificación,
el enfoque técnico y su estado. Cada mejora se implementa **solo después de aprobación
explícita** del propietario del proyecto.

Leyenda de estado: `Pendiente` · `Aprobada` · `Implementada` · `Rechazada`

---

## 1. Credenciales fuera del código fuente

**Estado:** Implementada (2026-07-06)

**Cambios realizados:**
- `app.py`: `db_config` y `ADMIN_PASSWORD` ahora se leen con `os.environ[...]` tras
  `load_dotenv()`, en vez de estar escritos en el código.
- `requirements.txt`: se agregó `python-dotenv==1.2.2`.
- Se creó `.env` (valores reales, ya está en `.gitignore`, no se sube al repo) y
  `.env.example` (plantilla sin secretos, sí se sube al repo).
- README: se documentó el nuevo paso 3d para crear `.env` a partir de
  `.env.example`, y se corrigieron las referencias a la contraseña en la sección
  de solución de problemas y en privacidad/seguridad.

**Verificado:** `app.py` compila sin errores; se confirmó que `python-dotenv` lee
correctamente `DB_HOST`, `DB_USER` y `ADMIN_PASSWORD` desde `.env`.

**Nota:** si faltara alguna variable en `.env`, la app ahora falla al iniciar con
un `KeyError` claro (en vez de arrancar con un valor por defecto silencioso) —
comportamiento intencional para detectar configuración incompleta.

**Problema actual:** en [app.py](app.py) la contraseña de MySQL (`db_config`) y la
contraseña administrativa de baja de empleados (`PASSWORD_ADMIN = 'Abd6S'`) están
escritas directamente en el código fuente.

**Por qué importa:** cualquiera con acceso al repositorio (o a un `git clone` del
proyecto) ve las credenciales reales de la base de datos y la contraseña de
administrador. Si el repo se sube a GitHub (como ya está, según el README), quedan
públicas.

**Propuesta:**
- Mover `db_config` y `PASSWORD_ADMIN` a variables de entorno mediante un archivo
  `.env` (ya está en `.gitignore`, así que no se subiría al repo).
- Añadir `python-dotenv` a `requirements.txt`.
- Crear un `.env.example` documentado para que cada quien configure el suyo.
- Actualizar el README con el nuevo paso de configuración.

**Riesgo de la migración:** bajo. No cambia comportamiento, solo el origen del dato.

---

## 2. Autenticación para acceder al panel

**Estado:** Implementada (2026-07-06) — mecanismo elegido: **admin único**

**Problema actual:** cualquier persona que conozca la URL `http://localhost:5000`
(o la IP si el servidor se expone en red) tiene acceso completo al panel: puede ver
empleados, marcar asistencia, dar de baja personal (con la contraseña) y ver reportes.
No hay ningún login.

**Por qué importa:** es un sistema de RR.HH. con datos personales y biométricos;
sin autenticación, no hay control de quién hace qué.

**Cambios realizados:**
- `.env` / `.env.example`: nuevas variables `LOGIN_USER`, `LOGIN_PASSWORD` y
  `SECRET_KEY` (esta última firma la cookie de sesión; se generó una aleatoria
  de 32 bytes con `secrets.token_hex(32)` para el `.env` local).
- `app.py`:
  - `app.secret_key = os.environ['SECRET_KEY']` y sesión nativa de Flask
    (sin dependencias extra tipo `flask-login`, suficiente para un solo rol).
  - `POST /api/login` — valida usuario/contraseña contra `.env` y marca
    `session['autenticado'] = True`.
  - `POST /api/logout` — limpia la sesión.
  - `GET /api/session-check` — usado por el frontend al cargar la página.
  - Decorador `login_required` aplicado a los 8 endpoints existentes de la
    API (datos-iniciales, empleados, asistencia, novedades, biometría
    enrolar/autenticar/verificar, baja). Sin sesión, responden `401`.
- `index.html` / `script.js`:
  - El panel (`#dashboard-main`) permanece oculto hasta confirmar sesión vía
    `/api/session-check`.
  - Nuevo overlay de login (reutiliza los estilos `.modal-bio-overlay` /
    `.modal-bio-panel` ya existentes) que bloquea el acceso hasta iniciar sesión.
  - Botón "Cerrar sesión" en la cabecera del panel.
- La contraseña administrativa (`ADMIN_PASSWORD`) para dar de baja empleados
  se mantiene sin cambios, como segunda confirmación sobre esa acción específica.

**Verificado en navegador (Chrome vía preview tools):**
- Login con credenciales incorrectas → mensaje de error, panel sigue oculto.
- Login con credenciales correctas → panel visible, datos reales cargados
  (directorio de empleados desde MySQL).
- Botón "Cerrar sesión" → vuelve a la pantalla de login.
- `curl` directo a `/api/datos-iniciales` sin cookie de sesión → `401`,
  confirmando que la protección es real a nivel de API y no solo un overlay
  visual en el frontend.
- Sin errores en consola del navegador durante todo el flujo.

**Limitación conocida (fuera de alcance de esta mejora):** no se implementó
protección CSRF ni HTTPS. Razonable para uso local/universitario; recomendado
revisar si el sistema llegara a exponerse en una red compartida o internet.

**Riesgo de la migración:** medio, ya implementado y probado.

---

## 3. Pool de conexiones a la base de datos

**Estado:** Implementada (2026-07-06)

**Problema actual:** cada endpoint abre una conexión nueva a MySQL
(`get_db_connection()`) y la cierra al final. Bajo carga concurrente esto es
ineficiente y puede agotar conexiones de MySQL.

**Por qué importa:** con varios empleados marcando asistencia a la vez (ej. hora
pico de entrada), abrir/cerrar conexión por request agrega latencia y no escala.

**Cambios realizados:**
- Se agregó `DBUtils==3.1.2` a `requirements.txt`.
- `app.py`: se creó `connection_pool = PooledDB(creator=pymysql, maxconnections=5, **db_config)`
  a nivel de módulo (se inicializa una sola vez al arrancar la app).
- `get_db_connection()` ahora devuelve `connection_pool.connection()` en vez de
  `pymysql.connect(**db_config)`. El resto del código no cambió: cada endpoint
  sigue llamando `get_db_connection()` y `conn.close()` igual que antes —
  `PooledDB` intercepta el `close()` y devuelve la conexión al pool en vez de
  destruirla.

**Verificado:**
- Script aislado que pide 3 conexiones seguidas del pool y ejecuta consultas
  reales contra `sistema_asistencia` — funcionó correctamente.
- Prueba end-to-end: se levantó `app.py` completo y se llamó
  `GET /api/datos-iniciales`, devolviendo `200 OK` con los datos reales de la
  base de datos.

**Riesgo de la migración:** bajo. Cambio aislado y fácil de revertir.

---

## 4. Desactivar `debug=True` fuera de desarrollo

**Estado:** Implementada (2026-07-06)

**Problema actual:** `app.run(debug=True, port=5000)` deja activado el modo debug
de Flask, que expone un **debugger interactivo con ejecución remota de código** si
ocurre un error no manejado y el servidor es accesible desde la red.

**Por qué importa:** si este servidor llega a exponerse fuera de `localhost` (ej. en
la red de la oficina), el modo debug es una puerta de ejecución de código arbitraria.

**Cambios realizados:**
- `app.py`: `app.run()` ahora lee `FLASK_DEBUG` de `.env` (`os.environ.get('FLASK_DEBUG', 'False')`)
  y solo activa `debug=True` si el valor es exactamente `"true"` (sin distinguir
  mayúsculas). Si la variable falta, el valor por defecto es `False`.
- `.env` (local): `FLASK_DEBUG=True`, para no interrumpir el flujo de desarrollo actual.
- `.env.example` (plantilla pública): `FLASK_DEBUG=False`, para que cualquiera
  que clone el repo arranque seguro por defecto y deba activarlo a propósito.
- README: documentado el nuevo valor en el paso 3d, con advertencia de para
  qué sirve y por qué no debe activarse fuera de desarrollo.

**Verificado:** `app.py` compila; se confirmó que `FLASK_DEBUG=True` en `.env`
se interpreta correctamente como `True` al cargar con `python-dotenv`.

**Riesgo de la migración:** muy bajo.

---

## 5. Tests automatizados

**Estado:** Implementada (2026-07-07) — estrategia elegida: **base de datos de prueba real**

**Problema actual:** no existe ninguna prueba automatizada. Cualquier cambio (como
las mejoras 1–4) se valida solo probando manualmente en el navegador.

**Por qué importa:** sin tests, cada mejora futura arriesga romper algo sin que nos
demos cuenta hasta probarlo a mano.

**Cambios realizados:**
- `requirements-dev.txt`: incluye `requirements.txt` + `pytest==8.3.4` (dependencia
  solo de desarrollo, no se instala en producción).
- `pytest.ini`: configura `testpaths = tests`.
- `tests/conftest.py`:
  - Fija `DB_NAME=sistema_asistencia_test` **antes** de importar `app.py`, para que
    el pool de conexiones se inicialice apuntando a la base de prueba, nunca a la real.
  - Fixture de sesión que crea `sistema_asistencia_test` con el mismo esquema que
    producción (5 tablas) y siembra los 4 departamentos.
  - Fixture que limpia (`TRUNCATE`) las tablas dependientes antes de cada prueba.
  - Fixtures `client` (cliente de pruebas de Flask) y `auth_client` (mismo cliente,
    ya autenticado vía `/api/login`) para no repetir el login en cada test.
- `tests/test_auth.py` — login correcto/incorrecto, session-check, logout, y que
  los 8 endpoints de la API respondan `401` sin sesión (protege la Mejora 4).
- `tests/test_empleados.py` — alta genera ID de 7 dígitos, baja con contraseña
  correcta/incorrecta, baja de empleado inexistente.
- `tests/test_asistencia.py` — entrada/salida exitosas, salida sin entrada previa
  (error esperado), entrada duplicada el mismo día.
- `tests/test_novedades.py` — registro por ID, por nombre, y empleado inexistente.
- `tests/test_biometria.py` — vector inválido (no 128 dimensiones), verificación 1:1
  con el mismo vector (coincide, distancia 0), con vector distinto (no coincide),
  e ID sin biometría registrada.
- README: nueva sección "Cómo correr las pruebas automatizadas".
- `.gitignore`: se agregó `.pytest_cache/`.

**Verificado:** `pytest` ejecutado contra MySQL real — **29 passed**. Se confirmó
además que la base de datos real (`sistema_asistencia`, con los 12 empleados
reales) permaneció intacta durante toda la corrida; las pruebas solo leen y
escriben en `sistema_asistencia_test`.

**Riesgo de la migración:** bajo, ya implementado y probado. Código nuevo que no
modifica los endpoints existentes.

---

## 0. Repositorio de control de versiones

**Estado:** Implementada (2026-07-06)

**Qué se hizo:** el proyecto no tenía control de versiones propio (venía como
descarga de un repo de terceros). Se creó un repositorio nuevo, público, en la
cuenta de GitHub del propietario:

- **Repositorio:** https://github.com/elidelrivero/PuntoFacial
- **Visibilidad:** público (decisión del propietario, para exponerlo en su perfil)

**Paso previo obligatorio — sanitización de datos:** antes de publicar, se
detectó que `Dump20260622/restore_completo.sql` contenía **datos reales**:
nombres de personas identificables y sus **vectores biométricos faciales
reales** (columna `face_embedding`). Esto es información sensible que no debe
publicarse.

Se resolvió así:
- Se guardó una copia del dump original con los datos reales en
  `Dump20260622/restore_completo.local.sql` — **excluido del repositorio**
  vía `.gitignore`, permanece solo en esta máquina.
- El archivo `Dump20260622/restore_completo.sql` (el que sí se sube) fue
  sanitizado: los nombres se reemplazaron por `Empleado Demo 1..12` y los
  vectores biométricos reales por vectores sintéticos generados
  aleatoriamente (mismo formato, 128 dimensiones, sin relación con rostros
  reales).
- Se verificó con `grep` que ningún nombre real quedara en el archivo antes
  del commit.

A partir de ahora, cada mejora aprobada se documentará aquí y se subirá como
un commit independiente a este repositorio.

---

## Orden de implementación

1. ✅ Credenciales fuera del código
2. ✅ Desactivar debug en producción
3. ✅ Pool de conexiones
4. ✅ Autenticación del panel
5. ✅ Tests automatizados

Las 5 mejoras propuestas están implementadas, probadas y publicadas en
[github.com/elidelrivero/PuntoFacial](https://github.com/elidelrivero/PuntoFacial).
