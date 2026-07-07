// ================================================================
// SISTEMA BIOMÉTRICO v2 — biometria.js
//
// FLUJO 1 (Enrolamiento):
//   script.js guarda el empleado → backend devuelve ID 7 dígitos
//   → script.js llama iniciarEnrolamientoEmpleado(id)
//   → abrirModalBio('enrolar', id) → cámara → vector → POST /enrolar
//
// FLUJO 2 (Verificación 1:1):
//   Usuario escribe ID en sec-asistencia → clic Entrada/Salida
//   → iniciarVerificacion1a1(tipo) → abrirModalBio('verificar', id, tipo)
//   → cámara → vector → POST /verificar (solo el ID ingresado)
//   → si coincide → POST /asistencia → registro automático
//
// POLÍTICA DE PRIVACIDAD:
//   La imagen es procesada en el navegador y descartada.
//   Solo el vector Float32[128] es enviado al servidor.
// ================================================================

const MODELS_URL = './models'; // Archivos en /Sistema-de-Asistecia--main/models/
const SCORE_MIN  = 0.70;       // Confianza mínima del detector (0-1)
const FRAMES_N   = 6;          // Frames a promediar para estabilidad del embedding

// ── Estado interno ───────────────────────────────────────────────
let modelosCargados = false;
let streamActual    = null;
let camaraActiva    = false;
let modoActual      = null;  // 'enrolar' | 'verificar'
let empIdActual     = null;  // ID de 7 dígitos
let tipoActual      = null;  // 'Entrada' | 'Salida'

// Datos temporales del acceso verificado, en espera de los metadatos
let pendingAcceso   = null;  // { codigoEmpleado, tipo, nombre, confianza }

// ── Referencias al DOM (todos dentro del #modal-bio) ─────────────
const videoEl        = document.getElementById('video-bio');
const canvasEl       = document.getElementById('canvas-bio');
const statusEl       = document.getElementById('bio-status');
const placeholderEl  = document.getElementById('cam-placeholder');
const loadingOverlay = document.getElementById('bio-loading-overlay');
const modalEl        = document.getElementById('modal-bio');


// ════════════════════════════════════════════════════════════════
// MODAL — apertura y cierre
// ════════════════════════════════════════════════════════════════

async function abrirModalBio(modo, empleadoId, tipoAsistencia) {
    modoActual  = modo;
    empIdActual = empleadoId;
    tipoActual  = tipoAsistencia || null;

    const tituloEl = document.getElementById('modal-bio-titulo');
    const infoEl   = document.getElementById('modal-bio-info');

    // Configurar el modal según el modo de operación
    if (modo === 'verificar') {
        tituloEl.innerHTML =
            `<i class="fa-solid fa-shield-halved"></i> Verificación — ${tipoAsistencia}`;
        infoEl.innerHTML = `
            <div class="modal-emp-badge">
                <i class="fa-solid fa-id-card"></i>
                <span>ID: <strong>${empleadoId}</strong></span>
            </div>
            <p class="text-muted" style="margin-top:6px; font-size:0.9rem;">
                Mira directamente a la cámara para verificar tu identidad
            </p>`;

    } else {
        tituloEl.innerHTML =
            '<i class="fa-solid fa-user-plus"></i> Registro Biométrico';
        infoEl.innerHTML = `
            <div class="modal-emp-badge enrolar">
                <i class="fa-solid fa-fingerprint"></i>
                <span>Nuevo empleado — ID: <strong>${empleadoId}</strong></span>
            </div>
            <p class="text-muted" style="margin-top:6px; font-size:0.9rem;">
                Mira directamente a la cámara para registrar tu rostro
            </p>`;
    }

    // Mostrar el modal y bloquear scroll del fondo
    modalEl.style.display  = 'flex';
    document.body.style.overflow = 'hidden';
    mostrarStatus('', '');

    // ── Inicio del flujo biométrico ──────────────────────────────
    const listo = await inicializarBiometria();
    if (!listo) return;

    const camOk = await abrirCamara();
    if (!camOk) return;

    // Pausa breve para que la exposición de la cámara se estabilice
    await new Promise(r => setTimeout(r, 800));

    if (modo === 'verificar') {
        await ejecutarVerificacion1a1();
    } else {
        await ejecutarEnrolamiento();
    }
}

function cerrarModalBio() {
    cerrarCamara();
    modalEl.style.display        = 'none';
    document.body.style.overflow = '';
    modoActual = empIdActual = tipoActual = null;
}


// ════════════════════════════════════════════════════════════════
// CARGA DE MODELOS (solo la primera vez que se abre el modal)
// ════════════════════════════════════════════════════════════════

