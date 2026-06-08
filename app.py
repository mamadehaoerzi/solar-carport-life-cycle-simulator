from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from assumptions import (
    DEFAULT_INPUTS,
    EMBODIED_CO2_FACTORS,
    REPLACEMENT_COSTS_EUR,
    SAMPLE_IMPACT_CONTRIBUTIONS,
)
from model import build_scenario_comparison, run_simulation


PROJECT_DIR = Path(__file__).parent
COMPONENT_FACTOR_TEMPLATE = PROJECT_DIR / "data" / "sample_component_factors_template.csv"
LCIA_CONTRIBUTION_TEMPLATE = PROJECT_DIR / "data" / "sample_lcia_contributions_template.csv"
SUMMARY_METRIC_OPTIONS = [
    "Annual PV generation",
    "Annual charging demand",
    "Demand coverage",
    "Annual electricity benefit",
    "Analysis-period cash flow",
    "Embodied CO2 incl. replacements",
    "Circularity score",
    "Main hotspot",
]
ENERGY_BALANCE_OPTIONS = [
    "PV generation",
    "Charging demand",
    "Self-consumed PV",
    "Exported PV",
]
DEFAULT_IMPACT_METRIC_CATEGORIES = [
    "Freshwater ecotoxicity",
    "Freshwater eutrophication",
    "Particulate matter formation",
    "Acidification",
]
DEFAULT_IMPACT_CHART_CATEGORIES = ["Climate change / GWP100"]


CASE_DEFAULT_OVERRIDES = {
    "scenario_name": "Baseline",
    "annual_pv_yield_kwh_per_kwp": 1200.0,
    "site_adjustment_factor": 0.90,
    "charging_points": 3,
    "operating_days_per_year": 365,
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
    "steel_structure_kg": 1419.610,
    "concrete_ballast_kg": 2610.0,
    "ev_charger_mass_kg_each": 76.0,
    "pv_module_mass_kg": 487.5,
    "battery_mass_kg": 167.0,
    "inverter_mass_kg": 24.0,
    "external_power_cables_kg": 22.275,
    "fasteners_connectors_kg": 97.202,
    "other_components_kg": 119.477,
}


st.set_page_config(
    page_title="Solar Carport Life-Cycle Simulator",
    page_icon="SC",
    layout="wide",
)


def eur(value: float) -> str:
    return f"EUR {value:,.0f}"


def kgco2(value: float) -> str:
    return f"{value:,.0f} kg CO2-eq"


def kwh(value: float) -> str:
    return f"{value:,.0f} kWh"


def pct(value: float) -> str:
    return f"{value:,.1f}%"


def impact_value(value: float, unit: str) -> str:
    if abs(value) < 0.01 and value != 0:
        return f"{value:.2e} {unit}"
    return f"{value:,.2f} {unit}"


def section_caption(text: str) -> None:
    st.caption(text)


def clamp_control_value(value, min_value, max_value, integer: bool):
    value = max(min_value, min(max_value, value))
    return int(value) if integer else float(value)


def sync_control_value(source_key: str, target_key: str, min_value, max_value, integer: bool) -> None:
    value = clamp_control_value(st.session_state[source_key], min_value, max_value, integer)
    st.session_state[source_key] = value
    st.session_state[target_key] = value


def slider_number_input(
    label: str,
    min_value,
    max_value,
    value,
    step,
    key: str,
    disabled: bool = False,
    number_format: str | None = None,
):
    integer = all(isinstance(item, int) and not isinstance(item, bool) for item in [min_value, max_value, step])
    slider_key = f"{key}_slider"
    input_key = f"{key}_input"
    initial_value = clamp_control_value(value, min_value, max_value, integer)

    if min_value >= max_value:
        fixed_value = clamp_control_value(initial_value, min_value, min_value, integer)
        st.text_input(label, value=str(fixed_value), key=f"{key}_fixed", disabled=True)
        return fixed_value

    for widget_key in [slider_key, input_key]:
        if widget_key not in st.session_state:
            st.session_state[widget_key] = initial_value
        else:
            st.session_state[widget_key] = clamp_control_value(
                st.session_state[widget_key], min_value, max_value, integer
            )

    slider_kwargs = {}
    input_kwargs = {}
    if number_format:
        slider_kwargs["format"] = number_format
        input_kwargs["format"] = number_format

    st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=st.session_state[slider_key],
        step=step,
        key=slider_key,
        disabled=disabled,
        on_change=sync_control_value,
        args=(slider_key, input_key, min_value, max_value, integer),
        **slider_kwargs,
    )
    st.number_input(
        "Exact value",
        min_value=min_value,
        max_value=max_value,
        value=st.session_state[input_key],
        step=step,
        key=input_key,
        disabled=disabled,
        label_visibility="collapsed",
        on_change=sync_control_value,
        args=(input_key, slider_key, min_value, max_value, integer),
        **input_kwargs,
    )
    return st.session_state[input_key]


def percent_slider_number_input(
    label: str,
    min_percent: float,
    max_percent: float,
    value_fraction: float,
    step_percent: float,
    key: str,
    disabled: bool = False,
    number_format: str = "%.1f",
) -> float:
    percent_value = slider_number_input(
        label,
        min_value=float(min_percent),
        max_value=float(max_percent),
        value=float(value_fraction) * 100,
        step=float(step_percent),
        key=key,
        disabled=disabled,
        number_format=number_format,
    )
    return percent_value / 100


