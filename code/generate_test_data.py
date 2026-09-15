"""
generate_test_data.py

Generates two Turtle files used as validation input alongside the ontology:

1. synthetic_price_timeseries.ttl
   A full 24-hour day-ahead price time series at the thesis's own 15-minute
   resolution (96 points), extending the single worked example already in
   the ontology (ex:PriceTimeSeries_20260810 / ex:PricePoint_0800) to a
   realistic scale. One point is deliberately set outside the EU-harmonised
   day-ahead price bounds, to demonstrate that dm:PlausiblePriceShape
   actually catches a violation rather than trivially passing everything.

2. test_fixtures.ttl
   Small, targeted individuals that exercise the remaining shapes:
     - a ManualOverride far in the future (should NOT be flagged as stale)
     - a Level3_Controllable device with no setpoint (SHOULD be flagged)
     - a ThermalZoneState with return temperature above supply temperature
       (SHOULD be flagged)

Both files use the same ex: namespace as the main ontology, so they can be
loaded together with it as one data graph.
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "generated_files"

EX = "http://www.semanticweb.org/rotter/interoperable-communication-data-model_ex#"
DM = "http://www.semanticweb.org/rotter/interoperable-communication-data-model_dm#"
CIM = "http://www.semanticweb.org/rotter/interoperable-communication-data-model_cim#"

PREFIXES = f"""
@prefix ex:   <{EX}> .
@prefix dm:   <{DM}> .
@prefix cim:  <{CIM}> .
@prefix saref: <https://saref.etsi.org/core/> .
@prefix s4ener: <https://saref.etsi.org/saref4ener/> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
"""


def generate_price_timeseries(day: str = "2026-08-11", bad_index: int = 60) -> str:
    """Build a 96-point (15-min resolution) synthetic day-ahead price curve.

    A simple two-peak shape (morning + evening) with random noise, in
    EUR/MWh. One point (bad_index) is set to an implausible value to
    exercise dm:PlausiblePriceShape.
    """
    random.seed(42)
    lines = [PREFIXES, ""]
    lines.append(f"ex:PriceTimeSeries_{day.replace('-', '')} rdf:type cim:TimeSeries .")
    lines.append("")

    for i in range(96):
        hour = (i * 15) // 60
        minute = (i * 15) % 60
        # Simple two-peak synthetic curve: base 60, +40 around 08:00, +55 around 19:00
        base = 60.0
        morning_peak = 40.0 * max(0, 1 - abs(hour - 8) / 3)
        evening_peak = 55.0 * max(0, 1 - abs(hour - 19) / 3)
        noise = random.uniform(-5, 5)
        price = round(base + morning_peak + evening_peak + noise, 1)

        if i == bad_index:
            # Deliberately implausible value to test dm:PlausiblePriceShape
            price = 5500.0

        point_name = f"PricePoint_{day.replace('-', '')}_{hour:02d}{minute:02d}"
        lines.append(f"ex:{point_name} rdf:type owl:NamedIndividual, cim:Point ;")
        lines.append(f'    dm:hasPrice "{price}"^^xsd:float .')
        lines.append(
            f"ex:PriceTimeSeries_{day.replace('-', '')} cim:TimeSeries.Point ex:{point_name} ."
        )
        lines.append("")

    return "\n".join(lines)


def generate_test_fixtures() -> str:
    """Targeted individuals exercising the ManualOverride, Level-3 setpoint,
    and ThermalZoneState plausibility shapes."""
    future_expiry = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%S")

    return f"""{PREFIXES}

### A currently-active override (expiry far in the future), should NOT
### be flagged by dm:ManualOverrideExpiryShape.
ex:Override_Future_Valid rdf:type owl:NamedIndividual, dm:ManualOverride ;
    dm:hasOverrideValue "22.0"^^xsd:float ;
    dm:hasOverrideExpiry "{future_expiry}"^^xsd:dateTime .

### A Level-3 controllable device with no setpoint, SHOULD be flagged by
### dm:Level3DeviceHasSetpointShape, since it cannot actually be dispatched.
ex:Battery_NoSetpoint_Broken rdf:type owl:NamedIndividual, s4ener:Storage ;
    dm:hasControllabilityLevel dm:Level3_Controllable .

### A thermal zone state with return temperature above supply temperature,
### physically implausible, SHOULD be flagged by
### dm:ThermalZoneStatePlausibilityShape.
ex:ThermalZoneState_Faulty_Sensor rdf:type owl:NamedIndividual, dm:ThermalZoneState ;
    dm:hasSupplyTemperature "45.0"^^xsd:float ;
    dm:hasReturnTemperature "52.0"^^xsd:float ;
    dm:isStateOf ex:DistrictHeatingNetwork_North .
"""


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    price_path = OUTPUT_DIR / "synthetic_price_timeseries.ttl"
    fixtures_path = OUTPUT_DIR / "test_fixtures.ttl"
    with open(price_path, "w", encoding="utf-8") as f:
        f.write(generate_price_timeseries())
    with open(fixtures_path, "w", encoding="utf-8") as f:
        f.write(generate_test_fixtures())
    print(f"Wrote {price_path} and {fixtures_path}")
