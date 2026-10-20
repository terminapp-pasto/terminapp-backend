"""Compra de pasajes: asientos, reservas, vencimientos e historial.

Aquí trabajan juntas las 5 estructuras de la compra:
- TablaHash: mapa de asientos de una salida (número -> estado), consulta O(1).
- Pila: registro para deshacer cuando se reservan varios asientos y uno falla.
- Cola: reservas pendientes por orden de llegada, para vencer las viejas.
- MaquinaEstados: decide qué cambios de estado son válidos para un tiquete.
- ListaDoble: historial de tiquetes del usuario, recorrible en los dos sentidos.
"""

import os
from datetime import date, datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

from estructuras.cola import Cola
from estructuras.lista_doble import ListaDoble
from estructuras.maquina_estados import (
    ELIGIENDO, PAGADO, PAGANDO, RESERVADO, ErrorTransicion, maquina_de_compra,
)
from estructuras.pila import Pila
from estructuras.tabla_hash import TablaHash

load_dotenv()

ZONA_COLOMBIA = timezone(timedelta(hours=-5))  # Colombia no tiene horario de verano
MINUTOS_RESERVA = 15     # tiempo para empezar a pagar
MINUTOS_PAGO = 45        # tiempo total para terminar de pagar (15 + 30 de Stripe)
MAX_ASIENTOS = 5
DIAS_DE_VENTA = 60       # se venden pasajes hasta 60 días adelante

LIBRE = "LIBRE"
OCUPADO = "OCUPADO"
VIVOS = (RESERVADO, PAGANDO, PAGADO)


class ErrorCompra(Exception):
    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def _conectar():
    return psycopg.connect(os.getenv("DATABASE_URL"))


# ------------------------------------------------------------------
# Lógica pura con las estructuras (no toca la base de datos)
# ------------------------------------------------------------------

def armar_mapa(capacidad, ocupados):
    """Crea la tabla hash con todos los asientos LIBRES y marca los ocupados."""
    mapa = TablaHash(capacidad * 2)
    for numero in range(1, capacidad + 1):
        mapa.insertar(numero, LIBRE)
    for numero in ocupados:
        mapa.insertar(numero, OCUPADO)
    return mapa


def asientos_en_orden(mapa, capacidad):
    """Pasa el mapa a la lista ordenada que se envía al frontend."""
    return [{"numero": n, "estado": mapa.obtener(n)} for n in range(1, capacidad + 1)]


def apartar_en_mapa(mapa, numeros):
    """Aparta cada asiento pedido. Si alguno ya está ocupado, deshace los anteriores
    con la pila (en orden inverso) y devuelve ese número; si todo sale bien, None."""
    deshacer = Pila()
    for numero in numeros:
        if mapa.obtener(numero) != LIBRE:
            while not deshacer.esta_vacia():
                mapa.insertar(deshacer.desapilar(), LIBRE)
            return numero
        mapa.insertar(numero, RESERVADO)
        deshacer.apilar(numero)
    return None


def buscar_vencidas(pendientes, ahora):
    """Recibe (id, estado, creado_en) ordenados del más viejo al más nuevo y
    devuelve los ids que ya vencieron. Usa una cola por cada tipo de espera:
    como están en orden de llegada, basta mirar el frente y parar en el
    primero que todavía está a tiempo."""
    reservados, pagando = Cola(), Cola()
    for pendiente in pendientes:
        (reservados if pendiente[1] == RESERVADO else pagando).encolar(pendiente)

    vencidas = []
    for cola, minutos in ((reservados, MINUTOS_RESERVA), (pagando, MINUTOS_PAGO)):
        limite = ahora - timedelta(minutes=minutos)
        while not cola.esta_vacia() and cola.ver_frente()[2] < limite:
            tiquete_id, estado, _ = cola.desencolar()
            maquina = maquina_de_compra(estado)
            maquina.disparar("vencer")
            vencidas.append(tiquete_id)
    return vencidas


def historial(tiquetes, orden="recientes"):
    """Arma la lista doble (más reciente en la cabeza) y la recorre en el sentido pedido."""
    lista = ListaDoble()
    for tiquete in tiquetes:  # llegan del más reciente al más antiguo
        lista.agregar_al_final(tiquete)
    resultado = []
    if orden == "antiguos":
        lista.recorrer_atras(resultado.append)
    else:
        lista.recorrer_adelante(resultado.append)
    return resultado


def cambiar_estado(estado_actual, evento):
    """Pregunta a la máquina de estados a qué estado se pasa; si no se puede, ErrorCompra."""
    try:
        return maquina_de_compra(estado_actual).disparar(evento)
    except ErrorTransicion as error:
        raise ErrorCompra(str(error), 409)


