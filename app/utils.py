from decimal import Decimal, ROUND_HALF_UP
from flask import request, g


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


# ============================================================
# User ID Helper
# ============================================================
def get_user_id(default=1):
    """
    يرجّع user_id:
    1. من g (اللي بيتحط في middleware)
    2. من الـ header X-User-Id
    3. القيمة الافتراضية
    """
    try:
        uid = getattr(g, 'user_id', None)
        if uid:
            return int(uid)
    except Exception:
        pass

    try:
        uid = request.headers.get('X-User-Id')
        if uid:
            return int(uid)
    except Exception:
        pass

    return default


# ============================================================
# Enrich with user name
# ============================================================
def enrich_with_user(rows, id_field='created_by', name_field='created_by_name'):
    """
    يضيف اسم المستخدم لكل صف.
    rows: قائمة من dict أو sqlite3.Row
    id_field: اسم الحقل اللي فيه user_id
    name_field: اسم الحقل الجديد اللي هيحتوي على الاسم
    """
    from app.database import db

    if not rows:
        return rows

    user_ids = set()
    for row in rows:
        try:
            uid = row.get(id_field) if isinstance(row, dict) else row[id_field]
            if uid:
                user_ids.add(int(uid))
        except Exception:
            pass

    if not user_ids:
        result = []
        for row in rows:
            d = dict(row)
            d[name_field] = '—'
            result.append(d)
        return result

    placeholders = ','.join(['?'] * len(user_ids))
    users = db.query(
        f"SELECT id, username, full_name FROM users WHERE id IN ({placeholders})",
        tuple(user_ids)
    )
    user_map = {u['id']: (u['full_name'] or u['username'] or ('#' + str(u['id']))) for u in users}

    result = []
    for row in rows:
        d = dict(row)
        try:
            uid = d.get(id_field)
            d[name_field] = user_map.get(int(uid), '—') if uid else '—'
        except Exception:
            d[name_field] = '—'
        result.append(d)

    return result