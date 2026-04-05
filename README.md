
# Network Route Optimization API

A Django REST Framework API for managing a directed weighted graph of network nodes and computing shortest paths using **Dijkstra's algorithm**.

---

## 🚀 Features

- ✅ Create and manage network nodes and edges
- ✅ Compute shortest path using Dijkstra’s algorithm (min-heap optimized)
- ✅ Store and query route history with filters
- ✅ Strong input validation and error handling
- ✅ 60+ test cases with full coverage
- ✅ Clean and scalable architecture

---

## 🛠️ Tech Stack

| Layer       | Technology                          |
|------------|--------------------------------------|
| Framework   | Django 4.2 + Django REST Framework 3.14 |
| Algorithm   | Dijkstra's (min-heap, O((V+E) log V)) |
| Database    | SQLite (can be switched to PostgreSQL) |
| Testing     | Django TestCase + DRF APIClient |

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Apply migrations
python manage.py migrate

# 3. Run the development server
python manage.py runserver

# 4. Run the full test suite
python manage.py test routes --verbosity=2
````

---

## 📡 API Reference

### Nodes

| Method | Endpoint      | Description    |
| ------ | ------------- | -------------- |
| POST   | `/nodes`      | Create a node  |
| GET    | `/nodes`      | List all nodes |
| DELETE | `/nodes/<id>` | Delete a node  |

#### POST /nodes

```json
// Request
{ "name": "ServerA" }

// Response 201
{ "id": 1, "name": "ServerA" }

// Error 400
{ "name": ["A node named 'ServerA' already exists."] }
```

---

### Edges

| Method | Endpoint      | Description    |
| ------ | ------------- | -------------- |
| POST   | `/edges`      | Create an edge |
| GET    | `/edges`      | List all edges |
| DELETE | `/edges/<id>` | Delete an edge |

#### POST /edges

```json
// Request
{ "source": "ServerA", "destination": "ServerB", "latency": 12.5 }

// Response 201
{ "id": 1, "source": "ServerA", "destination": "ServerB", "latency": 12.5 }
```

**Validation Rules:**

* `source` and `destination` must exist
* `latency` must be greater than 0
* Duplicate edges are not allowed
* Self-loops are not allowed

---

### Routes

#### POST `/routes/shortest`

```json
// Request
{ "source": "ServerA", "destination": "ServerD" }
```

```json
// Response 200
{
  "total_latency": 30.0,
  "path": ["ServerA", "ServerB", "ServerC", "ServerD"]
}
```

```json
// Response 404
{
  "error": "No path exists between ServerA and ServerD"
}
```

---

## 📌 Example Request

```bash
curl -X POST http://127.0.0.1:8000/routes/shortest \
-H "Content-Type: application/json" \
-d '{"source":"ServerA","destination":"ServerD"}'
```

---

### GET `/routes/history`

**Query Parameters (optional):**

| Param         | Type     | Description                     |
| ------------- | -------- | ------------------------------- |
| `source`      | string   | Filter by source node name      |
| `destination` | string   | Filter by destination node name |
| `limit`       | integer  | Limit number of records         |
| `date_from`   | ISO 8601 | Records after given timestamp   |
| `date_to`     | ISO 8601 | Records before given timestamp  |

```bash
GET /routes/history?source=ServerA&limit=5
```

---

## 🏗️ Architecture

```
routes/
├── models.py       – Node, Edge, RouteQuery ORM models
├── serializers.py  – Validation + serialization logic
├── views.py        – APIView controllers
├── algorithms.py   – Pure Python Dijkstra implementation
├── urls.py         – Routing
└── tests.py        – 60+ test cases
```

---

## 💡 Key Design Decisions

* `algorithms.py` is framework-independent for easy reuse/testing
* Route history stores node names (avoids FK deletion issues)
* Validation handled in serializers for clean separation
* Directed graph design (A→B ≠ B→A)

---

## 🧪 Running Tests

```bash
python manage.py test routes --verbosity=2
```

Expected output:

```
60+ tests, 0 failures
```

---

## 🐳 Run with Docker

```bash
docker-compose up --build
```

---

## 🌟 Highlights

* Optimized shortest path using priority queue (heap)
* Clean modular architecture
* Fully tested with edge cases
* Scalable and production-ready design

---

## 📬 Future Improvements

* Add authentication (JWT)
* Introduce caching (Redis) for frequent routes
* Migrate to PostgreSQL for production
* Add rate limiting and monitoring

```

---

---

```
