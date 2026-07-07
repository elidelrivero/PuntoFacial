# TimeCheck — Sistema de Asistencia Corporativo

Sistema web de control de asistencia con **reconocimiento facial** en tiempo real.  
Los empleados se identifican con un ID de 7 dígitos y verifican su identidad con la cámara.  
**Nunca se almacenan fotos** — solo un vector numérico de 128 valores matemáticos.

---

## ¿Qué necesito antes de empezar?

Instala los siguientes programas en tu computadora. Haz clic en cada enlace para descargarlos:

| Programa | Para qué sirve | Descarga |
|---|---|---|
| **Python 3.10 o superior** | Ejecuta el servidor de la aplicación | https://www.python.org/downloads/ |
| **MySQL 8.0 o superior** | Guarda los datos (empleados, asistencia, etc.) | https://dev.mysql.com/downloads/installer/ |
| **Git** | Descarga el proyecto desde internet | https://git-scm.com/downloads |
| **Chrome o Firefox** | Accede a la aplicación (necesario para la cámara) | — |

> **Nota sobre MySQL:** Durante la instalación, el programa te pedirá que pongas una contraseña para el usuario `root`. Escribe **`root`** como contraseña (así coincide con la configuración del proyecto). Si ya tienes MySQL instalado con otra contraseña, no hay problema — te explico cómo cambiarlo más adelante.

---

## Instalación paso a paso

### Paso 1 — Descargar el proyecto

Abre una ventana de terminal (en Windows: busca **"CMD"** o **"Símbolo del sistema"** en el menú Inicio) y escribe exactamente lo siguiente:

```bash
git clone https://github.com/AmoxhuaOchoa/Sistema-de-Asistecia--main.git
```

Luego entra a la carpeta del proyecto:

```bash
cd Sistema-de-Asistecia--main
```

> Todos los comandos del resto de esta guía debes ejecutarlos **desde esta carpeta**.

---

### Paso 2 — Instalar las dependencias de Python

Escribe este comando en la terminal (dentro de la carpeta del proyecto):

```bash
pip install -r requirements.txt
```

Esto descarga e instala automáticamente las librerías que necesita la aplicación:
- **Flask** — el servidor web
- **flask-cors** — permite que el navegador se comunique con el servidor
- **PyMySQL** — conecta Python con MySQL
- **NumPy** — procesa los vectores del reconocimiento facial

Espera a que termine. Al final verás un mensaje como `Successfully installed ...`.

> **Si el comando `pip` no funciona**, prueba con `pip3 install -r requirements.txt`

---

### Paso 3 — Configurar la base de datos

Este es el paso más importante. Aquí se crea toda la estructura de la base de datos y se cargan los datos.

#### 3a. Abre MySQL Workbench

MySQL Workbench es el programa visual que viene incluido al instalar MySQL.  
Búscalo en el menú Inicio de Windows y ábrelo.

#### 3b. Conéctate a tu base de datos local

En la pantalla principal verás una caja que dice **"Local instance MySQL80"** (o similar).  
Haz doble clic en ella. Si te pide contraseña, escribe `root`.

#### 3c. Ejecuta el archivo de restauración

Una vez conectado, en el menú superior haz clic en:

```
File → Open SQL Script...
```

Navega hasta la carpeta del proyecto y abre el archivo:

```
Dump20260622 → restore_completo.sql
```

Cuando el archivo se abra en el editor, haz clic en el botón del **rayo (⚡)** que dice **"Execute"** (o presiona `Ctrl + Shift + Enter`).

Verás varios mensajes en verde. Cuando terminen todos, la base de datos estará lista.

> **¿Qué hace este archivo?** Crea la base de datos `sistema_asistencia`, crea las 5 tablas y carga los datos de empleados, asistencia, biometría y departamentos. **Solo se ejecuta una vez.**

#### 3d. Crea tu archivo de configuración `.env`

La configuración de la base de datos y la contraseña administrativa ya no se editan en `app.py` — viven en un archivo `.env` que **cada persona debe crear la primera vez** (no viene incluido al descargar el proyecto, por seguridad).

1. En la carpeta del proyecto, busca el archivo `.env.example` y haz una copia llamada `.env` (sin el `.example`).
2. Abre `.env` con el Bloc de notas. Si tu contraseña de MySQL es `root` (la recomendada en este instructivo), puedes dejarlo tal cual. Si usaste otra contraseña, cámbiala en `DB_PASSWORD`:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=root      # <-- Cambia esto si tu contraseña de MySQL es otra
DB_NAME=sistema_asistencia

ADMIN_PASSWORD=Abd6S
```

3. Guarda el archivo. El archivo `.env` es privado (no se sube al repositorio) — cada persona que instale el proyecto crea el suyo a partir de `.env.example`.

---

### Paso 4 — Iniciar el servidor

En la terminal (dentro de la carpeta del proyecto), escribe:

```bash
python app.py
```

Si todo está bien, verás algo como esto en la terminal:

```
 * Running on http://127.0.0.1:5000
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

**Deja esta ventana de terminal abierta.** Si la cierras, la aplicación se detiene.

