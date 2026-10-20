"""Máquina de estados finitos.

Guarda las transiciones permitidas en una lista enlazada propia. Cada
transición dice: "desde este estado, con este evento, se pasa a este otro".
Si alguien intenta un paso que no está en la lista (por ejemplo pagar un
tiquete cancelado), la máquina lo rechaza.
"""


class ErrorTransicion(Exception):
    """Se intentó un evento que no está permitido en el estado actual."""


class Transicion:
    def __init__(self, origen, evento, destino):
        self.origen = origen
        self.evento = evento
        self.destino = destino
        self.siguiente = None


class MaquinaEstados:
    def __init__(self, estado_inicial):
        self.estado = estado_inicial
        self.primera = None
        self.cantidad = 0

    def agregar_transicion(self, origen, evento, destino):
        nueva = Transicion(origen, evento, destino)
        nueva.siguiente = self.primera
        self.primera = nueva
        self.cantidad += 1

    def _buscar(self, evento):
        """Busca la transición del estado actual con ese evento. O(t), t = transiciones."""
        actual = self.primera
        while actual is not None:
            if actual.origen == self.estado and actual.evento == evento:
                return actual
            actual = actual.siguiente
        return None

    def puede(self, evento):
        return self._buscar(evento) is not None

    def disparar(self, evento):
        """Aplica el evento y devuelve el nuevo estado; si no se puede, lanza ErrorTransicion."""
        transicion = self._buscar(evento)
        if transicion is None:
            raise ErrorTransicion(f"No se puede '{evento}' cuando el tiquete está {self.estado}")
        self.estado = transicion.destino
        return self.estado


# ---- Estados de una compra en TerminAPP ----
ELIGIENDO = "ELIGIENDO"    # el usuario está escogiendo asiento
RESERVADO = "RESERVADO"    # el asiento queda apartado mientras paga
PAGANDO = "PAGANDO"        # el usuario está en la página de Stripe
PAGADO = "PAGADO"          # Stripe confirmó el pago: el tiquete es válido
CANCELADO = "CANCELADO"    # el usuario desistió
VENCIDO = "VENCIDO"        # pasó el tiempo de reserva sin pagar


def maquina_de_compra(estado_actual=ELIGIENDO):
    """Crea la máquina con las reglas de una compra, empezando en estado_actual."""
    maquina = MaquinaEstados(estado_actual)
    maquina.agregar_transicion(ELIGIENDO, "reservar", RESERVADO)
    maquina.agregar_transicion(RESERVADO, "ir_a_pagar", PAGANDO)
    maquina.agregar_transicion(PAGANDO, "confirmar_pago", PAGADO)
    maquina.agregar_transicion(RESERVADO, "cancelar", CANCELADO)
    maquina.agregar_transicion(PAGANDO, "cancelar", CANCELADO)
    maquina.agregar_transicion(RESERVADO, "vencer", VENCIDO)
    maquina.agregar_transicion(PAGANDO, "vencer", VENCIDO)
    return maquina
