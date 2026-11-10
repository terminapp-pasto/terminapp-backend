"""Pruebas de la máquina de estados de la compra (structs/state_machine.py)."""
import unittest

from structs.state_machine import (
    CANCEL, CANCELLED, CONFIRM_PAYMENT, EXPIRE, EXPIRED, PAID, PAYING, RESERVE, RESERVED, SELECTING,
    START_PAYMENT, TransitionError, purchase_state_machine,
)


class StateMachineTest(unittest.TestCase):
    def test_happy_path(self):
        machine = purchase_state_machine()
        self.assertEqual(machine.state, SELECTING)
        self.assertEqual(machine.trigger(RESERVE), RESERVED)
        self.assertEqual(machine.trigger(START_PAYMENT), PAYING)
        self.assertEqual(machine.trigger(CONFIRM_PAYMENT), PAID)

    def test_a_paid_ticket_never_changes(self):
        machine = purchase_state_machine(PAID)
        for event in (CANCEL, EXPIRE, RESERVE, START_PAYMENT):
            self.assertFalse(machine.can(event))
            with self.assertRaises(TransitionError):
                machine.trigger(event)
        self.assertEqual(machine.state, PAID)

    def test_cancel_and_expire(self):
        self.assertEqual(purchase_state_machine(RESERVED).trigger(CANCEL), CANCELLED)
        self.assertEqual(purchase_state_machine(PAYING).trigger(EXPIRE), EXPIRED)

    def test_resuming_an_open_payment_keeps_paying(self):
        self.assertEqual(purchase_state_machine(PAYING).trigger(START_PAYMENT), PAYING)

    def test_cannot_pay_without_reserving(self):
        with self.assertRaises(TransitionError):
            purchase_state_machine(SELECTING).trigger(CONFIRM_PAYMENT)

    def test_cancelled_or_expired_cannot_be_paid(self):
        for state in (CANCELLED, EXPIRED):
            self.assertFalse(purchase_state_machine(state).can(START_PAYMENT))


if __name__ == "__main__":
    unittest.main()