def read_embodied_factor_csv(source) -> tuple[dict | None, str]:
    required_components = set(EMBODIED_CO2_FACTORS)
    try:
        frame = pd.read_csv(source)
    except Exception as exc:
        return None, f"Could not read CSV file: {exc}"

    required_columns = {"Component", "Factor"}
    missing_columns = required_columns - set(frame.columns)
    if missing_columns:
        return None, f"Missing CSV column(s): {', '.join(sorted(missing_columns))}"

    factors = {name: dict(spec) for name, spec in EMBODIED_CO2_FACTORS.items()}
    used_components = []
    for _, row in frame.iterrows():
        component = str(row["Component"]).strip()
        if component not in factors:
            continue
        try:
            factors[component]["value"] = float(row["Factor"])
        except ValueError:
            return None, f"Invalid numeric factor for component: {component}"
        if "Unit" in frame.columns and pd.notna(row["Unit"]):
            factors[component]["unit"] = str(row["Unit"])
        used_components.append(component)

    missing_components = required_components - set(used_components)
    if missing_components:
        return None, "CSV did not provide factors for: " + ", ".join(sorted(missing_components))

    return factors, "Using user-uploaded component factor table."


def read_impact_contribution_csv(source) -> tuple[dict | None, dict | None, str]:
    try:
        frame = pd.read_csv(source)
    except Exception as exc:
        return None, None, f"Could not read LCIA contribution CSV file: {exc}"

    required_columns = {"Impact category", "Component", "Value"}
    missing_columns = required_columns - set(frame.columns)
    if missing_columns:
        return None, None, "Missing LCIA CSV column(s): " + ", ".join(sorted(missing_columns))

    contributions: dict[str, dict[str, float]] = {}
    units: dict[str, str] = {}
    for _, row in frame.iterrows():
        category = str(row["Impact category"]).strip()
        component = str(row["Component"]).strip()
        if not category or not component:
            continue
        try:
            value = float(row["Value"])
        except ValueError:
            return None, None, f"Invalid numeric LCIA value for {category} / {component}"
        contributions.setdefault(category, {})[component] = value
        if "Unit" in frame.columns and pd.notna(row["Unit"]):
            units[category] = str(row["Unit"]).strip()

    if not contributions:
        return None, None, "LCIA contribution CSV did not contain usable rows."

    return contributions, units, "Using user-uploaded LCIA contribution table."


def factor_table_for_display(factors: dict | None) -> pd.DataFrame:
    source = factors or EMBODIED_CO2_FACTORS
    return pd.DataFrame(
        [
            {
                "Component": component,
                "Factor": spec["value"],
                "Unit": spec["unit"],
            }
            for component, spec in source.items()
        ]
    )


