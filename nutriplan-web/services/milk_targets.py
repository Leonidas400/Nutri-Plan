"""Discrete milk targets evaluated through independent native formulations."""
import math
from services.emissions import CandidateEmissionEstimationError
from services.milk_potential import resolve_reference
from services.native_ration import LACTATING_CATEGORIES, automatic_candidates, optimize_native
from services.numbers import parse_number

MAX_TARGETS = 8
TARGET_STEP_KG_DAY = 1
TARGETS_PER_SIDE = 7
DEFAULT_ALTERNATIVE_SAMPLES = 300
DEFAULT_BEYOND_ATTEMPTS = 6
MAX_BEYOND_SOLUTIONS = 6


def _solve(payload, level, allow_below_reference=False):
    parameters = {**(payload.get('parameters') or {}), 'milk_production': level}
    try:
        result = optimize_native({
            **payload, 'parameters': parameters,
            'allow_below_reference': allow_below_reference,
        })
    except CandidateEmissionEstimationError:
        result = {'ok': False, 'status': 'calculation_error', 'error_code': 'emissions_unavailable'}
    return {**result, 'milk_target': level}


def _summarize(result):
    constraints = result.get('constraints')
    potential = result.get('milk_potential') or {}
    return {
        'milk_target': result['milk_target'], 'status': result['status'],
        'cost_day': result.get('cost_day'), 'dmi': result.get('dmi'),
        'error_code': result.get('error_code'), 'solver_status': result.get('solver_status'),
        'milk_allowed': potential.get('allowed_kg_day'),
        'milk_allowed_energy': potential.get('allowed_energy_kg_day'),
        'milk_allowed_protein': potential.get('allowed_protein_kg_day'),
        'milk_floor_margin': potential.get('margin_kg_day'),
        'milk_status': potential.get('status'),
        'milk_floor_enforced': result.get('milk_floor_enforced'),
        'below_reference': potential.get('status') == 'below_reference',
        'floor_violated': (
            potential.get('status') == 'below_reference'
            or (potential.get('margin_kg_day') is not None and potential['margin_kg_day'] < -1e-4)
        ),
        'constraints_met': sum(item['satisfied'] for item in constraints) if constraints else None,
        'constraints_total': len(constraints) if constraints else None,
        'ingredients': [
            {key: row[key] for key in ('id', 'name', 'kg_dm', 'kg_as_fed')}
            for row in result.get('ingredients', ()) if row['kg_dm'] > 1e-6
        ],
    }


def _point_milk(row):
    value = row.get('milk_allowed')
    return value if value is not None else row.get('milk_target')


def _mark_non_dominated(rows):
    feasible = [
        row for row in rows
        if row['status'] == 'success' and row.get('cost_day') is not None
        and _point_milk(row) is not None
    ]
    for row in rows:
        row['non_dominated'] = row['status'] == 'success' and not any(
            other['cost_day'] <= row['cost_day']
            and _point_milk(other) >= _point_milk(row)
            and (other['cost_day'] < row['cost_day'] or _point_milk(other) > _point_milk(row))
            for other in feasible
        )
    return rows


def _mark_alternatives(alternatives, optimal_rows):
    points = []
    for row in optimal_rows:
        milk = _point_milk(row)
        if row['status'] == 'success' and row.get('cost_day') is not None and milk is not None:
            points.append({'milk_allowed': float(milk), 'cost_day': float(row['cost_day']),
                           'source': 'target', 'row': row})
    for alternative in alternatives:
        points.append({'milk_allowed': float(alternative['milk_allowed']),
                       'cost_day': float(alternative['cost_day']),
                       'source': 'alternative', 'row': alternative})
    for point in points:
        point['dominated'] = any(
            other is not point
            and other['cost_day'] <= point['cost_day']
            and other['milk_allowed'] >= point['milk_allowed']
            and (other['cost_day'] < point['cost_day']
                 or other['milk_allowed'] > point['milk_allowed'])
            for other in points
        )
        if point['source'] == 'alternative':
            point['row']['dominated'] = point['dominated']
    frontier = [
        {'milk_allowed': point['milk_allowed'], 'cost_day': point['cost_day'],
         'source': point['source']}
        for point in points if not point['dominated']
    ]
    frontier.sort(key=lambda point: point['milk_allowed'])
    return frontier


def _frontier(rows):
    return [
        {
            'milk_target': row['milk_target'],
            'cost_day': row['cost_day'],
            'milk_allowed': row['milk_allowed'],
            'milk_allowed_energy': row['milk_allowed_energy'],
            'milk_allowed_protein': row['milk_allowed_protein'],
        }
        for row in rows if row.get('non_dominated')
    ]


