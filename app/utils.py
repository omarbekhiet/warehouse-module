from decimal import Decimal, ROUND_HALF_UP


def to_decimal(v, default=0):
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal(str(default))


def round_decimal(v, places=4):
    d = to_decimal(v)
    return d.quantize(Decimal('1.' + '0' * places), rounding=ROUND_HALF_UP)


def json_safe(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(i) for i in obj]
    return obj
