# apps/zones/management/commands/import_zones.py
import json
import re
import os
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from apps.zones.models import Zone


# ── Helpers (module-level, not inside handle) ─────────────────────────────────

def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_str(val, default=""):
    return str(val).strip() if val is not None else default


def _parse_ratio(val):
    """
    Convert student-teacher ratio to float.
    '20:1' → 20.0  |  '20/1' → 20.0  |  20 → 20.0  |  None → None
    """
    if val is None:
        return None
    s = str(val).strip()
    # Plain number
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    # Ratio format  e.g. "20:1" or "20/1"
    m = re.match(r"(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)", s)
    if m:
        num, den = float(m.group(1)), float(m.group(2))
        return round(num / den, 2) if den else None
    return None


def _load_records(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("data", "zones", "results", "items", "records"):
            if key in raw and isinstance(raw[key], list):
                return raw[key]
        for val in raw.values():
            if isinstance(val, list):
                return val
    raise ValueError(f"Unrecognised JSON structure: type={type(raw)}")


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Import zones from tuacasaaqui_portugal_cleaned_data.json"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=None, help="Override default JSON path")

    def handle(self, *args, **options):
        json_path = options["file"] or os.path.join(
            settings.BASE_DIR, "tuacasaaqui_portugal_cleaned_data.json"
        )

        if not Path(json_path).exists():
            self.stderr.write(self.style.ERROR(f"File not found: {json_path}"))
            self.stderr.write(f"   BASE_DIR = {settings.BASE_DIR}")
            return

        self.stdout.write(f"Reading: {json_path}")

        try:
            records = _load_records(json_path)
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f"{e}"))
            return

        self.stdout.write(f"{len(records)} records found")
        if not records:
            self.stderr.write(self.style.WARNING("⚠  0 records — check file content."))
            return

        self.stdout.write(f"Keys: {list(records[0].keys())}")

        created_count = updated_count = skipped_count = 0

        for idx, rec in enumerate(records):
            try:
                loc    = rec.get("location", {})
                mkt    = rec.get("market", {})
                safety = rec.get("safety", {})
                sch    = rec.get("schools", {})
                trans  = rec.get("transport", {})
                bud    = rec.get("budget", {})

                external_id = _safe_str(rec.get("id"))
                if not external_id:
                    skipped_count += 1
                    continue

                defaults = {
                    "country":      _safe_str(rec.get("country")),
                    "district":     _safe_str(rec.get("district")),
                    "city":         _safe_str(rec.get("city")),
                    "zone_name":    _safe_str(rec.get("zone")),
                    "neighborhoods": rec.get("neighborhoods") or [],

                    "latitude":  _safe_float(loc.get("latitude")),
                    "longitude": _safe_float(loc.get("longitude")),

                    "market_avg_price_per_m2": _safe_float(mkt.get("average_price_per_m2")),
                    "market_status":           _safe_str(mkt.get("market_status"), "Unknown"),
                    "market_trend_12mo":       _safe_str(mkt.get("trend_12mo"), "0%"),

                    "safety_crime_rate":              _safe_float(safety.get("crime_rate")),
                    "safety_police_density":          _safe_float(safety.get("police_density")),
                    "safety_emergency_response_time": _safe_float(safety.get("emergency_response_time")),
                    "safety_street_light_density":    _safe_float(safety.get("street_light_density")),

                    "schools_count":                  _safe_int(sch.get("schools_count")),
                    "schools_avg_rating":             _safe_float(sch.get("avg_school_rating")),
                    "schools_student_teacher_ratio":  _parse_ratio(sch.get("student_teacher_ratio")),
                    "schools_exam_performance_index": _safe_float(sch.get("exam_performance_index")),

                    "transport_bus_stop_density": _safe_float(trans.get("bus_stop_density")),
                    "transport_metro_distance":   _safe_float(trans.get("metro_distance", -1)),
                    "transport_avg_commute_time": _safe_float(trans.get("avg_commute_time")),
                    "transport_congestion_index": _safe_float(trans.get("traffic_congestion_index")),

                    "budget_avg_rent":       _safe_float(bud.get("avg_rent")),
                    "budget_cost_of_living": _safe_float(bud.get("cost_of_living")),
                    "budget_utility_index":  _safe_float(bud.get("utility_cost_index")),
                    "budget_internet_cost":  _safe_float(bud.get("internet_cost")),

                    "livability_score": _safe_float(rec.get("livability_score")),
                }

                _, created = Zone.objects.update_or_create(
                    external_id=external_id,
                    defaults=defaults,
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                if (created_count + updated_count) % 5000 == 0:
                    self.stdout.write(f"   … {created_count + updated_count} processed")

            except Exception as exc:
                skipped_count += 1
                if skipped_count <= 10:
                    self.stderr.write(
                        self.style.WARNING(f"⚠  Skipped #{idx} ({rec.get('id','?')}): {exc}")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — Created: {created_count} | Updated: {updated_count} | Skipped: {skipped_count}"
            )
        )
        self.stdout.write(f"Total in DB: {Zone.objects.count()}")