def collect_inputs() -> tuple[dict, dict | None, dict | None, dict | None, str, dict]:
    defaults = {**DEFAULT_INPUTS, **CASE_DEFAULT_OVERRIDES}
    embodied_factors = None
    impact_contribution_factors = None
    impact_units = None
    data_source_note = "Using built-in sample factors. No licensed database data is bundled with this app."
    with st.sidebar:
        st.header("Input Panel")
        st.caption("Adjust engineering and operational parameters for the prototype model.")

        st.subheader("Scenario Metadata")
        scenario_name = st.text_input(
            "Scenario name",
            value=defaults.get("scenario_name", "Baseline"),
            help="Examples: Baseline, High utilisation, Battery replacement, High recycling.",
        ).strip() or "Untitled scenario"

        st.subheader("Component Factor Source")
        data_source = st.radio(
            "Embodied CO2 factor source",
            ["Built-in sample factors", "Upload user CSV factors"],
            index=0,
        )
        if data_source == "Upload user CSV factors":
            uploaded_file = st.file_uploader(
                "Upload component factor CSV",
                type=["csv"],
                help="Expected columns: Component, Factor, Unit. Component names must match the template.",
                key="component_factor_upload",
            )
            st.caption(f"Template: {COMPONENT_FACTOR_TEMPLATE.name}")
            if uploaded_file is None:
                st.warning("Upload a CSV factor table to replace the sample factors.")
            else:
                embodied_factors, data_source_note = read_embodied_factor_csv(uploaded_file)
                if embodied_factors is None:
                    st.error(data_source_note)
                    data_source_note = "CSV upload failed; using built-in sample assumptions."
                else:
                    st.success("User component factor table loaded.")

        st.subheader("Optional LCIA Contribution Source")
        impact_source = st.radio(
            "LCIA contribution source",
            ["Built-in sample LCIA table", "Upload user LCIA contribution CSV"],
            index=0,
        )
        if impact_source == "Upload user LCIA contribution CSV":
            uploaded_impact_file = st.file_uploader(
                "Upload LCIA contribution CSV",
                type=["csv"],
                help="Expected columns: Impact category, Component, Value, Unit.",
                key="impact_contribution_upload",
            )
            st.caption(f"Template: {LCIA_CONTRIBUTION_TEMPLATE.name}")
            if uploaded_impact_file is None:
                st.warning("Upload an LCIA contribution table to replace the sample LCIA table.")
            else:
                impact_contribution_factors, impact_units, impact_note = read_impact_contribution_csv(
                    uploaded_impact_file
                )
                if impact_contribution_factors is None:
                    st.error(impact_note)
                    impact_contribution_factors = None
                    impact_units = None
                else:
                    st.success("User LCIA contribution table loaded.")
                    data_source_note = f"{data_source_note} {impact_note}"

        st.subheader("PV and Storage")
        pv_capacity = slider_number_input(
            "PV capacity (kWp)",
            min_value=1.0,
            max_value=100.0,
            value=defaults["pv_capacity_kwp"],
            step=0.1,
            key="pv_capacity_kwp",
            number_format="%.2f",
        )
        pv_yield = slider_number_input(
            "Annual PV yield (kWh/kWp/year)",
            min_value=700.0,
            max_value=1900.0,
            value=defaults["annual_pv_yield_kwh_per_kwp"],
            step=25.0,
            key="annual_pv_yield",
            number_format="%.0f",
        )
        site_adjustment = percent_slider_number_input(
            "Site adjustment factor (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["site_adjustment_factor"],
            step_percent=1.0,
            key="site_adjustment_factor_percent",
            number_format="%.0f",
        )
        battery_capacity = slider_number_input(
            "Battery capacity (kWh)",
            min_value=0.0,
            max_value=120.0,
            value=defaults["battery_capacity_kwh"],
            step=0.5,
            key="battery_capacity",
            number_format="%.2f",
        )

        st.subheader("EV Charging")
        chargers = slider_number_input(
            "Number of EV chargers (units)",
            min_value=1,
            max_value=20,
            value=defaults["number_of_ev_chargers"],
            step=1,
            key="number_of_ev_chargers",
        )
        charging_points = slider_number_input(
            "Charging positions / parking spaces (spaces)",
            min_value=1,
            max_value=40,
            value=defaults["charging_points"],
            step=1,
            key="charging_positions",
        )
        avg_session_energy = slider_number_input(
            "Average charging energy per session (kWh/session)",
            min_value=5.0,
            max_value=80.0,
            value=defaults["avg_charging_energy_kwh"],
            step=1.0,
            key="avg_session_energy",
            number_format="%.1f",
        )
        sessions_per_day = slider_number_input(
            "Charging sessions per day per position (sessions/day/space)",
            min_value=0.0,
            max_value=30.0,
            value=defaults["charging_sessions_per_day"],
            step=0.5,
            key="sessions_per_day",
            number_format="%.1f",
        )
        operating_days = slider_number_input(
            "Operating days per year (days/year)",
            min_value=1,
            max_value=365,
            value=defaults["operating_days_per_year"],
            step=1,
            key="operating_days",
        )

        st.subheader("Energy Value")
        self_consumption = percent_slider_number_input(
            "Self-consumption ratio (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["self_consumption_ratio"],
            step_percent=1.0,
            key="self_consumption_ratio_percent",
            number_format="%.0f",
        )
        export_ratio = 1.0 - self_consumption
        st.info(f"Exported electricity ratio is calculated automatically: {export_ratio * 100:.0f}%")
        electricity_value = slider_number_input(
            "Electricity value for self-consumption (EUR/kWh)",
            min_value=0.01,
            max_value=0.80,
            value=defaults["electricity_value_eur_per_kwh"],
            step=0.01,
            key="electricity_value",
            number_format="%.2f",
        )
        export_tariff = slider_number_input(
            "Export tariff (EUR/kWh)",
            min_value=0.00,
            max_value=0.40,
            value=defaults["export_tariff_eur_per_kwh"],
            step=0.01,
            key="export_tariff",
            number_format="%.2f",
        )
        grid_factor = slider_number_input(
            "Grid emission factor (kg CO2-eq/kWh)",
            min_value=0.00,
            max_value=1.00,
            value=defaults["grid_emission_factor_kgco2_per_kwh"],
            step=0.01,
            key="grid_emission_factor",
            number_format="%.2f",
        )

        st.subheader("Life Cycle and Costs")
        lifetime = slider_number_input(
            "Economic analysis period (years)",
            min_value=5,
            max_value=99,
            value=defaults["project_lifetime_years"],
            step=1,
            key="economic_lifetime",
        )
        lca_lifetime = slider_number_input(
            "LCA normalisation lifetime (years)",
            min_value=5,
            max_value=99,
            value=defaults["lca_lifetime_years"],
            step=1,
            key="lca_lifetime",
        )
        investment_net = slider_number_input(
            "Initial investment excl. VAT (EUR, net)",
            min_value=0.0,
            max_value=200000.0,
            value=defaults.get("initial_investment_net_eur", defaults["initial_investment_eur"]),
            step=1000.0,
            key="initial_investment_net",
            number_format="%.0f",
        )
        include_vat = st.checkbox(
            "Include VAT in investment total",
            value=defaults.get("include_vat_in_investment", False),
        )
        vat_rate = percent_slider_number_input(
            "VAT rate (%)",
            min_percent=0.0,
            max_percent=35.0,
            value_fraction=defaults.get("vat_rate", 0.22),
            step_percent=0.5,
            key="vat_rate_percent",
            number_format="%.1f",
            disabled=not include_vat,
        )
        vat_amount = investment_net * vat_rate if include_vat else 0.0
        investment = investment_net + vat_amount
        st.info(
            f"Investment used in model: EUR {investment:,.0f} "
            f"(net EUR {investment_net:,.0f} + VAT EUR {vat_amount:,.0f})"
        )
        om_rate = percent_slider_number_input(
            "O&M rate (%/year)",
            min_percent=0.0,
            max_percent=20.0,
            value_fraction=defaults["om_rate"],
            step_percent=0.5,
            key="om_rate_percent",
            number_format="%.1f",
        )
        discount_rate = percent_slider_number_input(
            "Discount rate (%/year)",
            min_percent=0.0,
            max_percent=15.0,
            value_fraction=defaults["discount_rate"],
            step_percent=0.5,
            key="discount_rate_percent",
            number_format="%.1f",
        )
        include_battery_replacement = st.checkbox(
            "Include battery replacement",
            value=defaults["include_battery_replacement"],
        )
        battery_interval = slider_number_input(
            "Battery replacement interval (years/event)",
            min_value=1,
            max_value=lifetime,
            value=min(defaults["battery_replacement_interval_years"], lifetime),
            step=1,
            key="battery_replacement_interval",
            disabled=not include_battery_replacement,
        )
        battery_units = slider_number_input(
            "Battery systems replaced each event (systems/event)",
            min_value=1,
            max_value=5,
            value=defaults["battery_replacement_units_per_event"],
            step=1,
            key="battery_replacement_units",
            disabled=not include_battery_replacement,
        )
        include_inverter_replacement = st.checkbox(
            "Include inverter replacement",
            value=defaults["include_inverter_replacement"],
        )
        inverter_interval = slider_number_input(
            "Inverter replacement interval (years/event)",
            min_value=1,
            max_value=lifetime,
            value=min(defaults["inverter_replacement_interval_years"], lifetime),
            step=1,
            key="inverter_replacement_interval",
            disabled=not include_inverter_replacement,
        )
        inverter_units = slider_number_input(
            "Inverters replaced each event (units/event)",
            min_value=1,
            max_value=5,
            value=defaults["inverter_replacement_units_per_event"],
            step=1,
            key="inverter_replacement_units",
            disabled=not include_inverter_replacement,
        )
        include_charger_replacement = st.checkbox(
            "Include EV charger replacement",
            value=defaults["include_charger_replacement"],
        )
        charger_interval = slider_number_input(
            "EV charger replacement interval (years/event)",
            min_value=1,
            max_value=lifetime,
            value=min(defaults["charger_replacement_interval_years"], lifetime),
            step=1,
            key="charger_replacement_interval",
            disabled=not include_charger_replacement,
        )
        charger_units = slider_number_input(
            "EV chargers replaced each event (chargers/event)",
            min_value=1,
            max_value=chargers,
            value=min(defaults["charger_replacement_units_per_event"], chargers),
            step=1,
            key="charger_replacement_units",
            disabled=not include_charger_replacement,
        )

        st.subheader("Reliability-Informed Replacements")
        include_steel_partial_replacement = st.checkbox(
            "Include partial steel-structure repair",
            value=defaults["include_steel_partial_replacement"],
        )
        steel_replacement_interval = slider_number_input(
            "Steel repair interval (years/event)",
            min_value=1,
            max_value=lifetime,
            value=min(defaults["steel_replacement_interval_years"], lifetime),
            step=1,
            key="steel_replacement_interval",
            disabled=not include_steel_partial_replacement,
        )
        steel_replacement_fraction = percent_slider_number_input(
            "Steel mass replaced each event (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["steel_replacement_fraction"],
            step_percent=5.0,
            key="steel_replacement_fraction_percent",
            number_format="%.0f",
            disabled=not include_steel_partial_replacement,
        )
        steel_partial_cost = slider_number_input(
            "Steel repair cost per event (EUR/event)",
            min_value=0.0,
            max_value=20000.0,
            value=defaults["steel_partial_replacement_cost_eur"],
            step=100.0,
            key="steel_partial_cost",
            number_format="%.0f",
            disabled=not include_steel_partial_replacement,
        )

        include_cable_partial_replacement = st.checkbox(
            "Include partial external cable replacement",
            value=defaults["include_cable_partial_replacement"],
        )
        cable_replacement_interval = slider_number_input(
            "Cable replacement interval (years/event)",
            min_value=1,
            max_value=lifetime,
            value=min(defaults["cable_replacement_interval_years"], lifetime),
            step=1,
            key="cable_replacement_interval",
            disabled=not include_cable_partial_replacement,
        )
        cable_replacement_fraction = percent_slider_number_input(
            "Cable mass replaced each event (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["cable_replacement_fraction"],
            step_percent=5.0,
            key="cable_replacement_fraction_percent",
            number_format="%.0f",
            disabled=not include_cable_partial_replacement,
        )
        cable_partial_cost = slider_number_input(
            "Cable replacement cost per event (EUR/event)",
            min_value=0.0,
            max_value=20000.0,
            value=defaults["cable_partial_replacement_cost_eur"],
            step=100.0,
            key="cable_partial_cost",
            number_format="%.0f",
            disabled=not include_cable_partial_replacement,
        )

        include_wear_parts_replacement = st.checkbox(
            "Include fasteners/connectors wear-part replacement",
            value=defaults["include_wear_parts_replacement"],
        )
        wear_parts_interval = slider_number_input(
            "Wear-part replacement interval (years/event)",
            min_value=1,
            max_value=lifetime,
            value=min(defaults["wear_parts_replacement_interval_years"], lifetime),
            step=1,
            key="wear_parts_interval",
            disabled=not include_wear_parts_replacement,
        )
        wear_parts_fraction = percent_slider_number_input(
            "Wear-part mass replaced each event (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["wear_parts_replacement_fraction"],
            step_percent=5.0,
            key="wear_parts_fraction_percent",
            number_format="%.0f",
            disabled=not include_wear_parts_replacement,
        )
        wear_parts_cost = slider_number_input(
            "Wear-part replacement cost per event (EUR/event)",
            min_value=0.0,
            max_value=20000.0,
            value=defaults["wear_parts_replacement_cost_eur"],
            step=100.0,
            key="wear_parts_cost",
            number_format="%.0f",
            disabled=not include_wear_parts_replacement,
        )

        st.subheader("End-of-Life Scenario")
        metal_recycling = percent_slider_number_input(
            "Metals recycling rate (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["metal_recycling_rate"],
            step_percent=1.0,
            key="metal_recycling_rate_percent",
            number_format="%.0f",
        )
        concrete_recycling = percent_slider_number_input(
            "Concrete recycling rate (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["concrete_recycling_rate"],
            step_percent=1.0,
            key="concrete_recycling_rate_percent",
            number_format="%.0f",
        )
        battery_recovery = percent_slider_number_input(
            "Battery recovery rate (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["battery_recovery_rate"],
            step_percent=1.0,
            key="battery_recovery_rate_percent",
            number_format="%.0f",
        )
        electronics_recovery = percent_slider_number_input(
            "Electronics recovery rate (%)",
            min_percent=0.0,
            max_percent=100.0,
            value_fraction=defaults["electronics_recovery_rate"],
            step_percent=1.0,
            key="electronics_recovery_rate_percent",
            number_format="%.0f",
        )

        available_impact_categories = list(
            impact_contribution_factors or SAMPLE_IMPACT_CONTRIBUTIONS
        )

        st.subheader("Result Display Settings")
        selected_summary_metrics = st.multiselect(
            "Summary KPI cards",
            SUMMARY_METRIC_OPTIONS,
            default=SUMMARY_METRIC_OPTIONS,
            help="Choose which headline indicators appear at the top of the dashboard.",
        )
        selected_energy_categories = st.multiselect(
            "Energy balance chart bars",
            ENERGY_BALANCE_OPTIONS,
            default=ENERGY_BALANCE_OPTIONS,
            help="Choose which annual energy indicators appear in the energy bar chart.",
        )
        selected_impact_metric_categories = st.multiselect(
            "LCIA metric cards",
            available_impact_categories,
            default=[
                category
                for category in DEFAULT_IMPACT_METRIC_CATEGORIES
                if category in available_impact_categories
            ],
            help="Choose which environmental impact indicators appear as metric cards.",
        )
        selected_impact_chart_categories = st.multiselect(
            "LCIA contribution charts",
            available_impact_categories,
            default=[
                category
                for category in DEFAULT_IMPACT_CHART_CATEGORIES
                if category in available_impact_categories
            ],
            help="Choose which impact categories get component contribution charts.",
        )
        show_replacement_increase_chart = st.checkbox(
            "Show replacement increase chart",
            value=True,
        )

    inputs = {
        **defaults,
        "scenario_name": scenario_name,
        "pv_capacity_kwp": pv_capacity,
        "annual_pv_yield_kwh_per_kwp": pv_yield,
        "site_adjustment_factor": site_adjustment,
        "battery_capacity_kwh": battery_capacity,
        "number_of_ev_chargers": chargers,
        "charging_points": charging_points,
        "avg_charging_energy_kwh": avg_session_energy,
        "charging_sessions_per_day": sessions_per_day,
        "operating_days_per_year": operating_days,
        "self_consumption_ratio": self_consumption,
        "exported_electricity_ratio": export_ratio,
        "electricity_value_eur_per_kwh": electricity_value,
        "export_tariff_eur_per_kwh": export_tariff,
        "grid_emission_factor_kgco2_per_kwh": grid_factor,
        "project_lifetime_years": lifetime,
        "lca_lifetime_years": lca_lifetime,
        "initial_investment_net_eur": investment_net,
        "include_vat_in_investment": include_vat,
        "vat_rate": vat_rate,
        "vat_amount_eur": vat_amount,
        "initial_investment_eur": investment,
        "om_rate": om_rate,
        "include_battery_replacement": include_battery_replacement,
        "include_inverter_replacement": include_inverter_replacement,
        "include_charger_replacement": include_charger_replacement,
        "include_steel_partial_replacement": include_steel_partial_replacement,
        "steel_replacement_interval_years": steel_replacement_interval,
        "steel_replacement_fraction": steel_replacement_fraction,
        "steel_partial_replacement_cost_eur": steel_partial_cost,
        "include_cable_partial_replacement": include_cable_partial_replacement,
        "cable_replacement_interval_years": cable_replacement_interval,
        "cable_replacement_fraction": cable_replacement_fraction,
        "cable_partial_replacement_cost_eur": cable_partial_cost,
        "include_wear_parts_replacement": include_wear_parts_replacement,
        "wear_parts_replacement_interval_years": wear_parts_interval,
        "wear_parts_replacement_fraction": wear_parts_fraction,
        "wear_parts_replacement_cost_eur": wear_parts_cost,
        "battery_replacement_interval_years": battery_interval,
        "battery_replacement_units_per_event": battery_units,
        "inverter_replacement_interval_years": inverter_interval,
        "inverter_replacement_units_per_event": inverter_units,
        "charger_replacement_interval_years": charger_interval,
        "charger_replacement_units_per_event": charger_units,
        "discount_rate": discount_rate,
        "metal_recycling_rate": metal_recycling,
        "concrete_recycling_rate": concrete_recycling,
        "battery_recovery_rate": battery_recovery,
        "electronics_recovery_rate": electronics_recovery,
    }
    display_settings = {
        "summary_metrics": selected_summary_metrics,
        "energy_categories": selected_energy_categories,
        "impact_metric_categories": selected_impact_metric_categories,
        "impact_chart_categories": selected_impact_chart_categories,
        "show_replacement_increase_chart": show_replacement_increase_chart,
    }
    return (
        inputs,
        embodied_factors,
        impact_contribution_factors,
        impact_units,
        data_source_note,
        display_settings,
    )


