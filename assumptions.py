"""Default assumptions for the Solar Carport Life-Cycle Simulator.

This public version ships only with illustrative sample assumptions. It does
not include data exported from any licensed life-cycle inventory database.
Users can import their own authorized factors through the app sidebar.
"""

DEFAULT_INPUTS = {
    "scenario_name": "Baseline",
    "pv_capacity_kwp": 10.38,
    "annual_pv_yield_kwh_per_kwp": 1200.0,
    "site_adjustment_factor": 0.90,
    "battery_capacity_kwh": 11.04,
    "number_of_ev_chargers": 2,
    "charging_points": 3,
    "avg_charging_energy_kwh": 20.0,
    "charging_sessions_per_day": 2.0,
    "operating_days_per_year": 365,
    "self_consumption_ratio": 0.70,
    "exported_electricity_ratio": 0.30,
    "electricity_value_eur_per_kwh": 0.25,
    "export_tariff_eur_per_kwh": 0.10,
    "grid_emission_factor_kgco2_per_kwh": 0.30,
    "project_lifetime_years": 20,
    "lca_lifetime_years": 25,
    "initial_investment_net_eur": 81740.0,
    "include_vat_in_investment": False,
    "vat_rate": 0.22,
    "initial_investment_eur": 81740.0,
    "om_rate": 0.01,
    "include_battery_replacement": True,
    "include_inverter_replacement": False,
    "include_charger_replacement": False,
    "battery_replacement_interval_years": 10,
    "battery_replacement_units_per_event": 1,
    "inverter_replacement_interval_years": 12,
    "inverter_replacement_units_per_event": 1,
    "charger_replacement_interval_years": 15,
    "charger_replacement_units_per_event": 1,
    "include_steel_partial_replacement": False,
    "steel_replacement_interval_years": 10,
    "steel_replacement_fraction": 0.10,
    "steel_partial_replacement_cost_eur": 1000.0,
    "include_cable_partial_replacement": False,
    "cable_replacement_interval_years": 10,
    "cable_replacement_fraction": 0.20,
    "cable_partial_replacement_cost_eur": 500.0,
    "include_wear_parts_replacement": False,
    "wear_parts_replacement_interval_years": 5,
    "wear_parts_replacement_fraction": 0.10,
    "wear_parts_replacement_cost_eur": 400.0,
    "battery_replacement_year": 10,
    "inverter_replacement_year": 12,
    "charger_replacement_year": 15,
    "discount_rate": 0.03,
    "steel_structure_kg": 1419.610,
    "concrete_ballast_kg": 2610.0,
    "ev_charger_mass_kg_each": 76.0,
    "pv_module_mass_kg": 487.5,
    "battery_mass_kg": 167.0,
    "inverter_mass_kg": 24.0,
    "external_power_cables_kg": 22.275,
    "fasteners_connectors_kg": 97.202,
    "other_components_kg": 119.477,
    "metal_recycling_rate": 0.85,
    "concrete_recycling_rate": 0.55,
    "battery_recovery_rate": 0.65,
    "electronics_recovery_rate": 0.60,
}


EMBODIED_CO2_FACTORS = {
    "PV modules": {"value": 600.0, "unit": "kg CO2-eq/kWp"},
    "Battery": {"value": 150.0, "unit": "kg CO2-eq/kWh"},
    "Inverter": {"value": 80.0, "unit": "kg CO2-eq/kW"},
    "EV chargers": {"value": 500.0, "unit": "kg CO2-eq/charger"},
    "Steel structure": {"value": 2.5, "unit": "kg CO2-eq/kg"},
    "Concrete ballast": {"value": 0.12, "unit": "kg CO2-eq/kg"},
    "Cables and BOS": {"value": 1000.0, "unit": "fixed kg CO2-eq"},
}


REPLACEMENT_COSTS_EUR = {
    "Battery": 5000.0,
    "Inverter": 2500.0,
    "EV chargers": 8000.0,
}


IMPACT_CATEGORY_UNITS = {
    "Climate change / GWP100": "kg CO2-eq",
    "Acidification": "mol H+-eq",
    "Energy resources, non-renewable": "MJ NCV",
    "Freshwater eutrophication": "kg P-eq",
}


SAMPLE_IMPACT_CONTRIBUTIONS = {
    "Climate change / GWP100": {
        "EV chargers": 1000.0,
        "PV modules": 6200.0,
        "Steel structure": 2600.0,
        "Battery": 1650.0,
        "Fasteners/connectors": 350.0,
        "Inverter": 500.0,
        "Power cables": 180.0,
        "Concrete ballast": 310.0,
    },
    "Acidification": {
        "EV chargers": 6.0,
        "PV modules": 32.0,
        "Steel structure": 12.0,
        "Battery": 10.0,
        "Fasteners/connectors": 1.2,
        "Inverter": 2.0,
        "Power cables": 1.5,
        "Concrete ballast": 0.8,
    },
    "Energy resources, non-renewable": {
        "EV chargers": 12000.0,
        "PV modules": 90000.0,
        "Steel structure": 26000.0,
        "Battery": 19000.0,
        "Fasteners/connectors": 3500.0,
        "Inverter": 3200.0,
        "Power cables": 1200.0,
        "Concrete ballast": 1800.0,
    },
    "Freshwater eutrophication": {
        "EV chargers": 0.9,
        "PV modules": 3.8,
        "Steel structure": 1.4,
        "Battery": 1.1,
        "Fasteners/connectors": 0.3,
        "Inverter": 0.4,
        "Power cables": 0.3,
        "Concrete ballast": 0.05,
    },
}


SCENARIO_MULTIPLIERS = {
    "Baseline": {
        "pv_yield": 1.00,
        "self_consumption": 1.00,
        "electricity_value": 1.00,
        "embodied_co2": 1.00,
        "replacement_cost": 1.00,
    },
    "Optimistic": {
        "pv_yield": 1.08,
        "self_consumption": 1.10,
        "electricity_value": 1.08,
        "embodied_co2": 0.88,
        "replacement_cost": 0.90,
    },
    "Pessimistic": {
        "pv_yield": 0.92,
        "self_consumption": 0.88,
        "electricity_value": 0.92,
        "embodied_co2": 1.15,
        "replacement_cost": 1.12,
    },
}
