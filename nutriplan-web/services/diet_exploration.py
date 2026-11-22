"""Sample feasible alternative diets around the cost-optimal rations."""
from __future__ import annotations

import math
import random

import numpy as np

from RUFAS.biophysical.animal.nutrients.nutrition_supply_calculator import FeedInRation

from services.emissions import CandidateEmissionEstimationError, calculate_candidate_ration_emissions
from services.milk_potential import FLOOR_TOLERANCE_KG_DAY, evaluate as evaluate_milk_potential

FEASIBILITY_TOLERANCE = 1e-4


def _feed_rations(quantities, feeds):
    return [
        FeedInRation(amount=float(quantity), info=feed)
        for quantity, feed in zip(quantities, feeds)
    ]


def generate_alternatives(quantities, feeds, optimizer, configuration, animal_combination,
                          animal, requirements, base_emissions, reference_milk,
                          calculation_type, target, samples, seed=None):
    """Return feasible alternative diets around a solved ration.

    Each sample perturbs the solved quantities, clips them to the feed bounds and
    keeps only rations that satisfy every native constraint of the same target.
    The result is a local cloud: it is not an exhaustive search.
    """
    if samples <= 0:
        return []
    base = [float(value) for value in quantities]
    if len(base) != len(feeds) or sum(base) <= 0:
        return []
    constraint_functions = [constraint['fun'] for constraint in optimizer._select_constraints(animal_combination)]
    recompute_emissions = (
        getattr(optimizer, 'calculate_candidate_emissions', False)
        or base_emissions is None
    )
    rng = random.Random(seed)
    alternatives = []
    seen = set()

    for _ in range(samples):
        scale = rng.uniform(0.92, 1.08)
        candidate = []
        for quantity, feed in zip(base, feeds):
            if quantity > 1e-9:
                value = quantity * rng.uniform(0.75, 1.25) * scale
            elif rng.random() < 0.06:
                value = rng.uniform(0.0, max(0.25, 0.04 * sum(base)))
            else:
                value = 0.0
            value = min(max(value, float(feed.lower_limit)), float(feed.limit))
            candidate.append(value)
        if sum(candidate) <= 0:
            continue
        vector = np.asarray(candidate, dtype=float)
        try:
            slacks = [float(function(vector, configuration)) for function in constraint_functions]
        except (ArithmeticError, TypeError, ValueError):
            continue
        if any(not math.isfinite(slack) or slack < -FEASIBILITY_TOLERANCE for slack in slacks):
            continue
        candidate_feeds = _feed_rations(candidate, feeds)
        try:
            emissions = (
                calculate_candidate_ration_emissions(candidate_feeds, animal, calculation_type)
                if recompute_emissions else base_emissions
            )
            potential = evaluate_milk_potential(
                candidate_feeds, animal, requirements, emissions, reference_milk)
        except (CandidateEmissionEstimationError, ArithmeticError, TypeError, ValueError):
            continue
        milk_allowed = potential.get('allowed_kg_day')
        cost = sum(quantity * feed.purchase_cost for quantity, feed in zip(candidate, feeds))
        if milk_allowed is None or not math.isfinite(milk_allowed) or not math.isfinite(cost):
            continue
        key = (round(cost, 4), round(float(milk_allowed), 4))
        if key in seen:
            continue
        seen.add(key)
        alternatives.append({
            'milk_allowed': float(milk_allowed),
            'cost_day': float(cost),
            'target': float(target),
            'below_reference': float(milk_allowed) < float(reference_milk) - FLOOR_TOLERANCE_KG_DAY,
            'dominated': False,
        })
    return alternatives
