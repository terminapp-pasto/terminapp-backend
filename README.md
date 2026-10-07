# TerminAPP - Backend

Plataforma para consultar y comprar pasajes de la Terminal de Transportes de Pasto por medio de un chat.
Proyecto final de Estructuras de Datos - Universidad Cooperativa de Colombia, sede Pasto.

## Caso de estudio

**El problema.** Para saber qué buses salen de la Terminal de Transportes de Pasto, a qué hora y cuánto cuestan, hoy una persona tiene que ir hasta la terminal, llamar a cada empresa o revisar varias páginas de venta que no siempre coinciden entre sí. La página oficial de la terminal publica las empresas y los destinos, pero no los horarios ni las tarifas en un solo lugar.

**El usuario.** Personas que viajan desde Pasto hacia municipios de Nariño y hacia ciudades como Cali, Mocoa o Bogotá: estudiantes, trabajadores y familias que necesitan comparar opciones rápido y que no siempre tienen experiencia usando aplicaciones.

**Por qué la IA ayuda.** El usuario escribe como habla, por ejemplo "quiero ir a Cali esta noche, lo más barato", y la IA convierte esa frase en una búsqueda concreta: destino, hora y forma de ordenar. La búsqueda la resuelven las estructuras de datos del backend, y la IA devuelve el resultado en lenguaje natural y guía la compra. Así nadie tiene que aprender a usar filtros ni formularios.

## Integrantes
- Juan David Moreno
- Felipe Alejandro Cerón

## URLs
- Backend: https://terminapp-backend.onrender.com
- Frontend: https://terminapp-frontend.vercel.app
- Repositorio frontend: https://github.com/terminapp-pasto/terminapp-frontend

## Tecnologías
Python, FastAPI, PostgreSQL (Neon), Render.

## Base de datos

Diagrama entidad-relación de las 5 tablas en PostgreSQL.

```mermaid
erDiagram
    EMPRESAS ||--o{ RUTAS : "opera"
    DESTINOS ||--o{ RUTAS : "es origen de"
    DESTINOS ||--o{ RUTAS : "es destino de"
    RUTAS ||--o{ HORARIOS : "tiene"
    HORARIOS ||--o{ TIQUETES : "se vende en"

    EMPRESAS {
        int id PK
        text nombre
    }
    DESTINOS {
        int id PK
        text nombre
    }
    RUTAS {
        int id PK
        int empresa_id FK
        int origen_id FK
        int destino_id FK
        int duracion_min
    }
    HORARIOS {
        int id PK
        int ruta_id FK
        time hora_salida
        int precio
        int cupos
    }
    TIQUETES {
        int id PK
        int horario_id FK
        date fecha_viaje
        text estado
        timestamptz creado_en
    }
```
## Arquitectura

TerminAPP tiene cuatro capas. El frontend solo habla con el backend, y el backend es el único que habla con la base de datos, con la IA y con Stripe. Las claves viven en variables de entorno del backend, nunca en el frontend ni en Git.

```mermaid
flowchart LR
    U["Usuario<br/>navegador o celular"]
    F["Frontend<br/>React + Vite<br/>Vercel"]
    B["Backend<br/>Python + FastAPI<br/>Render"]
    BD[("Base de datos<br/>PostgreSQL<br/>Neon")]
    IA["IA<br/>API del modelo de lenguaje"]
    S["Stripe<br/>pagos en modo prueba"]

    U -->|escribe en el chat| F
    F -->|HTTP + JSON| B
    B -->|SQL| BD
    B -->|HTTPS + API key| IA
    B -->|sesion de pago| S
```

### Recorrido de una petición

```mermaid
sequenceDiagram
    actor U as Usuario
    participant F as Frontend
    participant B as Backend
    participant IA as IA
    participant BD as Base de datos

    U->>F: Quiero ir a Cali esta noche, lo mas barato
    F->>B: POST /chat
    B->>IA: mensaje y herramientas disponibles
    IA-->>B: usar buscar_salidas con destino Cali
    B->>BD: consulta de rutas y horarios
    BD-->>B: filas
    Note over B: El grafo valida la ruta, el AVL filtra por hora y el heap ordena por precio
    B->>IA: resultados de la busqueda
    IA-->>B: respuesta en lenguaje natural
    B-->>F: JSON con la respuesta
    F-->>U: muestra las opciones
```
