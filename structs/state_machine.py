"""Finite state machine.

It stores the allowed transitions in its own linked list. Each transition
says: "from this state, with this event, go to that state". If someone tries a
step that is not in the list (for example paying a cancelled ticket), the
machine rejects it.
"""


class TransitionError(Exception):
    """An event was attempted that is not allowed in the current state."""


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
        """Finds the transition for the current state and that event. O(t), t = transitions."""
        current = self.first_transition
        while current is not None:
            if current.source == self.state and current.event == event:
                return current
            current = current.next
        return None

    def can(self, event):
        return self._find_transition(event) is not None

    def trigger(self, event):
        """Applies the event and returns the new state; if not allowed, raises TransitionError."""
        transition = self._find_transition(event)
        if transition is None:
            raise TransitionError(f"No se puede '{event}' cuando el tiquete está {self.state}")
        self.state = transition.target
        return self.state


# ---- States of a purchase in TerminAPP ----
SELECTING = "SELECTING"    # the user is choosing seats
RESERVED = "RESERVED"      # the seat is held while the user pays
PAYING = "PAYING"          # the user is paying in Stripe
PAID = "PAID"              # Stripe confirmed the payment: the ticket is valid
CANCELLED = "CANCELLED"    # the user gave up
EXPIRED = "EXPIRED"        # the hold time ran out without payment

# ---- Events ----
RESERVE = "reserve"
START_PAYMENT = "start_payment"
CONFIRM_PAYMENT = "confirm_payment"
CANCEL = "cancel"
EXPIRE = "expire"
RECOVER_PAYMENT = "recover_payment"   # a late payment arrived and the seats were still free
REFUND = "refund"                     # the terminal gave the money back: the ticket is no longer valid


def purchase_state_machine(current_state=SELECTING):
    """Builds the machine with the purchase rules, starting at current_state."""
    machine = StateMachine(current_state)
    machine.add_transition(SELECTING, RESERVE, RESERVED)
    machine.add_transition(RESERVED, START_PAYMENT, PAYING)
    machine.add_transition(PAYING, START_PAYMENT, PAYING)   # resume an open payment
    machine.add_transition(PAYING, CONFIRM_PAYMENT, PAID)
    machine.add_transition(RESERVED, CANCEL, CANCELLED)
    machine.add_transition(PAYING, CANCEL, CANCELLED)
    machine.add_transition(RESERVED, EXPIRE, EXPIRED)
    machine.add_transition(PAYING, EXPIRE, EXPIRED)
    machine.add_transition(EXPIRED, RECOVER_PAYMENT, PAID)
    machine.add_transition(CANCELLED, RECOVER_PAYMENT, PAID)
    machine.add_transition(PAID, REFUND, CANCELLED)
    return machine