> **Si el comando `python` no funciona**, prueba con `python3 app.py`

---

### Paso 5 — Abrir la aplicación

Abre tu navegador (Chrome o Firefox) y escribe en la barra de direcciones:

```
http://localhost:5000
```

Presiona Enter. Deberías ver el panel de control de TimeCheck.

> **Importante:** Siempre accede por `http://localhost:5000`.  
> No abras el archivo `index.html` directamente haciendo doble clic, porque la cámara y el reconocimiento facial **no funcionarán** de esa manera.

---

## Cómo usar el sistema

### Registrar un nuevo empleado

1. En el menú lateral, haz clic en **"Empleados"**
2. Escribe el nombre completo del empleado
3. Selecciona el departamento al que pertenece
4. Haz clic en **"Guardar Empleado"**
5. El sistema genera automáticamente un **ID de 7 dígitos** — anótalo o entrégaselo al empleado
6. La cámara se abre automáticamente para registrar el rostro. El empleado debe mirar directo a la cámara hasta que aparezca el mensaje verde de éxito

### Registrar entrada o salida

1. Ve a **"Registro Asistencia"**
2. El empleado escribe su **ID de 7 dígitos**
3. Selecciona **"Entrada"** o **"Salida"**
4. Elige la **puerta** y la **sucursal** de acceso
5. Haz clic en **"Verificar con Cámara"** y mira directo al lente
6. Si el rostro coincide con el ID, el registro se guarda automáticamente

### Ver reporte del día

1. Ve a **"Reportes Diarios"**
2. Verás la lista de todos los empleados con su hora de entrada, salida, retrasos y estado

### Registrar permiso o incapacidad

1. Ve a **"Permisos e Incapacidades"**
2. Escribe el ID o nombre del empleado
3. Selecciona el tipo (Permiso Personal, Vacaciones, Incapacidad Médica)
4. Elige las fechas de inicio y fin
5. Guarda el registro

### Dar de baja a un empleado

1. Ve a **"Empleados"**
2. En la sección de baja, escribe el ID del empleado
3. Ingresa la contraseña administrativa: `Abd6S`
4. El empleado quedará inactivo (su historial se conserva)

---

## Módulos del sistema

| Módulo | Qué hace |
|---|---|
| **Registro Asistencia** | Marca entrada y salida con verificación facial 1:1 |
| **Empleados** | Registra nuevos empleados y enrola su biometría facial |
| **Permisos e Incapacidades** | Gestiona vacaciones, permisos personales e incapacidades médicas |
| **Reportes Diarios** | Muestra el estado de asistencia de todos los empleados del día actual |

---

## Estructura del proyecto

```
├── app.py                      # Servidor backend (Flask + API REST)
├── index.html                  # Interfaz principal del sistema
├── script.js                   # Lógica de empleados, reportes y navegación
├── biometria.js                # Reconocimiento facial (face-api.js)
├── style.css                   # Estilos visuales del panel
├── requirements.txt            # Librerías Python necesarias
├── .env.example                 # Plantilla de configuración (copiar como .env)
├── MEJORAS.md                   # Registro de mejoras propuestas e implementadas
├── asistencia_db.sql           # Esquema original de la base de datos
├── biometria.sql               # Migración de la tabla biométrica
├── Dump20260622/
│   └── restore_completo.sql   # ✅ ARCHIVO ÚNICO para restaurar todo
└── models/                     # Modelos de IA para reconocimiento facial
    ├── tiny_face_detector_model-*
    ├── face_landmark_68_model-*
    └── face_recognition_model-*
```

---

## Solución de problemas frecuentes

| Error que ves | Qué significa | Cómo solucionarlo |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Faltan las librerías de Python | Ejecuta `pip install -r requirements.txt` |
| `Access denied for user 'root'@'localhost'` | La contraseña de MySQL es incorrecta | Abre `.env` y corrige el valor de `DB_PASSWORD` |
| `KeyError: 'DB_HOST'` (u otra variable) | Falta el archivo `.env` | Copia `.env.example` como `.env` y complétalo |
| `Unknown database 'sistema_asistencia'` | La base de datos no fue creada | Ejecuta `Dump20260622/restore_completo.sql` en MySQL Workbench |
| La cámara no se activa | El navegador bloqueó el acceso | Asegúrate de entrar por `http://localhost:5000`, no por `file://` |
| Los modelos de IA no cargan | Falta la carpeta `models/` | Verifica que la carpeta `models/` exista dentro del proyecto |
| La página no carga en `localhost:5000` | El servidor no está corriendo | Abre la terminal y ejecuta `python app.py` |
| `python` no es reconocido como comando | Python no está en el PATH | Reinstala Python y marca la opción **"Add Python to PATH"** |

---

## Privacidad y seguridad

- El sistema **nunca almacena fotos ni imágenes** de ningún empleado
- Solo se guarda un **vector matemático de 128 números** por persona
- Las imágenes capturadas por la cámara se procesan en el navegador y se descartan inmediatamente
- La contraseña administrativa para dar de baja empleados se define en `.env` (`ADMIN_PASSWORD`) — cámbiala ahí si lo necesitas
