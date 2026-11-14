"""Preview standard UTF-8 CSV using the same animal input validation as the calculator."""
import csv
import io

from services.numbers import parse_number
from services.nutrition import HOUSING_TYPES, parse_numeric_parameter, profiles

PROPERTY_KEYS = ['mature_body_weight', 'calving_interval', 'housing', 'distance']
INDIVIDUAL_KEYS = ['days_in_milk', 'milk_production', 'milk_fat', 'milk_true_protein',
                   'body_condition_score_5', 'milk_lactose', 'process_based_phosphorus_requirement']
PROPERTY_HEADERS = ['property_name', *PROPERTY_KEYS]
ANIMAL_HEADERS = ['animal_id', 'animal_category', 'lactation_subcategory', 'body_weight_kg',
                  'days_in_milk', 'milk_production', 'milk_fat', 'milk_true_protein',
                  'pregnant', 'day_of_pregnancy', 'body_condition_score_5', 'milk_lactose',
                  'process_based_phosphorus_requirement', *PROPERTY_KEYS]
MAX_BYTES = 262144
MAX_RECORDS = 500
MAX_ERRORS = 100


def preview_csv(payload):
    if not isinstance(payload, dict) or payload.get('kind') not in ('animals', 'property'):
        raise ValueError('Choose animals or property CSV.')
    delimiter, text = payload.get('delimiter'), payload.get('text')
    if delimiter not in (';', ',') or not isinstance(text, str):
        raise ValueError('CSV requires text and an explicit semicolon or comma delimiter.')
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('CSV exceeds 256 KiB.')
    kind = payload['kind']
    headers = ANIMAL_HEADERS if kind == 'animals' else PROPERTY_HEADERS
    errors, records, seen = [], [], set()

    def error(line, column, code):
        if len(errors) < MAX_ERRORS:
            errors.append({'line': line, 'column': column, 'code': code})

    def number(row, key, line, required=False):
        raw = row[key].strip()
        if not raw:
            if required: error(line, key, 'required')
            return None
        try:
            if key == 'body_weight_kg':
                value = parse_number(raw, key, minimum=0)
                if value <= 0: raise ValueError('Weight must be positive.')
                return value
            return parse_numeric_parameter(key, raw)
        except ValueError:
            error(line, key, 'invalid_number')
            return None

    reader = csv.reader(io.StringIO(text.removeprefix('\ufeff'), newline=''), delimiter=delimiter, strict=True)
    try:
        actual = [value.strip() for value in next(reader, [])]
        if len(set(actual)) != len(actual): error(1, 'header', 'duplicate_header')
        for key in headers:
            if key not in actual: error(1, key, 'missing_header')
        for key in actual:
            if key not in headers: error(1, key, 'unknown_header')
        if errors:
            return {'ok': False, 'kind': kind, 'records': [], 'errors': errors}
        count = 0
        while True:
            line = reader.line_num + 1
            cells = next(reader, None)
            if cells is None: break
            if not any(value.strip() for value in cells): continue
            count += 1
            if count > MAX_RECORDS:
                error(line, '', 'too_many_records'); break
            if len(cells) != len(actual):
                error(line, '', 'column_count'); continue
            row = dict(zip(actual, (cell.strip() for cell in cells)))
            id_key = 'animal_id' if kind == 'animals' else 'property_name'
            identifier = row[id_key]
            if not identifier or len(identifier) > 120 or any(ch in identifier for ch in '\r\n\x00'):
                error(line, id_key, 'invalid_identifier')
            elif identifier.casefold() in seen: error(line, id_key, 'duplicate_record')
            seen.add(identifier.casefold())
            parameters = {}
            for key in PROPERTY_KEYS:
                if key == 'housing':
                    if row[key] and row[key] not in HOUSING_TYPES: error(line, key, 'invalid_housing')
                    elif row[key]: parameters[key] = row[key]
                else:
                    value = number(row, key, line)
                    if value is not None: parameters[key] = value
            if kind == 'property':
                if not parameters: error(line, '', 'empty_property')
                values = {'name': identifier, 'parameters': parameters}
            else:
                category, phase = row['animal_category'], row['lactation_subcategory']
                if category not in profiles(): error(line, 'animal_category', 'unsupported_category')
                if phase not in ('fresh', 'early', 'mid', 'late'): error(line, 'lactation_subcategory', 'invalid_phase')
                weight = number(row, 'body_weight_kg', line, required=True)
                for key in INDIVIDUAL_KEYS: parameters[key] = number(row, key, line, required=True)
                pregnant = row['pregnant'].lower()
                if pregnant not in ('true', 'false'): error(line, 'pregnant', 'invalid_boolean')
                day = number(row, 'day_of_pregnancy', line, required=pregnant == 'true')
                if pregnant == 'false' and row['day_of_pregnancy']: error(line, 'day_of_pregnancy', 'pregnancy_conflict')
                parameters['day_of_pregnancy'] = day if pregnant == 'true' else None
                values = {'animal_category': category, 'lactation_subcategory': phase,
                          'body_weight_kg': weight, 'parameters': parameters}
            records.append({'line': line, 'id': identifier, 'values': values})
    except csv.Error:
        error(max(1, reader.line_num), '', 'malformed_csv')
    if not records and not errors: error(2, '', 'no_records')
    return {'ok': not errors, 'kind': kind, 'records': records if not errors else [], 'errors': errors}
