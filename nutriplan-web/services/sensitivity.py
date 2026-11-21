"""Sensitivity analysis: repeated native optimization under controlled input changes.

The analysis reruns the existing RuFaS RationOptimizer pipeline while modifying a
single input at a time. SLSQP convergence does not prove global optimality, prices
simulated here are hypothetical, and no classical LP shadow prices are computed.
"""
from __future__ import annotations

import copy
import math

from services.numbers import parse_number
from services.native_ration import feed_library, optimize_native
from services.prices import resolve_price

MAX_PRICE_VARIATIONS = 9
MAX_AVAILABILITY_VARIATIONS = 5


def _experiment_shell(experiment_id, label, modified_input, modification, result, error=None):
    shell = {'experiment_id': experiment_id, 'label': label,
             'modified_input': modified_input, 'modification': modification}
    if error is not None:
        result = {'ok': False, 'status': 'experiment_error', 'message': str(error)}
    shell.update({'ok': result.get('ok', False), 'status': result.get('status', 'unknown'),
                  'error_code': result.get('error_code'),
                  'solver_status': result.get('solver_status'),
                  'dmi': result.get('dmi'), 'cost_day': result.get('cost_day'),
                  'currency': result.get('currency'),
                  'cost_month': result.get('cost_month'),
                  'ingredients': result.get('ingredients'),
                  'constraints': result.get('constraints'),
                  'message': result.get('message')})
    return shell


def _summarize(experiments, reference_index):
    feasible = [experiment for experiment in experiments if experiment['ok']]
    costs = [experiment['cost_day'] for experiment in feasible
             if experiment['cost_day'] is not None]
    summary = {'total': len(experiments), 'feasible': len(feasible),
               'infeasible': len(experiments) - len(feasible)}
    if costs:
        summary['min_cost_day'] = min(costs)
        summary['max_cost_day'] = max(costs)
        summary['cost_variation_pct'] = ((max(costs) - min(costs)) / min(costs) * 100
                                         if len(costs) >= 2 and min(costs) > 0
                                         else None)
    else:
        summary['min_cost_day'] = None
        summary['max_cost_day'] = None
        summary['cost_variation_pct'] = None
    reference = experiments[reference_index] if 0 <= reference_index < len(experiments) else None
    if reference is None or not reference['ok'] or reference['cost_day'] is None:
        reference_cost = None
    else:
        reference_cost = reference['cost_day']
    for experiment in experiments:
        cost = experiment['cost_day']
        if reference_cost is None or cost is None or experiment is reference:
            experiment['cost_difference'] = None
            experiment['cost_difference_pct'] = None
        else:
            experiment['cost_difference'] = cost - reference_cost
            experiment['cost_difference_pct'] = (100 * (cost - reference_cost) / reference_cost
                                                 if reference_cost > 0 else None)
    return summary


def _find_candidate(configuration, rufas_id):
    if not isinstance(configuration, dict) or not isinstance(configuration.get('feeds'), list):
        raise ValueError('Sensitivity requires a formulation with a list of candidate feeds.')
    identifier = parse_number(rufas_id, 'Candidate feed ID', integer=True, minimum=1)
    for position, item in enumerate(configuration['feeds']):
        if not isinstance(item, dict):
            raise ValueError('Each candidate feed must be an object.')
        if (parse_number(item.get('rufas_id'), 'Candidate feed ID', integer=True) == identifier
                and item.get('available', True)):
            return position, item
    raise ValueError(f'Unknown or unavailable feed ID: {identifier}.')


def run_price_sensitivity(configuration, rufas_id, variation_pcts):
    """Rerun native optimization with one feed price scaled by finite percentages."""
    if not isinstance(variation_pcts, list) or not variation_pcts:
        raise ValueError('Price variations must be a non-empty list of percentages.')
    if len(variation_pcts) > MAX_PRICE_VARIATIONS:
        raise ValueError(f'At most {MAX_PRICE_VARIATIONS} price variations are allowed per request.')
    for index, pct in enumerate(variation_pcts):
        if isinstance(pct, bool) or not isinstance(pct, (int, float)) or not math.isfinite(pct):
            raise ValueError(f'Variation {index}: percentage must be a finite number.')
        if pct <= -100:
            raise ValueError(f'Variation {index}: percentage must be greater than -100 '
                             'so the simulated price stays above zero.')
        if abs(pct) > 1000:
            raise ValueError(f'Variation {index}: percentage is unreasonably large (cap 1000%).')
    position, target = _find_candidate(configuration, rufas_id)
    identifier = int(target['rufas_id'])
    original_record = resolve_price(target, feed_library())
    if original_record is None:
        raise ValueError(f'Feed {identifier}: no documented price for sensitivity simulation.')
    original_amount = original_record['amount']
    if original_amount <= 0:
        raise ValueError(f'Feed {identifier}: original price amount must be positive '
                         'for sensitivity simulation.')
    experiments = []
    for index, pct in enumerate(variation_pcts):
        modified_amount = round(original_amount * (1 + pct / 100), 6) if pct else original_amount
        modification = {'type': 'price', 'rufas_id': identifier,
                        'original_amount': original_amount, 'amount': modified_amount,
                        'variation_pct': pct, 'currency': original_record.get('currency'),
                        'unit': original_record.get('unit'),
                        'original_source_type': original_record.get('source_type'),
                        'original_source': original_record.get('source'),
                        'original_reference_date': original_record.get('reference_date'),
                        'hypothetical': True}
        if modified_amount <= 0:
            experiments.append(_experiment_shell(
                f'experiment_{index + 1}', f'price variation {pct:+g}%', 'price', modification,
                {'ok': False, 'status': 'invalid_price',
                 'message': f'Simulated price for feed {identifier} would be {modified_amount}.'}))
            continue
        try:
            modified_config = copy.deepcopy(configuration)
            if pct:
                item = modified_config['feeds'][position]
                if original_record['source_type'] == 'legacy_unspecified':
                    item['price_as_fed'] = modified_amount
                else:
                    item.pop('price_as_fed', None)
                    item['price_record'] = {
                        **original_record, 'amount': modified_amount,
                        'notes': f'Hypothetical sensitivity value: {pct:+g}% for feed {identifier}.',
                    }
                    if original_record['source_type'] == 'preloaded':
                        item['price_record'].update(source_type='current', currency='BRL')
            result = optimize_native(modified_config)
            experiments.append(_experiment_shell(
                f'experiment_{index + 1}', f'price variation {pct:+g}%', 'price',
                modification, result))
        except (ValueError, KeyError, TypeError) as error:
            experiments.append(_experiment_shell(
                f'experiment_{index + 1}', f'price variation {pct:+g}%', 'price',
                modification, None, error=error))
    reference_index = variation_pcts.index(0) if 0 in variation_pcts else -1
    summary = _summarize(experiments, reference_index)
    return {'ok': True, 'mode': 'price_sensitivity',
            'experiments': experiments, 'summary': summary}


