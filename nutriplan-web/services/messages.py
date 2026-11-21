"""Public validation categories consumed by both interface languages."""
import re


def validation_error(error):
    detail = str(error).lower()
    code = 'invalid_input'
    for pattern, category in (
        ('automatic emission estimation', 'emissions_unavailable'),
        ('invalid methane or urinary nitrogen', 'invalid_emissions'),
        ('price|currency|preço', 'price'), ('feed|ingredient|alimento', 'ingredient'),
        ('number|numeric|integer', 'number'),
        ('missing|required|obrigat', 'incomplete_input'),
    ):
        if re.search(pattern, detail):
            code = category
            break
    result = {'error_code': code}
    ingredient = re.search(r'(?:feed|rufas id)\s*:?\s*(\d+)', detail)
    if ingredient:
        result['feed_id'] = int(ingredient[1])
    return result
