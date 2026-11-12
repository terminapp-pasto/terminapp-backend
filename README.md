# TerminAPP - Backend

A chat-based platform to look up and buy bus tickets from the Pasto bus terminal (Terminal de Transportes de Pasto, Colombia).
Final project for Data Structures (Estructuras de Datos) - Universidad Cooperativa de Colombia, Pasto campus.

## Case study

**The problem.** To find out which buses leave the Pasto bus terminal, at what time and for how much, people today have to go to the terminal, call each company, or check several ticket websites that do not always agree. The terminal's official website lists the companies and destinations, but not the schedules or fares in one place.

**The user.** People travelling from Pasto to towns in Nariño and to cities such as Cali, Mocoa or Bogotá: students, workers and families who need to compare options quickly and are not always used to apps.

**Why AI helps.** Users write the way they talk, for example "quiero ir a Cali esta noche, lo más barato", and the AI turns that sentence into a concrete search: destination, time and sort order. The search itself is solved by the backend data structures, and the AI returns the result in natural language and guides the purchase. Nobody has to learn filters or forms.

## Team
- Juan David Moreno
- Felipe Alejandro Cerón

## URLs
- Backend: https://terminapp-backend.onrender.com
- Frontend: https://terminapp-frontend.vercel.app
- Frontend repository: https://github.com/terminapp-pasto/terminapp-frontend

## Technologies
Python, FastAPI, PostgreSQL (Neon), Gemini (AI), Stripe (test mode), Render.

## Code layout

```
config.py            every environment variable (nothing is hardcoded)
main.py              assembles the application and plugs in the routes
routes/              HTTP routes: system, search, chat, auth, purchases
services/            business logic: search, purchases, users, dates, validation, database
structs/             the 10 data structures built from scratch
authentication/      utilities.py (encrypt and verify passwords) and tokens.py (JWT)
ai/                  gemini.py (provider), tools.py (tools), orchestrator.py (the chat)
payments/            stripe_client.py (embedded Stripe payment in test mode)
db/                  SQL scripts 01 to 08
tests/               automated tests
```

