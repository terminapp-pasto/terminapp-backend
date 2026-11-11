"""AVL tree ordered by departure time (in minutes after midnight).

Rotations keep it balanced, so inserting costs O(log n) and walking the
departures from a given time comes out already sorted.
"""


class AVLNode:
    def __init__(self, minutes, schedule_id, route_id, price, seats):
        self.minutes = minutes
        self.schedule_id = schedule_id
        self.route_id = route_id
        self.price = price
        self.seats = seats
        self.left = None
        self.right = None
        self.height = 1


class AVLTree:
    def __init__(self):
        self.root = None
        self.size = 0

    def _height(self, node):
        if node is None:
            return 0
        return node.height

    def _update_height(self, node):
        node.height = 1 + max(self._height(node.left), self._height(node.right))

    def _balance_factor(self, node):
        return self._height(node.left) - self._height(node.right)

    def _rotate_right(self, node):
        child = node.left
        grandchild = child.right
        child.right = node
        node.left = grandchild
        self._update_height(node)
        self._update_height(child)
        return child

    def _rotate_left(self, node):
        child = node.right
        grandchild = child.left
        child.left = node
        node.right = grandchild
        self._update_height(node)
        self._update_height(child)
        return child

    def insert(self, minutes, schedule_id, route_id, price, seats):
        new_node = AVLNode(minutes, schedule_id, route_id, price, seats)
        self.root = self._insert(self.root, new_node)
        self.size += 1

    def _insert(self, node, new_node):
        if node is None:
            return new_node
        if new_node.minutes < node.minutes:
            node.left = self._insert(node.left, new_node)
        else:
            node.right = self._insert(node.right, new_node)
        self._update_height(node)
        return self._rebalance(node)

    def _rebalance(self, node):
        balance = self._balance_factor(node)
        if balance > 1:
            if self._balance_factor(node.left) < 0:
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        if balance < -1:
            if self._balance_factor(node.right) > 0:
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        return node

    def traverse_from(self, start_minutes, visit):
        """Calls visit(node) in order for every departure from start_minutes on."""
        self._traverse_from(self.root, start_minutes, visit)

    def _traverse_from(self, node, start_minutes, visit):
        if node is None:
            return
        if node.minutes >= start_minutes:
            self._traverse_from(node.left, start_minutes, visit)
            visit(node)
        self._traverse_from(node.right, start_minutes, visit)


def time_to_minutes(time_value):
    return time_value.hour * 60 + time_value.minute


def minutes_to_text(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
