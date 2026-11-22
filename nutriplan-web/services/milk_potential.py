"""Milk production allowed by the NASEM energy and protein supplied by a ration.

This module converts native NASEM supply calculations into an explicit "milk
ceiling" for a given animal and ration. It is a model-derived ceiling, not a
biological prediction: it states how much milk the formulated diet can support
under the installed NASEM 2021 equations.

The reference milk production is the floor used by the optimizer: a formulated
ration is only accepted when the allowed milk is not below that reference.
"""
from __future__ import annotations

import math

from RUFAS.biophysical.animal.nutrients.nutrition_supply_calculator import (
    FeedInRation, NutritionSupplyCalculator,
)

from services.numbers import parse_number

# NASEM (2021) chapter 6: target efficiency of converting metabolizable protein
# into milk protein. Mirrors NASEMRequirementsCalculator._calculate_protein_requirement.
MP_TO_MILK_EFFICIENCY = 0.69

# Energy per kg of milk uses the same NASEM lactation equation implemented in
# NutritionRequirementsCalculator._calculate_lactation_energy_requirements.
_FAT_FACTOR = 0.0929
_TRUE_PROTEIN_FACTOR = 0.0547 / 0.93
_LACTOSE_FACTOR = 0.0395

# A difference below this tolerance is reported as "maintained" rather than
# "increased"; keeps floating-point noise from becoming a user-facing gain.
INCREASE_THRESHOLD_KG_DAY = 0.05
FLOOR_TOLERANCE_KG_DAY = 1e-4


def milk_energy_per_kg(milk_fat, milk_true_protein, milk_lactose):
    """Return the net energy required per kg of milk (Mcal/kg) per NASEM 2021."""
    return (
        _FAT_FACTOR * milk_fat
        + _TRUE_PROTEIN_FACTOR * milk_true_protein
        + _LACTOSE_FACTOR * milk_lactose
    )


def classify_status(allowed_kg_day, reference_kg_day):
    """Return (status, margin) for an allowed milk value against a floor."""
    margin = float(allowed_kg_day) - float(reference_kg_day)
    if margin < -FLOOR_TOLERANCE_KG_DAY:
        return 'below_reference', margin
    if margin <= INCREASE_THRESHOLD_KG_DAY:
        return 'maintained', margin
    return 'increased', margin


def resolve_reference(payload):
    """Return (reference_kg_day, source) for the milk floor.

    The dedicated ``milk_reference_kg_day`` field is the current production.
    When it is absent, existing API callers fall back to the optimization
    target; the source is reported so the fallback is explicit.
    """
    raw = payload.get('milk_reference_kg_day')
    if raw is not None and not (isinstance(raw, str) and not raw.strip()):
        return parse_number(raw, 'milk_reference_kg_day', minimum=0), 'current_production'
    parameters = payload.get('parameters') or {}
    target = parse_number(parameters.get('milk_production'), 'milk_production', minimum=0)
    return target, 'optimization_target_fallback'


def _emission_values(emissions):
    if not isinstance(emissions, dict):
        return None, None
    methane = emissions.get('enteric_methane_g_day')
    urine = emissions.get('urine_nitrogen_kg_day')
    if methane is None or urine is None:
        return None, None
    return float(methane), float(urine)


def evaluate(feeds, animal, requirements, emissions, reference_kg_day):
    """Build the milk-potential contract for a formulated ration.

    Parameters
    ----------
    feeds : list[FeedInRation]
        Ration feeds with dry-matter amounts.
    animal : dict
        Animal payload returned by ``services.nutrition.calculate``.
    requirements : NutritionRequirements
        Native requirements used by the optimizer for this ration.
    emissions : dict
        Native methane (g/day) and urinary nitrogen (kg/day) for this ration.
    reference_kg_day : float
        Current milk production that must not be reduced.
    """
    parameters = animal.get('parameters') or {}
    body_weight = animal.get('body_weight_kg')
    base = {
        'allowed_kg_day': None,
        'allowed_energy_kg_day': None,
        'allowed_protein_kg_day': None,
        'reference_kg_day': reference_kg_day,
        'margin_kg_day': None,
        'status': 'unavailable',
        'method': 'NASEM 2021 NEL/MP supply',
    }
    try:
        milk_fat = float(parameters['milk_fat'])
        milk_true_protein = float(parameters['milk_true_protein'])
        milk_lactose = float(parameters['milk_lactose'])
        target_milk = float(parameters['milk_production'])
    except (KeyError, TypeError, ValueError):
        base['reason'] = 'missing_milk_composition'
        return base
    if milk_true_protein <= 0:
        base['reason'] = 'invalid_milk_true_protein'
        return base
    milk_energy = milk_energy_per_kg(milk_fat, milk_true_protein, milk_lactose)
    if not math.isfinite(milk_energy) or milk_energy <= 0:
        base['reason'] = 'invalid_milk_energy'
        return base
    methane, urine = _emission_values(emissions)
    if methane is None or body_weight is None:
        base['reason'] = 'emissions_unavailable'
        return base
    dry_matter = sum(feed.amount for feed in feeds)
    if not math.isfinite(dry_matter) or dry_matter <= 0:
        base['reason'] = 'invalid_dry_matter'
        return base
    total_starch = sum(feed.amount * feed.info.starch / 100 for feed in feeds)
    metabolizable_energy = NutritionSupplyCalculator.calculate_NASEM_metabolizable_energy(
        feeds=feeds, dry_matter_intake=dry_matter, body_weight=body_weight,
        total_starch=total_starch, enteric_methane=methane, urinary_nitrogen=urine,
    )
    net_energy = NutritionSupplyCalculator.calculate_NASEM_net_energy(metabolizable_energy)
    non_lactation_energy = requirements.total_energy_requirement - requirements.lactation_energy
    allowed_energy = (net_energy - non_lactation_energy) / milk_energy

    discount = NutritionSupplyCalculator.calculate_nutrient_intake_discount(
        feeds=feeds, body_weight=body_weight
    )
    actual_tdn_percentages = {
        feed.info.rufas_id: feed.info.TDN * discount for feed in feeds
    }
    mp_supply = NutritionSupplyCalculator.calculate_metabolizable_protein_supply(
        feeds=feeds, dry_matter_intake=dry_matter,
        actual_tdn_percentages=actual_tdn_percentages, body_weight=body_weight,
    )
    milk_net_protein_g = milk_true_protein / 100 * target_milk * 1000
    mp_non_lactation = requirements.metabolizable_protein - (
        milk_net_protein_g / MP_TO_MILK_EFFICIENCY
    )
    if mp_non_lactation < 0 and abs(mp_non_lactation) < 1e-6:
        mp_non_lactation = 0.0
    allowed_protein = (
        (mp_supply - mp_non_lactation) * MP_TO_MILK_EFFICIENCY
    ) / (milk_true_protein / 100 * 1000)

    values = [allowed_energy, allowed_protein]
    if any(value is None or not math.isfinite(value) for value in values):
        base['reason'] = 'non_finite_potential'
        return base
    allowed_energy = float(allowed_energy)
    allowed_protein = float(allowed_protein)
    allowed = min(allowed_energy, allowed_protein)
    status, margin = classify_status(allowed, reference_kg_day)
    return {
        'allowed_kg_day': allowed,
        'allowed_energy_kg_day': allowed_energy,
        'allowed_protein_kg_day': allowed_protein,
        'reference_kg_day': reference_kg_day,
        'margin_kg_day': margin,
        'status': status,
        'method': 'NASEM 2021 NEL/MP supply',
    }