All code (folders, files, classes, functions, variables, comments, tables and columns) is in English.
Only the text the end user reads (the interface, error messages and the assistant's replies) is in Spanish,
because TerminAPP is used by travellers in Colombia.

## Endpoints
| Method | Route | What it does |
|---|---|---|
| GET | `/health` | Checks the database connection |
| GET | `/search?destination=Cali&date=2026-10-24&from_time=18:00&sort_by=price` | Searches the departures from Pasto on one day, with that day's free seats |
| GET | `/destinations` | Lists the destinations with routes from Pasto |
| POST | `/chat` | Receives the conversation (`{"messages": [{"role": "user", "text": "..."}]}`) and answers with the AI and the departures found |
| POST | `/register` | Creates an account (the password is stored encrypted with PBKDF2) and returns a token |
| POST | `/login` | Checks email and password and returns a JWT token valid for 24 hours |
| GET | `/me` | 🔒 Protected route: returns the user who owns the token (`Authorization: Bearer <token>`) |
| GET | `/schedules/{id}/seats?date=YYYY-MM-DD` | Map of the 40 seats of a departure on a date |
| POST | `/purchases` | 🔒 Holds 1 to 5 seats for 15 minutes, with one passenger's details per seat |
| POST | `/purchases/{payment_id}/pay` | 🔒 Prepares the embedded Stripe payment; reuses an open one if it exists |
| GET | `/purchases/confirm?session_id=...` | 🔒 Asks Stripe whether it was paid and confirms the tickets |
| POST | `/purchases/{payment_id}/cancel` | 🔒 Cancels an unpaid purchase and frees the seats |
| GET | `/my-tickets?order=newest` | 🔒 The user's purchase history (`newest` or `oldest`), with each booking code |
| POST | `/stripe/webhook` | Stripe calls it when a payment is completed (signed with `STRIPE_WEBHOOK_SECRET`) |

## Purchase rules
- **One passenger per seat.** Buying 3 seats asks for 3 names and 3 documents.
- **Document types.** Each passenger has a document type: `CC` (cédula, 5 to 10 digits), `TI` (tarjeta de
  identidad, 10 or 11 digits), `CE` (cédula de extranjería, 5 to 12 digits) or `PA` (passport, letters and digits,
  5 to 12). Dots, spaces and hyphens are removed before checking (`1.085.123.456` → `1085123456`).
- **Booking code.** Every purchase gets a random 6-character code such as `K7M2QX`, without the characters that
  are easy to confuse (O/0, I/1). It is what the passenger shows when boarding.
- **At most 2 unpaid purchases per user**, so nobody can hold half a bus without paying.
- **Validation with regular expressions** (in the frontend and again in the backend, `services/validation.py`):
  name only letters and spaces, 3 to 50 characters; document only digits, 5 to 12; email up to 100 characters;
  password 8 to 72. A huge text is rejected before it reaches the database.
- **Two people and the last seat.** Reserving locks the departure (`SELECT ... FOR UPDATE`): PostgreSQL queues (FIFO)
  the other reservations for that departure, the first one wins and the second gets "El asiento 40 acaba de ser ocupado".
  On top of that, the unique index `unique_seat_per_trip` prevents a seat from being sold twice. The test
  `test_two_people_take_the_last_seat_at_the_same_time` proves it with two reservations at the same instant.
- **Never two payments in progress for the same trip.** If the user goes back and reserves the same departure again,
  the previous pending purchase is cancelled and its Stripe session closed. When paying, an open session is reused.
- **Payments are confirmed by asking Stripe**, never by trusting that the user came back to the page.

## Running it locally
1. Copy `.env.example` to `.env` and fill in `DATABASE_URL`, `GEMINI_API_KEY`, `TOKEN_SECRET`, `STRIPE_SECRET_KEY` and `FRONTEND_URL` (never commit it).
2. Activate the environment: `.\venv\Scripts\Activate.ps1`
3. Start the server **on port 8001**, so it does not clash with other projects on port 8000:
   ```
   uvicorn main:app --reload --port 8001
   ```
4. Open http://127.0.0.1:8001/docs

## Data structures

The 10 structures are built from scratch in `structs/`, with our own linked nodes (no Python lists or dictionaries as the structure).

| # | Structure | File | What it does in TerminAPP | Complexity |
|---|---|---|---|---|
| 1 | Directed weighted graph (adjacency list) | `graph.py` | Towns as vertices and routes as edges weighted by duration; answers "is there a route from Pasto to X?" | Find vertex O(V), walk a vertex's routes O(degree) |
| 2 | Linked-node matrix | `matrix.py` | Edit distance table to fix misspelled destinations ("bodota" → Bogotá) and travel time matrix between towns | Access O(r + c); correction O(n·m·(n+m)) |
| 3 | AVL tree | `avl_tree.py` | A route's schedules sorted by time; "from 18:00 on" without checking them all | Insert and search O(log n) |
| 4 | Min-heap | `min_heap.py` | Sorts the departures found by time or by price | Insert and extract O(log n) |
| 5 | N-ary tree | `nary_tree.py` | Hierarchy terminal → companies → routes → schedules | Traversal O(n) |
| 6 | Hash table with chaining | `hash_table.py` | A bus seat map (number → FREE/TAKEN) and grouping the history by purchase | Insert, find and remove O(1) on average |
| 7 | Stack | `stack.py` | Undo: if one of several seats is already taken, the previous ones are released in reverse order | Push and pop O(1) |
| 8 | Queue | `queue.py` | Pending reservations in arrival order; those unpaid after 15 minutes expire | Enqueue and dequeue O(1) |
| 9 | State machine | `state_machine.py` | Ticket life cycle: SELECTING → RESERVED → PAYING → PAID, or CANCELLED / EXPIRED | Transition O(t) |
| 10 | Doubly linked list | `doubly_linked_list.py` | Purchase history, walkable from newest to oldest and back | Add and remove O(1), traverse O(n) |

```mermaid
stateDiagram-v2
    [*] --> SELECTING
    SELECTING --> RESERVED: reserve
    RESERVED --> PAYING: start_payment
    PAYING --> PAYING: start_payment (resumes the open payment)
    PAYING --> PAID: confirm_payment
    RESERVED --> CANCELLED: cancel
    PAYING --> CANCELLED: cancel
    RESERVED --> EXPIRED: expire (15 min)
    PAYING --> EXPIRED: expire (45 min)
    PAID --> [*]
```

### Automated tests

`tests/` has 77 tests: the 10 structures, authentication, dates, form validation and purchases against a real
database. The purchase tests cover more than the happy path: taken seat, invalid or huge data, another user touching
my purchase, cancelling, expiring, paying twice and **two people asking for the last seat at the same time**.

Run them with the environment activated:

```
python -m unittest discover -s tests -v
```

The 11 purchase tests need an **empty, disposable** database (for example a Neon branch), because they drop and
recreate the tables. Without that variable they are skipped:

```
$env:TEST_DATABASE_URL="postgresql://...test-branch..."
python -m unittest tests.test_purchases_database -v
```

If everything is fine, the last line says `OK`.

## Database

Entity-relationship diagram of the 12 PostgreSQL tables. A new database is created with scripts `db/01` to `db/04`; a database that already existed in Spanish is translated to English, without losing data, with `db/05_translate_to_english.sql`. The first 5 tables support the search; the rest support authentication, purchases, payments and the AI chat.

```mermaid
erDiagram
    COMPANIES ||--o{ ROUTES : "operates"
    COMPANIES ||--o{ BUSES : "has"
    DESTINATIONS ||--o{ ROUTES : "is origin of"
    DESTINATIONS ||--o{ ROUTES : "is destination of"
    ROUTES ||--o{ SCHEDULES : "has"
    SCHEDULES ||--o{ TICKETS : "is sold as"
    BUSES ||--o{ SEATS : "has"
    SEATS ||--o{ TICKETS : "is assigned to"
    USERS ||--o{ PASSENGERS : "registers"
    PASSENGERS ||--o{ TICKETS : "travels on"
    PAYMENTS ||--o{ TICKETS : "covers"
    USERS ||--o{ CONVERSATIONS : "starts"
    CONVERSATIONS ||--o{ MESSAGES : "contains"

    COMPANIES {
        int id PK
        text name
    }
    DESTINATIONS {
        int id PK
        text name
    }
    ROUTES {
        int id PK
        int company_id FK
        int origin_id FK
        int destination_id FK
        int duration_min
    }
    SCHEDULES {
        int id PK
        int route_id FK
        time departure_time
        int price
        int seats
    }
    TICKETS {
        int id PK
        int schedule_id FK
        int passenger_id FK
        int seat_id FK
        int payment_id FK
        date travel_date
        text status
        timestamptz created_at
    }
    USERS {
        int id PK
        varchar50 name
        varchar100 email
        text password_hash
        timestamptz created_at
    }
    PASSENGERS {
        int id PK
        int user_id FK
        varchar50 name
        varchar12 document
    }
    BUSES {
        int id PK
        int company_id FK
        text plate
        int capacity
    }
    SEATS {
        int id PK
        int bus_id FK
        int number
    }
    PAYMENTS {
        int id PK
        text stripe_session_id
        int amount
        text status
        timestamptz created_at
    }
    CONVERSATIONS {
        int id PK
        int user_id FK
        timestamptz created_at
    }
    MESSAGES {
        int id PK
        int conversation_id FK
        text role
        text content
        timestamptz created_at
    }
```
## Architecture

TerminAPP has four layers. The frontend only talks to the backend, and the backend is the only one that talks to the database, the AI and Stripe. Keys live in the backend environment variables, never in the frontend or in Git.

```mermaid
flowchart LR
    U["User<br/>browser or phone"]
    F["Frontend<br/>React + Vite<br/>Vercel"]
    B["Backend<br/>Python + FastAPI<br/>Render"]
    DB[("Database<br/>PostgreSQL<br/>Neon")]
    AI["AI<br/>Gemini API"]
    S["Stripe<br/>test payments"]

    U -->|types in the chat| F
    F -->|HTTP + JSON| B
    B -->|SQL| DB
    B -->|HTTPS + API key| AI
    B -->|embedded payment session| S
```

### How a request flows

```mermaid
sequenceDiagram
    actor U as User
    participant F as Frontend
    participant B as Backend
    participant AI as AI
    participant DB as Database

    U->>F: Quiero ir a Cali esta noche, lo mas barato
    F->>B: POST /chat
    B->>AI: message and available tools
    AI-->>B: use search_tickets with destination Cali
    B->>DB: routes and schedules query
    DB-->>B: rows
    Note over B: The graph checks the route, the AVL filters by time and the heap sorts by price
    B->>AI: search results
    AI-->>B: natural language answer
    B-->>F: JSON with the answer
    F-->>U: shows the options
```
