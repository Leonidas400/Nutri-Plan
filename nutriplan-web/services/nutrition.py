"""CSV profiles and RuFaS NASEM requirements for NutriPlan."""
from __future__ import annotations

import csv
import math
from pathlib import Path

from services.numbers import parse_number

from RUFAS.biophysical.animal.data_types.animal_types import AnimalType
from RUFAS.biophysical.animal.nutrients.nasem_requirements_calculator import NASEMRequirementsCalculator

DATA = Path(__file__).resolve().parents[1] / 'data'
PARAMETERS = (
    'mature_body_weight', 'body_condition_score_5', 'days_in_milk',
    'day_of_pregnancy', 'average_daily_gain_heifer', 'calving_interval',
    'milk_fat', 'milk_true_protein', 'milk_lactose', 'milk_production',
    'housing', 'distance', 'ndf_percentage',
    'process_based_phosphorus_requirement',
)
OPTIONAL = {'day_of_pregnancy', 'average_daily_gain_heifer'}
NUMERIC = set(PARAMETERS) - {'housing'}
HOUSING_TYPES = {'Barn', 'Grazing'}


def parse_numeric_parameter(key, raw):
    """Shared input validation for the existing numeric animal parameters."""
    value = parse_number(raw, key, minimum=1 if key == 'body_condition_score_5' else 0,
                         maximum=5 if key == 'body_condition_score_5' else
                         100 if key in {'milk_fat', 'milk_true_protein', 'milk_lactose', 'ndf_percentage'} else None,
                         integer=key in {'days_in_milk', 'day_of_pregnancy', 'calving_interval'})
    if key == 'mature_body_weight' and value <= 0:
        raise ValueError('mature_body_weight must be positive.')
    return value


def profiles():
    with (DATA / 'animal_profiles.csv').open(newline='', encoding='utf-8') as stream:
        return {row['animal_category']: row for row in csv.DictReader(stream)}


def categories():
    result = []
    for key, row in profiles().items():
        missing = [parameter for parameter in PARAMETERS if parameter not in OPTIONAL and not row[parameter]]
        result.append({'id': key, 'label': row['label'], 'standard': 'NASEM_2021',
                       'readiness': 'requires_additional_inputs' if missing else 'ready',
                       'missing_inputs': missing, 'requires_additional_data': bool(missing),
                       'profile_source': row['source'], 'assumption_type': row['assumption_type']})
    return result


def calculate(payload, include_native=False):
    if not isinstance(payload, dict):
        return {'status': 'invalid_input', 'message': 'Animal input must be an object.', 'missing_inputs': []}
    category = payload.get('animal_category')
    profile = profiles().get(category)
    if profile is None:
        return {'status': 'unsupported_category', 'missing_inputs': [], 'message': 'Unsupported animal category.'}
    try:
        weight = parse_number(payload.get('body_weight_kg'), 'body_weight_kg', minimum=0)
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {'status': 'incomplete_input', 'animal_category': category,
                'missing_inputs': ['body_weight_kg'], 'message': 'A positive body weight is required.'}
    overrides = payload.get('parameters', {})
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict) or set(overrides) - set(PARAMETERS):
        return {'status': 'invalid_input', 'message': 'Invalid profile parameters.', 'missing_inputs': []}
    values = {}
    missing = []
    for key in PARAMETERS:
        raw = overrides.get(key, profile[key])
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            values[key] = None
            if key not in OPTIONAL:
                missing.append(key)
        elif key in NUMERIC:
            try:
                value = parse_numeric_parameter(key, raw)
                values[key] = value
            except (TypeError, ValueError):
                return {'status': 'invalid_input', 'message': f'Invalid value for {key}.', 'missing_inputs': []}
        else:
            if key == 'housing' and raw not in HOUSING_TYPES:
                return {'status': 'invalid_input', 'message': 'Invalid housing type.', 'missing_inputs': []}
            values[key] = str(raw)
    base = {'animal_category': category, 'body_weight_kg': weight,
            'nutritional_standard': 'NASEM_2021', 'profile_source': profile['source'],
            'assumption_type': profile['assumption_type'], 'parameters': values,
            'missing_inputs': missing}
    if missing:
        return {**base, 'status': 'incomplete_input', 'requirements': {}, 'constraints': {}}
    try:
        result = NASEMRequirementsCalculator.calculate_requirements(
            body_weight=weight, mature_body_weight=values['mature_body_weight'],
            day_of_pregnancy=values['day_of_pregnancy'],
            body_condition_score_5=values['body_condition_score_5'],
            days_in_milk=int(values['days_in_milk']),
            average_daily_gain_heifer=values['average_daily_gain_heifer'],
            animal_type=AnimalType[profile['animal_type']], parity=int(profile['parity']),
            calving_interval=int(values['calving_interval']), milk_fat=values['milk_fat'],
            milk_true_protein=values['milk_true_protein'], milk_lactose=values['milk_lactose'],
            milk_production=values['milk_production'], housing=values['housing'],
            distance=values['distance'], lactating=profile['lactating'].lower() == 'true',
            ndf_percentage=values['ndf_percentage'],
            process_based_phosphorus_requirement=values['process_based_phosphorus_requirement'],
        )
        requirements = {'net_energy': result.total_energy_requirement,
                        'metabolizable_protein': result.metabolizable_protein,
                        'calcium': result.calcium, 'phosphorus': result.phosphorus,
                        'dry_matter': result.dry_matter}
        if any(not math.isfinite(value) or value < 0 for value in requirements.values()):
            raise ValueError('The calculator returned invalid nutritional values.')
    except (ValueError, TypeError, ArithmeticError, KeyError) as error:
        return {**base, 'status': 'calculation_error', 'message': str(error),
                'requirements': {}, 'constraints': {}}
    with (DATA / 'nutritional_constraint_rules.csv').open(newline='', encoding='utf-8') as stream:
        rules = list(csv.DictReader(stream))
    constraints = {rule['nutrient']: {'minimum': None if rule['nutrient'] == 'dry_matter' else requirements[rule['nutrient']],
                    'maximum': None, 'unit': rule['unit'],
                    'minimum_source': rule['minimum_source'],
                    'maximum_source': rule['maximum_source'],
                    'reference': rule['reference'],
                    'status': 'requires_ration_configuration' if rule['nutrient'] == 'dry_matter' else
                              'preliminary_diet_dependent' if rule['nutrient'] == 'metabolizable_protein' else 'calculated'} for rule in rules}
    response = {**base, 'status': 'success', 'constraints_status': 'partial', 'requirements': requirements, 'constraints': constraints}
    if include_native:
        response['_native_requirements'] = result
    return response
