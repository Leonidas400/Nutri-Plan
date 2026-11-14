"""Validate price provenance and convert user prices to RuFaS as-fed units."""
from __future__ import annotations

import datetime
import math

from services.numbers import parse_number

UNITS = {'kg_as_fed', 'kg_dm', 'metric_ton_as_fed'}
SOURCES = {'manual', 'market_reference', 'historical', 'actual_cost', 'demonstration'}


def normalize_price(record, dry_matter_percent, feed_id):
    """Return a validated price record with an added price_as_fed value."""
    if not isinstance(record, dict):
        raise ValueError(f'Feed {feed_id}: price record must be an object.')
    try:
        amount = parse_number(record['amount'], 'Price', minimum=0)
        dm = float(dry_matter_percent) / 100
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f'Feed {feed_id}: invalid price or dry matter.') from error
    currency = record.get('currency')
    unit = record.get('unit')
    source_type = record.get('source_type')
    source = record.get('source')
    date = record.get('reference_date')
    if not math.isfinite(amount) or amount < 0 or not math.isfinite(dm) or not 0 < dm <= 1:
        raise ValueError(f'Feed {feed_id}: invalid price or dry matter.')
    if currency is None or (isinstance(currency, str) and not currency.strip()):
        if source_type == 'demonstration':
            normalized_currency = None
        else:
            raise ValueError(f'Feed {feed_id}: currency must be a three-letter code.')
    elif not isinstance(currency, str) or len(currency.strip()) != 3 or not currency.strip().isalpha():
        raise ValueError(f'Feed {feed_id}: currency must be a three-letter code.')
    else:
        normalized_currency = currency.strip().upper()
    if unit not in UNITS:
        raise ValueError(f'Feed {feed_id}: unsupported price unit.')
    if source_type not in SOURCES or not isinstance(source, str) or not source.strip():
        raise ValueError(f'Feed {feed_id}: price source and source type are required.')
    if not date and source_type == 'demonstration':
        date = None
    else:
        if not isinstance(date, str) or not date:
            raise ValueError(f'Feed {feed_id}: reference date is required.')
        try:
            if datetime.date.fromisoformat(date).isoformat() != date:
                raise ValueError
        except ValueError as error:
            raise ValueError(f'Feed {feed_id}: invalid reference date.') from error
    converted = amount if unit == 'kg_as_fed' else amount * dm if unit == 'kg_dm' else amount / 1000
    return {'rufas_id': int(feed_id), 'amount': amount, 'currency': normalized_currency,
            'unit': unit, 'source_type': source_type, 'source': source.strip(),
            'reference_date': date, 'geography': str(record.get('geography') or '').strip(),
            'notes': str(record.get('notes') or '').strip(), 'price_as_fed': converted}


def resolve_price(item, library):
    """Accept the structured contract and keep legacy price_as_fed compatible."""
    identifier = int(item['rufas_id'])
    if identifier not in library:
        raise ValueError(f'Unknown RuFaS feed ID: {identifier}.')
    if item.get('price_record') is not None:
        record = normalize_price(item['price_record'], library[identifier]['DM'], identifier)
        if item.get('price_as_fed') is not None and not math.isclose(parse_number(item['price_as_fed'], 'Price', minimum=0), record['price_as_fed'], rel_tol=1e-8, abs_tol=1e-8):
            raise ValueError(f'Feed {identifier}: conflicting price fields.')
        return record
    raw = item.get('price_as_fed')
    if raw is None or raw == '':
        return None
    try:
        amount = parse_number(raw, 'Price', minimum=0)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Feed {identifier}: invalid price.') from error
    if not math.isfinite(amount) or amount < 0:
        raise ValueError(f'Feed {identifier}: invalid price.')
    return {'rufas_id': identifier, 'amount': amount, 'currency': None, 'unit': 'kg_as_fed',
            'source_type': 'legacy_unspecified', 'source': None, 'reference_date': None,
            'geography': '', 'notes': '', 'price_as_fed': amount}


def comparison_status(records):
    """Return why a set of price records cannot support direct savings claims."""
    currencies = {record['currency'] for record in records if record is not None}
    dates = {record['reference_date'] for record in records if record is not None}
    if None in currencies or len(currencies) != 1:
        return 'incompatible_currency'
    if None in dates or len(dates) != 1:
        return 'incompatible_dates'
    return 'comparable'


