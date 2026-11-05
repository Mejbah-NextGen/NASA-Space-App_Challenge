from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class BaselineOutput:
    estimated_suitability: Decimal
    water_stress: Decimal
    heat_stress: Decimal
    overall_stress: Decimal
    summary: str
    input_snapshot: dict


CROP_PROFILES = {
    "rice": {"temperature": (22.0, 35.0), "rainfall": (900.0, 1800.0)},
    "jute": {"temperature": (24.0, 37.0), "rainfall": (1000.0, 2000.0)},
    "maize": {"temperature": (18.0, 32.0), "rainfall": (500.0, 900.0)},
    "wheat": {"temperature": (12.0, 26.0), "rainfall": (300.0, 650.0)},
    "potato": {"temperature": (15.0, 25.0), "rainfall": (400.0, 700.0)},
    "sesame": {"temperature": (20.0, 34.0), "rainfall": (350.0, 650.0)},
}
DEFAULT_PROFILE = {"temperature": (18.0, 32.0), "rainfall": (500.0, 1000.0)}
IRRIGATION_OFFSETS = {"NONE": 0.0, "LOW": 8.0, "MODERATE": 18.0, "HIGH": 30.0}


def _outside_range_penalty(value, lower, upper, span_factor):
    if value < lower:
        return min(100.0, (lower - value) * span_factor)
    if value > upper:
        return min(100.0, (value - upper) * span_factor)
    return 0.0


def _decimal(value):
    return Decimal(str(max(0.0, min(100.0, value)))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def run_baseline(scenario):
    crop_key = scenario.crop.name.strip().lower()
    profile = CROP_PROFILES.get(crop_key, DEFAULT_PROFILE)
    temperature = float(scenario.temperature_assumption)
    rainfall = float(scenario.rainfall_assumption)
    temp_low, temp_high = profile["temperature"]
    rain_low, rain_high = profile["rainfall"]

    heat_stress = _outside_range_penalty(temperature, temp_low, temp_high, 8.0)
    irrigation_credit = IRRIGATION_OFFSETS[scenario.irrigation_scenario]
    effective_rainfall = rainfall + irrigation_credit * 10
    water_stress = _outside_range_penalty(effective_rainfall, rain_low, rain_high, 0.12)
    overall_stress = water_stress * 0.58 + heat_stress * 0.42
    suitability = 100.0 - overall_stress

    if suitability >= 75:
        interpretation = "The assumptions fall mostly within this crop's simplified tolerance profile."
    elif suitability >= 50:
        interpretation = "The assumptions show moderate stress; compare irrigation and planting timing before deciding."
    else:
        interpretation = "The assumptions show substantial stress in this simplified model; local expert review is recommended."

    return BaselineOutput(
        estimated_suitability=_decimal(suitability),
        water_stress=_decimal(water_stress),
        heat_stress=_decimal(heat_stress),
        overall_stress=_decimal(overall_stress),
        summary=interpretation,
        input_snapshot={
            "crop": scenario.crop.name,
            "crop_profile": profile,
            "temperature_c": temperature,
            "rainfall_mm": rainfall,
            "irrigation": scenario.irrigation_scenario,
            "historical_year": scenario.historical_year,
            "season": scenario.season,
            "method": "Fixed crop tolerance ranges and transparent weighted stress penalties.",
        },
    )


def calculate_and_store(scenario):
    from .models import SimulationResult

    output = run_baseline(scenario)
    result, _ = SimulationResult.objects.update_or_create(
        scenario=scenario,
        defaults={
            "estimated_suitability": output.estimated_suitability,
            "water_stress": output.water_stress,
            "heat_stress": output.heat_stress,
            "overall_stress": output.overall_stress,
            "summary": output.summary,
            "input_snapshot": output.input_snapshot,
        },
    )
    return result

