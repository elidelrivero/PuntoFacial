const API_URL = 'http://localhost:5000/api';

// ── NAVEGACIÓN DEL MENÚ ──────────────────────────────────────────
const menuBtns = document.querySelectorAll('.menu-btn');
const sections = document.querySelectorAll('.content-section');

menuBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        menuBtns.forEach(b => b.classList.remove('active'));
        sections.forEach(s => s.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.getAttribute('data-target')).classList.add('active');
    });
});

// ── RELOJ EN TIEMPO REAL ─────────────────────────────────────────
function actualizarReloj() {
    document.getElementById('reloj').textContent =
        new Date().toTimeString().split(' ')[0];
}
setInterval(actualizarReloj, 1000);
actualizarReloj();

// ── CARGAR DATOS DESDE MYSQL ─────────────────────────────────────
async function cargarDatosBD() {
    try {
        const res   = await fetch(`${API_URL}/datos-iniciales`);
        const datos = await res.json();

        // ── Directorio de empleados ──────────────────────────────
        const tbodyDir = document.getElementById('tabla-directorio');
        tbodyDir.innerHTML = '';
        datos.directorio.forEach(emp => {
            tbodyDir.innerHTML += `
                <tr>
                    <td><strong class="id-tag">${emp.id}</strong></td>
                    <td>${emp.nombre}</td>
                    <td>${emp.depto}</td>
                    <td>
                        <button class="btn btn-small btn-bio"
                                onclick="iniciarEnrolamientoEmpleado('${emp.id}')">
                            <i class="fa-solid fa-camera-rotate"></i> Enrolar
                        </button>
                    </td>
                    <td>
                        <!-- Baja lógica protegida con contraseña administrativa -->
                        <button class="btn btn-small btn-baja"
                                onclick="abrirModalBaja('${emp.id}', '${emp.nombre}')">
                            <i class="fa-solid fa-user-slash"></i> Baja
                        </button>
                    </td>
                </tr>`;
        });

        // ── Reporte de asistencia del día ────────────────────────
        const tbodyRep = document.getElementById('tabla-reportes');
        tbodyRep.innerHTML = '';
        datos.reporte.forEach(emp => {
            const badgeColor = emp.Estado === 'Retardo' || emp.Estado === 'Sin registro'
                ? 'badge-warning' : 'badge-success';
            tbodyRep.innerHTML += `
                <tr>
                    <td>${emp.id_emp}</td>
                    <td>
                        <strong>${emp.Empleado}</strong><br>
                        <small class="text-muted">${emp.Departamento}</small>
                    </td>
                    <td>${emp.Horario}</td>
                    <td>${emp.Entrada}</td>
                    <td style="color:${emp.Retraso.includes('Sí') ? '#ef4444' : '#10b981'}">${emp.Retraso}</td>
                    <td>${emp.Salida}</td>
                    <td>${emp.Dif_Salida}</td>
                    <td>${emp.Puerta   !== '--' ? `<span class="badge-puerta">${emp.Puerta}</span>`   : '--'}</td>
                    <td>${emp.Sucursal !== '--' ? `<span class="badge-sucursal">${emp.Sucursal}</span>` : '--'}</td>
                    <td><span class="badge ${badgeColor}">${emp.Estado}</span></td>
                </tr>`;
        });

    } catch (err) {
        console.error('Error cargando datos:', err);
    }
}
cargarDatosBD();

