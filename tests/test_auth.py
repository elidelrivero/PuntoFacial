import os

import pytest


def test_login_credenciales_incorrectas(client):
    res = client.post('/api/login', json={'usuario': 'admin', 'password': 'incorrecta'})
    assert res.status_code == 401
    assert res.get_json()['success'] is False


def test_login_credenciales_correctas(client):
    res = client.post('/api/login', json={
        'usuario':  os.environ['LOGIN_USER'],
        'password': os.environ['LOGIN_PASSWORD'],
    })
    assert res.status_code == 200
    assert res.get_json()['success'] is True


def test_session_check_sin_sesion(client):
    res = client.get('/api/session-check')
    assert res.get_json()['autenticado'] is False


def test_session_check_con_sesion(auth_client):
    res = auth_client.get('/api/session-check')
    assert res.get_json()['autenticado'] is True


def test_logout_cierra_sesion(auth_client):
    res = auth_client.post('/api/logout')
    assert res.get_json()['success'] is True

    res2 = auth_client.get('/api/session-check')
    assert res2.get_json()['autenticado'] is False


@pytest.mark.parametrize('metodo,ruta', [
    ('get',  '/api/datos-iniciales'),
    ('post', '/api/empleados'),
    ('post', '/api/asistencia'),
    ('post', '/api/novedades'),
    ('post', '/api/biometria/enrolar'),
    ('post', '/api/biometria/verificar'),
    ('post', '/api/empleados/baja'),
])
def test_endpoints_protegidos_sin_sesion(client, metodo, ruta):
    """Ningún endpoint de la API debe responder sin sesión activa (Mejora 4)."""
    res = getattr(client, metodo)(ruta, json={})
    assert res.status_code == 401


def test_login_bloquea_tras_varios_intentos_fallidos(client):
    """Hallazgo #10: límite de intentos fallidos de login."""
    for _ in range(5):
        client.post('/api/login', json={'usuario': 'admin', 'password': 'incorrecta'})

    res = client.post('/api/login', json={'usuario': 'admin', 'password': 'incorrecta'})
    assert res.status_code == 429


def test_no_refleja_origen_arbitrario_en_cors(client):
    """Hallazgo #6: no debe existir CORS permisivo con credenciales."""
    res = client.get('/api/session-check', headers={'Origin': 'https://sitio-ajeno.com'})
    assert 'Access-Control-Allow-Origin' not in res.headers
