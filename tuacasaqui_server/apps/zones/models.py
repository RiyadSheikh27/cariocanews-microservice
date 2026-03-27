from django.db import models
from django.contrib.postgres.fields import ArrayField
 
from apps.core.models import TimeStampedModel
 
# ---- Zone Section ----------------------------------------------------

class Zone(TimeStampedModel):
    """
    Represents a single zone/area record imported from the JSON dataset.
    All monetary values are in EUR.  Area values are in m².
    """
 

    external_id = models.CharField(max_length=20, unique=True, db_index=True)
    country     = models.CharField(max_length=100, db_index=True)
    district    = models.CharField(max_length=100, db_index=True)
    city        = models.CharField(max_length=100, db_index=True)
    zone_name   = models.CharField(max_length=200)
    neighborhoods = ArrayField(
        models.CharField(max_length=200), blank=True, default=list
    )
 

    # Geography
    latitude  = models.FloatField()
    longitude = models.FloatField()
 
    # Market (EUR / m²)
    market_avg_price_per_m2 = models.FloatField(default=0)   # EUR/m^2
    market_status           = models.CharField(max_length=50, default="Unknown")
    market_trend_12mo       = models.CharField(max_length=20, default="0%")
 
    # Safety
    safety_crime_rate              = models.FloatField(default=0)
    safety_police_density          = models.FloatField(default=0)
    safety_emergency_response_time = models.FloatField(default=0)
    safety_street_light_density    = models.FloatField(default=0)
 
    # Schools
    schools_count              = models.IntegerField(default=0)
    schools_avg_rating         = models.FloatField(default=0)
    schools_student_teacher_ratio = models.FloatField(null=True, blank=True)
    schools_exam_performance_index = models.FloatField(default=0)
 
    # Transport 
    transport_bus_stop_density      = models.FloatField(default=0)
    transport_metro_distance        = models.FloatField(default=-1)   # metres; -1 = no metro
    transport_avg_commute_time      = models.FloatField(default=0)    # minutes
    transport_congestion_index      = models.FloatField(default=0)
 
    # Budget (EUR)
    budget_avg_rent       = models.FloatField(default=0)   # EUR/month
    budget_cost_of_living = models.FloatField(default=0)   # EUR/month
    budget_utility_index  = models.FloatField(default=0)   # index 0-100
    budget_internet_cost  = models.FloatField(default=0)   # EUR/month
 
    # Overall
    livability_score = models.FloatField(default=0)         # 0-10
 
    class Meta:
        ordering = ["-livability_score"]
        indexes = [
            models.Index(fields=["country", "city"]),
            models.Index(fields=["budget_avg_rent"]),
        ]
 
    def __str__(self):
        return f"{self.zone_name} — {self.city}, {self.country}"

# ---- Bookmark Section ----------------------------------------------------  
class Bookmark(TimeStampedModel):
    """
    Stores a user's bookmarked zone.
    Auth will be wired later — for now session_key acts as user identifier.
    """
    session_key = models.CharField(max_length=100, db_index=True)
    zone        = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="bookmarks")
 
    class Meta:
        unique_together = ("session_key", "zone")
        ordering = ["-created_at"]
 
    def __str__(self):
        return f"[{self.session_key}] → {self.zone.zone_name}"