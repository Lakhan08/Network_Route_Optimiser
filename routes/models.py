"""
Models for Network Route Optimization.

Represents a directed graph of network nodes (servers) connected by edges
(links with latency). Route queries are persisted for history retrieval.
"""

from django.db import models


class Node(models.Model):
    """
    A network node (e.g. a server or router).

    Fields:
        name (str): Unique human-readable identifier (e.g. 'ServerA').
        created_at (datetime): Auto-set timestamp on creation.
    """
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"Node({self.id}: {self.name})"


class Edge(models.Model):
    """
    A directed, weighted connection between two nodes.

    Latency represents the cost (milliseconds) to traverse from
    source -> destination. Duplicate edges (same source + destination)
    are rejected at the serializer level.
    """
    source = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="outgoing_edges",
    )
    destination = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="incoming_edges",
    )
    latency = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "destination"],
                name="unique_edge_source_destination",
            )
        ]

    def __str__(self) -> str:
        return f"Edge({self.source.name} -> {self.destination.name}, {self.latency}ms)"


class RouteQuery(models.Model):
    """
    Persisted record of every shortest-path query.

    Stores the result (or lack thereof) so that history can be
    filtered and paginated via GET /routes/history.
    """
    source = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    total_latency = models.FloatField(null=True, blank=True)
    path = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"RouteQuery({self.source} -> {self.destination}, "
            f"latency={self.total_latency})"
        )