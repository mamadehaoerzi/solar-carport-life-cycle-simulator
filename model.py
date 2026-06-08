"""Calculation model for the Solar Carport Life-Cycle Simulator."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from assumptions import (
    EMBODIED_CO2_FACTORS,
    IMPACT_CATEGORY_UNITS,
    REPLACEMENT_COSTS_EUR,
    SAMPLE_IMPACT_CONTRIBUTIONS,
    SCENARIO_MULTIPLIERS,
)


@dataclass(frozen=True)
class SimulationResult:
    inputs: dict
    energy: dict
    economics: dict
    co2: dict
    circularity: dict
    replacement_events: pd.DataFrame
    cash_flow: pd.DataFrame
    component_co2: pd.DataFrame
    impact_summary: pd.DataFrame
    impact_contributions: pd.DataFrame


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def factor_value(component: str, embodied_factors: dict | None = None) -> float:
    factors = embodied_factors or EMBODIED_CO2_FACTORS
    return float(factors[component]["value"])


def calculate_component_co2(
    inputs: dict,
    embodied_multiplier: float = 1.0,
    embodied_factors: dict | None = None,
) -> pd.DataFrame:
    pv = inputs["pv_capacity_kwp"] * factor_value("PV modules", embodied_factors)
    battery = inputs["battery_capacity_kwh"] * factor_value("Battery", embodied_factors)
    inverter = inputs["pv_capacity_kwp"] * factor_value("Inverter", embodied_factors)
    chargers = inputs["number_of_ev_chargers"] * factor_value("EV chargers", embodied_factors)
    steel = inputs["steel_structure_kg"] * factor_value("Steel structure", embodied_factors)
    concrete = inputs["concrete_ballast_kg"] * factor_value("Concrete ballast", embodied_factors)
    bos = factor_value("Cables and BOS", embodied_factors)

    rows = [
        ("PV modules", pv),
        ("Battery", battery),
        ("Inverter", inverter),
        ("EV chargers", chargers),
        ("Steel structure", steel),
        ("Concrete ballast", concrete),
        ("Cables and BOS", bos),
    ]
    frame = pd.DataFrame(rows, columns=["Component", "Embodied CO2 (kg CO2-eq)"])
    frame["Embodied CO2 (kg CO2-eq)"] *= embodied_multiplier
    return frame


def calculate_replacement_events(
    inputs: dict,
    component_co2: pd.DataFrame,
    cost_multiplier: float = 1.0,
) -> pd.DataFrame:
    component_lookup = component_co2.set_index("Component")["Embodied CO2 (kg CO2-eq)"].to_dict()
    lifetime = inputs["project_lifetime_years"]
    rows = []

    if inputs.get("include_battery_replacement", True):
        battery_units = max(1, int(inputs.get("battery_replacement_units_per_event", 1)))
        unit_word = "unit" if battery_units == 1 else "units"
        for year in interval_years(
            inputs.get("battery_replacement_interval_years", inputs.get("battery_replacement_year", 10)),
            lifetime,
            True,
        ):
            rows.append(
                {
                    "Year": year,
                    "Event": f"Battery replacement ({battery_units} {unit_word})",
                    "Impact component": "Battery",
                    "Units replaced": battery_units,
                    "Replacement fraction": float(battery_units),
                    "Cost (EUR)": REPLACEMENT_COSTS_EUR["Battery"] * battery_units * cost_multiplier,
                    "CO2 (kg CO2-eq)": component_lookup["Battery"] * battery_units,
                }
            )

    if inputs.get("include_inverter_replacement", False):
        inverter_units = max(1, int(inputs.get("inverter_replacement_units_per_event", 1)))
        unit_word = "unit" if inverter_units == 1 else "units"
        for year in interval_years(
            inputs.get("inverter_replacement_interval_years", inputs.get("inverter_replacement_year", 12)),
            lifetime,
            True,
        ):
            rows.append(
                {
                    "Year": year,
                    "Event": f"Inverter replacement ({inverter_units} {unit_word})",
                    "Impact component": "Inverter",
                    "Units replaced": inverter_units,
                    "Replacement fraction": float(inverter_units),
                    "Cost (EUR)": REPLACEMENT_COSTS_EUR["Inverter"] * inverter_units * cost_multiplier,
                    "CO2 (kg CO2-eq)": component_lookup["Inverter"] * inverter_units,
                }
            )

    if inputs.get("include_charger_replacement", False):
        charger_count = max(1, int(inputs.get("number_of_ev_chargers", 1)))
        charger_units = max(1, int(inputs.get("charger_replacement_units_per_event", 1)))
        charger_units = min(charger_units, charger_count)
        charger_fraction = charger_units / charger_count
        for year in interval_years(
            inputs.get("charger_replacement_interval_years", inputs.get("charger_replacement_year", 15)),
            lifetime,
            True,
        ):
            rows.append(
                {
                    "Year": year,
                    "Event": f"EV charger replacement ({charger_units} of {charger_count} units)",
                    "Impact component": "EV chargers",
                    "Units replaced": charger_units,
                    "Replacement fraction": charger_fraction,
                    "Cost (EUR)": REPLACEMENT_COSTS_EUR["EV chargers"] * charger_fraction * cost_multiplier,
                    "CO2 (kg CO2-eq)": component_lookup["EV chargers"] * charger_fraction,
                }
            )

    for year in interval_years(
        inputs.get("steel_replacement_interval_years", 10),
        lifetime,
        inputs.get("include_steel_partial_replacement", False),
    ):
        fraction = inputs.get("steel_replacement_fraction", 0.0)
        rows.append(
            {
                "Year": year,
                "Event": "Partial steel-structure repair",
                "Impact component": "Steel structure",
                "Units replaced": None,
                "Replacement fraction": fraction,
                "Cost (EUR)": inputs.get("steel_partial_replacement_cost_eur", 0.0) * cost_multiplier,
                "CO2 (kg CO2-eq)": component_lookup["Steel structure"] * fraction,
            }
        )

    cables_bos = component_lookup.get("Cables and BOS", 0.0)
    power_cable_share = 116.74 / (116.74 + 753.49)
    wear_parts_share = 753.49 / (116.74 + 753.49)
    for year in interval_years(
        inputs.get("cable_replacement_interval_years", 10),
        lifetime,
        inputs.get("include_cable_partial_replacement", False),
    ):
        fraction = inputs.get("cable_replacement_fraction", 0.0)
        rows.append(
            {
                "Year": year,
                "Event": "Partial external power-cable replacement",
                "Impact component": "Power cables",
                "Units replaced": None,
                "Replacement fraction": fraction,
                "Cost (EUR)": inputs.get("cable_partial_replacement_cost_eur", 0.0) * cost_multiplier,
                "CO2 (kg CO2-eq)": cables_bos * power_cable_share * fraction,
            }
        )

    for year in interval_years(
        inputs.get("wear_parts_replacement_interval_years", 5),
        lifetime,
        inputs.get("include_wear_parts_replacement", False),
    ):
        fraction = inputs.get("wear_parts_replacement_fraction", 0.0)
        rows.append(
            {
                "Year": year,
                "Event": "Fasteners/connectors wear-part replacement",
                "Impact component": "Fasteners/connectors",
                "Units replaced": None,
                "Replacement fraction": fraction,
                "Cost (EUR)": inputs.get("wear_parts_replacement_cost_eur", 0.0) * cost_multiplier,
                "CO2 (kg CO2-eq)": cables_bos * wear_parts_share * fraction,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "Year",
                "Event",
                "Impact component",
                "Units replaced",
                "Replacement fraction",
                "Cost (EUR)",
                "CO2 (kg CO2-eq)",
            ]
        )
    return pd.DataFrame(rows).sort_values("Year").reset_index(drop=True)


def interval_years(interval: int | float, lifetime: int | float, enabled: bool) -> list[int]:
    if not enabled:
        return []
    interval = int(interval)
    lifetime = int(lifetime)
    if interval <= 0:
        return []
    return list(range(interval, lifetime + 1, interval))


def calculate_impact_contributions(
    replacement_events: pd.DataFrame,
    impact_contribution_factors: dict | None = None,
    impact_units: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    contribution_source = impact_contribution_factors or SAMPLE_IMPACT_CONTRIBUTIONS
    units = impact_units or IMPACT_CATEGORY_UNITS
    rows = []
    for category, components in contribution_source.items():
        for component, value in components.items():
            rows.append(
                {
                    "Stage": "Reference baseline",
                    "Impact category": category,
                    "Component": component,
                    "Value": value,
                    "Unit": units.get(category, ""),
                }
            )

    if not replacement_events.empty:
        for _, event in replacement_events.iterrows():
            component = event["Impact component"]
            fraction = float(event["Replacement fraction"])
            for category, components in contribution_source.items():
                if component not in components:
                    continue
                rows.append(
                    {
                        "Stage": f"Replacement year {int(event['Year'])}",
                        "Impact category": category,
                        "Component": component,
                        "Value": components[component] * fraction,
                        "Unit": units.get(category, ""),
                    }
                )

    contributions = pd.DataFrame(rows)
    if contributions.empty:
        return (
            pd.DataFrame(
                columns=[
                    "Impact category",
                    "Reference baseline",
                    "Replacement additions",
                    "Total with selected replacements",
                    "Unit",
                    "Main hotspot",
                ]
            ),
            pd.DataFrame(columns=["Stage", "Impact category", "Component", "Value", "Unit"]),
        )
    summary_rows = []
    for category, group in contributions.groupby("Impact category", sort=False):
        baseline_total = group.loc[group["Stage"] == "Reference baseline", "Value"].sum()
        replacement_total = group.loc[group["Stage"] != "Reference baseline", "Value"].sum()
        by_component = group.groupby("Component")["Value"].sum().sort_values(ascending=False)
        summary_rows.append(
            {
                "Impact category": category,
                "Reference baseline": baseline_total,
                "Replacement additions": replacement_total,
                "Total with selected replacements": baseline_total + replacement_total,
                "Unit": units.get(category, ""),
                "Main hotspot": by_component.index[0],
            }
        )
    return pd.DataFrame(summary_rows), contributions


def calculate_circularity_score(inputs: dict) -> dict:
    weights = {
        "Metals": 0.35,
        "Concrete": 0.15,
        "Battery": 0.30,
        "Electronics": 0.20,
    }
    rates = {
        "Metals": inputs["metal_recycling_rate"],
        "Concrete": inputs["concrete_recycling_rate"],
        "Battery": inputs["battery_recovery_rate"],
        "Electronics": inputs["electronics_recovery_rate"],
    }
    score = sum(rates[name] * weights[name] for name in weights) * 100
    return {
        "score": score,
        "rates": rates,
        "weights": weights,
    }


def calculate_cash_flow(
    inputs: dict,
    annual_benefit: float,
    replacement_events: pd.DataFrame,
) -> pd.DataFrame:
    lifetime = int(inputs["project_lifetime_years"])
    discount_rate = inputs["discount_rate"]
    annual_om_cost = inputs["initial_investment_eur"] * inputs.get("om_rate", 0.0)
    rows = []
    cumulative = -inputs["initial_investment_eur"]
    discounted_cumulative = -inputs["initial_investment_eur"]

    rows.append(
        {
            "Year": 0,
            "Annual net cash flow (EUR)": -inputs["initial_investment_eur"],
            "Annual electricity benefit (EUR)": 0.0,
            "Annual O&M cost (EUR)": 0.0,
            "Replacement cost (EUR)": 0.0,
            "Cumulative cash flow (EUR)": cumulative,
            "Discounted cumulative cash flow (EUR)": discounted_cumulative,
        }
    )

    replacement_costs = replacement_events.groupby("Year")["Cost (EUR)"].sum().to_dict()
    for year in range(1, lifetime + 1):
        replacement_cost = replacement_costs.get(year, 0.0)
        annual_net = annual_benefit - annual_om_cost - replacement_cost
        cumulative += annual_net
        discounted_cumulative += annual_net / ((1 + discount_rate) ** year)
        rows.append(
            {
                "Year": year,
                "Annual net cash flow (EUR)": annual_net,
                "Annual electricity benefit (EUR)": annual_benefit,
                "Annual O&M cost (EUR)": annual_om_cost,
                "Replacement cost (EUR)": replacement_cost,
                "Cumulative cash flow (EUR)": cumulative,
                "Discounted cumulative cash flow (EUR)": discounted_cumulative,
            }
        )

    return pd.DataFrame(rows)


def run_simulation(
    inputs: dict,
    scenario_name: str = "Baseline",
    embodied_factors: dict | None = None,
    impact_contribution_factors: dict | None = None,
    impact_units: dict | None = None,
) -> SimulationResult:
    scenario = SCENARIO_MULTIPLIERS[scenario_name]
    adjusted = dict(inputs)
    adjusted["annual_pv_yield_kwh_per_kwp"] *= scenario["pv_yield"]
    adjusted["self_consumption_ratio"] = clamp(
        adjusted["self_consumption_ratio"] * scenario["self_consumption"], 0.0, 1.0
    )
    adjusted["exported_electricity_ratio"] = clamp(1.0 - adjusted["self_consumption_ratio"], 0.0, 1.0)
    adjusted["electricity_value_eur_per_kwh"] *= scenario["electricity_value"]

    annual_pv_generation = (
        adjusted["pv_capacity_kwp"]
        * adjusted["annual_pv_yield_kwh_per_kwp"]
        * adjusted.get("site_adjustment_factor", 1.0)
    )
    annual_charging_demand = (
        adjusted["charging_points"]
        * adjusted["charging_sessions_per_day"]
        * adjusted["avg_charging_energy_kwh"]
        * adjusted["operating_days_per_year"]
    )
    self_consumed_pv = annual_pv_generation * adjusted["self_consumption_ratio"]
    exported_pv = annual_pv_generation * adjusted["exported_electricity_ratio"]
    demand_coverage = self_consumed_pv / annual_charging_demand if annual_charging_demand else np.nan
    annual_benefit = (
        self_consumed_pv * adjusted["electricity_value_eur_per_kwh"]
        + exported_pv * adjusted["export_tariff_eur_per_kwh"]
    )
    annual_avoided_co2 = self_consumed_pv * adjusted["grid_emission_factor_kgco2_per_kwh"]

    component_co2 = calculate_component_co2(adjusted, scenario["embodied_co2"], embodied_factors)
    replacement_events = calculate_replacement_events(
        adjusted,
        component_co2,
        scenario["replacement_cost"],
    )
    impact_summary, impact_contributions = calculate_impact_contributions(
        replacement_events,
        impact_contribution_factors,
        impact_units,
    )
    cash_flow = calculate_cash_flow(adjusted, annual_benefit, replacement_events)

    initial_embodied_co2 = component_co2["Embodied CO2 (kg CO2-eq)"].sum()
    replacement_co2 = replacement_events["CO2 (kg CO2-eq)"].sum()
    total_lifecycle_co2 = initial_embodied_co2 + replacement_co2
    lifetime_pv_generation = (
        adjusted["pv_capacity_kwp"]
        * adjusted["annual_pv_yield_kwh_per_kwp"]
        * adjusted.get("lca_lifetime_years", adjusted["project_lifetime_years"])
    )
    lifetime_avoided_co2 = annual_avoided_co2 * adjusted.get(
        "lca_lifetime_years", adjusted["project_lifetime_years"]
    )
    embodied_intensity = (
        total_lifecycle_co2 * 1000 / lifetime_pv_generation if lifetime_pv_generation else np.nan
    )
    hotspot = component_co2.sort_values("Embodied CO2 (kg CO2-eq)", ascending=False).iloc[0]

    return SimulationResult(
        inputs=adjusted,
        energy={
            "Annual PV generation (kWh)": annual_pv_generation,
            "Annual charging demand (kWh)": annual_charging_demand,
            "Self-consumed PV energy (kWh)": self_consumed_pv,
            "Exported PV energy (kWh)": exported_pv,
            "Grid electricity required (kWh)": max(annual_charging_demand - self_consumed_pv, 0.0),
            "Charging demand coverage (%)": demand_coverage * 100,
            "Lifetime PV generation for LCA normalisation (kWh)": lifetime_pv_generation,
        },
        economics={
            "Initial investment excl. VAT (EUR)": adjusted.get(
                "initial_investment_net_eur", adjusted["initial_investment_eur"]
            ),
            "VAT included in investment": adjusted.get("include_vat_in_investment", False),
            "VAT rate (%)": adjusted.get("vat_rate", 0.0) * 100,
            "VAT amount included (EUR)": adjusted.get("vat_amount_eur", 0.0),
            "Initial investment used in model (EUR)": adjusted["initial_investment_eur"],
            "Annual electricity benefit (EUR)": annual_benefit,
            "Annual O&M cost (EUR)": adjusted["initial_investment_eur"] * adjusted.get("om_rate", 0.0),
            "Annual net cash flow before replacement (EUR)": (
                annual_benefit - adjusted["initial_investment_eur"] * adjusted.get("om_rate", 0.0)
            ),
            "Analysis-period cumulative cash flow (EUR)": cash_flow["Cumulative cash flow (EUR)"].iloc[-1],
            "Analysis-period discounted cumulative cash flow (EUR)": cash_flow[
                "Discounted cumulative cash flow (EUR)"
            ].iloc[-1],
        },
        co2={
            "Initial embodied CO2 (kg CO2-eq)": initial_embodied_co2,
            "Replacement CO2 (kg CO2-eq)": replacement_co2,
            "Annual avoided CO2 (kg CO2-eq)": annual_avoided_co2,
            "Lifetime avoided CO2 (kg CO2-eq)": lifetime_avoided_co2,
            "Total simplified life-cycle CO2 (kg CO2-eq)": total_lifecycle_co2,
            "Embodied intensity (g CO2-eq/kWh PV)": embodied_intensity,
            "Main environmental hotspot": hotspot["Component"],
        },
        circularity=calculate_circularity_score(adjusted),
        replacement_events=replacement_events,
        cash_flow=cash_flow,
        component_co2=component_co2,
        impact_summary=impact_summary,
        impact_contributions=impact_contributions,
    )


def build_scenario_comparison(inputs: dict, embodied_factors: dict | None = None) -> pd.DataFrame:
    rows = []
    for name in SCENARIO_MULTIPLIERS:
        result = run_simulation(inputs, name, embodied_factors)
        rows.append(
            {
                "Scenario": name,
                "PV generation (kWh/year)": result.energy["Annual PV generation (kWh)"],
                "Demand coverage (%)": result.energy["Charging demand coverage (%)"],
                "Annual benefit (EUR/year)": result.economics["Annual electricity benefit (EUR)"],
                "Analysis-period cash flow (EUR)": result.economics[
                    "Analysis-period cumulative cash flow (EUR)"
                ],
                "Embodied CO2 incl. replacements (kg CO2-eq)": result.co2[
                    "Total simplified life-cycle CO2 (kg CO2-eq)"
                ],
                "Hotspot": result.co2["Main environmental hotspot"],
            }
        )
    return pd.DataFrame(rows)
