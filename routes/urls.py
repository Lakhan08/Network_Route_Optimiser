"""URL patterns for the routes app."""

from django.urls import path

from .views import (
    EdgeDetailView,
    EdgeListCreateView,
    NodeDetailView,
    NodeListCreateView,
    RouteHistoryView,
    ShortestRouteView,
)

urlpatterns = [
    # Nodes
    path("nodes", NodeListCreateView.as_view(), name="node-list-create"),
    path("nodes/<int:node_id>", NodeDetailView.as_view(), name="node-detail"),

    # Edges
    path("edges", EdgeListCreateView.as_view(), name="edge-list-create"),
    path("edges/<int:edge_id>", EdgeDetailView.as_view(), name="edge-detail"),

    # Routes
    path("routes/shortest", ShortestRouteView.as_view(), name="route-shortest"),
    path("routes/history", RouteHistoryView.as_view(), name="route-history"),
]