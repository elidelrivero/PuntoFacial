def test_novedades_body_vacio_responde_400_no_500(auth_client):
    """Hallazgo #7: campos faltantes deben dar 400 JSON, no un 500 sin manejar."""
    res = auth_client.post('/api/novedades', json={})
    assert res.status_code == 400
    assert res.get_json()['success'] is False


def test_novedad_nombre_ambiguo_pide_especificar_id(auth_client):
    """Hallazgo #8: nombre parcial que coincide con varios empleados no debe
    adivinar — debe rechazar y pedir el ID."""
    auth_client.post('/api/empleados', json={'nombre': 'Ana Torres', 'depto': 'Ventas'})
    auth_client.post('/api/empleados', json={'nombre': 'Mariana Lopez', 'depto': 'Ventas'})

    res = auth_client.post('/api/novedades', json={
        'empleado':     'Ana',
        'tipo':         'Vacaciones',
        'fecha_inicio': '2026-08-01',
        'fecha_fin':    '2026-08-05',
    })
    assert res.status_code == 400
    assert res.get_json()['success'] is False


def test_novedad_nombre_exacto_no_es_ambiguo(auth_client):
    """Un nombre completo exacto debe resolverse aunque sea substring de otro."""
    auth_client.post('/api/empleados', json={'nombre': 'Ana Torres', 'depto': 'Ventas'})
    auth_client.post('/api/empleados', json={'nombre': 'Mariana Lopez', 'depto': 'Ventas'})

    res = auth_client.post('/api/novedades', json={
        'empleado':     'Ana Torres',
        'tipo':         'Vacaciones',
        'fecha_inicio': '2026-08-01',
        'fecha_fin':    '2026-08-05',
    })
    assert res.status_code == 200
    assert res.get_json()['success'] is True


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