def format_hover_number(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    if value == 0:
        return "0"
    if abs(value) < 0.01:
        return f"{value:.6g}"
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    return f"{value:,.4f}".rstrip("0").rstrip(".")


def scenario_title(scenario_name: str, title: str) -> str:
    return f"{scenario_name} - {title}" if scenario_name else title


def safe_filename_text(text: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in text.strip().lower())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "scenario"


def methodology_note_text() -> str:
    return """Methodology and limitations

This public prototype uses built-in sample factors unless the user uploads their own authorized data.
Operational avoided CO2 is shown separately from embodied impacts.
Replacement impacts are based on the selected scenario.
The model can be connected to external factor tables through CSV upload.

This is not a certified LCA model, validated industrial software or a commercial simulator.
"""


def build_scenario_summary(result, inputs: dict, data_source_note: str) -> pd.DataFrame:
    rows = [
        ("Scenario", "Scenario name", inputs.get("scenario_name", "Baseline"), ""),
        ("Scenario", "Inventory data source", data_source_note, ""),
        ("Investment", "Initial investment excl. VAT", inputs["initial_investment_net_eur"], "EUR"),
        ("Investment", "Include VAT in investment total", inputs["include_vat_in_investment"], ""),
        ("Investment", "VAT rate", inputs["vat_rate"] * 100, "%"),
        ("Investment", "VAT amount included", inputs["vat_amount_eur"], "EUR"),
        ("Investment", "Initial investment used in model", inputs["initial_investment_eur"], "EUR"),
        ("Configuration", "PV capacity", inputs["pv_capacity_kwp"], "kWp"),
        ("Configuration", "Battery capacity", inputs["battery_capacity_kwh"], "kWh"),
        ("Configuration", "EV chargers", inputs["number_of_ev_chargers"], "units"),
        ("Configuration", "Economic analysis period", inputs["project_lifetime_years"], "years"),
        ("Configuration", "LCA normalisation lifetime", inputs["lca_lifetime_years"], "years"),
    ]
    rows.extend(("Energy", key, value, "") for key, value in result.energy.items())
    rows.extend(("Economics", key, value, "") for key, value in result.economics.items())
    rows.extend(("Embodied LCA", key, value, "") for key, value in result.co2.items())
    rows.append(("Circularity", "Circularity score", result.circularity["score"], "score / 100"))
    rows.extend(
        ("Circularity", f"{name} recovery / recycling rate", value * 100, "%")
        for name, value in result.circularity["rates"].items()
    )
    return pd.DataFrame(rows, columns=["Section", "Indicator", "Value", "Unit"])


def summary_metric_values(result) -> dict[str, str]:
    return {
        "Annual PV generation": kwh(result.energy["Annual PV generation (kWh)"]),
        "Annual charging demand": kwh(result.energy["Annual charging demand (kWh)"]),
        "Demand coverage": pct(result.energy["Charging demand coverage (%)"]),
        "Annual electricity benefit": eur(result.economics["Annual electricity benefit (EUR)"]),
        "Analysis-period cash flow": eur(result.economics["Analysis-period cumulative cash flow (EUR)"]),
        "Embodied CO2 incl. replacements": kgco2(
            result.co2["Total simplified life-cycle CO2 (kg CO2-eq)"]
        ),
        "Circularity score": f"{result.circularity['score']:.0f} / 100",
        "Main hotspot": result.co2["Main environmental hotspot"],
    }


def metric_grid(result, selected_metrics: list[str]) -> None:
    metrics = summary_metric_values(result)
    selected = [name for name in selected_metrics if name in metrics]
    if not selected:
        st.info("No summary KPI cards selected.")
        return
    for start in range(0, len(selected), 4):
        batch = selected[start : start + 4]
        cols = st.columns(len(batch))
        for col, name in zip(cols, batch):
            col.metric(name, metrics[name])


def interactive_horizontal_bar(
    data: pd.DataFrame,
    title: str,
    unit: str,
    color: str,
    label_title: str = "Indicator",
) -> None:
    if data.empty:
        st.info("No indicators selected for this chart.")
        return
    chart_data = data.copy()
    chart_data["Display value"] = chart_data["Value"].map(lambda value: f"{format_hover_number(value)} {unit}")
    chart_data = chart_data.sort_values("Value", ascending=False)
    height = max(280, min(620, 42 * len(chart_data) + 80))
    chart = (
        alt.Chart(chart_data)
        .mark_bar(color=color)
        .encode(
            x=alt.X("Value:Q", title=unit),
            y=alt.Y("Label:N", sort=chart_data["Label"].tolist(), title=None),
            tooltip=[
                alt.Tooltip("Label:N", title=label_title),
                alt.Tooltip("Display value:N", title="Exact value"),
            ],
        )
        .properties(title=title, height=height)
        .interactive()
    )
    st.altair_chart(chart, width="stretch")


def interactive_vertical_bar(
    data: pd.DataFrame,
    title: str,
    unit: str,
    color_range: list[str],
) -> None:
    if data.empty:
        st.info("No indicators selected for this chart.")
        return
    chart_data = data.copy()
    chart_data["Display value"] = chart_data["Value"].map(lambda value: f"{format_hover_number(value)} {unit}")
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
    "Label:N",
    title=None,
    sort=chart_data["Label"].tolist(),
    axis=alt.Axis(labelAngle=0, labelLimit=0, labelOverlap=False),
),
            y=alt.Y("Value:Q", title=unit),
            color=alt.Color(
                "Label:N",
                scale=alt.Scale(domain=chart_data["Label"].tolist(), range=color_range),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Label:N", title="Indicator"),
                alt.Tooltip("Display value:N", title="Exact value"),
            ],
        )
        .properties(title=title, height=340)
        .interactive()
    )
    st.altair_chart(chart, width="stretch")


