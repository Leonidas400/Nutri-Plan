"""Versioned, input-only NutriPlan scenario validation."""
from __future__ import annotations

import datetime
import hashlib
import subprocess
from pathlib import Path

from services.numbers import parse_number
from services.native_ration import feed_library
from services.nutrition import PARAMETERS, profiles
from services.prices import normalize_price

SCHEMA_VERSION = 1
APP_ID = 'nutriplan'
MAX_FEEDS = 25


def _number(value, label, positive=False):
    result = parse_number(value, label, minimum=0)
    if positive and result <= 0:
        raise ValueError(f'{label}: a positive number is required.')
    return result


def validate_scenario(document, allow_incomplete=False):
    """Reject unsupported or ambiguous configurations before browser state changes."""
    if not isinstance(document, dict):
        raise ValueError('Scenario must be a JSON object.')
    version = document.get('schema_version')
    if version != SCHEMA_VERSION or isinstance(version, bool):
        raise ValueError(f'Unsupported scenario schema version: {version}. Expected {SCHEMA_VERSION}.')
    if document.get('app_id') != APP_ID:
        raise ValueError('Scenario application identifier is invalid.')
    if 'result' in document or 'results' in document:
        raise ValueError('Calculation results cannot be loaded as a scenario configuration.')
    if not isinstance(document.get('id'), str) or not document['id'].strip() or len(document['id']) > 100:
        raise ValueError('Scenario ID is required.')
    if allow_incomplete and document['id'] != 'working':
        raise ValueError('Incomplete validation is reserved for the local working configuration.')
    if not isinstance(document.get('name'), str) or not document['name'].strip() or len(document['name']) > 120:
        raise ValueError('Scenario name is required (up to 120 characters).')
    if not isinstance(document.get('description', ''), str) or len(document.get('description', '')) > 500:
        raise ValueError('Scenario description must be text (up to 500 characters).')
    for key in ('created_at', 'modified_at'):
        try:
            datetime.datetime.fromisoformat(document[key].replace('Z', '+00:00'))
        except (KeyError, AttributeError, ValueError) as error:
            raise ValueError(f'Invalid {key}.') from error
    meta = document.get('metadata')
    if not isinstance(meta, dict) or meta.get('nutritional_standard') != 'NASEM_2021' or meta.get('engine') != 'RuFaS RationOptimizer':
        raise ValueError('Scenario engine or nutritional standard is incompatible.')
    if meta.get('feed_library') != 'input/data/feed/NASEM_Comp_with_TDN.csv':
        raise ValueError('Scenario feed library is incompatible.')
    library_path = Path(__file__).resolve().parents[2] / meta['feed_library']
    if meta.get('feed_library_sha256'):
        try:
            actual_hash = hashlib.sha256(library_path.read_bytes()).hexdigest()
        except OSError as error:
            raise ValueError('Current RuFaS feed library is unavailable.') from error
        if meta['feed_library_sha256'] != actual_hash:
            raise ValueError('Scenario feed library content differs from the current RuFaS library.')
    if meta.get('rufas_commit'):
        try:
            revision = subprocess.run(['git', '-C', str(library_path.parents[3]), 'rev-parse', 'HEAD'],
                                      capture_output=True, text=True, check=False)
            commit = revision.stdout.strip() if revision.returncode == 0 else None
        except OSError:
            commit = None
        if commit != meta['rufas_commit']:
            raise ValueError('Scenario RuFaS revision differs from the current installation.')
    config = document.get('configuration')
    if not isinstance(config, dict):
        raise ValueError('Scenario configuration is required.')
    reference = config.get('reference')
    if reference is not None and (not isinstance(reference, dict) or
                                  not isinstance(reference.get('id'), str) or
                                  not isinstance(reference.get('label', ''), str)):
        raise ValueError('Invalid scenario reference metadata.')
    if 'result' in config or 'results' in config:
        raise ValueError('Scenario configuration must not contain calculation results.')
    if config.get('animal_category') not in profiles() and not (allow_incomplete and config.get('animal_category') == ''):
        raise ValueError('Unsupported animal category.')
    if not (allow_incomplete and config.get('body_weight_kg') in (None, '')):
        _number(config.get('body_weight_kg'), 'Body weight', positive=True)
    parameters = config.get('parameters')
    if not isinstance(parameters, dict) or set(parameters) - set(PARAMETERS):
        raise ValueError('Invalid physiological parameters.')
    for key, value in parameters.items():
        if value in (None, ''):
            continue
        if key == 'housing':
            if value not in ('Barn', 'Grazing'):
                raise ValueError('Invalid housing parameter.')
        else:
            _number(value, key)
    library = feed_library()
    candidates = config.get('feeds')
    if not isinstance(candidates, list) or not (0 if allow_incomplete else 2) <= len(candidates) <= MAX_FEEDS:
        raise ValueError('Scenario requires 2 to 25 candidate feeds.')
    seen = set()
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError('Invalid candidate feed.')
        try:
            identifier = int(item['rufas_id'])
        except (KeyError, TypeError, ValueError) as error:
            if allow_incomplete and item.get('rufas_id') in (None, ''):
                continue
            raise ValueError('Invalid candidate RuFaS ID.') from error
        if identifier not in library or identifier in seen:
            raise ValueError(f'Unknown or duplicate candidate RuFaS ID: {identifier}.')
        seen.add(identifier)
        if not isinstance(item.get('available', True), bool):
            raise ValueError(f'Feed {identifier}: availability must be true or false.')
        minimum = _number(item.get('min', 0), 'Minimum inclusion') if not (allow_incomplete and item.get('min') in (None, '')) else None
        maximum = _number(item.get('max'), 'Maximum inclusion') if not (allow_incomplete and item.get('max') in (None, '')) else None
        if minimum is not None and maximum is not None and maximum < minimum:
            raise ValueError(f'Feed {identifier}: inclusion maximum is below minimum.')
        if not allow_incomplete:
            _validate_ui_price(item, library, identifier)
        elif item.get('price') not in (None, ''):
            _number(item['price'], 'Feed price')
    previous = config.get('previous_ration') or []
    if not isinstance(previous, list) or len(previous) > MAX_FEEDS:
        raise ValueError('Invalid previous ration.')
    previous_ids = set()
    for item in previous:
        if not isinstance(item, dict):
            raise ValueError('Invalid previous-ration feed.')
        try:
            identifier = int(item['rufas_id'])
        except (KeyError, TypeError, ValueError) as error:
            if allow_incomplete and item.get('rufas_id') in (None, ''):
                continue
            raise ValueError('Invalid previous-ration RuFaS ID.') from error
        if identifier not in library or identifier in previous_ids:
            raise ValueError(f'Unknown or duplicate previous-ration RuFaS ID: {identifier}.')
        previous_ids.add(identifier)
        if not (allow_incomplete and item.get('kg_dm_day') in (None, '')):
            _number(item.get('kg_dm_day'), 'Previous ration dry matter', positive=True)
        if item.get('price_as_fed') not in (None, ''):
            _number(item['price_as_fed'], 'Previous ration price')
        if item.get('price_record') is not None:
            normalize_price(item['price_record'], library[identifier]['DM'], identifier)
    previous_source = config.get('previous_ration_source')
    if previous_source is not None and not isinstance(previous_source, str):
        raise ValueError('Invalid previous-ration source.')
    if previous and not allow_incomplete and len(previous) < 2:
        raise ValueError('Previous ration requires at least two feeds.')
    imported = config.get('imported_prices', [])
    if not isinstance(imported, list) or len(imported) > len(library):
        raise ValueError('Invalid imported prices.')
    imported_ids = set()
    for record in imported:
        if not isinstance(record, dict):
            raise ValueError('Invalid imported price record.')
        try:
            identifier = int(record['rufas_id'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Invalid imported price RuFaS ID.') from error
        if identifier not in library or identifier in imported_ids:
            raise ValueError(f'Unknown or duplicate imported price RuFaS ID: {identifier}.')
        imported_ids.add(identifier)
        normalize_price(record, library[identifier]['DM'], identifier)
    emissions = config.get('emissions') or {}
    if not isinstance(emissions, dict):
        raise ValueError('Invalid emission inputs.')
    for key in ('enteric_methane_g_day', 'urine_nitrogen_kg_day'):
        if emissions.get(key) not in (None, ''):
            _number(emissions[key], key)
    return document


def _validate_ui_price(item, library, identifier):
    if item.get('price_record') is not None:
        normalize_price(item['price_record'], library[identifier]['DM'], identifier)
        return
    normalize_price({'amount': item.get('price'), 'currency': item.get('currency'),
                     'unit': item.get('price_unit'), 'source_type': item.get('source_type'),
                     'source': item.get('source'), 'reference_date': item.get('source_date'),
                     'geography': item.get('geography'), 'notes': item.get('price_notes')},
                    library[identifier]['DM'], identifier)
