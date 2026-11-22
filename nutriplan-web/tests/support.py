"""Shared fixtures for the NutriPlan application tests."""
import json
from pathlib import Path

REFERENCE_RATIONS = Path(__file__).resolve().parents[1] / 'data/reference_rations.json'
_METADATA_KEYS = (
    'id', 'label', 'unit', 'standard', 'assumption', 'source_url', 'profile_source',
)


def guelph_payload(animal_category='first_lactation_cow', reference=None, **overrides):
    """Return the retained Guelph demonstration payload shaped for the API."""
    payload = json.loads(REFERENCE_RATIONS.read_text(encoding='utf-8'))[0]
    for key in _METADATA_KEYS:
        payload.pop(key, None)
    payload['animal_category'] = animal_category
    payload['milk_reference_kg_day'] = (
        payload['parameters']['milk_production'] if reference is None else reference
    )
    payload['beyond_optimum_attempts'] = 0
    payload.update(overrides)
    return payload
