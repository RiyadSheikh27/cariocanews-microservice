from rest_framework import serializers
from .models import Zone, Bookmark

# ---- Zone Section -------------------------------------------------

class ZoneListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for recommendation list results."""

    """ Computed fields injected by the view (scoring engine output)"""
    fit_score     = serializers.FloatField(read_only=True, default=0)
    safety_pct    = serializers.FloatField(read_only=True, default=0)
    schools_pct   = serializers.FloatField(read_only=True, default=0)
    transit_pct   = serializers.FloatField(read_only=True, default=0)
    budget_pct    = serializers.FloatField(read_only=True, default=0)
    match_label   = serializers.CharField(read_only=True, default="")

    class Meta:
        model = Zone
        fields = [
            "id",
            "external_id",
            "zone_name",
            "city",
            "district",
            "neighborhoods",
            "latitude",
            "longitude",
            "market_status",
            "market_trend_12mo",
            "budget_avg_rent",
            # Scored fields
            "fit_score",
            "safety_pct",
            "schools_pct",
            "transit_pct",
            "budget_pct",
            "match_label",
        ]


class ZoneDetailSerializer(serializers.ModelSerializer):
    """Full serializer for zone detail / map popup."""

    class Meta:
        model = Zone
        fields = "__all__"