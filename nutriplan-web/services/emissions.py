"""Resolve RuFaS emission prerequisites from an explicit previous ration."""
from __future__ import annotations

import math

from services.numbers import parse_number

from RUFAS.biophysical.animal.data_types.nutrition_data_structures import NutritionSupply
from RUFAS.biophysical.animal.digestive_system.enteric_methane_calculator import EntericMethaneCalculator
from RUFAS.biophysical.animal.digestive_system.manure_excretion_calculator import ManureExcretionCalculator
from RUFAS.biophysical.animal.nutrients.nutrition_supply_calculator import FeedInRation, NutritionSupplyCalculator


def previous_ration_feeds(previous_ration, library, build_feed):
    """Validate and build feeds for an explicitly supplied previous ration."""
    if not isinstance(previous_ration, list) or len(previous_ration) < 2:
        raise ValueError('A previous ration requires at least two feeds.')
    seen = set()
    feeds = []
    for item in previous_ration:
        if not isinstance(item, dict):
            raise ValueError('Previous-ration feed entries must be objects.')
        try:
            identifier = int(item['rufas_id'])
            amount = parse_number(item['kg_dm_day'], 'kg_dm_day', minimum=0)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Invalid previous-ration feed identifier or dry matter quantity.') from error
        if identifier in seen or not math.isfinite(amount) or amount <= 0:
            raise ValueError('Previous-ration feed identifiers and quantities must be unique and positive.')
        seen.add(identifier)
        feed = build_feed({'rufas_id': identifier, 'price_as_fed': 0,
                           'minimum_kg_dm': 0, 'maximum_kg_dm': amount}, library)
        feeds.append(FeedInRation(amount=amount, info=feed))
    return feeds


def previous_ration_ndf_percent(previous_ration, library, build_feed):
    """Calculate previous-diet NDF using the native RuFaS feed composition."""
    feeds = previous_ration_feeds(previous_ration, library, build_feed)
    dry_matter = sum(item.amount for item in feeds)
    ndf = NutritionSupplyCalculator._calculate_nutritive_content(feeds, 'NDF')
    return ndf / dry_matter * 100


def calculate_previous_ration_emissions(previous_ration, library, animal, build_feed,
                                        calculation_type='lactating'):
    """Use native IPCC methane and stage-specific manure models on a known ration.

    Energy fields are unavailable before methane and urine nitrogen are known.
    The selected IPCC methane and urine-nitrogen pathways do not use them.
    """
    feeds = previous_ration_feeds(previous_ration, library, build_feed)
    emissions = calculate_ration_emissions(feeds, animal, calculation_type)
    emissions.update({
        'provenance': 'native_rufas_previous_ration',
        'previous_ration': [{'rufas_id': item.info.rufas_id, 'kg_dm_day': item.amount} for item in feeds],
        'previous_ration_dmi_kg_day': emissions['ration_dmi_kg_day'],
        'previous_ration_ndf_percent': emissions['ration_ndf_percent'],
    })
    del emissions['ration_dmi_kg_day']
    del emissions['ration_ndf_percent']
    return emissions


class CandidateEmissionEstimationError(ValueError):
    """A candidate lies outside the domain of the automatic emission calculations."""


def calculate_candidate_ration_emissions(feeds, animal, calculation_type='lactating'):
    """Apply the same native stage-specific emission methods to a candidate ration."""
    try:
        emissions = calculate_ration_emissions(feeds, animal, calculation_type)
    except (ValueError, ArithmeticError) as error:
        raise CandidateEmissionEstimationError('Automatic emission estimation failed.') from error
    emissions.update({
        'provenance': 'native_rufas_candidate_ration',
        'source_reference': 'RuFaS native candidate-feed calculation',
        'candidate_ration': [{'rufas_id': item.info.rufas_id, 'kg_dm_day': item.amount} for item in feeds],
        'candidate_ration_dmi_kg_day': emissions['ration_dmi_kg_day'],
        'candidate_ndf_percent': emissions['ration_ndf_percent'],
    })
    del emissions['ration_dmi_kg_day']
    del emissions['ration_ndf_percent']
    return emissions


