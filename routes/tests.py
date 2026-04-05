"""
Comprehensive test suite for Network Route Optimization API.

Test structure
--------------
TestDijkstraAlgorithm  – pure unit tests for the algorithm (no DB)
TestNodeAPI            – integration tests for POST/GET/DELETE /nodes
TestEdgeAPI            – integration tests for POST/GET/DELETE /edges
TestShortestRouteAPI   – integration tests for POST /routes/shortest
TestRouteHistoryAPI    – integration tests for GET /routes/history

Run with:
    python manage.py test routes --verbosity=2
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .algorithms import build_graph, dijkstra
from .models import Edge, Node, RouteQuery


# ===========================================================================
# Pure algorithm tests (no database required)
# ===========================================================================

class TestDijkstraAlgorithm(TestCase):
    """Unit tests for dijkstra() and build_graph() in algorithms.py."""

    def _graph(self, edges):
        return build_graph(edges)

    # --- build_graph -------------------------------------------------------

    def test_build_graph_basic(self):
        """build_graph populates outbound adjacency lists."""
        g = self._graph([{"source": "A", "destination": "B", "latency": 5}])
        self.assertIn("A", g)
        self.assertIn("B", g)
        self.assertEqual(g["A"], [("B", 5)])
        self.assertEqual(g["B"], [])

    def test_build_graph_multiple_edges(self):
        """Multiple edges from same source are all stored."""
        edges = [
            {"source": "A", "destination": "B", "latency": 3},
            {"source": "A", "destination": "C", "latency": 7},
        ]
        g = self._graph(edges)
        self.assertEqual(len(g["A"]), 2)

    # --- dijkstra ----------------------------------------------------------

    def test_direct_path(self):
        """Single direct edge is the shortest path."""
        g = self._graph([{"source": "A", "destination": "B", "latency": 10}])
        latency, path = dijkstra(g, "A", "B")
        self.assertEqual(latency, 10)
        self.assertEqual(path, ["A", "B"])

    def test_prefers_lower_latency_path(self):
        """Algorithm picks multi-hop low-cost route over direct high-cost one."""
        edges = [
            {"source": "A", "destination": "B", "latency": 10},
            {"source": "B", "destination": "C", "latency": 5},
            {"source": "A", "destination": "C", "latency": 20},
        ]
        g = self._graph(edges)
        latency, path = dijkstra(g, "A", "C")
        self.assertEqual(latency, 15)
        self.assertEqual(path, ["A", "B", "C"])

    def test_no_path_returns_none(self):
        """Returns (None, None) when destination is unreachable."""
        g = self._graph([{"source": "A", "destination": "B", "latency": 5}])
        g["C"] = []  # isolated node
        latency, path = dijkstra(g, "A", "C")
        self.assertIsNone(latency)
        self.assertIsNone(path)

    def test_source_equals_destination(self):
        """Source == destination should return zero cost and single-element path."""
        g = self._graph([{"source": "A", "destination": "B", "latency": 5}])
        latency, path = dijkstra(g, "A", "A")
        self.assertEqual(latency, 0)
        self.assertEqual(path, ["A"])

    def test_unknown_node_returns_none(self):
        """Non-existent node names return (None, None)."""
        g = self._graph([{"source": "A", "destination": "B", "latency": 5}])
        self.assertEqual(dijkstra(g, "X", "B"), (None, None))
        self.assertEqual(dijkstra(g, "A", "Y"), (None, None))

    def test_complex_graph(self):
        """Verify optimal path in a multi-node graph."""
        #  A -1-> B -2-> D
        #  |             ^
        #  +-----10------+  (direct A->D = 10, via B->D = 3, via B->C->D = 5)
        edges = [
            {"source": "A", "destination": "B", "latency": 1},
            {"source": "B", "destination": "C", "latency": 2},
            {"source": "C", "destination": "D", "latency": 2},
            {"source": "B", "destination": "D", "latency": 10},
            {"source": "A", "destination": "D", "latency": 20},
        ]
        g = self._graph(edges)
        latency, path = dijkstra(g, "A", "D")
        self.assertEqual(latency, 5)
        self.assertEqual(path, ["A", "B", "C", "D"])

    def test_float_latencies(self):
        """Algorithm handles floating-point latency values correctly."""
        edges = [
            {"source": "A", "destination": "B", "latency": 1.5},
            {"source": "B", "destination": "C", "latency": 2.3},
        ]
        g = self._graph(edges)
        latency, path = dijkstra(g, "A", "C")
        self.assertAlmostEqual(latency, 3.8)
        self.assertEqual(path, ["A", "B", "C"])


# ===========================================================================
# Base test case with helpers
# ===========================================================================

class BaseAPITestCase(TestCase):
    """Common setup and helpers shared across API test classes."""

    def setUp(self):
        self.client = APIClient()

    # Convenience helpers ---------------------------------------------------

    def create_node(self, name: str):
        return self.client.post("/nodes", {"name": name}, format="json")

    def create_edge(self, source: str, destination: str, latency: float):
        return self.client.post(
            "/edges",
            {"source": source, "destination": destination, "latency": latency},
            format="json",
        )

    def setup_linear_graph(self):
        """Creates A -> B -> C -> D (latencies 5, 10, 15)."""
        for name in ("ServerA", "ServerB", "ServerC", "ServerD"):
            self.create_node(name)
        self.create_edge("ServerA", "ServerB", 5)
        self.create_edge("ServerB", "ServerC", 10)
        self.create_edge("ServerC", "ServerD", 15)


# ===========================================================================
# Node API tests
# ===========================================================================

class TestNodeAPI(BaseAPITestCase):

    # POST /nodes -----------------------------------------------------------

    def test_create_node_success(self):
        res = self.create_node("ServerA")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "ServerA")
        self.assertIn("id", res.data)

    def test_create_node_persisted(self):
        self.create_node("ServerA")
        self.assertTrue(Node.objects.filter(name="ServerA").exists())

    def test_create_node_missing_name(self):
        res = self.client.post("/nodes", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_node_empty_name(self):
        res = self.create_node("   ")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_node_duplicate_name(self):
        self.create_node("ServerA")
        res = self.create_node("ServerA")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # GET /nodes ------------------------------------------------------------

    def test_list_nodes_empty(self):
        res = self.client.get("/nodes")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_list_nodes_returns_all(self):
        self.create_node("ServerA")
        self.create_node("ServerB")
        res = self.client.get("/nodes")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    # DELETE /nodes/<id> ----------------------------------------------------

    def test_delete_node_success(self):
        self.create_node("ServerA")
        node_id = Node.objects.get(name="ServerA").id
        res = self.client.delete(f"/nodes/{node_id}")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Node.objects.filter(name="ServerA").exists())

    def test_delete_node_not_found(self):
        res = self.client.delete("/nodes/9999")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_node_cascades_edges(self):
        """Deleting a node removes its associated edges."""
        self.create_node("ServerA")
        self.create_node("ServerB")
        self.create_edge("ServerA", "ServerB", 5)
        self.assertEqual(Edge.objects.count(), 1)
        node_id = Node.objects.get(name="ServerA").id
        self.client.delete(f"/nodes/{node_id}")
        self.assertEqual(Edge.objects.count(), 0)


# ===========================================================================
# Edge API tests
# ===========================================================================

class TestEdgeAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.create_node("ServerA")
        self.create_node("ServerB")
        self.create_node("ServerC")

    # POST /edges -----------------------------------------------------------

    def test_create_edge_success(self):
        res = self.create_edge("ServerA", "ServerB", 12.5)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["source"], "ServerA")
        self.assertEqual(res.data["destination"], "ServerB")
        self.assertEqual(res.data["latency"], 12.5)

    def test_create_edge_persisted(self):
        self.create_edge("ServerA", "ServerB", 12.5)
        self.assertEqual(Edge.objects.count(), 1)

    def test_create_edge_missing_source(self):
        res = self.client.post(
            "/edges", {"destination": "ServerB", "latency": 5}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_missing_destination(self):
        res = self.client.post(
            "/edges", {"source": "ServerA", "latency": 5}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_missing_latency(self):
        res = self.client.post(
            "/edges", {"source": "ServerA", "destination": "ServerB"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_zero_latency(self):
        res = self.create_edge("ServerA", "ServerB", 0)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_negative_latency(self):
        res = self.create_edge("ServerA", "ServerB", -5)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_source_not_found(self):
        res = self.create_edge("Ghost", "ServerB", 5)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_destination_not_found(self):
        res = self.create_edge("ServerA", "Ghost", 5)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_duplicate(self):
        self.create_edge("ServerA", "ServerB", 5)
        res = self.create_edge("ServerA", "ServerB", 8)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_self_loop(self):
        res = self.create_edge("ServerA", "ServerA", 5)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reverse_edge_allowed(self):
        """A->B and B->A are distinct directed edges."""
        self.create_edge("ServerA", "ServerB", 5)
        res = self.create_edge("ServerB", "ServerA", 7)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    # GET /edges ------------------------------------------------------------

    def test_list_edges_empty(self):
        res = self.client.get("/edges")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_list_edges_returns_all(self):
        self.create_edge("ServerA", "ServerB", 5)
        self.create_edge("ServerB", "ServerC", 10)
        res = self.client.get("/edges")
        self.assertEqual(len(res.data), 2)

    # DELETE /edges/<id> ----------------------------------------------------

    def test_delete_edge_success(self):
        self.create_edge("ServerA", "ServerB", 5)
        edge_id = Edge.objects.first().id
        res = self.client.delete(f"/edges/{edge_id}")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Edge.objects.count(), 0)

    def test_delete_edge_not_found(self):
        res = self.client.delete("/edges/9999")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# ===========================================================================
# Shortest route API tests
# ===========================================================================

class TestShortestRouteAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.setup_linear_graph()

    # Basic success ---------------------------------------------------------

    def test_direct_edge_path(self):
        res = self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerB"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["path"], ["ServerA", "ServerB"])
        self.assertEqual(res.data["total_latency"], 5)

    def test_multi_hop_path(self):
        res = self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerD"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["path"], ["ServerA", "ServerB", "ServerC", "ServerD"])
        self.assertAlmostEqual(res.data["total_latency"], 30)

    def test_shortest_among_multiple_paths(self):
        """When a shortcut exists, algorithm picks the faster route."""
        # Add A -> D direct with high cost (should NOT be chosen)
        self.create_edge("ServerA", "ServerD", 100)
        # Also add A -> C with medium cost; A->B->C = 15, A->C direct = 8 => A->C->D = 23
        self.create_edge("ServerA", "ServerC", 8)
        res = self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerD"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # A->C->D = 8+15 = 23 < A->B->C->D = 30 < A->D = 100
        self.assertEqual(res.data["total_latency"], 23)

    # No path ---------------------------------------------------------------

    def test_no_path_returns_404(self):
        # ServerD has no outbound edges; create isolated ServerE
        self.create_node("ServerE")
        res = self.client.post(
            "/routes/shortest",
            {"source": "ServerD", "destination": "ServerE"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", res.data)

    # Validation ------------------------------------------------------------

    def test_invalid_source_node(self):
        res = self.client.post(
            "/routes/shortest",
            {"source": "Ghost", "destination": "ServerB"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_destination_node(self):
        res = self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "Ghost"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_source_field(self):
        res = self.client.post(
            "/routes/shortest", {"destination": "ServerB"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_destination_field(self):
        res = self.client.post(
            "/routes/shortest", {"source": "ServerA"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # History persistence ---------------------------------------------------

    def test_successful_query_saved_to_history(self):
        self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerD"},
            format="json",
        )
        self.assertEqual(RouteQuery.objects.count(), 1)
        rq = RouteQuery.objects.first()
        self.assertEqual(rq.source, "ServerA")
        self.assertEqual(rq.destination, "ServerD")
        self.assertIsNotNone(rq.total_latency)

    def test_failed_query_saved_to_history(self):
        """Even when no path exists, the query must be persisted."""
        self.create_node("ServerE")
        self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerE"},
            format="json",
        )
        self.assertEqual(RouteQuery.objects.count(), 1)
        rq = RouteQuery.objects.first()
        self.assertIsNone(rq.total_latency)
        self.assertEqual(rq.path, [])


# ===========================================================================
# Route history API tests
# ===========================================================================

class TestRouteHistoryAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.setup_linear_graph()
        # Seed two route queries
        self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerD"},
            format="json",
        )
        self.client.post(
            "/routes/shortest",
            {"source": "ServerB", "destination": "ServerC"},
            format="json",
        )

    def test_history_returns_all_records(self):
        res = self.client.get("/routes/history")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_history_record_schema(self):
        res = self.client.get("/routes/history")
        record = res.data[0]
        for field in ("id", "source", "destination", "total_latency", "path", "created_at"):
            self.assertIn(field, record)

    def test_history_ordered_newest_first(self):
        res = self.client.get("/routes/history")
        self.assertEqual(res.data[0]["source"], "ServerB")  # latest query

    def test_filter_by_source(self):
        res = self.client.get("/routes/history?source=ServerA")
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["source"], "ServerA")

    def test_filter_by_destination(self):
        res = self.client.get("/routes/history?destination=ServerC")
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["destination"], "ServerC")

    def test_filter_by_source_and_destination(self):
        res = self.client.get("/routes/history?source=ServerA&destination=ServerD")
        self.assertEqual(len(res.data), 1)

    def test_limit_parameter(self):
        res = self.client.get("/routes/history?limit=1")
        self.assertEqual(len(res.data), 1)

    def test_limit_zero_is_invalid(self):
        res = self.client.get("/routes/history?limit=0")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_limit_negative_is_invalid(self):
        res = self.client.get("/routes/history?limit=-1")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_limit_non_integer_is_invalid(self):
        res = self.client.get("/routes/history?limit=abc")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_from_filter(self):
        # All records were created now; filtering from far future returns nothing
        res = self.client.get("/routes/history?date_from=2099-01-01T00:00:00Z")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_date_to_filter(self):
        # All records were created now; filtering before epoch returns nothing
        res = self.client.get("/routes/history?date_to=2000-01-01T00:00:00Z")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_invalid_date_from(self):
        res = self.client.get("/routes/history?date_from=not-a-date")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_to(self):
        res = self.client.get("/routes/history?date_to=not-a-date")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_history(self):
        RouteQuery.objects.all().delete()
        res = self.client.get("/routes/history")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])