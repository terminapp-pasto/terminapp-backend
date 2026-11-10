"""Grafo dirigido con lista de adyacencia hecha con nodos enlazados.

Cada vértice es un municipio y cada arista una ruta de una empresa, con su
duración en minutos como peso.
"""

from structs.matrix import Matrix


def normalize(text):
    text = text.strip().lower()
    text = text.replace("á", "a").replace("é", "e").replace("í", "i")
    text = text.replace("ó", "o").replace("ú", "u").replace("ü", "u")
    return text


def edit_distance(first, second):
    """Cuántas letras hay que cambiar, quitar o poner para pasar de first a second (Levenshtein).
    Usa la matriz de nodos como tabla de programación dinámica: la celda (i, j)
    guarda la distancia entre las primeras i letras de first y las primeras j de second."""
    first, second = normalize(first), normalize(second)
    table = Matrix(len(first) + 1, len(second) + 1, 0)
    for i in range(len(first) + 1):
        table.set(i, 0, i)
    for j in range(len(second) + 1):
        table.set(0, j, j)
    for i in range(1, len(first) + 1):
        for j in range(1, len(second) + 1):
            substitution_cost = 0 if first[i - 1] == second[j - 1] else 1
            table.set(i, j, min(
                table.get(i - 1, j) + 1,                       # quitar una letra
                table.get(i, j - 1) + 1,                       # poner una letra
                table.get(i - 1, j - 1) + substitution_cost,   # cambiar una letra
            ))
    return table.get(len(first), len(second))


class Edge:
    def __init__(self, destination, weight, company, route_id):
        self.destination = destination
        self.weight = weight
        self.company = company
        self.route_id = route_id
        self.next = None


class Vertex:
    def __init__(self, name, index):
        self.name = name
        self.index = index
        self.first_edge = None
        self.next = None

    def add_edge(self, edge):
        edge.next = self.first_edge
        self.first_edge = edge

    def find_edge(self, route_id):
        edge = self.first_edge
        while edge is not None:
            if edge.route_id == route_id:
                return edge
            edge = edge.next
        return None


class Graph:
    def __init__(self):
        self.first_vertex = None
        self.size = 0

    def find_vertex(self, name):
        wanted = normalize(name)
        current = self.first_vertex
        while current is not None:
            if normalize(current.name) == wanted:
                return current
            current = current.next
        return None

    def add_vertex(self, name):
        existing = self.find_vertex(name)
        if existing is not None:
            return existing
        new_vertex = Vertex(name, self.size)
        new_vertex.next = self.first_vertex
        self.first_vertex = new_vertex
        self.size += 1
        return new_vertex

    def add_route(self, origin, destination, weight, company, route_id):
        origin_vertex = self.add_vertex(origin)
        self.add_vertex(destination)
        origin_vertex.add_edge(Edge(destination, weight, company, route_id))

    def describe(self):
        """Devuelve un texto con cada municipio y sus rutas de salida."""
        lines = []
        vertex = self.first_vertex
        while vertex is not None:
            line = vertex.name + " →"
            edge = vertex.first_edge
            if edge is None:
                line += " (sin salidas)"
            while edge is not None:
                line += f" [{edge.destination} {edge.weight} min {edge.company}]"
                edge = edge.next
            lines.append(line)
            vertex = vertex.next
        return "\n".join(lines)

    def find_closest(self, name):
        """El municipio con el nombre más parecido, para corregir errores como "bodota".
        Solo acepta hasta 2 letras de diferencia (y no más de un tercio del nombre)."""
        best, smallest = None, None
        vertex = self.first_vertex
        while vertex is not None:
            distance = edit_distance(name, vertex.name)
            if smallest is None or distance < smallest:
                best, smallest = vertex, distance
            vertex = vertex.next
        if best is None or smallest > 2 or smallest * 3 > len(normalize(name)):
            return None
        return best

    def find_by_index(self, index):
        current = self.first_vertex
        while current is not None:
            if current.index == index:
                return current
            current = current.next
        return None

    def travel_time_matrix(self):
        """Matriz de tiempos directos: la celda (i, j) es la ruta más corta de i a j."""
        matrix = Matrix(self.size, self.size)
        vertex = self.first_vertex
        while vertex is not None:
            matrix.set(vertex.index, vertex.index, 0)
            edge = vertex.first_edge
            while edge is not None:
                destination = self.find_vertex(edge.destination)
                current = matrix.get(vertex.index, destination.index)
                if current is None or edge.weight < current:
                    matrix.set(vertex.index, destination.index, edge.weight)
                edge = edge.next
            vertex = vertex.next
        return matrix