async function inicializarBiometria() {
    if (modelosCargados) return true;

    loadingOverlay.classList.add('visible');
    mostrarStatus('scanning',
        '<i class="fa-solid fa-circle-notch fa-spin"></i> Cargando modelos de IA...');

    try {
        await Promise.all([
            faceapi.nets.tinyFaceDetector.loadFromUri(MODELS_URL),
            faceapi.nets.faceLandmark68Net.loadFromUri(MODELS_URL),
            faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_URL),
        ]);
        modelosCargados = true;
        loadingOverlay.classList.remove('visible');
        mostrarStatus('success',
            '<i class="fa-solid fa-circle-check"></i> Modelos listos.');
        return true;
    } catch (err) {
        loadingOverlay.classList.remove('visible');
        console.error('Error cargando modelos face-api.js:', err);
        mostrarStatus('error',
            '<i class="fa-solid fa-triangle-exclamation"></i> No se encontraron los modelos en /models/');
        return false;
    }
}


// ════════════════════════════════════════════════════════════════
// CÁMARA
// ════════════════════════════════════════════════════════════════

async function abrirCamara() {
    if (camaraActiva) return true;
    try {
        streamActual = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' },
            audio: false,
        });
        videoEl.srcObject = streamActual;
        await new Promise(r =>
            videoEl.addEventListener('loadedmetadata', r, { once: true })
        );

        canvasEl.width  = videoEl.videoWidth;
        canvasEl.height = videoEl.videoHeight;

        videoEl.style.display       = 'block';
        canvasEl.style.display      = 'block';
        placeholderEl.style.display = 'none';

        camaraActiva = true;
        return true;
    } catch (err) {
        mostrarStatus('error',
            '<i class="fa-solid fa-video-slash"></i> No se pudo acceder a la cámara. Verifica los permisos del navegador.');
        return false;
    }
}

function cerrarCamara() {
    if (streamActual) {
        streamActual.getTracks().forEach(t => t.stop());
        streamActual = null;
    }
    videoEl.srcObject           = null;
    videoEl.style.display       = 'none';
    canvasEl.style.display      = 'none';
    placeholderEl.style.display = 'flex';
    canvasEl.getContext('2d').clearRect(0, 0, canvasEl.width, canvasEl.height);
    camaraActiva = false;
}


// ════════════════════════════════════════════════════════════════
// EXTRACCIÓN DEL EMBEDDING
// ✅ PRIVACIDAD: La imagen se procesa en memoria y se descarta.
//    Solo retorna el vector matemático Float32[128].
// ════════════════════════════════════════════════════════════════

async function extraerDescriptorDeFrame() {
    const opts = new faceapi.TinyFaceDetectorOptions({
        inputSize: 320, scoreThreshold: SCORE_MIN,
    });
    return await faceapi
        .detectSingleFace(videoEl, opts)
        .withFaceLandmarks()
        .withFaceDescriptor() || null;
    // El frame de imagen es liberado por el GC al retornar
}

// Promedia FRAMES_N frames válidos para mayor estabilidad biométrica
async function capturarEmbeddingEstable() {
    const frames = [];
    mostrarStatus('scanning',
        '<i class="fa-solid fa-magnifying-glass fa-pulse"></i> Posiciona tu rostro frente a la cámara...');

    while (frames.length < FRAMES_N) {
        const det = await extraerDescriptorDeFrame();
        if (det) {
            frames.push(det.descriptor);
            dibujarDeteccion(det);
            mostrarStatus('scanning',
                `<i class="fa-solid fa-circle-notch fa-spin"></i> Analizando... (${frames.length}/${FRAMES_N} muestras)`);
        }
        await new Promise(r => setTimeout(r, 200));
    }

    // ✅ Promediar los vectores matemáticamente → resultado: Array[128 floats]
    const avg = new Float32Array(128);
    frames.forEach(desc => desc.forEach((v, i) => { avg[i] += v; }));
    avg.forEach((_, i) => { avg[i] /= frames.length; });

    return Array.from(avg); // ✅ Solo el vector — sin imagen
}

function dibujarDeteccion(det) {
    const ctx  = canvasEl.getContext('2d');
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    const dims = { width: videoEl.videoWidth, height: videoEl.videoHeight };
    const res  = faceapi.resizeResults(det, dims);
    faceapi.draw.drawDetections(canvasEl, res);
    faceapi.draw.drawFaceLandmarks(canvasEl, res);
}


// ════════════════════════════════════════════════════════════════
// FLUJO 2 — VERIFICACIÓN 1:1
// Compara el rostro SOLO contra el vector del ID ingresado.
// Si el ID no existe o el rostro no coincide → acceso denegado.
// ════════════════════════════════════════════════════════════════