# ------------------------------------------------------------------
# Consultas
# ------------------------------------------------------------------

CONSULTA_SALIDA = """
    SELECT h.id, h.hora_salida, h.precio, e.nombre, o.nombre, d.nombre,
           r.duracion_min, b.id, b.capacidad, b.placa
    FROM horarios h
    JOIN rutas r ON r.id = h.ruta_id
    JOIN empresas e ON e.id = r.empresa_id
    JOIN destinos o ON o.id = r.origen_id
    JOIN destinos d ON d.id = r.destino_id
    JOIN buses b ON b.empresa_id = r.empresa_id
    WHERE h.id = %s
    LIMIT 1;
"""

CONSULTA_OCUPADOS = """
    SELECT a.numero
    FROM tiquetes t
    JOIN asientos a ON a.id = t.asiento_id
    WHERE t.horario_id = %s AND t.fecha_viaje = %s AND t.estado IN ('RESERVADO', 'PAGANDO', 'PAGADO');
"""


def _vencer_reservas(cursor):
    cursor.execute(
        "SELECT id, estado, creado_en FROM tiquetes WHERE estado IN ('RESERVADO', 'PAGANDO') ORDER BY creado_en;"
    )
    vencidas = buscar_vencidas(cursor.fetchall(), datetime.now(timezone.utc))
    if vencidas:
        cursor.execute("UPDATE tiquetes SET estado = 'VENCIDO' WHERE id = ANY(%s);", (vencidas,))
        cursor.execute(
            """UPDATE pagos SET estado = 'VENCIDO'
               WHERE estado = 'PENDIENTE' AND id IN (SELECT pago_id FROM tiquetes WHERE id = ANY(%s));""",
            (vencidas,),
        )


def _salida(cursor, horario_id):
    cursor.execute(CONSULTA_SALIDA, (horario_id,))
    fila = cursor.fetchone()
    if fila is None:
        raise ErrorCompra("Esa salida no existe", 404)
    return {
        "horario_id": fila[0],
        "hora_salida": fila[1].strftime("%H:%M"),
        "precio": fila[2],
        "empresa": fila[3],
        "origen": fila[4],
        "destino": fila[5],
        "duracion_min": fila[6],
        "bus_id": fila[7],
        "capacidad": fila[8],
        "placa": fila[9],
    }


def _validar_fecha(fecha, salida):
    hoy = datetime.now(ZONA_COLOMBIA).date()
    if fecha < hoy:
        raise ErrorCompra("No se pueden comprar pasajes para fechas pasadas")
    if fecha > hoy + timedelta(days=DIAS_DE_VENTA):
        raise ErrorCompra(f"Solo se venden pasajes hasta {DIAS_DE_VENTA} días adelante")
    if fecha == hoy and salida["hora_salida"] <= datetime.now(ZONA_COLOMBIA).strftime("%H:%M"):
        raise ErrorCompra("Ese bus ya salió hoy. Elige otra hora u otro día")


def mapa_de_asientos(horario_id, fecha):
    with _conectar() as conexion, conexion.cursor() as cursor:
        _vencer_reservas(cursor)
        salida = _salida(cursor, horario_id)
        cursor.execute(CONSULTA_OCUPADOS, (horario_id, fecha))
        mapa = armar_mapa(salida["capacidad"], (fila[0] for fila in cursor))
        libres = 0
        for asiento in asientos_en_orden(mapa, salida["capacidad"]):
            libres += asiento["estado"] == LIBRE
        return {
            "salida": salida,
            "fecha": fecha.isoformat(),
            "libres": libres,
            "asientos": asientos_en_orden(mapa, salida["capacidad"]),
        }


