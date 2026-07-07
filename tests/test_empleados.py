import os


def test_registrar_empleado_genera_id_7_digitos(auth_client):
    res = auth_client.post('/api/empleados', json={'nombre': 'Empleado Prueba', 'depto': 'Tecnología'})
    data = res.get_json()

    assert res.status_code == 201
    assert data['success'] is True
    assert len(data['nuevo_id']) == 7
    assert data['nuevo_id'].isdigit()


def test_dar_baja_password_incorrecta(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Baja', 'depto': 'Ventas'})
    codigo = alta.get_json()['nuevo_id']

    res = auth_client.post('/api/empleados/baja', json={'codigo_empleado': codigo, 'password': 'incorrecta'})
    assert res.status_code == 403
    assert res.get_json()['success'] is False


def test_dar_baja_password_correcta(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Baja 2', 'depto': 'Ventas'})
    codigo = alta.get_json()['nuevo_id']

    res = auth_client.post('/api/empleados/baja', json={
        'codigo_empleado': codigo,
        'password':        os.environ['ADMIN_PASSWORD'],
    })
    assert res.status_code == 200
    assert res.get_json()['success'] is True

    # El empleado dado de baja ya no debe aparecer en el directorio activo
    datos = auth_client.get('/api/datos-iniciales').get_json()
    ids_directorio = [e['id'] for e in datos['directorio']]
    assert codigo not in ids_directorio


def test_dar_baja_empleado_inexistente(auth_client):
    res = auth_client.post('/api/empleados/baja', json={
        'codigo_empleado': '0000000',
        'password':        os.environ['ADMIN_PASSWORD'],
    })
    assert res.status_code == 404
