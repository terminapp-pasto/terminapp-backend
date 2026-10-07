# TerminAPP - Backend

Plataforma para consultar y comprar pasajes de la Terminal de Transportes de Pasto por medio de un chat.
Proyecto final de Estructuras de Datos - Universidad Cooperativa de Colombia, sede Pasto.

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