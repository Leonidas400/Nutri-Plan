"""Strict cost and IOFC comparisons from documented feed-price records."""
from __future__ import annotations

import datetime
import math

from services.prices import normalize_price


PRICE_FIELDS = ('amount', 'currency', 'unit', 'source_type', 'source', 'reference_date', 'geography')
ECONOMIC_SOURCE_TYPES = {'manual', 'market_reference', 'historical', 'actual_cost'}
MILK_PRICE_UNITS = {'kg_milk', 'metric_ton_milk'}


def _issue(code, message, feed_id=None, field=None):
    item = {'code': code, 'message': message}
    if feed_id is not None:
        item['rufas_id'] = feed_id
    if field is not None:
        item['field'] = field
    return item


def _diet_items(ration, label, feed_catalog, issues):
    if not isinstance(ration, list) or not ration:
        issues.append(_issue('invalid_diet', f'{label} diet must contain feed entries.'))
        return []
    items = []
    seen = set()
    for entry in ration:
        if not isinstance(entry, dict):
            issues.append(_issue('invalid_diet_entry', f'{label} diet contains a non-object entry.'))
            continue
        raw_id = entry.get('rufas_id', entry.get('id'))
        try:
            if isinstance(raw_id, bool):
                raise ValueError
            feed_id = int(raw_id)
        except (TypeError, ValueError):
            issues.append(_issue('invalid_feed_id', f'{label} diet contains an invalid RuFaS feed ID.'))
            continue
        if feed_id in seen:
            issues.append(_issue('duplicate_feed_id', f'{label} diet repeats RuFaS feed {feed_id}.', feed_id))
            continue
        seen.add(feed_id)
        catalog_entry = feed_catalog.get(feed_id) if isinstance(feed_catalog, dict) else None
        if catalog_entry is None:
            issues.append(_issue('unknown_feed_id', f'RuFaS feed {feed_id} is not in the supplied catalog.', feed_id))
            continue
        name = entry.get('name')
        catalog_name = catalog_entry.get('Name')
        if name is not None and str(name).strip() != str(catalog_name).strip():
            issues.append(_issue('ingredient_identity_mismatch',
                                 f'Feed name does not match RuFaS ID {feed_id}.', feed_id, 'name'))
        try:
            if isinstance(catalog_entry.get('DM'), bool):
                raise ValueError
            dm_percent = float(catalog_entry['DM'])
            if not math.isfinite(dm_percent) or not 0 < dm_percent <= 100:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            issues.append(_issue('invalid_feed_dry_matter',
                                 f'RuFaS feed {feed_id} has no usable dry-matter fraction.', feed_id, 'DM'))
            continue
        raw_amount = entry.get('kg_dm_day', entry.get('kg_dm'))
        try:
            if isinstance(raw_amount, bool):
                raise ValueError
            amount = float(raw_amount)
            if not math.isfinite(amount) or amount < 0:
                raise ValueError
        except (TypeError, ValueError):
            issues.append(_issue('invalid_quantity',
                                 f'{label} feed {feed_id} must have a finite nonnegative kg DM/day quantity.',
                                 feed_id, 'kg_dm_day'))
            continue
        items.append({'rufas_id': feed_id, 'kg_dm_day': amount, 'dm_fraction': dm_percent / 100})
    if not items or sum(item['kg_dm_day'] for item in items) <= 0:
        issues.append(_issue('empty_diet', f'{label} diet must provide positive dry matter.'))
    return items