def _integrated_formulation(payload):
    parameters = payload.get('parameters') or {}
    level = parse_number(parameters.get('milk_production'), 'milk_production', minimum=0)
    reference_milk = parse_number(payload.get('milk_reference_kg_day'), 'milk_reference_kg_day', minimum=0)
    base = max(level, reference_milk)
    explore = payload.get('explore_alternatives') is True
    try:
        total_samples = int(payload.get('alternative_samples', DEFAULT_ALTERNATIVE_SAMPLES))
    except (TypeError, ValueError):
        total_samples = DEFAULT_ALTERNATIVE_SAMPLES
    left = [base - step * TARGET_STEP_KG_DAY for step in range(1, TARGETS_PER_SIDE + 1)
            if base - step * TARGET_STEP_KG_DAY >= 0]
    right = [base + step * TARGET_STEP_KG_DAY for step in range(1, TARGETS_PER_SIDE + 1)]
    levels = sorted(set(left + right))
    per_target_samples = max(0, total_samples // (len(levels) + 1)) if explore else 0
    explore_payload = {
        **payload,
        'explore_alternatives': explore,
        'alternative_samples_per_target': per_target_samples,
    }
    reference = _solve(explore_payload, base, allow_below_reference=False)
    if reference['status'] in ('unsupported_category', 'incomplete_input', 'invalid_input'):
        return reference

    # The resolution and number of runs bound the search. Each target still
    # needs to pass the native physiological and feed constraints individually.
    tested = [reference, *(
        _solve(explore_payload, target, allow_below_reference=True) for target in levels
    )]
    feasible = [result for result in tested if result['ok']]
    floor_feasible = [
        result for result in feasible
        if result['milk_target'] >= reference_milk - 1e-9
    ]
    highest = (
        max(floor_feasible, key=lambda result: result['milk_target'])
        if floor_feasible else None
    )
    rows = _mark_non_dominated([_summarize(result) for result in tested])
    alternatives = []
    seen = set()
    for result in tested:
        for alternative in result.get('alternative_solutions', ()):
            key = (round(alternative['cost_day'], 4), round(alternative['milk_allowed'], 4))
            if key in seen:
                continue
            seen.add(key)
            alternatives.append({
                **alternative,
                'target': result.get('milk_target', alternative.get('target')),
            })
    exploration_frontier = _mark_alternatives(alternatives, rows) if explore else []
    beyond = []
    if highest is not None:
        try:
            attempts = int(payload.get('beyond_optimum_attempts', DEFAULT_BEYOND_ATTEMPTS))
        except (TypeError, ValueError):
            attempts = DEFAULT_BEYOND_ATTEMPTS
        attempts = max(0, min(attempts, 12))
        max_milk = float(highest['milk_target'])
        max_cost = float(highest['cost_day'])
        current = {
            int(item['id']): float(item['kg_dm'])
            for item in highest.get('ingredients', ())
        }
        base_candidates = payload.get('feeds')
        if not isinstance(base_candidates, list) or len(base_candidates) < 2:
            base_candidates = automatic_candidates()
        candidates = [dict(item) for item in base_candidates if item.get('available', True)]
        candidates.sort(key=lambda item: current.get(int(item['rufas_id']), 0.0))
        seen_beyond = set()
        for candidate in candidates[:attempts]:
            identifier = int(candidate['rufas_id'])
            existing = current.get(identifier, 0.0)
            maximum = float(candidate.get('maximum_kg_dm', 100) or 100)
            forced_amount = min(max(1.0, existing + 0.5), maximum)
            if forced_amount <= existing + 1e-6:
                continue
            forced = [dict(item) for item in candidates]
            for item in forced:
                if int(item['rufas_id']) == identifier:
                    item['minimum_kg_dm'] = forced_amount
                    break
            forced_payload = {
                **payload,
                'feeds': forced,
                'explore_alternatives': False,
                'alternative_samples_per_target': 0,
                'allow_below_reference': True,
            }
            try:
                forced_result = _solve(forced_payload, max_milk, allow_below_reference=True)
            except (ArithmeticError, TypeError, ValueError):
                continue
            if not forced_result.get('ok'):
                continue
            potential = forced_result.get('milk_potential') or {}
            milk = potential.get('allowed_kg_day')
            cost = forced_result.get('cost_day')
            if not isinstance(milk, (int, float)) or not isinstance(cost, (int, float)):
                continue
            if not math.isfinite(milk) or not math.isfinite(cost):
                continue
            if milk > max_milk + 1e-4 or cost < max_cost - 1e-4:
                continue
            key = (round(float(cost), 4), round(float(milk), 4))
            if key in seen_beyond:
                continue
            seen_beyond.add(key)
            beyond.append({
                'milk_allowed': float(milk), 'cost_day': float(cost),
                'target': max_milk,
                'below_reference': float(milk) < float(reference_milk) - 1e-4,
                'dominated': True,
            })
            if len(beyond) >= MAX_BEYOND_SOLUTIONS:
                break
        beyond.sort(key=lambda item: (item['cost_day'], -item['milk_allowed']))
    primary = reference if reference['ok'] or highest is None else highest
    return {**primary, 'reference_result': reference, 'highest_feasible_result': highest,
            'target_results': rows, 'frontier': _frontier(rows),
            'alternative_solutions': alternatives,
            'beyond_optimum_solutions': beyond,
            'exploration_frontier': exploration_frontier}


def formulate(payload):
    if not isinstance(payload, dict):
        raise ValueError('Milk target input must be an object.')
    if payload.get('animal_category') not in LACTATING_CATEGORIES:
        return optimize_native(payload)
    reference, _ = resolve_reference(payload)
    # Share one production reference across every target so the floor does not
    # change with the tested target.
    payload = {**payload, 'milk_reference_kg_day': reference}

    if payload.get('evaluate_milk_targets') is True:
        return _integrated_formulation(payload)

    # Preserve the fixed and explicit-target contracts for existing API callers.
    targets = payload.get('milk_targets')
    if targets is None:
        return optimize_native(payload)
    if not isinstance(targets, list) or not 2 <= len(targets) <= MAX_TARGETS:
        raise ValueError('Two to eight milk targets are required.')
    levels = sorted({max(parse_number(item, 'milk target', minimum=0), reference) for item in targets})
    if len(levels) < 2:
        raise ValueError('Two distinct milk targets are required.')
    tested = [_solve(payload, level) for level in levels]
    primary = next((result for result in reversed(tested) if result['ok']), tested[0])
    rows = _mark_non_dominated([_summarize(result) for result in tested])
    return {**primary, 'target_results': rows, 'frontier': _frontier(rows)}