def plot_cash_flow(cash_flow: pd.DataFrame, scenario_name: str) -> None:
    data = cash_flow[
        ["Year", "Cumulative cash flow (EUR)", "Discounted cumulative cash flow (EUR)"]
    ].melt("Year", var_name="Series", value_name="Value")
    data["Display value"] = data["Value"].map(lambda value: f"EUR {format_hover_number(value)}")
    line = (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X("Year:Q", title="Year"),
            y=alt.Y("Value:Q", title="EUR"),
            color=alt.Color("Series:N", title=None),
            tooltip=[
                alt.Tooltip("Year:Q", title="Year", format=".0f"),
                alt.Tooltip("Series:N", title="Series"),
                alt.Tooltip("Display value:N", title="Exact value"),
            ],
        )
    )
    zero = alt.Chart(pd.DataFrame({"Value": [0]})).mark_rule(color="#444444").encode(y="Value:Q")
    st.altair_chart(
        (line + zero)
        .properties(
            title=scenario_title(scenario_name, "Cumulative cash flow over analysis period"),
    height=420,
    padding={"bottom": 45},
        )
        .interactive(),
        width="stretch",
    )


def plot_component_co2(component_co2: pd.DataFrame, scenario_name: str) -> None:
    data = component_co2.rename(
        columns={"Component": "Label", "Embodied CO2 (kg CO2-eq)": "Value"}
    )[["Label", "Value"]]
    interactive_horizontal_bar(
        data,
        title=scenario_title(scenario_name, "Component embodied CO2 contribution"),
        unit="kg CO2-eq",
        color="#496c7a",
        label_title="Component",
    )