def _price_records(price_records, used_ids, feed_catalog, issues):
    if not isinstance(price_records, list):
        issues.append(_issue('invalid_price_records', 'Price records must be supplied as a list.'))
        return {}, False
    normalized = {}
    documented = True
    for entry in price_records:
        if not isinstance(entry, dict):
            issues.append(_issue('invalid_price_record', 'A price record is not an object.'))
            documented = False
            continue
        nested = entry.get('price_record')
        raw = nested if isinstance(nested, dict) else entry
        raw_id = entry.get('rufas_id', entry.get('id', raw.get('rufas_id')))
        try:
            if isinstance(raw_id, bool):
                raise ValueError
            feed_id = int(raw_id)
        except (TypeError, ValueError):
            issues.append(_issue('invalid_price_record', 'A price record has no valid RuFaS feed ID.'))
            documented = False
            continue
        if feed_id not in used_ids:
            continue
        missing = [field for field in PRICE_FIELDS
                   if field not in raw or raw[field] is None or (isinstance(raw[field], str) and not raw[field].strip())]
        if missing:
            documented = False
            for field in missing:
                issues.append(_issue('missing_price_provenance',
                                     f'Price for RuFaS feed {feed_id} is missing {field}.', feed_id, field))
            continue
        if not isinstance(raw.get('source'), str) or not isinstance(raw.get('geography'), str):
            documented = False
            issues.append(_issue('invalid_price_provenance',
                                 f'Price source and geography for RuFaS feed {feed_id} must be text.', feed_id))
            continue
        if feed_id not in feed_catalog:
            continue
        try:
            record = normalize_price(raw, float(feed_catalog[feed_id]['DM']), feed_id)
        except (KeyError, TypeError, ValueError) as error:
            documented = False
            issues.append(_issue('invalid_price_record', str(error), feed_id))
            continue
        if not str(record.get('geography', '')).strip():
            documented = False
            issues.append(_issue('missing_price_provenance',
                                 f'Price for RuFaS feed {feed_id} is missing geography.', feed_id, 'geography'))
            continue
        if record['source_type'] == 'demonstration':
            issues.append(_issue('demonstration_price',
                                 f'Demonstration price for RuFaS feed {feed_id} cannot support an economic comparison.',
                                 feed_id, 'source_type'))
        elif record['source_type'] not in ECONOMIC_SOURCE_TYPES:
            issues.append(_issue('invalid_price_source_type',
                                 f'Price type for RuFaS feed {feed_id} is not eligible for comparison.',
                                 feed_id, 'source_type'))
        if feed_id in normalized:
            prior = normalized[feed_id]
            comparable_fields = ('amount', 'currency', 'unit', 'source_type', 'source', 'reference_date', 'geography')
            if any(prior[field] != record[field] for field in comparable_fields):
                issues.append(_issue('conflicting_price_records',
                                     f'More than one incompatible price was supplied for RuFaS feed {feed_id}.', feed_id))
            continue
        normalized[feed_id] = record
    for feed_id in sorted(used_ids - set(normalized)):
        if not any(issue.get('rufas_id') == feed_id for issue in issues):
            issues.append(_issue('missing_price', f'No documented price was supplied for RuFaS feed {feed_id}.', feed_id))
    return normalized, documented


