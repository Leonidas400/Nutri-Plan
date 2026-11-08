"""Sensitivity analysis: repeated native optimization under controlled input changes.

The analysis reruns the existing RuFaS RationOptimizer pipeline while modifying a
single input at a time. SLSQP convergence does not prove global optimality, prices
simulated here are hypothetical, and no classical LP shadow prices are computed.
"""
from __future__ import annotations

import copy
import json
import math

from services.native_ration import optimize_native
from services.scenarios import validate_scenario

MAX_PRICE_VARIATIONS = 9
MAX_AVAILABILITY_VARIATIONS = 5
MAX_COMPARISON_SCENARIOS = 4


def _float(value, label, allow_missing=False, default=None):
    """Coerce a scenario value to float, optionally tolerating absence."""
    if value in (None, ''):
        if allow_missing:
            return default
        raise ValueError(f'{label} is required.')
    if isinstance(value, bool):
        raise ValueError(f'{label}: invalid number.')
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'{label}: invalid number.') from error
    if not math.isfinite(result):
        raise ValueError(f'{label}: invalid number.')
    return result


def resolve_candidate_price(item, configuration):
    """Resolve the price record of a scenario feed item (explicit wins, then import)."""
    if item.get('price_record') is not None:
        return copy.deepcopy(item['price_record'])
    if item.get('price') not in (None, ''):
        return {'amount': _float(item['price'], f'Feed {item.get("rufas_id")} price'),
                'currency': item.get('currency'),
                'unit': item.get('price_unit') or 'kg_as_fed',
                'source_type': item.get('source_type') or 'manual',
                'source': item.get('source'),
                'reference_date': item.get('source_date') or None,
                'geography': item.get('geography') or '',
                'notes': item.get('price_notes') or ''}
    imported = configuration.get('imported_prices') or []
    identifier = int(item.get('rufas_id'))
    for record in imported:
        if isinstance(record, dict) and int(record.get('rufas_id')) == identifier:
            return copy.deepcopy(record)
    return None


def configuration_to_rufas_payload(configuration):
    """Map a scenario configuration dict to the payload optimize_native() accepts.

    Mirrors the browser merge: explicit feed prices win, imported prices top up
    missing ones, previous ration supplies emissions unless explicit values exist.
    Never mutates the source configuration.
    """
    if not isinstance(configuration, dict):
        raise ValueError('Scenario configuration must be a JSON object.')
    config = copy.deepcopy(configuration)
    payload = {
        'animal_category': config.get('animal_category'),
        'body_weight_kg': _float(config.get('body_weight_kg'), 'Body weight',
                                 allow_missing=True),
        'parameters': copy.deepcopy(config.get('parameters') or {}),
        'feeds': [],
    }
    imported = config.get('imported_prices') or []
    for item in config.get('feeds') or []:
        identifier = _float(item.get('rufas_id'), 'Candidate RuFaS ID')
        identifier = int(identifier)
        available = item.get('available', True) is not False
        minimum = _float(item.get('minimum_kg_dm', item.get('min', 0)), f'Feed {identifier} minimum',
                         allow_missing=True, default=0)
        maximum = _float(item.get('maximum_kg_dm', item.get('max')), f'Feed {identifier} maximum',
                         allow_missing=True)
        if available and maximum is None:
            raise ValueError(f'Feed {identifier}: inclusion bounds are required.')
        feed_payload = {'rufas_id': identifier, 'available': available,
                        'minimum_kg_dm': minimum if minimum is not None else 0,
                        'maximum_kg_dm': maximum}
        record = resolve_candidate_price(item, config)
        if record is not None:
            feed_payload['price_record'] = record
        elif available:
            raise ValueError(f'Feed {identifier}: no documented price.')
        payload['feeds'].append(feed_payload)
    previous = config.get('previous_ration') or []
    items = []
    for item in previous:
        identifier = int(_float(item.get('rufas_id'), 'Previous-ration RuFaS ID'))
        entry = {'rufas_id': identifier,
                 'kg_dm_day': _float(item.get('kg_dm_day'), f'Feed {identifier} previous dry matter')}
        if item.get('price_record') is not None:
            entry['price_record'] = copy.deepcopy(item['price_record'])
        elif item.get('price_as_fed') not in (None, ''):
            entry['price_as_fed'] = _float(item['price_as_fed'], f'Feed {identifier} previous price')
        else:
            for record in imported:
                if isinstance(record, dict) and int(record.get('rufas_id')) == identifier:
                    entry['price_record'] = copy.deepcopy(record)
                    break
        items.append(entry)
    source = str(config.get('previous_ration_source') or '').strip()
    if items:
        if not source:
            raise ValueError('A documented previous-ration source is required.')
        payload['previous_ration'] = items
        payload['previous_ration_source'] = source
        return payload
    emissions = config.get('emissions') or {}
    methane = _float(emissions.get('enteric_methane_g_day'), 'Methane', allow_missing=True)
    urine = _float(emissions.get('urine_nitrogen_kg_day'), 'Urine nitrogen', allow_missing=True)
    if methane is not None and urine is not None:
        emission_source = str(emissions.get('emission_source') or '').strip()
        if not emission_source:
            raise ValueError('A documented emission source is required for explicit values.')
        payload['enteric_methane_g_day'] = methane
        payload['urine_nitrogen_kg_day'] = urine
        payload['emission_source'] = emission_source
    return payload


