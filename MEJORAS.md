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

**Estado:** Pendiente

**Problema actual:** cualquier persona que conozca la URL `http://localhost:5000`
(o la IP si el servidor se expone en red) tiene acceso completo al panel: puede ver
empleados, marcar asistencia, dar de baja personal (con la contraseña) y ver reportes.
No hay ningún login.

**Por qué importa:** es un sistema de RR.HH. con datos personales y biométricos;
sin autenticación, no hay control de quién hace qué.

**Propuesta:**
- Agregar un login simple (usuario/contraseña de administrador) con sesión de Flask
  (`flask-login` o sesión nativa firmada con `secret_key`).
- Proteger las rutas de la API con un decorador `@login_required`.
- Pantalla de login antes de mostrar el panel.

**Riesgo de la migración:** medio. Es la mejora más grande — cambia el flujo de
acceso a la app. Requiere decidir contigo el mecanismo (¿un solo usuario admin fijo?
¿tabla de usuarios?) antes de tocar código.

---

## 3. Pool de conexiones a la base de datos

**Estado:** Pendiente

**Problema actual:** cada endpoint abre una conexión nueva a MySQL
(`get_db_connection()`) y la cierra al final. Bajo carga concurrente esto es
ineficiente y puede agotar conexiones de MySQL.

**Por qué importa:** con varios empleados marcando asistencia a la vez (ej. hora
pico de entrada), abrir/cerrar conexión por request agrega latencia y no escala.

**Propuesta:**
- Usar `DBUtils` (`PooledDB`) sobre PyMySQL para mantener un pool de conexiones
  reutilizables en vez de abrir una nueva cada vez.
- Cambio interno en `get_db_connection()`; el resto del código no cambia.

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

**Estado:** Pendiente

**Problema actual:** no existe ninguna prueba automatizada. Cualquier cambio (como
las mejoras 1–4) se valida solo probando manualmente en el navegador.

**Por qué importa:** sin tests, cada mejora futura arriesga romper algo sin que nos
demos cuenta hasta probarlo a mano.

**Propuesta:**
- Añadir `pytest` + `pytest-mock` (o una base de datos SQLite/MySQL de prueba) y
  crear pruebas para los endpoints críticos: registrar empleado, registrar
  asistencia (entrada/salida), verificación biométrica 1:1, baja de empleado.

**Riesgo de la migración:** bajo, es código nuevo que no toca el existente. Depende
de que decidamos la estrategia de base de datos de prueba.

---

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

## Orden sugerido de implementación

1. Credenciales fuera del código (rápido, bajo riesgo, habilita el resto)
2. Desactivar debug en producción (rápido, bajo riesgo)
3. Pool de conexiones (aislado, bajo riesgo)
4. Autenticación del panel (mayor alcance, requiere decisiones contigo)
5. Tests automatizados (se benefician de que 1-4 ya estén hechos)
