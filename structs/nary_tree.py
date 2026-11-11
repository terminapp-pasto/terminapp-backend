"""N-ary tree using first child / next sibling links.

In TerminAPP it represents the hierarchy Terminal → company → route → departure.
"""


class NaryNode:
    def __init__(self, name, data=None):
        self.name = name
        self.data = data
        self.first_child = None
        self.next_sibling = None

    def add_child(self, child):
        if self.first_child is None:
            self.first_child = child
            return
        current = self.first_child
        while current.next_sibling is not None:
            current = current.next_sibling
        current.next_sibling = child

    def find_child(self, name):
        current = self.first_child
        while current is not None:
            if current.name == name:
                return current
            current = current.next_sibling
        return None

    def get_or_create_child(self, name):
        child = self.find_child(name)
        if child is None:
            child = NaryNode(name)
            self.add_child(child)
        return child


class NaryTree:
    def __init__(self, root_name):
        self.root = NaryNode(root_name)

    def describe(self):
        """Returns the tree as text, indented by level."""
        lines = []
        self._describe(self.root, 0, lines)
        return "\n".join(lines)

    def _describe(self, node, level, lines):
        lines.append("    " * level + node.name)
        child = node.first_child
        while child is not None:
            self._describe(child, level + 1, lines)
            child = child.next_sibling