def run_availability_sensitivity(configuration, rufas_id, variations):
    """Rerun native optimization with one feed's availability or inclusion bounds changed."""
    if not isinstance(variations, list) or not variations:
        raise ValueError('Availability experiments must be a non-empty list.')
    if len(variations) > MAX_AVAILABILITY_VARIATIONS:
        raise ValueError(f'At most {MAX_AVAILABILITY_VARIATIONS} availability experiments '
                         'are allowed per request.')
    states = []
    for index, variation in enumerate(variations):
        if not isinstance(variation, dict):
            raise ValueError(f'Variation {index}: must be an object.')
        kind = variation.get('type')
        if kind not in ('baseline', 'exclude', 'bound'):
            raise ValueError(f'Variation {index}: unsupported experiment type {kind!r}.')
        if kind == 'bound' and variation.get('minimum_kg_dm') is None \
                and variation.get('maximum_kg_dm') is None:
            raise ValueError(f'Variation {index}: bound experiment requires a minimum or maximum.')
        minimum = parse_number(variation.get('minimum_kg_dm'), f'Variation {index} minimum',
                               optional=True)
        maximum = parse_number(variation.get('maximum_kg_dm'), f'Variation {index} maximum',
                               optional=True)
        if minimum is not None and minimum < 0 or maximum is not None and maximum < 0:
            raise ValueError(f'Variation {index}: inclusion bounds cannot be negative.')
        if minimum is not None and maximum is not None and maximum < minimum:
            raise ValueError(f'Variation {index}: inclusion maximum is below minimum.')
        states.append({'type': kind, 'minimum_kg_dm': minimum, 'maximum_kg_dm': maximum})
    position, target = _find_candidate(configuration, rufas_id)
    identifier = int(target['rufas_id'])
    original_minimum = parse_number(target.get('minimum_kg_dm', 0), f'Feed {identifier} minimum')
    original_maximum = parse_number(target.get('maximum_kg_dm'), f'Feed {identifier} maximum')
    experiments = []
    for index, state in enumerate(states):
        modification = {'type': state['type'], 'rufas_id': identifier,
                        'original_minimum_kg_dm': original_minimum,
                        'original_maximum_kg_dm': original_maximum,
                        'new_minimum_kg_dm': original_minimum,
                        'new_maximum_kg_dm': original_maximum,
                        'configuration_modified': state['type'] != 'baseline'}
        try:
            modified_config = copy.deepcopy(configuration)
            item = modified_config['feeds'][position]
            if state['type'] == 'exclude':
                item['available'] = False
            elif state['type'] == 'bound':
                for key in ('minimum_kg_dm', 'maximum_kg_dm'):
                    if state[key] is not None:
                        item[key] = state[key]
                        modification[f'new_{key}'] = state[key]
            result = optimize_native(modified_config)
            experiments.append(_experiment_shell(
                f'experiment_{index + 1}', f"availability {state['type']}", 'availability',
                modification, result))
        except (ValueError, KeyError, TypeError) as error:
            experiments.append(_experiment_shell(
                f'experiment_{index + 1}', f"availability {state['type']}", 'availability',
                modification, None, error=error))
    baseline_index = next((position for position, state in enumerate(states)
                           if state['type'] == 'baseline'), -1)
    summary = _summarize(experiments, baseline_index)
    return {'ok': True, 'mode': 'availability_sensitivity',
            'experiments': experiments, 'summary': summary}


def run_sensitivity(request):
    """Dispatch a sensitivity analysis request to the selected experiment family."""
    if not isinstance(request, dict):
        raise ValueError('Sensitivity request must be a JSON object.')
    mode = request.get('mode')
    if mode == 'price_sensitivity':
        if request.get('rufas_id') in (None, ''):
            raise ValueError('Price sensitivity requires a candidate rufas_id.')
        return run_price_sensitivity(request.get('configuration'), request['rufas_id'],
                                     request.get('variations'))
    if mode == 'availability_sensitivity':
        if request.get('rufas_id') in (None, ''):
            raise ValueError('Availability sensitivity requires a candidate rufas_id.')
        return run_availability_sensitivity(request.get('configuration'), request['rufas_id'],
                                            request.get('variations'))
    raise ValueError(f'Unknown sensitivity analysis mode: {mode}.')