def plot_impact_contribution(contributions: pd.DataFrame, category: str, scenario_name: str) -> None:
    selected = contributions[contributions["Impact category"] == category]
    if selected.empty:
        st.info(f"No contribution data available for {category}.")
        return
    unit = selected["Unit"].iloc[0]
    data = selected.groupby("Component", as_index=False)["Value"].sum()
    data = data.rename(columns={"Component": "Label"})
    interactive_horizontal_bar(
        data,
        title=scenario_title(scenario_name, f"{category} contribution including selected replacements"),
        unit=unit,
        color="#5f6f52",
        label_title="Component",
    )


def plot_impact_replacement_increase(summary: pd.DataFrame, scenario_name: str) -> None:
    data = summary.copy()
    data["Value"] = (
        data["Replacement additions"] / data["Reference baseline"].replace(0, pd.NA) * 100
    ).fillna(0)
    data = data.rename(columns={"Impact category": "Label"})
    interactive_horizontal_bar(
        data[["Label", "Value"]],
        title=scenario_title(scenario_name, "Reliability scenario effect across impact categories"),
        unit="%",
        color="#8a6f3d",
        label_title="Impact category",
    )


def plot_energy_balance(result, selected_categories: list[str], scenario_name: str) -> None:
    energy_map = {
        "PV generation": result.energy["Annual PV generation (kWh)"],
        "Charging demand": result.energy["Annual charging demand (kWh)"],
        "Self-consumed PV": result.energy["Self-consumed PV energy (kWh)"],
        "Exported PV": result.energy["Exported PV energy (kWh)"],
    }
    rows = [
        {"Label": category, "Value": energy_map[category]}
        for category in selected_categories
        if category in energy_map
    ]
    interactive_vertical_bar(
        pd.DataFrame(rows),
        title=scenario_title(scenario_name, "Annual energy balance"),
        unit="kWh/year",
        color_range=["#496c7a", "#8a6f3d", "#4f7f58", "#7a7a7a"],
    )


