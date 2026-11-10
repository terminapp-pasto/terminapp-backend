"""Máquina de estados finitos.

Guarda las transiciones permitidas en una lista enlazada propia. Cada
transición dice: "desde este estado, con este evento, se pasa a este otro".
Si alguien intenta un paso que no está en la lista (por ejemplo pagar un
tiquete cancelado), la máquina lo rechaza.
"""


class TransitionError(Exception):
    """Se intentó un evento que no está permitido en el estado actual."""


class Transition:
    def __init__(self, source, event, target):
        self.source = source
        self.event = event
        self.target = target
        self.next = None


class StateMachine:
    def __init__(self, initial_state):
        self.state = initial_state
        self.first_transition = None
        self.size = 0

    def add_transition(self, source, event, target):
        new_transition = Transition(source, event, target)
        new_transition.next = self.first_transition
        self.first_transition = new_transition
        self.size += 1

    def _find_transition(self, event):
        """Busca la transición del estado actual con ese evento. O(t), t = transiciones."""
        current = self.first_transition
        while current is not None:
            if current.source == self.state and current.event == event:
                return current
            current = current.next
        return None

    def can(self, event):
        return self._find_transition(event) is not None

    def trigger(self, event):
        """Aplica el evento y devuelve el nuevo estado; si no se puede, lanza TransitionError."""
        transition = self._find_transition(event)
        if transition is None:
            raise TransitionError(f"No se puede '{event}' cuando el tiquete está {self.state}")
        self.state = transition.target
        return self.state


# ---- Estados de una compra en TerminAPP ----
SELECTING = "SELECTING"    # el usuario está escogiendo asiento
RESERVED = "RESERVED"      # el asiento queda apartado mientras paga
PAYING = "PAYING"          # el usuario está pagando en Stripe
PAID = "PAID"              # Stripe confirmó el pago: el tiquete es válido
CANCELLED = "CANCELLED"    # el usuario desistió
EXPIRED = "EXPIRED"        # pasó el tiempo de reserva sin pagar

# ---- Eventos ----
RESERVE = "reserve"
START_PAYMENT = "start_payment"
CONFIRM_PAYMENT = "confirm_payment"
CANCEL = "cancel"
EXPIRE = "expire"


def purchase_state_machine(current_state=SELECTING):
    """Crea la máquina con las reglas de una compra, empezando en current_state."""
    machine = StateMachine(current_state)
    machine.add_transition(SELECTING, RESERVE, RESERVED)
    machine.add_transition(RESERVED, START_PAYMENT, PAYING)
    machine.add_transition(PAYING, START_PAYMENT, PAYING)   # retomar un pago abierto
    machine.add_transition(PAYING, CONFIRM_PAYMENT, PAID)
    machine.add_transition(RESERVED, CANCEL, CANCELLED)
    machine.add_transition(PAYING, CANCEL, CANCELLED)
    machine.add_transition(RESERVED, EXPIRE, EXPIRED)
    machine.add_transition(PAYING, EXPIRE, EXPIRED)
    return machine