def _reference_file(scenario, config):
    reference = {'id': scenario.get('id'), 'name': scenario.get('name'),
                 'animal_category': config.get('animal_category'),
                 'body_weight_kg': config.get('body_weight_kg')}
    metadata = scenario.get('metadata') or {}
    for key in ('rufas_commit', 'feed_library_sha256'):
        if metadata.get(key):
            reference[key] = metadata[key]
    return reference


def _experiment_shell(experiment_id, label, modified_input, modification, result, error=None):
    shell = {'experiment_id': experiment_id, 'label': label,
             'modified_input': modified_input, 'modification': modification}
    if error is not None:
        result = {'ok': False, 'status': 'experiment_error', 'message': str(error)}
    shell.update({'ok': result.get('ok', False), 'status': result.get('status', 'unknown'),
                  'solver_status': result.get('solver_status'),
                  'dmi': result.get('dmi'), 'cost_day': result.get('cost_day'),
                  'cost_month': result.get('cost_month'),
                  'ingredients': result.get('ingredients'),
                  'constraints': result.get('constraints'),
                  'message': result.get('message')})
    return shell


def _summarize(experiments, reference_index, comparable=True):
    feasible = [experiment for experiment in experiments if experiment['ok']]
    costs = [experiment['cost_day'] for experiment in feasible
             if experiment['cost_day'] is not None]
    summary = {'total': len(experiments), 'feasible': len(feasible),
               'infeasible': len(experiments) - len(feasible)}
    if costs:
        summary['min_cost_day'] = min(costs)
        summary['max_cost_day'] = max(costs)
        summary['cost_variation_pct'] = ((max(costs) - min(costs)) / min(costs) * 100
                                         if comparable and len(costs) >= 2 and min(costs) > 0
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


def _prepare(scenario, rufas_id, variations_variants):
    """Shared validation for single-feed experiments: returns (config, feed item)."""
    validate_scenario(scenario)
    config = scenario.get('configuration') or {}
    identifier = int(rufas_id)
    target = None
    for item in config.get('feeds') or []:
        if int(item.get('rufas_id')) == identifier:
            target = item
            break
    if target is None:
        raise ValueError(f'Unknown feed ID: {identifier}.')
    return config, target


def run_price_sensitivity(scenario, rufas_id, variation_pcts):
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
    config, target = _prepare(scenario, rufas_id, variation_pcts)
    identifier = int(rufas_id)
    original_record = resolve_candidate_price(target, config)
    if original_record is None:
        raise ValueError(f'Feed {identifier}: no documented price for sensitivity simulation.')
    original_amount = _float(original_record.get('amount'), f'Feed {identifier} original price')
    if original_amount <= 0:
        raise ValueError(f'Feed {identifier}: original price amount must be positive '
                         'for sensitivity simulation.')
    experiments = []
    for index, pct in enumerate(variation_pcts):
        modified_amount = round(original_amount * (1 + pct / 100), 6)
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
            modified_config = copy.deepcopy(config)
            item = next(feed for feed in modified_config['feeds']
                        if int(feed.get('rufas_id')) == identifier)
            item['price_record'] = {**original_record, 'amount': modified_amount,
                                    'notes': (f'Hypothetical sensitivity value: {pct:+g}% '
                                              f'applied to feed {identifier} (original amount '
                                              f'{original_amount})')}
            result = optimize_native(configuration_to_rufas_payload(modified_config))
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
            'reference': _reference_file(scenario, config),
            'experiments': experiments, 'summary': summary}