def _validate_iofc(milk_data, economic_results):
    if economic_results is None:
        return {'status': 'unavailable', 'missing_fields': ['complete_economic_comparison']}
    expected = ('baseline', 'optimized')
    if not isinstance(milk_data, dict):
        fields = [f'{diet}.{field}' for diet in expected
                  for field in ('production_kg_day', 'production_type', 'production_source', 'reference_date')]
        fields.append('milk_price_record')
        return {'status': 'unavailable', 'missing_fields': fields}
    issues = []
    missing = []
    production = {}
    for diet in expected:
        entry = milk_data.get(diet)
        if not isinstance(entry, dict):
            missing.extend(f'{diet}.{field}' for field in
                           ('production_kg_day', 'production_type', 'production_source', 'reference_date'))
            continue
        for field in ('production_kg_day', 'production_type', 'production_source', 'reference_date'):
            if entry.get(field) is None or (isinstance(entry.get(field), str) and not entry[field].strip()):
                missing.append(f'{diet}.{field}')
        for field in ('production_type', 'production_source', 'reference_date'):
            if entry.get(field) is not None and not isinstance(entry[field], str):
                issues.append(_issue('invalid_milk_record',
                                     f'{diet}.{field} must be text.', field=field))
        try:
            if isinstance(entry.get('production_kg_day'), bool):
                raise ValueError
            amount = float(entry['production_kg_day'])
            if not math.isfinite(amount) or amount <= 0:
                raise ValueError
            production[diet] = amount
        except (KeyError, TypeError, ValueError):
            if f'{diet}.production_kg_day' not in missing:
                issues.append(_issue('invalid_milk_production',
                                     f'{diet} milk production must be a positive kg/day value.', field='production_kg_day'))
        try:
            if datetime.date.fromisoformat(entry['reference_date']).isoformat() != entry['reference_date']:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            if f'{diet}.reference_date' not in missing:
                issues.append(_issue('invalid_milk_reference_date', f'{diet} milk production date must use YYYY-MM-DD.'))
    milk_price = milk_data.get('milk_price_record')
    milk_price_fields = ('amount', 'currency', 'unit', 'source_type', 'source', 'reference_date', 'geography')
    if not isinstance(milk_price, dict):
        missing.append('milk_price_record')
    else:
        for field in milk_price_fields:
            if milk_price.get(field) is None or (isinstance(milk_price.get(field), str) and not milk_price[field].strip()):
                missing.append(f'milk_price_record.{field}')
    if missing:
        return {'status': 'unavailable', 'missing_fields': sorted(set(missing)), 'issues': issues}
    price = milk_price
    try:
        if isinstance(price['amount'], bool):
            raise ValueError
        price_amount = float(price['amount'])
        if not math.isfinite(price_amount) or price_amount < 0 or price['unit'] not in MILK_PRICE_UNITS:
            raise ValueError
        if price['source_type'] not in ECONOMIC_SOURCE_TYPES:
            raise ValueError
        if datetime.date.fromisoformat(price['reference_date']).isoformat() != price['reference_date']:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        issues.append(_issue('invalid_milk_price', 'Milk price must have a documented eligible source and known milk unit.'))
        return {'status': 'unavailable', 'missing_fields': [], 'issues': issues}
    if not isinstance(price.get('source'), str) or not isinstance(price.get('geography'), str):
        issues.append(_issue('invalid_milk_price_provenance', 'Milk price source and geography must be text.'))
    if issues:
        return {'status': 'unavailable', 'missing_fields': [], 'issues': issues}
    production_types = {milk_data[diet]['production_type'] for diet in expected}
    dates = {milk_data[diet]['reference_date'] for diet in expected} | {price['reference_date'], economic_results['price_date']}
    if len(production_types) != 1:
        issues.append(_issue('incompatible_milk_production_basis',
                             'Baseline and optimized milk production must use the same documented basis.'))
    if len(dates) != 1:
        issues.append(_issue('incompatible_milk_reference_date',
                             'Milk production and price records must cover the same reference date.'))
    if not production_types.issubset({'observed', 'modeled', 'scenario'}):
        issues.append(_issue('invalid_milk_production_basis', 'Milk production type must be observed, modeled, or scenario.'))
    geographies = [str(price.get('geography') or '').strip()]
    if not geographies[0]:
        issues.append(_issue('missing_milk_price_geography', 'Milk price geography is required.'))
    milk_currency = price.get('currency').strip().upper() if isinstance(price.get('currency'), str) else ''
    if len(milk_currency) != 3 or not milk_currency.isalpha():
        issues.append(_issue('invalid_milk_currency', 'Milk price currency must be a three-letter code.'))
    elif milk_currency != economic_results['currency']:
        issues.append(_issue('incompatible_milk_currency', 'Milk price and feed costs must use the same currency.'))
    if str(price.get('geography') or '').strip().casefold() != economic_results['geography'].casefold():
        issues.append(_issue('incompatible_milk_geography', 'Milk price and feed prices must use the same geography.'))
    if issues:
        return {'status': 'unavailable', 'missing_fields': [], 'issues': issues}
    amount_per_kg = price_amount if price['unit'] == 'kg_milk' else price_amount / 1000
    currency = milk_currency
    out = {}
    for diet in expected:
        revenue = production[diet] * amount_per_kg
        feed_cost = economic_results[diet]['cost_day']
        out[diet] = {
            'production_kg_day': production[diet],
            'production_type': milk_data[diet]['production_type'],
            'production_source': milk_data[diet]['production_source'],
            'milk_revenue_day': revenue,
            'feed_cost_day': feed_cost,
            'iofc_day': revenue - feed_cost,
        }
    return {'status': 'calculated', 'currency': currency, 'milk_price_source': price['source'],
            'milk_price_unit': price['unit'], 'milk_price_amount': price_amount,
            'baseline': out['baseline'], 'optimized': out['optimized'],
            'difference_baseline_minus_optimized_day': out['baseline']['iofc_day'] - out['optimized']['iofc_day']}


