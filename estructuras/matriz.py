class Celda:
    def __init__(self, valor):
        self.valor = valor
        self.siguiente = None


class Fila:
    def __init__(self):
        self.primera_celda = None
        self.siguiente = None


class Matriz:
    def __init__(self, filas, columnas, valor_inicial=None):
        self.filas = filas
        self.columnas = columnas
        self.primera_fila = None
        for _ in range(filas):
            fila = Fila()
            for _ in range(columnas):
                celda = Celda(valor_inicial)
                celda.siguiente = fila.primera_celda
                fila.primera_celda = celda
            fila.siguiente = self.primera_fila
            self.primera_fila = fila

    def _buscar_celda(self, fila, columna):
        if fila < 0 or fila >= self.filas or columna < 0 or columna >= self.columnas:
            raise IndexError("La posición está fuera de la matriz")
        fila_actual = self.primera_fila
        for _ in range(fila):
            fila_actual = fila_actual.siguiente
        celda = fila_actual.primera_celda
        for _ in range(columna):
            celda = celda.siguiente
        return celda

    def obtener(self, fila, columna):
        return self._buscar_celda(fila, columna).valor

    def asignar(self, fila, columna, valor):
        self._buscar_celda(fila, columna).valor = valor