from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.core.api_response import APIResponse
from .models import Zone, Bookmark
from .serializers import ZoneListSerializer, ZoneDetailSerializer, BookmarkSerializer
from .scoring import UserPreferences, rank_zones, compute_scores
from .validators import RecommendationInputSerializer

# --- Constants & Helpers ------------------------------------------------

ZONE_ONLY_FIELDS = (
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
 
 
def _build_zone_payload(zone, scores, rank=None):
    """Build the standard zone dict used across all endpoints."""
    data = ZoneListSerializer(zone).data
    data.update({
        "fit_score":   scores.fit_score,
        "safety_pct":  scores.safety_pct,
        "schools_pct": scores.schools_pct,
        "transit_pct": scores.transit_pct,
        "budget_pct":  scores.budget_pct,
        "match_label": scores.match_label,
    })
    if rank is not None:
        data["rank"] = rank
    return data
 
 
def _default_prefs():
    """Neutral preferences used when no scoring context is available (bookmarks/compare)."""
    return UserPreferences(
        budget=0,
        safety_priority="Important",
        schools_priority="Important",
        transport_priority="Important",
        commute_preference="bus",
    )
 
 # --- Zone Recommendation & Detail Views ------------------------------------------------

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

        # ---- Fetch & filter zones --------------------------------------
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

# ---- Other views (e.g. Bookmark management) would go here ------------------------------------------------

class BookmarkListView(APIView):
    """
    GET  /api/v1/zones/bookmarks/
    POST /api/v1/zones/bookmarks/
    """
 
    def _session_key(self, request):
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key
 
    def get(self, request):
        key = self._session_key(request)
        bms = (
            Bookmark.objects
            .filter(session_key=key)
            .select_related("zone")
            .order_by("-created_at")
        )
 
        # Return same shape as recommendation list
        prefs   = _default_prefs()
        results = []
        map_markers = []
 
        for bm in bms:
            zone   = bm.zone
            scores = compute_scores(zone, prefs)
            payload = _build_zone_payload(zone, scores)
            payload["bookmark_id"]         = bm.id
            payload["bookmarked_at"]        = bm.created_at
            results.append(payload)
            map_markers.append({
                "bookmark_id": bm.id,
                "zone_id":     zone.id,
                "zone_name":   zone.zone_name,
                "latitude":    zone.latitude,
                "longitude":   zone.longitude,
                "fit_score":   scores.fit_score,
                "match_label": scores.match_label,
            })
 
        return APIResponse.success_response(
            data={"zones": results, "map_markers": map_markers, "total": len(results)},
            message="Bookmarks fetched",
        )
 
    def post(self, request):
        key     = self._session_key(request)
        zone_id = request.data.get("zone_id")
 
        if not zone_id:
            return APIResponse.error_response(
                errors={"zone_id": ["This field is required."]},
                message="zone_id is required",
            )
 
        zone = get_object_or_404(Zone, pk=zone_id)
        bm, created = Bookmark.objects.get_or_create(session_key=key, zone=zone)
 
        if not created:
            return APIResponse.error_response(
                message="Zone already bookmarked",
                status_code=status.HTTP_409_CONFLICT,
            )
 
        prefs   = _default_prefs()
        scores  = compute_scores(zone, prefs)
        payload = _build_zone_payload(zone, scores)
        payload["bookmark_id"]  = bm.id
        payload["bookmarked_at"] = bm.created_at
 
        return APIResponse.success_response(
            data=payload,
            message="Bookmark added",
            status_code=status.HTTP_201_CREATED,
        )
 
 
class BookmarkDetailView(APIView):
    """
    GET    /api/v1/zones/bookmarks/<pk>/
    DELETE /api/v1/zones/bookmarks/<pk>/
    """
 
    def _session_key(self, request):
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key
 
    def get(self, request, pk):
        key = self._session_key(request)
        bm  = get_object_or_404(Bookmark, pk=pk, session_key=key)
 
        prefs   = _default_prefs()
        scores  = compute_scores(bm.zone, prefs)
        payload = _build_zone_payload(bm.zone, scores)
        payload["bookmark_id"]  = bm.id
        payload["bookmarked_at"] = bm.created_at
 
        return APIResponse.success_response(
            data=payload,
            message="Bookmark detail fetched",
        )
 
    def delete(self, request, pk):
        key = self._session_key(request)
        bm  = get_object_or_404(Bookmark, pk=pk, session_key=key)
        bm.delete()
        return APIResponse.success_response(message="Bookmark removed")
    
# ── Zone Detail ───────────────────────────────────────────────────────────────
 
class ZoneDetailView(APIView):
    """GET /api/v1/zones/<pk>/"""
 
    def get(self, request, pk):
        zone = get_object_or_404(Zone, pk=pk)
        return APIResponse.success_response(
            data=ZoneDetailSerializer(zone).data,
            message="Zone detail fetched",
        )
 
 
# ── Compare ───────────────────────────────────────────────────────────────────
 
class ZoneCompareView(APIView):
    """
    POST /api/v1/zones/compare/
 
    Body:
        zone_ids: [12, 47]          — 2 to 4 zone PKs
    """
 
    def post(self, request):
        zone_ids = request.data.get("zone_ids", [])
 
        if not isinstance(zone_ids, list) or len(zone_ids) < 2:
            return APIResponse.error_response(
                errors={"zone_ids": ["Provide at least 2 zone IDs to compare."]},
                message="Invalid input",
            )
 
        if len(zone_ids) > 4:
            return APIResponse.error_response(
                errors={"zone_ids": ["Maximum 4 zones can be compared at once."]},
                message="Invalid input",
            )
 
        zones = list(Zone.objects.filter(pk__in=zone_ids).only(*ZONE_ONLY_FIELDS))
 
        if len(zones) != len(zone_ids):
            found_ids = [z.id for z in zones]
            missing   = [z for z in zone_ids if z not in found_ids]
            return APIResponse.error_response(
                errors={"zone_ids": [f"Zone IDs not found: {missing}"]},
                message="One or more zones not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
 
        prefs = _default_prefs()
 
        compared_zones = []
        for zone in zones:
            scores = compute_scores(zone, prefs)
            compared_zones.append({
                "zone_id":     zone.id,
                "zone_name":   zone.zone_name,
                "fit_score":   scores.fit_score,
                "safety_pct":  scores.safety_pct,
                "schools_pct": scores.schools_pct,
                "transit_pct": scores.transit_pct,
                "budget_pct":  scores.budget_pct,
                "match_label": scores.match_label,
            })
 
        return APIResponse.success_response(
            data=compared_zones,
            message="Comparison fetched successfully",
        )
 