def run_availability_sensitivity(scenario, rufas_id, variations):
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
        minimum = _float(variation.get('minimum_kg_dm'), f'Variation {index} minimum',
                         allow_missing=True)
        maximum = _float(variation.get('maximum_kg_dm'), f'Variation {index} maximum',
                         allow_missing=True)
        if minimum is not None and minimum < 0 or maximum is not None and maximum < 0:
            raise ValueError(f'Variation {index}: inclusion bounds cannot be negative.')
        if minimum is not None and maximum is not None and maximum < minimum:
            raise ValueError(f'Variation {index}: inclusion maximum is below minimum.')
        states.append({'type': kind, 'minimum_kg_dm': minimum, 'maximum_kg_dm': maximum})
    config, target = _prepare(scenario, rufas_id, states)
    identifier = int(rufas_id)
    original_minimum = _float(target.get('minimum_kg_dm', target.get('min', 0)),
                              f'Feed {identifier} minimum', allow_missing=True)
    original_maximum = _float(target.get('maximum_kg_dm', target.get('max')),
                              f'Feed {identifier} maximum', allow_missing=True)
    experiments = []
    for index, state in enumerate(states):
        modification = {'type': state['type'], 'rufas_id': identifier,
                        'original_minimum_kg_dm': original_minimum,
                        'original_maximum_kg_dm': original_maximum,
                        'new_minimum_kg_dm': original_minimum,
                        'new_maximum_kg_dm': original_maximum,
                        'configuration_modified': state['type'] != 'baseline'}
        try:
            modified_config = copy.deepcopy(config)
            item = next(feed for feed in modified_config['feeds']
                        if int(feed.get('rufas_id')) == identifier)
            if state['type'] == 'exclude':
                item['available'] = False
            elif state['type'] == 'bound':
                if state['minimum_kg_dm'] is not None:
                    item['min'] = state['minimum_kg_dm']
                if state['maximum_kg_dm'] is not None:
                    item['max'] = state['maximum_kg_dm']
                modification['new_minimum_kg_dm'] = _float(
                    item.get('minimum_kg_dm', item.get('min')), f'Feed {identifier} minimum',
                    allow_missing=True)
                modification['new_maximum_kg_dm'] = _float(
                    item.get('maximum_kg_dm', item.get('max')), f'Feed {identifier} maximum',
                    allow_missing=True)
            result = optimize_native(configuration_to_rufas_payload(modified_config))
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
            'reference': _reference_file(scenario, config),
            'experiments': experiments, 'summary': summary}


def _scenario_prices(scenario):
    """Resolved candidate price records of a scenario, for comparability checks."""
    config = scenario.get('configuration') or {}
    return [resolve_candidate_price(item, config) for item in config.get('feeds') or []
            if isinstance(item, dict)]


