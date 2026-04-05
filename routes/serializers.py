"""
DRF Serializers for Network Route Optimization API.

Each serializer handles validation, error messaging, and
object creation/representation for its respective model.
"""

from rest_framework import serializers

from .models import Edge, Node, RouteQuery


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class NodeSerializer(serializers.ModelSerializer):
    """Serializer for Node create + list/detail responses."""

    class Meta:
        model = Node
        fields = ["id", "name"]

    def validate_name(self, value: str) -> str:
        """Reject blank names and duplicates."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Node name must not be blank.")
        if Node.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"A node named '{value}' already exists."
            )
        return value


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------

class EdgeSerializer(serializers.ModelSerializer):
    """
    Serializer for Edge create + list/detail responses.

    Accepts 'source' and 'destination' as node *names* in the request body
    and returns them as node names in the response.
    """

    source = serializers.CharField()
    destination = serializers.CharField()

    class Meta:
        model = Edge
        fields = ["id", "source", "destination", "latency"]

    # ------------------------------------------------------------------
    # Field-level validation
    # ------------------------------------------------------------------

    def validate_latency(self, value: float) -> float:
        if value <= 0:
            raise serializers.ValidationError("Latency must be greater than 0.")
        return value

    # ------------------------------------------------------------------
    # Object-level validation (cross-field checks)
    # ------------------------------------------------------------------

    def validate(self, attrs: dict) -> dict:
        source_name = attrs["source"]
        destination_name = attrs["destination"]
        latency = attrs["latency"]

        # Resolve source node
        try:
            source_node = Node.objects.get(name=source_name)
        except Node.DoesNotExist:
            raise serializers.ValidationError(
                {"source": f"Node '{source_name}' does not exist."}
            )

        # Resolve destination node
        try:
            destination_node = Node.objects.get(name=destination_name)
        except Node.DoesNotExist:
            raise serializers.ValidationError(
                {"destination": f"Node '{destination_name}' does not exist."}
            )

        # Reject self-loops
        if source_node == destination_node:
            raise serializers.ValidationError(
                "Source and destination must be different nodes."
            )

        # Reject duplicate edges
        if Edge.objects.filter(
            source=source_node, destination=destination_node
        ).exists():
            raise serializers.ValidationError(
                f"An edge from '{source_name}' to '{destination_name}' already exists."
            )

        # Store resolved model instances for use in create()
        attrs["source_node"] = source_node
        attrs["destination_node"] = destination_node
        return attrs

    def create(self, validated_data: dict) -> Edge:
        source_node = validated_data.pop("source_node")
        destination_node = validated_data.pop("destination_node")
        # Remove the raw name strings before creating the model instance
        validated_data.pop("source")
        validated_data.pop("destination")
        return Edge.objects.create(
            source=source_node,
            destination=destination_node,
            **validated_data,
        )

    def to_representation(self, instance: Edge) -> dict:
        """Return node names (not PKs) in the response."""
        return {
            "id": instance.id,
            "source": instance.source.name,
            "destination": instance.destination.name,
            "latency": instance.latency,
        }


# ---------------------------------------------------------------------------
# Route (shortest-path request)
# ---------------------------------------------------------------------------

class RouteRequestSerializer(serializers.Serializer):
    """Validates the body of POST /routes/shortest."""

    source = serializers.CharField()
    destination = serializers.CharField()

    def validate_source(self, value: str) -> str:
        if not Node.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"Node '{value}' does not exist.")
        return value

    def validate_destination(self, value: str) -> str:
        if not Node.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"Node '{value}' does not exist.")
        return value


# ---------------------------------------------------------------------------
# RouteQuery (history record)
# ---------------------------------------------------------------------------

class RouteQuerySerializer(serializers.ModelSerializer):
    """Read-only serializer for GET /routes/history entries."""

    class Meta:
        model = RouteQuery
        fields = ["id", "source", "destination", "total_latency", "path", "created_at"]