def reservar(usuario_id, horario_id, fecha, numeros, nombre_pasajero, documento):
    if not numeros:
        raise ErrorCompra("Elige al menos un asiento")
    if len(numeros) > MAX_ASIENTOS:
        raise ErrorCompra(f"Puedes comprar máximo {MAX_ASIENTOS} asientos por compra")
    if len(set(numeros)) != len(numeros):
        raise ErrorCompra("Elegiste el mismo asiento dos veces")
    if len(nombre_pasajero.strip()) < 3 or len(documento.strip()) < 5:
        raise ErrorCompra("Escribe el nombre completo y el documento del pasajero")

    with _conectar() as conexion, conexion.cursor() as cursor:
        _vencer_reservas(cursor)
        salida = _salida(cursor, horario_id)
        _validar_fecha(fecha, salida)

        for numero in numeros:
            if numero < 1 or numero > salida["capacidad"]:
                raise ErrorCompra(f"El asiento {numero} no existe en este bus")

        cursor.execute(CONSULTA_OCUPADOS, (horario_id, fecha))
        mapa = armar_mapa(salida["capacidad"], (fila[0] for fila in cursor))
        ocupado = apartar_en_mapa(mapa, numeros)
        if ocupado is not None:
            raise ErrorCompra(f"El asiento {ocupado} acaba de ser ocupado. Elige otro", 409)

        cursor.execute(
            "SELECT numero, id FROM asientos WHERE bus_id = %s AND numero = ANY(%s);",
            (salida["bus_id"], numeros),
        )
        ids_asiento = TablaHash()
        for numero, asiento_id in cursor:
            ids_asiento.insertar(numero, asiento_id)

        cursor.execute(
            "INSERT INTO pasajeros (usuario_id, nombre, documento) VALUES (%s, %s, %s) RETURNING id;",
            (usuario_id, nombre_pasajero.strip(), documento.strip()),
        )
        pasajero_id = cursor.fetchone()[0]

        total = salida["precio"] * len(numeros)
        cursor.execute(
            "INSERT INTO pagos (valor, estado) VALUES (%s, 'PENDIENTE') RETURNING id, creado_en;", (total,)
        )
        pago_id, creado_en = cursor.fetchone()

        estado = cambiar_estado(ELIGIENDO, "reservar")
        try:
            for numero in numeros:
                cursor.execute(
                    """INSERT INTO tiquetes (horario_id, fecha_viaje, estado, pasajero_id, asiento_id, pago_id)
                       VALUES (%s, %s, %s, %s, %s, %s);""",
                    (horario_id, fecha, estado, pasajero_id, ids_asiento.obtener(numero), pago_id),
                )
        except psycopg.errors.UniqueViolation:
            # otra persona apartó el asiento en el mismo instante: el índice único lo impidió
            raise ErrorCompra("Uno de los asientos acaba de ser ocupado. Elige otro", 409)

    return {
        "pago_id": pago_id,
        "estado": estado,
        "salida": salida,
        "fecha": fecha.isoformat(),
        "asientos": sorted(numeros),
        "total": total,
        "vence": (creado_en + timedelta(minutes=MINUTOS_RESERVA)).isoformat(),
    }


def _tiquetes_del_pago(cursor, usuario_id, pago_id):
    cursor.execute(
        """SELECT t.id, t.estado
           FROM tiquetes t JOIN pasajeros p ON p.id = t.pasajero_id
           WHERE t.pago_id = %s AND p.usuario_id = %s;""",
        (pago_id, usuario_id),
    )
    filas = cursor.fetchall()
    if not filas:
        raise ErrorCompra("No encontramos esa compra", 404)
    return filas


def _cambiar_pago(cursor, usuario_id, pago_id, evento):
    """Aplica el evento a todos los tiquetes de una compra y devuelve el estado nuevo."""
    nuevo = None
    for _, estado in _tiquetes_del_pago(cursor, usuario_id, pago_id):
        nuevo = cambiar_estado(estado, evento)
    cursor.execute("UPDATE tiquetes SET estado = %s WHERE pago_id = %s;", (nuevo, pago_id))
    return nuevo


def datos_para_pagar(usuario_id, pago_id):
    """Revisa que la compra se pueda pagar y devuelve lo que Stripe necesita."""
    with _conectar() as conexion, conexion.cursor() as cursor:
        _vencer_reservas(cursor)
        filas = _tiquetes_del_pago(cursor, usuario_id, pago_id)
        for _, estado in filas:
            if not maquina_de_compra(estado).puede("ir_a_pagar"):
                raise ErrorCompra(f"Esta compra no se puede pagar porque está {estado}", 409)
        cursor.execute(
            """SELECT h.precio, o.nombre, d.nombre, h.hora_salida, MIN(t.fecha_viaje)
               FROM tiquetes t
               JOIN horarios h ON h.id = t.horario_id
               JOIN rutas r ON r.id = h.ruta_id
               JOIN destinos o ON o.id = r.origen_id
               JOIN destinos d ON d.id = r.destino_id
               WHERE t.pago_id = %s
               GROUP BY h.precio, o.nombre, d.nombre, h.hora_salida;""",
            (pago_id,),
        )
        precio, origen, destino, hora, fecha = cursor.fetchone()
    return {
        "precio": precio,
        "cantidad": len(filas),
        "descripcion": f"Pasaje {origen} - {destino}, {fecha.isoformat()} {hora.strftime('%H:%M')}",
    }


