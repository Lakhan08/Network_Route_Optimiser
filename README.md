# Network Route Optimization API

A Django REST Framework API for managing a directed weighted graph of network nodes and computing shortest paths using **Dijkstra's algorithm**.

---

## Tech Stack

| Layer       | Technology                  |
|-------------|-----------------------------|
| Framework   | Django 4.2 + Django REST Framework 3.14 |
| Algorithm   | Dijkstra's (min-heap, O((V+E) log V)) |
| Database    | SQLite (swap to PostgreSQL via `DATABASES` setting) |
| Testing     | Django TestCase + DRF APIClient |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Apply migrations
python manage.py migrate

# 3. Run the development server
python manage.py runserver

# 4. Run the full test suite
python manage.py test routes --verbosity=2
```

---

## API Reference

### Nodes

| Method | Endpoint        | Description        |
|--------|-----------------|--------------------|
| POST   | `/nodes`        | Create a node      |
| GET    | `/nodes`        | List all nodes     |
| DELETE | `/nodes/<id>`   | Delete a node      |

**POST /nodes**
```json
// Request
{ "name": "ServerA" }

// Response 201
{ "id": 1, "name": "ServerA" }

// Error 400 (duplicate / blank name)
{ "name": ["A node named 'ServerA' already exists."] }
```

---

### Edges

| Method | Endpoint        | Description       |
|--------|-----------------|-------------------|
| POST   | `/edges`        | Create an edge    |
| GET    | `/edges`        | List all edges    |
| DELETE | `/edges/<id>`   | Delete an edge    |

**POST /edges**
```json
// Request
{ "source": "ServerA", "destination": "ServerB", "latency": 12.5 }

// Response 201
{ "id": 1, "source": "ServerA", "destination": "ServerB", "latency": 12.5 }
```

Validation rules:
- `source` and `destination` must refer to existing node names
- `latency` must be > 0
- Duplicate edges (same source + destination) are rejected
- Self-loops (source == destination) are rejected

---

### Routes

#### POST `/routes/shortest`
```json
// Request
{ "source": "ServerA", "destination": "ServerD" }

// Response 200
{ "total_latency": 30.0, "path": ["ServerA", "ServerB", "ServerC", "ServerD"] }

// Response 404 (no path)
{ "error": "No path exists between ServerA and ServerD" }
```

#### GET `/routes/history`
Query parameters (all optional):

| Param        | Type     | Description                          |
|--------------|----------|--------------------------------------|
| `source`     | string   | Filter by source node name           |
| `destination`| string   | Filter by destination node name      |
| `limit`      | integer  | Max number of records to return      |
| `date_from`  | ISO 8601 | Include records created at or after  |
| `date_to`    | ISO 8601 | Include records created at or before |

```
GET /routes/history?source=ServerA&limit=5
```

---

## Architecture

```
routes/
├── models.py       – Node, Edge, RouteQuery ORM models
├── serializers.py  – Validation + serialization for each model
├── views.py        – APIView classes (thin controllers)
├── algorithms.py   – Pure-Python Dijkstra (no Django dependency)
├── urls.py         – URL routing
└── tests.py        – 50+ test cases covering all endpoints + edge cases
```

**Key design decisions:**
- `algorithms.py` is framework-agnostic — tested independently, easy to swap.
- Route history stores node *names* (not FKs) so records survive node deletion.
- All validation lives in serializers, keeping views clean.
- Edges are directed; A→B and B→A are independent edges.

---

## Running Tests

```bash
python manage.py test routes --verbosity=2
```

Expected output: **50+ tests, 0 failures**.