def plot_replacement_timeline(replacements: pd.DataFrame, lifetime: int, scenario_name: str) -> None:
    if replacements.empty:
        st.info("No replacement events selected.")
        return
    data = replacements.copy()
    data["Year"] = data["Year"].astype(int)
    data["Cost display"] = data["Cost (EUR)"].map(lambda value: f"EUR {format_hover_number(value)}")
    data["CO2 display"] = data["CO2 (kg CO2-eq)"].map(lambda value: f"{format_hover_number(value)} kg CO2-eq")
    data["Replacement fraction display"] = data["Replacement fraction"].map(format_hover_number)
    data["Units display"] = data["Units replaced"].fillna("n/a").astype(str)
    height = max(260, min(680, 34 * len(data) + 80))
    chart = (
        alt.Chart(data)
        .mark_circle(size=120, color="#8a4f4f")
        .encode(
            x=alt.X("Year:Q", title="Project year", scale=alt.Scale(domain=[0, lifetime])),
            y=alt.Y("Event:N", title=None, sort=alt.SortField("Year", order="ascending")),
            tooltip=[
                alt.Tooltip("Year:Q", title="Year", format=".0f"),
                alt.Tooltip("Event:N", title="Event"),
                alt.Tooltip("Units display:N", title="Units replaced"),
                alt.Tooltip("Replacement fraction display:N", title="Replacement fraction"),
                alt.Tooltip("Cost display:N", title="Replacement cost"),
                alt.Tooltip("CO2 display:N", title="Replacement CO2"),
            ],
        )
        .properties(title=scenario_title(scenario_name, "Replacement event timeline"), height=height)
        .interactive()
    )
    st.altair_chart(chart, width="stretch")