async function ejecutarVerificacion1a1() {
    // Capturar embedding estable (6 frames promediados)
    const embedding = await capturarEmbeddingEstable();

    if (!embedding) {
        mostrarStatus('warning',
            '<i class="fa-solid fa-face-frown"></i> Rostro no detectado. Asegúrate de tener buena iluminación.');
        return; // El usuario puede cerrar manualmente o intentar de nuevo
    }

    mostrarStatus('scanning',
        '<i class="fa-solid fa-circle-notch fa-spin"></i> Verificando identidad 1:1...');

    try {
        // ✅ Solo enviamos el vector + el ID específico a comparar
        // El backend busca ÚNICAMENTE el embedding de ese empleado (1:1, no 1:N)
        const res = await fetch(`${API_URL}/biometria/verificar`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                codigo_empleado: empIdActual, // ← restringe la búsqueda a este ID
                face_embedding:  embedding,   // ← vector puro, sin imagen
                tipo:            tipoActual,
            }),
        });
        const data = await res.json();

        if (data.verificado) {
            // ── ACCESO CONCEDIDO ────────────────────────────────
            if (tipoActual === 'Entrada') {
                // Para Entrada: guardar datos verificados y abrir modal de metadatos.
                // La asistencia NO se registra todavía; espera puerta + sucursal.
                pendingAcceso = {
                    codigoEmpleado: empIdActual,
                    tipo:           tipoActual,
                    nombre:         data.nombre,
                    confianza:      data.confianza,
                };

                mostrarStatus('success', `
                    <i class="fa-solid fa-circle-check"></i>
                    <strong>${data.nombre}</strong> verificado.
                    Selecciona puerta y sede...
                `);

                // Cerrar modal biométrico → abrir modal de metadatos
                setTimeout(() => {
                    cerrarModalBio();
                    abrirModalMetadatos();
                }, 1300);

            } else {
                // Para Salida: registrar directamente, sin metadatos adicionales
                await fetch(`${API_URL}/asistencia`, {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body:    JSON.stringify({ id: empIdActual, tipo: tipoActual }),
                });

                mostrarStatus('success', `
                    <div style="text-align:center; line-height:2">
                        <i class="fa-solid fa-circle-check" style="font-size:2rem; display:block;"></i>
                        <strong>${data.nombre}</strong><br>
                        <span>Salida registrada · ${new Date().toTimeString().split(' ')[0]}</span><br>
                        <small style="opacity:0.8;">Confianza: ${data.confianza}%</small>
                    </div>
                `);
                cargarDatosBD();
                setTimeout(cerrarModalBio, 3500);
            }

        } else {
            // ── ACCESO DENEGADO ─────────────────────────────────
            mostrarStatus('error', `
                <div style="text-align:center; line-height:2">
                    <i class="fa-solid fa-shield-xmark" style="font-size:2rem; display:block;"></i>
                    <strong>Acceso Denegado</strong><br>
                    <span style="font-size:0.9rem;">${data.mensaje}</span>
                </div>
            `);
            setTimeout(cerrarModalBio, 3000);
        }

    } catch (err) {
        console.error('Error en verificación 1:1:', err);
        mostrarStatus('error',
            '<i class="fa-solid fa-server"></i> Error de conexión. ¿Está corriendo app.py?');
        setTimeout(cerrarModalBio, 2500);
    }
}


// ════════════════════════════════════════════════════════════════
// FLUJO 1 — ENROLAMIENTO
// Guarda el vector del nuevo empleado en la BD.
// ════════════════════════════════════════════════════════════════

async function ejecutarEnrolamiento() {
    const embedding = await capturarEmbeddingEstable();

    if (!embedding) {
        mostrarStatus('warning',
            '<i class="fa-solid fa-face-frown"></i> Rostro no detectado. Mejora la iluminación e intenta de nuevo.');
        return;
    }

    mostrarStatus('scanning',
        '<i class="fa-solid fa-circle-notch fa-spin"></i> Guardando biometría...');

    try {
        // ✅ Solo enviamos el vector (Float32→Array) — la imagen fue descartada
        const res = await fetch(`${API_URL}/biometria/enrolar`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                codigo_empleado: empIdActual,
                face_embedding:  embedding,
            }),
        });
        const data = await res.json();

        if (data.success) {
            mostrarStatus('success', `
                <div style="text-align:center; line-height:2">
                    <i class="fa-solid fa-check-circle" style="font-size:2rem; display:block;"></i>
                    <strong>Biometría registrada</strong><br>
                    <small>${data.mensaje}</small>
                </div>
            `);
            setTimeout(cerrarModalBio, 2500);
        } else {
            mostrarStatus('error',
                `<i class="fa-solid fa-times-circle"></i> ${data.mensaje}`);
            setTimeout(cerrarModalBio, 2500);
        }

    } catch (err) {
        console.error('Error en enrolamiento:', err);
        mostrarStatus('error',
            '<i class="fa-solid fa-server"></i> Error de conexión. ¿Está corriendo app.py?');
        setTimeout(cerrarModalBio, 2500);
    }
}