def marcar_pagando(usuario_id, pago_id, stripe_session_id):
    with _conectar() as conexion, conexion.cursor() as cursor:
        estado = _cambiar_pago(cursor, usuario_id, pago_id, "ir_a_pagar")
        cursor.execute("UPDATE pagos SET stripe_session_id = %s WHERE id = %s;", (stripe_session_id, pago_id))
    return estado


def marcar_pagado(usuario_id, pago_id):
    with _conectar() as conexion, conexion.cursor() as cursor:
        filas = _tiquetes_del_pago(cursor, usuario_id, pago_id)
        if all(estado == PAGADO for _, estado in filas):
            return PAGADO  # ya estaba confirmado (por ejemplo, el usuario recargó la página)
        estado = _cambiar_pago(cursor, usuario_id, pago_id, "confirmar_pago")
        cursor.execute("UPDATE pagos SET estado = 'PAGADO' WHERE id = %s;", (pago_id,))
    return estado


def cancelar(usuario_id, pago_id):
    with _conectar() as conexion, conexion.cursor() as cursor:
        estado = _cambiar_pago(cursor, usuario_id, pago_id, "cancelar")
        cursor.execute("UPDATE pagos SET estado = 'CANCELADO' WHERE id = %s;", (pago_id,))
    return estado


def _hora_de_vencimiento(estado, creado_en):
    """Hora de Colombia hasta la que se guarda una reserva sin pagar (None si no aplica)."""
    minutos = {RESERVADO: MINUTOS_RESERVA, PAGANDO: MINUTOS_PAGO}.get(estado)
    if minutos is None:
        return None
    return (creado_en + timedelta(minutes=minutos)).astimezone(ZONA_COLOMBIA).strftime("%H:%M")


def mis_tiquetes(usuario_id, orden="recientes"):
    with _conectar() as conexion, conexion.cursor() as cursor:
        _vencer_reservas(cursor)
        cursor.execute(
            """SELECT t.id, t.pago_id, t.estado, t.fecha_viaje, h.hora_salida, e.nombre,
                      o.nombre, d.nombre, a.numero, p.nombre, p.documento, h.precio, t.creado_en
               FROM tiquetes t
               JOIN pasajeros p ON p.id = t.pasajero_id
               JOIN asientos a ON a.id = t.asiento_id
               JOIN horarios h ON h.id = t.horario_id
               JOIN rutas r ON r.id = h.ruta_id
               JOIN empresas e ON e.id = r.empresa_id
               JOIN destinos o ON o.id = r.origen_id
               JOIN destinos d ON d.id = r.destino_id
               WHERE p.usuario_id = %s
               ORDER BY t.creado_en DESC, a.numero;""",
            (usuario_id,),
        )
        filas = cursor.fetchall()

    tiquetes = (
        {
            "tiquete_id": f[0], "pago_id": f[1], "estado": f[2],
            "fecha": f[3].isoformat(), "hora_salida": f[4].strftime("%H:%M"),
            "empresa": f[5], "origen": f[6], "destino": f[7], "asiento": f[8],
            "pasajero": f[9], "documento": f[10], "precio": f[11],
            "vence": _hora_de_vencimiento(f[2], f[12]),
        }
        for f in filas
    )
    return historial(tiquetes, orden)


def leer_fecha(texto):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise ErrorCompra("La fecha debe tener el formato AAAA-MM-DD")


def hoy_en_colombia():
    return datetime.now(ZONA_COLOMBIA).date()


def fecha_de_venta(texto):
    """Lee una fecha AAAA-MM-DD (vacía = hoy) y revisa que se vendan pasajes para ese día."""
    hoy = hoy_en_colombia()
    fecha = hoy if not texto else leer_fecha(texto)
    if fecha < hoy:
        raise ErrorCompra("Esa fecha ya pasó. Elige hoy o un día futuro")
    if fecha > hoy + timedelta(days=DIAS_DE_VENTA):
        raise ErrorCompra(f"Solo se venden pasajes hasta {DIAS_DE_VENTA} días adelante")
    return fecha


def ocupados_por_horario(fecha):
    """Tabla hash horario_id -> asientos ya vendidos o apartados ese día."""
    ocupados = TablaHash()
    with _conectar() as conexion, conexion.cursor() as cursor:
        _vencer_reservas(cursor)
        cursor.execute(
            """SELECT horario_id, COUNT(*) FROM tiquetes
               WHERE fecha_viaje = %s AND estado IN ('RESERVADO', 'PAGANDO', 'PAGADO')
               GROUP BY horario_id;""",
            (fecha,),
        )
        for horario_id, cantidad in cursor:
            ocupados.insertar(horario_id, cantidad)
    return ocupados
