"""
API Views for Network Route Optimization.
"""

from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from typing import Optional, List, Dict

from .algorithms import build_graph, dijkstra
from .models import Edge, Node, RouteQuery
from .serializers import (
    EdgeSerializer,
    NodeSerializer,
    RouteQuerySerializer,
    RouteRequestSerializer,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _err(detail: str) -> dict:
    return {"error": detail}


# ---------------------------------------------------------------------------
# Node Views
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        summary="List all nodes",
        responses={200: NodeSerializer(many=True)},
        tags=["Nodes"],
    ),
    post=extend_schema(
        summary="Create a node",
        request=NodeSerializer,
        responses={201: NodeSerializer},
        tags=["Nodes"],
    ),
)
class NodeListCreateView(APIView):

    def get(self, request: Request) -> Response:
        nodes = Node.objects.all()
        return Response(NodeSerializer(nodes, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = NodeSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                NodeSerializer(serializer.save()).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    delete=extend_schema(
        summary="Delete a node",
        responses={204: OpenApiResponse(description="Deleted")},
        tags=["Nodes"],
    ),
)
class NodeDetailView(APIView):

    def _get_node(self, node_id: int) -> Optional[Node]:
        try:
            return Node.objects.get(pk=node_id)
        except Node.DoesNotExist:
            return None

    def delete(self, request: Request, node_id: int) -> Response:
        node = self._get_node(node_id)
        if node is None:
            return Response(
                {"error": f"Node with id {node_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        node.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Edge Views
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        summary="List all edges",
        responses={200: EdgeSerializer(many=True)},
        tags=["Edges"],
    ),
    post=extend_schema(
        summary="Create an edge",
        request=EdgeSerializer,
        responses={201: EdgeSerializer},
        tags=["Edges"],
    ),
)
class EdgeListCreateView(APIView):

    def get(self, request: Request) -> Response:
        edges = Edge.objects.select_related("source", "destination").all()
        return Response(EdgeSerializer(edges, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = EdgeSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                EdgeSerializer(serializer.save()).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    delete=extend_schema(
        summary="Delete an edge",
        responses={204: OpenApiResponse(description="Deleted")},
        tags=["Edges"],
    ),
)
class EdgeDetailView(APIView):

    def _get_edge(self, edge_id: int) -> Optional[Edge]:
        try:
            return Edge.objects.get(pk=edge_id)
        except Edge.DoesNotExist:
            return None

    def delete(self, request: Request, edge_id: int) -> Response:
        edge = self._get_edge(edge_id)
        if edge is None:
            return Response(
                {"error": f"Edge with id {edge_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        edge.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Route Views
# ---------------------------------------------------------------------------

class ShortestRouteView(APIView):

    @extend_schema(
        summary="Get shortest route",
        request=RouteRequestSerializer,
        responses={200: RouteQuerySerializer},
        tags=["Routes"],
    )
    def post(self, request: Request) -> Response:
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        source_name: str = serializer.validated_data["source"]
        destination_name: str = serializer.validated_data["destination"]

        edges_qs = Edge.objects.select_related("source", "destination").all()

        edge_dicts = [
            {
                "source": e.source.name,
                "destination": e.destination.name,
                "latency": e.latency,
            }
            for e in edges_qs
        ]

        graph = build_graph(edge_dicts)

        for name in Node.objects.values_list("name", flat=True):
            graph.setdefault(name, [])

        total_latency, path = dijkstra(graph, source_name, destination_name)

        RouteQuery.objects.create(
            source=source_name,
            destination=destination_name,
            total_latency=total_latency,
            path=path or [],
        )

        if path is None:
            return Response(
                {"error": f"No path exists between {source_name} and {destination_name}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"total_latency": total_latency, "path": path},
            status=status.HTTP_200_OK,
        )


class RouteHistoryView(APIView):

    @extend_schema(
        summary="Get route history",
        parameters=[
            OpenApiParameter("source", str),
            OpenApiParameter("destination", str),
            OpenApiParameter("limit", int),
            OpenApiParameter("date_from", str),
            OpenApiParameter("date_to", str),
        ],
        responses={200: RouteQuerySerializer(many=True)},
        tags=["Routes"],
    )
    def get(self, request: Request) -> Response:
        qs = RouteQuery.objects.all()

        source = request.query_params.get("source")
        destination = request.query_params.get("destination")
        limit = request.query_params.get("limit")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if source:
            qs = qs.filter(source=source)
        if destination:
            qs = qs.filter(destination=destination)

        if date_from:
            dt = parse_datetime(date_from)
            if not dt:
                return Response({"error": "Invalid date_from"}, status=400)
            qs = qs.filter(created_at__gte=dt)

        if date_to:
            dt = parse_datetime(date_to)
            if not dt:
                return Response({"error": "Invalid date_to"}, status=400)
            qs = qs.filter(created_at__lte=dt)

        if limit:
            try:
                limit_int = int(limit)
                if limit_int <= 0:
                    raise ValueError
                qs = qs[:limit_int]
            except ValueError:
                return Response(
                    {"error": "limit must be a positive integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(RouteQuerySerializer(qs, many=True).data)