// ════════════════════════════════════════════════════════════════
// FUNCIONES PÚBLICAS — invocadas desde index.html y script.js
// ════════════════════════════════════════════════════════════════

// Llamada desde los botones "Registrar Entrada / Salida" en sec-asistencia.
// Valida que sea exactamente 7 dígitos y abre el modal de verificación 1:1.
function iniciarVerificacion1a1(tipo) {
    const idInput = document.getElementById('emp-id');
    const msgEl   = document.getElementById('mensaje-asistencia');
    const id      = idInput.value.trim();

    if (!/^\d{7}$/.test(id)) {
        msgEl.style.color   = '#ef4444';
        msgEl.textContent   = 'El ID debe tener exactamente 7 dígitos numéricos.';
        setTimeout(() => { msgEl.textContent = ''; }, 3000);
        return;
    }

    // ── Transición: limpiar campo → abrir modal de verificación ──
    idInput.value = '';
    abrirModalBio('verificar', id, tipo);
}

// Llamada desde script.js tras registrar un nuevo empleado,
// y desde los botones "Enrolar" del directorio de empleados.
function iniciarEnrolamientoEmpleado(codigoEmpleado) {
    abrirModalBio('enrolar', codigoEmpleado, null);
}


// ── Utilidad: mostrar mensajes de estado con estilo visual ───────
function mostrarStatus(tipo, html) {
    statusEl.className = `bio-status${tipo ? ' ' + tipo : ''}`;
    statusEl.innerHTML = html;
}


// ════════════════════════════════════════════════════════════════
// MÓDULO 2 — MODAL METADATOS DE ACCESO
// Se abre tras verificación exitosa de Entrada.
// El empleado elige puerta y sucursal; al confirmar se guarda la asistencia.
// ════════════════════════════════════════════════════════════════

function abrirModalMetadatos() {
    const modal = document.getElementById('modal-metadatos');

    // Mostrar resumen del empleado verificado
    document.getElementById('meta-empleado-info').innerHTML = `
        <div class="modal-emp-badge">
            <i class="fa-solid fa-circle-check"></i>
            <span>${pendingAcceso.nombre} — Entrada · ${new Date().toTimeString().split(' ')[0]}</span>
        </div>
        <p class="text-muted" style="margin-top:6px; font-size:0.85rem;">
            Confianza biométrica: ${pendingAcceso.confianza}%
        </p>`;

    // Limpiar selecciones anteriores
    document.querySelectorAll('input[name="puerta"]').forEach(r => r.checked = false);
    document.getElementById('sel-sucursal').value    = '';
    document.getElementById('meta-error').style.display = 'none';

    modal.style.display          = 'flex';
    document.body.style.overflow = 'hidden';
}

async function confirmarAccesoConMetadatos() {
    const puerta   = document.querySelector('input[name="puerta"]:checked')?.value;
    const sucursal = document.getElementById('sel-sucursal').value;
    const errorEl  = document.getElementById('meta-error');

    // Validar que ambos campos estén seleccionados
    if (!puerta) {
        errorEl.textContent   = 'Selecciona la puerta de ingreso.';
        errorEl.style.display = 'block';
        return;
    }
    if (!sucursal) {
        errorEl.textContent   = 'Selecciona la sede / sucursal.';
        errorEl.style.display = 'block';
        return;
    }

    errorEl.style.display = 'none';

    try {
        // Ahora sí se registra la asistencia, con los metadatos completos
        const res = await fetch(`${API_URL}/asistencia`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                id:       pendingAcceso.codigoEmpleado,
                tipo:     pendingAcceso.tipo,
                puerta,    // puerta de ingreso seleccionada
                sucursal,  // sede/sucursal seleccionada
            }),
        });
        const data = await res.json();

        if (data.success) {
            cerrarModalMetadatos();
            cargarDatosBD(); // Refrescar reporte con los nuevos datos
            // Mostrar confirmación breve en la sección de asistencia
            const msgEl = document.getElementById('mensaje-asistencia');
            msgEl.style.color = '#10b981';
            msgEl.innerHTML   =
                `✅ Entrada de <strong>${pendingAcceso.nombre}</strong> registrada · ${puerta} · ${sucursal}`;
            setTimeout(() => { msgEl.textContent = ''; }, 5000);
        } else {
            errorEl.textContent   = data.mensaje || 'Error al registrar la asistencia.';
            errorEl.style.display = 'block';
        }
    } catch {
        errorEl.textContent   = 'Error de conexión con el servidor.';
        errorEl.style.display = 'block';
    }
}

function cerrarModalMetadatos() {
    document.getElementById('modal-metadatos').style.display = 'none';
    document.body.style.overflow = '';
    pendingAcceso = null;
}