def compare_diets_economically(baseline_ration, optimized_ration, price_records, feed_catalog,
                               batch_size=None, milk_data=None):
    """Compare two kg-DM/day diets only when exact-feed prices share a documented basis.

    Price records retain their original amount/unit in the result. Known feed DM
    fractions are used only to normalize each quote to currency/kg as-fed.
    Provenance fields are checked for completeness, not independently audited.
    """
    issues = []
    baseline = _diet_items(baseline_ration, 'baseline', feed_catalog, issues)
    optimized = _diet_items(optimized_ration, 'optimized', feed_catalog, issues)
    used_ids = {item['rufas_id'] for item in baseline + optimized if item['kg_dm_day'] > 0}
    normalized, provenance_documented = _price_records(price_records, used_ids, feed_catalog, issues)
    missing_ids = sorted(used_ids - set(normalized))
    usable = [normalized[feed_id] for feed_id in sorted(used_ids) if feed_id in normalized]
    if not missing_ids and usable:
        for field, code in (('currency', 'incompatible_currency'), ('reference_date', 'incompatible_reference_date'),
                            ('geography', 'incompatible_geography'), ('source_type', 'incompatible_source_type')):
            values = {str(record[field]).casefold() if field == 'geography' else record[field] for record in usable}
            if len(values) > 1:
                issues.append(_issue(code, f'Prices must share one {field.replace("_", " ")} for direct comparison.'))
    structural_codes = {'invalid_diet', 'invalid_diet_entry', 'invalid_feed_id', 'duplicate_feed_id',
                        'unknown_feed_id', 'ingredient_identity_mismatch', 'invalid_feed_dry_matter',
                        'invalid_quantity', 'empty_diet'}
    structurally_valid = not any(issue['code'] in structural_codes for issue in issues)
    provenance_codes = {'missing_price_provenance', 'invalid_price_provenance', 'invalid_price_record'}
    provenance_documented = provenance_documented and not any(issue['code'] in provenance_codes for issue in issues)
    blockers = {'demonstration_price', 'invalid_price_source_type', 'incompatible_currency',
                'incompatible_reference_date', 'incompatible_geography', 'incompatible_source_type',
                'conflicting_price_records'}
    has_price_blocker = bool(missing_ids) or any(issue['code'] in blockers | {
        'missing_price', 'missing_price_provenance', 'invalid_price_provenance', 'invalid_price_record'
    } for issue in issues)
    economic_results = None
    batch_issue = None
    batch_count = None
    if batch_size is not None:
        try:
            if isinstance(batch_size, bool) or int(batch_size) != batch_size or int(batch_size) <= 0:
                raise ValueError
            batch_count = int(batch_size)
        except (TypeError, ValueError, OverflowError):
            batch_issue = _issue('invalid_batch_size', 'Batch size must be a positive integer.', field='batch_size')
            issues.append(batch_issue)
    available = (structurally_valid and not has_price_blocker and bool(used_ids)
                 and not any(issue['code'] != 'invalid_batch_size' for issue in issues))
    if available:
        records_by_id = normalized
        def ration_cost(items):
            return sum(item['kg_dm_day'] / item['dm_fraction'] * records_by_id[item['rufas_id']]['price_as_fed']
                       for item in items if item['kg_dm_day'] > 0)
        baseline_cost = ration_cost(baseline)
        optimized_cost = ration_cost(optimized)
        difference = baseline_cost - optimized_cost
        baseline_result = {'cost_day': baseline_cost, 'cost_month_30_days': baseline_cost * 30}
        optimized_result = {'cost_day': optimized_cost, 'cost_month_30_days': optimized_cost * 30}
        difference_result = {
            'per_animal_day': difference,
            'per_animal_month_30_days': difference * 30,
            'percent_of_baseline': 100 * difference / baseline_cost if baseline_cost > 0 else None,
        }
        batch = None
        if batch_count is not None:
            batch = {'animal_count': batch_count,
                     'baseline_cost_day': baseline_cost * batch_count,
                     'optimized_cost_day': optimized_cost * batch_count,
                     'difference_day': difference * batch_count,
                     'difference_month_30_days': difference * batch_count * 30}
        economic_results = {'currency': usable[0]['currency'], 'price_date': usable[0]['reference_date'],
                            'geography': usable[0]['geography'], 'price_source_type': usable[0]['source_type'],
                            'baseline': baseline_result, 'optimized': optimized_result,
                            'difference': difference_result, 'batch': batch,
                            'batch_size_issue': batch_issue}
    if economic_results is not None:
        status = 'comparable'
    elif not structurally_valid:
        status = 'invalid_input'
    elif missing_ids or any(issue['code'] in {
        'missing_price', 'missing_price_provenance', 'invalid_price_provenance', 'invalid_price_record'
    } for issue in issues):
        status = 'missing_prices'
    else:
        status = 'incompatible_prices'
    return {
        'status': status,
        'structurally_valid': structurally_valid,
        'price_coverage_complete': not missing_ids,
        'provenance_documented': provenance_documented,
        'provenance_independently_verified': False,
        'scientific_validation_established': False,
        'economic_comparison_available': economic_results is not None,
        'missing_price_ids': missing_ids,
        'issues': issues,
        'normalized_price_records': [normalized[key] for key in sorted(normalized)],
        'economic_results': economic_results,
        'iofc': _validate_iofc(milk_data, economic_results),
    }
