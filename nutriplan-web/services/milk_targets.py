"""Discrete milk targets evaluated through independent native formulations."""
from services.emissions import CandidateEmissionEstimationError
from services.native_ration import optimize_native
from services.numbers import parse_number

MAX_TARGETS = 8
TARGET_STEP_KG_DAY = 1


def _solve(payload, level):
    parameters = {**(payload.get('parameters') or {}), 'milk_production': level}
    try:
        result = optimize_native({**payload, 'parameters': parameters})
    except CandidateEmissionEstimationError:
        result = {'ok': False, 'status': 'calculation_error', 'error_code': 'emissions_unavailable'}
    return {**result, 'milk_target': level}


def _summarize(result):
    constraints = result.get('constraints')
    return {
        'milk_target': result['milk_target'], 'status': result['status'],
        'cost_day': result.get('cost_day'), 'dmi': result.get('dmi'),
        'error_code': result.get('error_code'), 'solver_status': result.get('solver_status'),
        'constraints_met': sum(item['satisfied'] for item in constraints) if constraints else None,
        'constraints_total': len(constraints) if constraints else None,
        'ingredients': [
            {key: row[key] for key in ('id', 'name', 'kg_dm', 'kg_as_fed')}
            for row in result.get('ingredients', ()) if row['kg_dm'] > 1e-6
        ],
    }


def _integrated_formulation(payload):
    parameters = payload.get('parameters') or {}
    level = parse_number(parameters.get('milk_production'), 'milk_production', minimum=0)
    reference = _solve(payload, level)
    if reference['status'] in ('unsupported_category', 'incomplete_input', 'invalid_input'):
        return reference

    # The resolution and number of runs bound the search. Each target still
    # needs to pass the native physiological and feed constraints individually.
    levels = sorted({level + step * TARGET_STEP_KG_DAY for step in range(MAX_TARGETS)} - {level})
    tested = [reference, *(_solve(payload, target) for target in levels)]
    feasible = [result for result in tested if result['ok']]
    rows = []
    for result in tested:
        row = _summarize(result)
        row['non_dominated'] = result['ok'] and not any(
            other['cost_day'] <= result['cost_day'] and other['milk_target'] >= result['milk_target']
            and (other['cost_day'] < result['cost_day'] or other['milk_target'] > result['milk_target'])
            for other in feasible
        )
        rows.append(row)
    highest = feasible[-1] if feasible else None
    primary = reference if reference['ok'] or highest is None else highest
    return {**primary, 'reference_result': reference, 'highest_feasible_result': highest,
            'target_results': rows}


def formulate(payload):
    if payload.get('evaluate_milk_targets') is True:
        return _integrated_formulation(payload)

    # Preserve the fixed and explicit-target contracts for existing API callers.
    targets = payload.get('milk_targets')
    if targets is None:
        return optimize_native(payload)
    if not isinstance(targets, list) or not 2 <= len(targets) <= MAX_TARGETS:
        raise ValueError('Two to eight milk targets are required.')
    levels = sorted({parse_number(item, 'milk target', minimum=0) for item in targets})
    if len(levels) != len(targets):
        raise ValueError('Duplicate milk target.')
    tested = [_solve(payload, level) for level in levels]
    primary = next((result for result in reversed(tested) if result['ok']), tested[0])
    return {**primary, 'target_results': [_summarize(result) for result in tested]}