def calculate_ration_emissions(feeds, animal, calculation_type='lactating'):
    """Calculate FDN, methane and urinary nitrogen from native feed composition."""
    dry_matter = sum(item.amount for item in feeds)
    if not math.isfinite(dry_matter) or dry_matter <= 0:
        raise ValueError('Ration emissions require positive dry matter intake.')
    nutrients = {key: NutritionSupplyCalculator._calculate_nutritive_content(feeds, key)
                 for key in ('NDF', 'EE', 'CP', 'ADF', 'ash', 'potassium', 'starch')}
    wet_matter = sum(item.amount / (item.info.DM / 100) for item in feeds)
    unavailable = math.nan
    supply = NutritionSupply(
        metabolizable_energy=unavailable, maintenance_energy=unavailable,
        lactation_energy=unavailable, growth_energy=unavailable,
        metabolizable_protein=unavailable, calcium=unavailable, phosphorus=unavailable,
        dry_matter=dry_matter, wet_matter=wet_matter,
        ndf_supply=nutrients['NDF'], forage_ndf_supply=unavailable,
        fat_supply=nutrients['EE'], crude_protein=nutrients['CP'],
        adf_supply=nutrients['ADF'], digestible_energy_supply=unavailable,
        tdn_supply=unavailable, lignin_supply=unavailable,
        ash_supply=nutrients['ash'], potassium_supply=nutrients['potassium'],
        starch_supply=nutrients['starch'], byproduct_supply=unavailable,
    )
    parameters = animal['parameters']
    body_weight = animal['body_weight_kg']
    if calculation_type == 'lactating':
        methane_models = {'cows': {'lactating cows': 'IPCC'}}
        methane, unmitigated = EntericMethaneCalculator.calculate_cow_methane(
            is_lactating=True, body_weight=body_weight,
            milk_fat=parameters['milk_fat'], metabolizable_energy_intake=unavailable,
            nutrient_amounts=supply, methane_mitigation_method='',
            methane_mitigation_additive_amount=0, methane_models=methane_models,
        )
        _, excretion = ManureExcretionCalculator.calculate_cow_manure(
            is_lactating=True, body_weight=body_weight,
            days_in_milk=int(parameters['days_in_milk']),
            milk_protein=parameters['milk_true_protein'],
            daily_milk_production=parameters['milk_production'],
            fecal_phosphorus=unavailable, urine_phosphorus_required=unavailable,
            nutrient_amounts=supply,
        )
        methane_model = 'RuFaS IPCC lactating-cow model'
        manure_model = 'RuFaS lactating-cow manure model'
    elif calculation_type in ('growth', 'heifer'):
        unmitigated = EntericMethaneCalculator.calculate_heifer_methane('IPCC', supply)
        methane = unmitigated
        _, excretion = ManureExcretionCalculator.calculate_heifer_manure(
            body_weight=body_weight, fecal_phosphorus=unavailable,
            urine_phosphorus_required=unavailable, nutrient_amount=supply,
        )
        methane_model = 'RuFaS IPCC heifer model'
        manure_model = 'RuFaS heifer manure model'
    elif calculation_type in ('dry', 'dry_cow'):
        methane_models = {'cows': {'dry cows': 'IPCC'}}
        methane, unmitigated = EntericMethaneCalculator.calculate_cow_methane(
            is_lactating=False, body_weight=body_weight, milk_fat=0.0,
            metabolizable_energy_intake=unavailable, nutrient_amounts=supply,
            methane_mitigation_method='', methane_mitigation_additive_amount=0,
            methane_models=methane_models,
        )
        _, excretion = ManureExcretionCalculator.calculate_cow_manure(
            is_lactating=False, body_weight=body_weight, days_in_milk=0,
            milk_protein=0.0, daily_milk_production=0.0,
            fecal_phosphorus=unavailable, urine_phosphorus_required=unavailable,
            nutrient_amounts=supply,
        )
        methane_model = 'RuFaS IPCC dry-cow model'
        manure_model = 'RuFaS dry-cow manure model'
    else:
        raise ValueError(f'Unsupported emission calculation type: {calculation_type}.')
    urine_nitrogen = excretion.urine_nitrogen
    if not all(math.isfinite(value) and value >= 0 for value in (methane, unmitigated, urine_nitrogen)):
        raise ValueError('Native ration emissions are not finite and nonnegative.')
    return {
        'enteric_methane_g_day': unmitigated,
        'urine_nitrogen_kg_day': urine_nitrogen,
        'methane_model': methane_model,
        'urinary_nitrogen_model': manure_model,
        'ration_dmi_kg_day': dry_matter,
        'ration_ndf_percent': supply.ndf_percentage,
    }
