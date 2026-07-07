def test_enrolar_vector_invalido(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Bio', 'depto': 'Tecnología'})
    codigo = alta.get_json()['nuevo_id']

    res = auth_client.post('/api/biometria/enrolar', json={
        'codigo_empleado': codigo,
        'face_embedding':  [0.1, 0.2],  # no son 128 dimensiones
    })
    assert res.status_code == 400


def test_enrolar_empleado_inexistente(auth_client):
    res = auth_client.post('/api/biometria/enrolar', json={
        'codigo_empleado': '0000000',
        'face_embedding':  [0.01] * 128,
    })
    assert res.status_code == 404


def test_verificar_1a1_mismo_vector_coincide(auth_client):
    """Verificación 1:1 — comparar un rostro contra sí mismo debe dar distancia 0 (coincide)."""
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Bio 2', 'depto': 'Tecnología'})
    codigo = alta.get_json()['nuevo_id']

    vector = [0.01 * i for i in range(128)]
    enrol  = auth_client.post('/api/biometria/enrolar', json={
        'codigo_empleado': codigo,
        'face_embedding':  vector,
    })
    assert enrol.status_code == 200

    verif = auth_client.post('/api/biometria/verificar', json={
        'codigo_empleado': codigo,
        'face_embedding':  vector,
    })
    data = verif.get_json()
    assert data['verificado'] is True
    assert data['distancia'] == 0.0


def test_verificar_1a1_vector_distinto_no_coincide(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Bio 3', 'depto': 'Tecnología'})
    codigo = alta.get_json()['nuevo_id']

    vector_enrolado = [0.01 * i for i in range(128)]
    auth_client.post('/api/biometria/enrolar', json={
        'codigo_empleado': codigo,
        'face_embedding':  vector_enrolado,
    })

    vector_diferente = [-0.2] * 128  # muy distinto al enrolado → distancia alta
    verif = auth_client.post('/api/biometria/verificar', json={
        'codigo_empleado': codigo,
        'face_embedding':  vector_diferente,
    })
    assert verif.get_json()['verificado'] is False


def test_verificar_1a1_id_sin_biometria_registrada(auth_client):
    alta   = auth_client.post('/api/empleados', json={'nombre': 'Empleado Sin Bio', 'depto': 'Ventas'})
    codigo = alta.get_json()['nuevo_id']

    res = auth_client.post('/api/biometria/verificar', json={
        'codigo_empleado': codigo,
        'face_embedding':  [0.0] * 128,
    })
    assert res.get_json()['verificado'] is False