def run_scenario_comparison(scenarios):
    """Validate and run several saved scenarios with the identical native pipeline."""
    if not isinstance(scenarios, list):
        raise ValueError('Scenario comparison requires a list of scenarios.')
    if not 2 <= len(scenarios) <= MAX_COMPARISON_SCENARIOS:
        raise ValueError(f'Scenario comparison requires 2 to {MAX_COMPARISON_SCENARIOS} scenarios.')
    identifiers = set()
    for scenario in scenarios:
        validate_scenario(scenario)
        identifier = scenario.get('id')
        if identifier in identifiers:
            raise ValueError(f'Duplicate scenario ID: {identifier}.')
        identifiers.add(identifier)
    experiments = []
    prices = []
    for position, scenario in enumerate(scenarios):
        config = scenario.get('configuration') or {}
        try:
            result = optimize_native(configuration_to_rufas_payload(config))
            shell = _experiment_shell(f'experiment_{position + 1}', scenario.get('name', ''),
                                      'none', {'type': 'none'}, result)
        except (ValueError, KeyError, TypeError) as error:
            shell = _experiment_shell(f'experiment_{position + 1}', scenario.get('name', ''),
                                      'none', {'type': 'none'}, None, error=error)
        shell['modification'].update(base_attributes(scenario, config))
        experiments.append(shell)
        prices.append(_scenario_prices(scenario))
    records = [record for scenario_prices in prices for record in scenario_prices
               if record is not None]
    currencies = {record.get('currency') for record in records}
    units = {record.get('unit') for record in records}
    dates = {record.get('reference_date') for record in records if record is not None}
    animals = [json.dumps({'animal_category': scenario['configuration'].get('animal_category'),
                           'body_weight_kg': scenario['configuration'].get('body_weight_kg'),
                           'parameters': scenario['configuration'].get('parameters')},
                          sort_keys=True, default=str)
               for scenario in scenarios]
    fingerprints = [json.dumps({'rufas_commit': (scenario.get('metadata') or {}).get('rufas_commit'),
                                'feed_library_sha256':
                                    (scenario.get('metadata') or {}).get('feed_library_sha256'),
                                'standard': (scenario.get('metadata') or {}).get('nutritional_standard')},
                               sort_keys=True, default=str)
                    for scenario in scenarios]
    currency_list = [record.get('currency') for record in records]
    comparability = {
        'same_currency': None not in currency_list and len(currencies) <= 1,
        'same_price_units': None not in units and len(units) <= 1,
        'applied_price_dates': None not in dates and len(dates) > 1,
        'same_animal_configuration': len(set(animals)) <= 1,
        'same_scientific_fingerprint': len(set(fingerprints)) <= 1,
    }
    comparability['costs_comparable'] = (comparability['same_currency']
                                         and comparability['same_price_units'])
    summary = _summarize(experiments, 0, comparable=comparability['costs_comparable'])
    return {'ok': True, 'mode': 'scenario_comparison',
            'experiments': experiments, 'comparability': comparability, 'summary': summary}


def base_attributes(scenario, config):
    """Top-level scenario identity recorded on every comparison experiment."""
    attributes = {'scenario_id': scenario.get('id')}
    metadata = scenario.get('metadata') or {}
    for key in ('rufas_commit', 'feed_library_sha256'):
        if metadata.get(key):
            attributes[key] = metadata[key]
    return attributes


def run_sensitivity(request):
    """Dispatch a sensitivity analysis request to the selected experiment family."""
    if not isinstance(request, dict):
        raise ValueError('Sensitivity request must be a JSON object.')
    mode = request.get('mode')
    if mode == 'price_sensitivity':
        if request.get('rufas_id') in (None, ''):
            raise ValueError('Price sensitivity requires a candidate rufas_id.')
        return run_price_sensitivity(request.get('scenario'), request['rufas_id'],
                                     request.get('variations'))
    if mode == 'availability_sensitivity':
        if request.get('rufas_id') in (None, ''):
            raise ValueError('Availability sensitivity requires a candidate rufas_id.')
        return run_availability_sensitivity(request.get('scenario'), request['rufas_id'],
                                            request.get('variations'))
    if mode == 'scenario_comparison':
        return run_scenario_comparison(request.get('scenarios'))
    raise ValueError(f'Unknown sensitivity analysis mode: {mode}.')
