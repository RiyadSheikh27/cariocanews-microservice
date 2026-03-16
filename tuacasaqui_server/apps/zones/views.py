from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.core.api_response import APIResponse
from .models import Zone
from .serializers import ZoneListSerializer, ZoneDetailSerializer
from .scoring import UserPreferences, rank_zones, compute_scores
from .validators import RecommendationInputSerializer


class RecommendationView(APIView):
    """
    POST /api/v1/zones/recommendations/

    Body:
        country, city, budget, safety_priority,
        schools_priority, transport_priority, commute_preference
    """

    def post(self, request):
        # ---- Validate input ---------------------------------------------
        input_ser = RecommendationInputSerializer(data=request.data)
        if not input_ser.is_valid():
            return APIResponse.error_response(
                errors=input_ser.errors,
                message="Invalid input",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        v = input_ser.validated_data

        prefs = UserPreferences(
            budget=v["budget"],
            safety_priority=v["safety_priority"],
            schools_priority=v["schools_priority"],
            transport_priority=v["transport_priority"],
            commute_preference=v["commute_preference"],
        )

        # ---- Fetch & filter zones -------------------------------------
        # Only pull columns we need → avoids loading heavy unused fields
        zones = (
            Zone.objects
            .filter(country__iexact=v["country"], city__iexact=v["city"])
            .only(
                "id", "external_id", "zone_name", "city", "district",
                "neighborhoods", "latitude", "longitude",
                "market_status", "market_trend_12mo", "budget_avg_rent",
                "safety_crime_rate", "safety_police_density",
                "safety_emergency_response_time", "safety_street_light_density",
                "schools_count", "schools_avg_rating",
                "schools_student_teacher_ratio", "schools_exam_performance_index",
                "transport_bus_stop_density", "transport_metro_distance",
                "transport_avg_commute_time", "transport_congestion_index",
                "budget_avg_rent", "budget_cost_of_living",
                "budget_utility_index", "budget_internet_cost",
                "livability_score",
            )
        )

        if not zones.exists():
            return APIResponse.error_response(
                message=f"No zones found for {v['city']}, {v['country']}",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # ---- Score & rank -------------------------------
        ranked = rank_zones(list(zones), prefs, top_n=10)

        # ---- Serialize -----------------------------------
        results      = []
        # map_markers  = []

        for rank_position, item in enumerate(ranked, start=1):
            zone   = item["zone"]
            scores = item["scores"]

            zone_data = ZoneListSerializer(zone).data
            # Inject computed scores
            zone_data.update({
                "rank":        rank_position,
                "fit_score":   scores.fit_score,
                "safety_pct":  scores.safety_pct,
                "schools_pct": scores.schools_pct,
                "transit_pct": scores.transit_pct,
                "budget_pct":  scores.budget_pct,
                "match_label": scores.match_label,
            })
            results.append(zone_data)

            # map_markers.append({
            #     "rank":      rank_position,
            #     "zone_id":   zone.id,
            #     "zone_name": zone.zone_name,
            #     "latitude":  zone.latitude,
            #     "longitude": zone.longitude,
            #     "fit_score": scores.fit_score,
            #     "match_label": scores.match_label,
            # })

        return APIResponse.success_response(
            data={
                "zones":       results,
                # "map_markers": map_markers,
                "total":       len(results),
            },
            message="Recommendations fetched successfully",
            meta={"city": v["city"], "country": v["country"]},
        )


class ZoneDetailView(APIView):
    """
    GET /api/v1/zones/<pk>/
    """

    def get(self, request, pk):
        zone = get_object_or_404(Zone, pk=pk)
        return APIResponse.success_response(
            data=ZoneDetailSerializer(zone).data,
            message="Zone detail fetched",
        )
