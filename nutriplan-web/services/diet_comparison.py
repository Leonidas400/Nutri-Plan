"""Evaluate both rations at the same animal requirements and current prices."""
import math
import numpy as np
from RUFAS.biophysical.animal.ration.ration_optimizer import RationConfig, RationOptimizer
from RUFAS.biophysical.animal.nutrients.nutrition_supply_calculator import NutritionSupplyCalculator
from services.emissions import calculate_ration_emissions
from services.prices import default_price
from services.numbers import parse_number


def _evaluate(ration, config, emissions):
    """Reuse the native solver constraints with this ration's own feed matrix."""
    local = RationConfig(config.nutrient_standard, config.animal_requirements,
                        [item.info for item in ration], config.initial_dry_matter_requirement,
                        config.initial_protein_requirement, config.pen_average_body_weight,
                        emissions.get('enteric_methane_g_day'), emissions.get('urine_nitrogen_kg_day'),
                        config.animal_combination)
    amounts = np.array([item.amount for item in ration])
    optimizer = RationOptimizer()
    optimizer.set_constraints(local)
    def evaluate(function):
        try:
            value = float(function())
            return value if math.isfinite(value) else None
        except (ArithmeticError, ValueError, TypeError):
            return None

    margins = {c['fun'].__name__: evaluate(lambda: c['fun'](amounts, local))
               for c in optimizer._select_constraints(config.animal_combination)}
    energy_margin = margins['NASEM_net_energy_constraint']
    protein = evaluate(lambda: optimizer._calculate_protein_constraint_parameters(amounts, local, False)[0])
    values = {
        'dry_matter': float(sum(amounts)),
        'energy': None if energy_margin is None else energy_margin + config.animal_requirements.total_energy_requirement,
        'protein': protein,
        'ndf': evaluate(lambda: NutritionSupplyCalculator._calculate_nutritive_content(ration, 'NDF')),
    }
    passed = None if None in margins.values() else sum(margin >= -1e-4 for margin in margins.values())
    return values, passed


def compare_rations(previous, optimized, config, prices, payload, animal, emissions):
    previous_emissions = emissions
    automatic = emissions['provenance'] == 'native_rufas_candidate_ration'
    if automatic:
        try:
            previous_emissions = calculate_ration_emissions(previous, animal)
        except (ValueError, ArithmeticError):
            previous_emissions = {}
    current, current_pass = _evaluate(previous, config, previous_emissions)
    proposed, proposed_pass = _evaluate(optimized, config, emissions)
    old = {i.info.rufas_id:i for i in previous}
    new = {i.info.rufas_id:i for i in optimized if i.amount > 0}
    lines = []
    currencies = set()
    cost = [0., 0.]
    missing = []
    previous_prices = {int(row['rufas_id']):row.get('current_price_brl') for row in payload['previous_ration']}
    confirmed = payload.get('confirm_catalog_prices') is True
    for key in sorted(old.keys() | new.keys()):
        feed = (old.get(key) or new[key]).info
        amounts = [old[key].amount if key in old else 0., new[key].amount if key in new else 0.]
        lines.append({'id': key, 'name': feed.Name, 'current': amounts[0], 'optimized': amounts[1]})
        record = prices.get(key) or {}
        source = record.get('source_type')
        price, currency = None, None
        if source == 'current' or (confirmed and source in {'manual', 'actual_cost', 'market_reference'}):
            price, currency = record['price_as_fed'], record['currency']
        elif previous_prices.get(key) not in (None,'') and key not in new:
            try:
                price = parse_number(previous_prices[key], 'price', minimum=0)
                currency = 'BRL'
            except ValueError:
                pass  # An unusable optional quote leaves nutrient comparisons available.
        elif confirmed and source in (None, 'preloaded'):
            price, currency = default_price(key), 'BRL'
        if price is None or not currency:
            missing.append(key)
        else:
            currencies.add(currency)
            for index, amount in enumerate(amounts):
                cost[index] += amount * price / (feed.DM / 100)
    comparable = not missing and len(currencies)==1
    return {'automatic_emissions':automatic, 'current':current, 'optimized':proposed, 'ingredients':lines,
            'constraints_met':[current_pass,proposed_pass], 'missing_prices':missing,
            'cost':cost if comparable else None, 'currency':next(iter(currencies)) if comparable else None}
