# apps/zones/validators.py
from rest_framework import serializers

PRIORITY_CHOICES = ["Not", "Somewhat", "Important", "Essential"]
COMMUTE_CHOICES  = ["metro", "bus", "car", "walk", "tram", "bike"]


class RecommendationInputSerializer(serializers.Serializer):
    country = serializers.CharField(max_length=100)
    city    = serializers.CharField(max_length=100)
    budget  = serializers.FloatField(min_value=0)

    safety_priority    = serializers.ChoiceField(choices=PRIORITY_CHOICES)
    schools_priority   = serializers.ChoiceField(choices=PRIORITY_CHOICES)
    transport_priority = serializers.ChoiceField(choices=PRIORITY_CHOICES)

    commute_preference = serializers.ChoiceField(choices=COMMUTE_CHOICES)