def show_methodology() -> None:
    with st.expander("Methodology and limitations", expanded=False):
        st.markdown(
            """
This public prototype uses built-in sample factors unless the user uploads their own authorized data.

Operational avoided CO2 is shown separately from embodied impacts.

Replacement impacts are based on the selected scenario.

The model can be connected to external factor tables through CSV upload.

This is not a certified LCA model, validated industrial software or a commercial simulator.
            """
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {"Component": name, "Factor": spec["value"], "Unit": spec["unit"]}
                    for name, spec in EMBODIED_CO2_FACTORS.items()
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        st.dataframe(
            pd.DataFrame(
                [{"Replacement": name, "Default cost (EUR)": value} for name, value in REPLACEMENT_COSTS_EUR.items()]
            ),
            width="stretch",
            hide_index=True,
        )


def main() -> None:
    (
        inputs,
        embodied_factors,
        impact_contribution_factors,
        impact_units,
        data_source_note,
        display_settings,
    ) = collect_inputs()
    result = run_simulation(
        inputs,
        embodied_factors=embodied_factors,
        impact_contribution_factors=impact_contribution_factors,
        impact_units=impact_units,
    )
    scenario_table = build_scenario_comparison(inputs, embodied_factors)

    st.title("Solar Carport Life-Cycle Simulator")
    st.subheader("Prototype Research Demonstrator")
    st.caption(f"Current scenario: {inputs['scenario_name']}")
    st.markdown(
        """
This is a small Python/Streamlit prototype for a photovoltaic solar carport with battery storage and EV charging infrastructure. The user can change technical and economic parameters and see simplified LCA, cost and scenario results. The public version includes sample assumptions only. Users who have access to their own LCA database or factor table can import their own CSV files.
        """
    )
    st.info(data_source_note)
    summary_csv = build_scenario_summary(result, inputs, data_source_note).to_csv(index=False).encode("utf-8-sig")
    download_cols = st.columns(2)
    download_cols[0].download_button(
        "Download scenario summary as CSV",
        data=summary_csv,
        file_name=f"{safe_filename_text(inputs['scenario_name'])}_scenario_summary.csv",
        mime="text/csv",
    )
    download_cols[1].download_button(
        "Download methodology note",
        data=methodology_note_text(),
        file_name=f"{safe_filename_text(inputs['scenario_name'])}_methodology_note.txt",
        mime="text/plain",
    )
    with st.expander("Current LCIA / environmental impact factors", expanded=False):
        st.dataframe(
            factor_table_for_display(embodied_factors),
            width="stretch",
            hide_index=True,
        )

    metric_grid(result, display_settings["summary_metrics"])

    st.divider()
    st.header("System Configuration Summary")
    section_caption("Selected engineering parameters for the current scenario.")
    config_cols = st.columns(3)
    config_cols[0].info(f"Scenario: {inputs['scenario_name']}")
    config_cols[0].info(f"PV system: {inputs['pv_capacity_kwp']:.2f} kWp")
    config_cols[0].info(f"Site adjustment: {inputs['site_adjustment_factor']:.0%}")
    config_cols[0].info(f"Battery: {inputs['battery_capacity_kwh']:.2f} kWh")
    config_cols[1].info(f"EV chargers: {inputs['number_of_ev_chargers']} units")
    config_cols[1].info(f"Charging positions: {inputs['charging_points']}")
    config_cols[1].info(
        f"Investment: EUR {inputs['initial_investment_eur']:,.0f} "
        f"({'VAT included' if inputs['include_vat_in_investment'] else 'VAT excluded'})"
    )
    config_cols[2].info(f"Cash-flow period: {inputs['project_lifetime_years']} years")
    config_cols[2].info(f"O&M rate: {inputs['om_rate']:.1%}")

    st.header("Energy Balance Results")
    section_caption("Annual PV generation, charging demand, self-consumption and exported electricity.")
    left, right = st.columns([1.1, 1])
    with left:
        plot_energy_balance(result, display_settings["energy_categories"], inputs["scenario_name"])
    with right:
        energy_labels = {
            "Annual PV generation (kWh)": "PV generation",
            "Annual charging demand (kWh)": "Charging demand",
            "Self-consumed PV energy (kWh)": "Self-consumed PV",
            "Exported PV energy (kWh)": "Exported PV",
        }
        energy_table = pd.DataFrame(
            [
                {"Indicator": label, "Value": result.energy[key]}
                for key, label in energy_labels.items()
                if label in display_settings["energy_categories"]
            ]
        )
        st.dataframe(
            energy_table,
            width="stretch",
            hide_index=True,
        )

    st.header("LCA/LCC Results")
    section_caption("Embodied-LCA contribution structure, selected replacement scenario and electricity-only cash-flow indicators.")
    left, right = st.columns(2)
    with left:
        plot_component_co2(result.component_co2, inputs["scenario_name"])
    with right:
        plot_cash_flow(result.cash_flow, inputs["scenario_name"])

    st.header("Additional Environmental Impact Factors")
    section_caption(
        "Supporting LCIA indicators from sample or user-uploaded contribution tables. Replacement events are scaled by component group and replacement fraction."
    )
    selected_impact_metrics = [
        category
        for category in display_settings["impact_metric_categories"]
        if category in result.impact_summary["Impact category"].tolist()
    ]
    if selected_impact_metrics:
        for start in range(0, len(selected_impact_metrics), 4):
            batch = selected_impact_metrics[start : start + 4]
            metric_cols = st.columns(len(batch))
            for col, category in zip(metric_cols, batch):
                row = result.impact_summary[result.impact_summary["Impact category"] == category].iloc[0]
                col.metric(
                    category,
                    impact_value(row["Total with selected replacements"], row["Unit"]),
                    help=f"Main hotspot: {row['Main hotspot']}",
                )
                col.caption(f"Hotspot: {row['Main hotspot']}")
    else:
        st.info("No LCIA metric cards selected.")

    selected_impact_charts = [
        category
        for category in display_settings["impact_chart_categories"]
        if category in result.impact_summary["Impact category"].tolist()
    ]
    if selected_impact_charts:
        st.subheader("Selected LCIA Contribution Charts")
        for start in range(0, len(selected_impact_charts), 2):
            batch = selected_impact_charts[start : start + 2]
            chart_cols = st.columns(len(batch))
            for col, category in zip(chart_cols, batch):
                with col:
                    plot_impact_contribution(result.impact_contributions, category, inputs["scenario_name"])
    else:
        st.info("No LCIA contribution charts selected.")

    if display_settings["show_replacement_increase_chart"]:
        st.subheader("Replacement Effect Across Impact Categories")
        plot_impact_replacement_increase(result.impact_summary, inputs["scenario_name"])

    selected_impact_rows = list(dict.fromkeys(selected_impact_metrics + selected_impact_charts))
    impact_display = result.impact_summary.copy()
    if selected_impact_rows:
        impact_display = impact_display[impact_display["Impact category"].isin(selected_impact_rows)]
    st.dataframe(
        impact_display,
        width="stretch",
        hide_index=True,
    )

    st.header("Replacement and Lifetime Events")
    section_caption("Replacement events add cost, replacement embodied CO2 and scaled supporting LCIA impacts in selected project years.")
    plot_replacement_timeline(result.replacement_events, inputs["project_lifetime_years"], inputs["scenario_name"])
    st.dataframe(result.replacement_events, width="stretch", hide_index=True)

    st.header("End-of-Life / Circularity Scenario")
    section_caption("Circularity-oriented assessment based on recovery assumptions for materials and electronics.")
    eol_cols = st.columns(5)
    eol_cols[0].metric("Circularity score", f"{result.circularity['score']:.0f} / 100")
    for index, (name, value) in enumerate(result.circularity["rates"].items(), start=1):
        eol_cols[index].metric(name, pct(value * 100))

    st.header("Scenario Comparison")
    section_caption("Baseline, optimistic and pessimistic variants apply simple multipliers to key assumptions.")
    st.dataframe(
        scenario_table.style.format(
            {
                "PV generation (kWh/year)": "{:,.0f}",
                "Demand coverage (%)": "{:,.1f}",
                "Annual benefit (EUR/year)": "EUR {:,.0f}",
                "Analysis-period cash flow (EUR)": "EUR {:,.0f}",
                "Embodied CO2 incl. replacements (kg CO2-eq)": "{:,.0f}",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    show_methodology()


if __name__ == "__main__":
    main()
