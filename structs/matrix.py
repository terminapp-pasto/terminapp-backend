"""Matriz hecha con nodos enlazados: una lista de filas, y cada fila una lista de celdas."""


class Cell:
    def __init__(self, value):
        self.value = value
        self.next = None


class Row:
    def __init__(self):
        self.first_cell = None
        self.next = None


class Matrix:
    def __init__(self, rows, columns, initial_value=None):
        self.rows = rows
        self.columns = columns
        self.first_row = None
        for _ in range(rows):
            row = Row()
            for _ in range(columns):
                cell = Cell(initial_value)
                cell.next = row.first_cell
                row.first_cell = cell
            row.next = self.first_row
            self.first_row = row

    def _find_cell(self, row, column):
        if row < 0 or row >= self.rows or column < 0 or column >= self.columns:
            raise IndexError("La posición está fuera de la matriz")
        current_row = self.first_row
        for _ in range(row):
            current_row = current_row.next
        cell = current_row.first_cell
        for _ in range(column):
            cell = cell.next
        return cell

    def get(self, row, column):
        return self._find_cell(row, column).value

    def set(self, row, column, value):
        self._find_cell(row, column).value = value
