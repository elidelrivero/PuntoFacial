def test_registrar_novedad_por_id(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Novedad', 'depto': 'Recursos Humanos'})
    codigo = alta.get_json()['nuevo_id']

    res = auth_client.post('/api/novedades', json={
        'empleado':     codigo,
        'tipo':         'Vacaciones',
        'fecha_inicio': '2026-08-01',
        'fecha_fin':    '2026-08-10',
    })
    assert res.status_code == 200
    assert res.get_json()['success'] is True


def test_registrar_novedad_por_nombre(auth_client):
    auth_client.post('/api/empleados', json={'nombre': 'Empleado Novedad Nombre', 'depto': 'Recursos Humanos'})

    res = auth_client.post('/api/novedades', json={
        'empleado':     'Empleado Novedad Nombre',
        'tipo':         'Permiso Personal',
        'fecha_inicio': '2026-08-01',
        'fecha_fin':    '2026-08-02',
    })
    assert res.status_code == 200
    assert res.get_json()['success'] is True


def test_registrar_novedad_empleado_inexistente(auth_client):
    res = auth_client.post('/api/novedades', json={
        'empleado':     'NoExiste123',
        'tipo':         'Permiso Personal',
        'fecha_inicio': '2026-08-01',
        'fecha_fin':    '2026-08-02',
    })
    assert res.status_code == 404
