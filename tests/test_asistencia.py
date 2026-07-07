def test_registrar_entrada_empleado_no_existe(auth_client):
    res = auth_client.post('/api/asistencia', json={'id': '9999999', 'tipo': 'Entrada'})
    assert res.status_code == 404


def test_salida_sin_entrada_previa(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Asistencia', 'depto': 'Operaciones'})
    codigo = alta.get_json()['nuevo_id']

    res = auth_client.post('/api/asistencia', json={'id': codigo, 'tipo': 'Salida'})
    assert res.status_code == 400
    assert 'entrada' in res.get_json()['mensaje'].lower()


def test_entrada_y_salida_exitosas(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Asistencia 2', 'depto': 'Operaciones'})
    codigo = alta.get_json()['nuevo_id']

    entrada = auth_client.post('/api/asistencia', json={
        'id': codigo, 'tipo': 'Entrada', 'puerta': 'Puerta principal', 'sucursal': 'CDMX',
    })
    assert entrada.status_code == 200
    assert entrada.get_json()['success'] is True

    salida = auth_client.post('/api/asistencia', json={'id': codigo, 'tipo': 'Salida'})
    assert salida.status_code == 200
    assert salida.get_json()['success'] is True


def test_entrada_duplicada_mismo_dia_actualiza_registro(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Asistencia 3', 'depto': 'Ventas'})
    codigo = alta.get_json()['nuevo_id']

    primera  = auth_client.post('/api/asistencia', json={'id': codigo, 'tipo': 'Entrada'})
    segunda  = auth_client.post('/api/asistencia', json={'id': codigo, 'tipo': 'Entrada'})

    assert primera.status_code == 200
    assert segunda.status_code == 200  # ON DUPLICATE KEY UPDATE, no debe fallar