// ── FLUJO 1: REGISTRO DE EMPLEADO + REDIRECCIÓN AL MODAL BIOMÉTRICO ──
// Cuando el administrador guarda los datos base del empleado:
//   1. Backend genera el ID de 7 dígitos aleatorio
//   2. Se muestra confirmación con el ID asignado
//   3. Tras 1.5 s → modal biométrico se abre automáticamente para enrolar el rostro
document.getElementById('form-empleado').addEventListener('submit', async function (e) {
    e.preventDefault();
    const nombre = document.getElementById('emp-nombre').value.trim();
    const depto  = document.getElementById('emp-depto').value;
    const msgEl  = document.getElementById('msg-nuevo-empleado');

    try {
        const res  = await fetch(`${API_URL}/empleados`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ nombre, depto }),
        });
        const data = await res.json();

        if (data.success) {
            this.reset();
            cargarDatosBD();

            // Mostrar el ID recién generado antes de abrir la cámara
            msgEl.innerHTML = `
                <i class="fa-solid fa-circle-check"></i>
                Empleado <strong>${nombre}</strong> registrado —
                ID asignado: <strong class="id-display">${data.nuevo_id}</strong>.
                Abriendo registro biométrico...
            `;
            msgEl.style.display = 'flex';

            // Transición automática: ocultar mensaje → abrir modal de enrolamiento
            setTimeout(() => {
                msgEl.style.display = 'none';
                iniciarEnrolamientoEmpleado(data.nuevo_id);  // definida en biometria.js
            }, 1500);

        } else {
            alert(`Error al registrar: ${data.error}`);
        }
    } catch (err) {
        console.error('Error al guardar empleado:', err);
        alert('Error de conexión con el servidor.');
    }
});

// ── MÓDULO 1: BAJA DE EMPLEADO ───────────────────────────────────
let pendingBajaId = null;

function abrirModalBaja(codigoEmpleado, nombre) {
    pendingBajaId = codigoEmpleado;

    document.getElementById('baja-empleado-info').innerHTML = `
        <i class="fa-solid fa-triangle-exclamation" style="font-size:1.4rem; color:#dc2626;"></i>
        <div>
            Estás a punto de dar de baja a
            <strong>${nombre}</strong>
            <span class="id-tag">${codigoEmpleado}</span>.<br>
            <small>Esta acción desactivará su acceso y biometría sin borrar su historial.</small>
        </div>`;

    document.getElementById('input-pwd-baja').value   = '';
    document.getElementById('baja-error').style.display = 'none';
    document.getElementById('modal-baja').style.display = 'flex';
    // Enfocar el campo de contraseña automáticamente
    setTimeout(() => document.getElementById('input-pwd-baja').focus(), 200);
}

async function confirmarBaja() {
    const password = document.getElementById('input-pwd-baja').value;
    const errorEl  = document.getElementById('baja-error');

    if (!password) {
        errorEl.textContent    = 'Ingresa la contraseña administrativa.';
        errorEl.style.display  = 'block';
        return;
    }
    try {
        const res  = await fetch(`${API_URL}/empleados/baja`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ codigo_empleado: pendingBajaId, password }),
        });
        const data = await res.json();

        if (data.success) {
            cerrarModalBaja();
            cargarDatosBD();
            alert(`✅ ${data.mensaje}`);
        } else {
            errorEl.textContent   = data.mensaje;
            errorEl.style.display = 'block';
            document.getElementById('input-pwd-baja').value = '';
            document.getElementById('input-pwd-baja').focus();
        }
    } catch {
        errorEl.textContent   = 'Error de conexión con el servidor.';
        errorEl.style.display = 'block';
    }
}

function cerrarModalBaja() {
    document.getElementById('modal-baja').style.display = 'none';
    pendingBajaId = null;
}

// ── NOVEDADES ────────────────────────────────────────────────────
document.getElementById('form-novedades').addEventListener('submit', async function (e) {
    e.preventDefault();
    try {
        const res  = await fetch(`${API_URL}/novedades`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                empleado:     document.getElementById('nov-empleado').value,
                tipo:         document.getElementById('nov-tipo').value,
                fecha_inicio: document.getElementById('nov-inicio').value,
                fecha_fin:    document.getElementById('nov-fin').value,
            }),
        });
        const data = await res.json();
        alert(data.success ? `✅ ${data.mensaje}` : `❌ ${data.mensaje}`);
        if (data.success) this.reset();
    } catch (err) {
        alert('Error de conexión con el servidor.');
    }
});
