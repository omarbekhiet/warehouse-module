# -*- coding: utf-8 -*-
"""
سكربت فحص وتصحيح قيود اليومية وقاعدة بيانات نظام ERP
=====================================================
مخصص لمسار/اسم قاعدة البيانات لديك:  I:\\warehouse-module\\database\\warehouse

طرق الاستخدام (PowerShell):
    1) فحص فقط (لا يعدّل شيئًا — ابدأ به دائمًا):
        python scripts/check_and_fix_db.py --check

    2) فحص + تصحيح تلقائي مع أخذ نسخة احتياطية تلقائية أولًا:
        python scripts/check_and_fix_db.py --fix

    3) تحديد مسار يدويًا إذا كان مختلفًا:
        python scripts/check_and_fix_db.py --db "I:\\warehouse-module\\database\\warehouse" --fix

التصحيحات التي ينفذها الوضع --fix (كلها آمنة وقابلة للتراجع عبر النسخة الاحتياطية):
    [F1] حذف القيود اليتيمة (سطور مرتبطة بقيود محذوفة).
    [F2] حذف القيود التي لا تحتوي أي سطور.
    [F3] حذف القيود الصفرية (كل مدين ودائن = 0).
    [F4] كشف القيود غير المتوازنة (مدين != دائن) وإصلاحها بإضافة/تعديل سطر
         التسوية على حساب "أخطاء تسوية القيود" (يُنشأ تلقائيًا إن لم يوجد).
         ⚠ يُبلغ عن كل قيد تمت معالجته ورقمه وتفاصيله في التقرير النهائي للمراجعة.
    [F5] إزالة تكرار رقم القيد entry_no (إعادة ترقيم المكرر بلاحقة -DUPn) بدل حذفه،
         لأن الحذف قد يفقد حركة مالية حقيقية.
    [F6] إعادة بناء قيد الإقفال السنوي CLOSE-{year} للفترات المنتهية بحيث يكون:
         متوازنًا، ويصفّر أرصدة الإيرادات والمصروفات المتراكمة حتى نهاية العام،
         ويحوّل صافي النتيجة إلى الأرباح المحتجزة (3100 أو ما يقوم مقامه).
         يحذف القيود المسماة CLOSE-* غير المتوازنة أو المكررة أولًا.
    [F7] ضبط تواريخ القيود الخارجة عن المنطق (تواريخ NULL/فارغة → تاريخ الإنشاء).
    [F8] فحص سلامة حقول المبالغ (NULL في debit/credit → 0).

ملاحظات مهنية:
    - لا يغيّر السكربت أي سطر صحيح التوازن؛ القيود السليمة تبقى كما هي حرفيًا.
    - بعد التصحيح يُعاد الفحص تلقائيًا ويُطبع تقرير "قبل/بعد".
    - لبيئة PostgreSQL يمكن لاحقًا تكييف نفس المنطق؛ الحالي يعمل على SQLite.
"""
import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

DEFAULT_DB_CANDIDATES = [
    r"I:\warehouse-module\database\warehouse",
    r"I:\warehouse-module\database\warehouse.db",
    "erp.db",
    "backend/erp.db",
]

ENTRY_TABLE = "acc_journal_entries"
LINE_TABLE = "acc_journal_lines"
ACC_TABLE = "acc_accounts"

SUSPENSE_CODE = "9999"
SUSPENSE_NAME = "أخطاء تسوية القيود (حساب وسطي للمراجعة)"
REVENUE_TYPES = ("revenue", "income")
EXPENSE_TYPES = ("expense",)


def q(cur, sql, args=()):
    cur.execute(sql, args)
    return cur.fetchall()


def table_exists(cur, name):
    return len(q(cur, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))) > 0


def get_acc_map(cur):
    rows = q(cur, f"SELECT id, code, name_ar, account_type FROM {ACC_TABLE}")
    return {r[0]: {"code": r[1], "name": r[2], "type": r[3]} for r in rows}


def ensure_suspense_account(cur):
    row = q(cur, f"SELECT id FROM {ACC_TABLE} WHERE code=?", (SUSPENSE_CODE,))
    if row:
        return row[0][0]
    cur.execute(
        f"INSERT INTO {ACC_TABLE} (code, name_ar, name_en, account_type, is_active, notes, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (SUSPENSE_CODE, SUSPENSE_NAME, "Journal Suspense (audit)", "equity", 1,
         "حساب وسطي مؤقت يُنشئه سكربت الفحص تلقائيًا لتسوية القيود غير المتوازنة — يلزم مراجعته يدويًا وحصر بنوده.",
         datetime.now().isoformat(sep=" ", timespec="seconds")),
    )
    return cur.lastrowid


def find_retained_earnings_id(cur):
    row = q(cur, f"SELECT id FROM {ACC_TABLE} WHERE code LIKE '31%' ORDER BY code LIMIT 1")
    if row:
        return row[0][0]
    row = q(cur, f"SELECT id FROM {ACC_TABLE} WHERE account_type='equity' AND code NOT LIKE '30%' ORDER BY code LIMIT 1")
    return row[0][0] if row else None


def entry_summary(cur):
    """ملخص لكل قيد: إجماليات + عدد الأسطر."""
    return q(cur, f"""
        SELECT e.id, e.entry_no, e.date, e.description, e.source_module, e.source_ref,
               COUNT(l.id), COALESCE(SUM(l.debit),0), COALESCE(SUM(l.credit),0)
        FROM {ENTRY_TABLE} e LEFT JOIN {LINE_TABLE} l ON l.entry_id = e.id
        GROUP BY e.id ORDER BY e.date, e.id""")


def fmt(v):
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return str(v)


# ─────────────────────────── الفحص ───────────────────────────
def run_checks(cur):
    issues = []
    accmap = get_acc_map(cur)

    # 1) قيود يتيم / بدون أسطر / صفرية / غير متوازنة
    for eid, eno, edate, desc, smod, sref, nlines, tot_d, tot_c in entry_summary(cur):
        d, c = float(tot_d or 0), float(tot_c or 0)
        if nlines == 0:
            issues.append(("NO_LINES", eid, eno, f"قيد بلا أي سطور ({desc})", (d, c)))
        elif abs(d) < 0.005 and abs(c) < 0.005:
            issues.append(("ZERO", eid, eno, f"قيد صفر القيم ({desc})", (d, c)))
        elif abs(d - c) > 0.005:
            issues.append(("UNBALANCED", eid, eno,
                           f"غير متوازن: مدين {fmt(d)} ≠ دائن {fmt(c)} — '{desc}' [{smod or '-'}]",
                           (d, c)))

    # 2) أسطر يتيمة
    orphans = q(cur, f"SELECT COUNT(*) FROM {LINE_TABLE} l LEFT JOIN {ENTRY_TABLE} e ON e.id=l.entry_id WHERE e.id IS NULL")[0][0]
    if orphans:
        issues.append(("ORPHAN_LINES", None, "-", f"{orphans} سطر مرتبط بقيود محذوفة", (0, 0)))

    # 3) تكرار رقم القيد
    dups = q(cur, f"SELECT entry_no, COUNT(*) FROM {ENTRY_TABLE} GROUP BY entry_no HAVING COUNT(*)>1")
    for eno, cnt in dups:
        issues.append(("DUP_ENTRY_NO", None, eno, f"رقم قيد مكرر {cnt} مرات", (0, 0)))

    # 4) أسطر بها مدين ودائن معًا أو قيم NULL
    bad = q(cur, f"SELECT COUNT(*) FROM {LINE_TABLE} WHERE debit IS NULL OR credit IS NULL OR (debit>0 AND credit>0)")
    if bad[0][0]:
        issues.append(("BAD_LINE_VALUES", None, "-", f"{bad[0][0]} سطر بقيم غير سليمة (NULL أو مدين+دائن معًا)", (0, 0)))

    # 5) تواريخ مفقودة
    nd = q(cur, f"SELECT COUNT(*) FROM {ENTRY_TABLE} WHERE date IS NULL OR TRIM(CAST(date AS TEXT))=''")[0][0]
    if nd:
        issues.append(("MISSING_DATE", None, "-", f"{nd} قيد بلا تاريخ", (0, 0)))

    # 6) أرصدة دورية متراكمة (إيرادات/مصروفات) قبل آخر قيد إقفال سليم — تنبيه فقط
    # 7) توازن عام الأستاذ
    tb = q(cur, f"SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM {LINE_TABLE}")[0]
    if abs(float(tb[0]) - float(tb[1])) > 0.005:
        issues.append(("TB_IMBALANCE", None, "-",
                       f"ميزان الأستاذ العام غير متوازن: مدين {fmt(tb[0])} / دائن {fmt(tb[1])}",
                       (float(tb[0]), float(tb[1]))))

    # 8) فحص تكاملي: مسيرات الرواتب المعتمدة مقابل قيودها المحاسبية (إن وُجدت جداول HR)
    if table_exists(cur, "hr_payroll_runs") and table_exists(cur, "hr_payroll_details"):
        runs = q(cur, """SELECT id, run_no, period, status, gross_total, deductions_total, net_total,
                                accrual_entry_id FROM hr_payroll_runs WHERE status IN ('approved','posted')""")
        for rid, run_no, period, st, g, dd, n, aid in runs:
            dl = q(cur, """SELECT COALESCE(SUM(gross),0), COALESCE(SUM(deductions_total),0),
                                  COALESCE(SUM(net),0) FROM hr_payroll_details WHERE run_id=?""", (rid,))[0]
            if abs(float(dl[0]) - float(g or 0)) > 0.01 or abs(float(dl[2]) - float(n or 0)) > 0.01:
                issues.append(("PAYROLL_MISMATCH", rid, run_no,
                               f"مسير {run_no}: إجماليات المسير ({fmt(g)}/{fmt(n)}) لا تطابق تفاصيل الموظفين ({fmt(dl[0])}/{fmt(dl[2])})",
                               (0, 0)))
            if aid:
                # إجمالي مدين قيود المسير يجب أن يطابق الإجمالي المستحق (gross_total)
                tot_d = float(q(cur, f"SELECT COALESCE(SUM(debit),0) FROM {LINE_TABLE} WHERE entry_id=?", (aid,))[0][0] or 0)
                if abs(tot_d - float(g or 0)) > 0.01:
                    issues.append(("PAYROLL_ENTRY_MISMATCH", rid, run_no,
                                   f"مسير {run_no}: مدين قيد الاستحقاق ({fmt(tot_d)}) ≠ إجمالي المستحق ({fmt(g)}) — راجع القيد id={aid}",
                                   (tot_d, float(g))))
                # دائن حسابات الخصوم (24xx) يجب أن يساوي الصافي + الاستقطاعات
                cr_liab = float(q(cur, f"""SELECT COALESCE(SUM(l.credit),0) FROM {LINE_TABLE} l
                          JOIN {ACC_TABLE} a ON a.id=l.account_id
                          WHERE l.entry_id=? AND a.code LIKE '24%'""", (aid,))[0][0] or 0)
                expected_cr = round(float(n or 0) + float(dd or 0), 4)
                if abs(cr_liab - expected_cr) > 0.01:
                    issues.append(("PAYROLL_LIAB_MISMATCH", rid, run_no,
                                   f"مسير {run_no}: دائن حسابات الاستحقاق ({fmt(cr_liab)}) ≠ صافي+استقطاعات ({fmt(expected_cr)}) — راجع القيد id={aid}",
                                   (cr_liab, expected_cr)))
    return issues, accmap


# ─────────────────────────── التصحيح ───────────────────────────
def apply_fixes(cur):
    fixes = []
    accmap = get_acc_map(cur)

    # F1: أسطر يتيمة
    n = cur.execute(f"DELETE FROM {LINE_TABLE} WHERE entry_id NOT IN (SELECT id FROM {ENTRY_TABLE})").rowcount
    if n:
        fixes.append(f"[F1] حُذفت {n} سطور يتيمة.")

    # F2: قيود بلا أسطر
    ids = [r[0] for r in q(cur, f"SELECT e.id FROM {ENTRY_TABLE} e LEFT JOIN {LINE_TABLE} l ON l.entry_id=e.id WHERE l.id IS NULL")]
    if ids:
        cur.execute(f"DELETE FROM {ENTRY_TABLE} WHERE id IN ({','.join('?'*len(ids))})", ids)
        fixes.append(f"[F2] حُذفت {len(ids)} قيود بلا أسطر (ids={ids}).")

    # F3: قيود صفر القيم
    zero_ids = [r[0] for r in q(cur, f"""
        SELECT e.id FROM {ENTRY_TABLE} e JOIN {LINE_TABLE} l ON l.entry_id=e.id
        GROUP BY e.id HAVING COALESCE(SUM(l.debit),0)=0 AND COALESCE(SUM(l.credit),0)=0""")]
    if zero_ids:
        cur.execute(f"DELETE FROM {LINE_TABLE} WHERE entry_id IN ({','.join('?'*len(zero_ids))})", zero_ids)
        cur.execute(f"DELETE FROM {ENTRY_TABLE} WHERE id IN ({','.join('?'*len(zero_ids))})", zero_ids)
        fixes.append(f"[F3] حُذفت {len(zero_ids)} قيود صفرية القيم (ids={zero_ids}).")

    # F5: تكرار أرقام القيود
    dups = q(cur, f"SELECT entry_no FROM {ENTRY_TABLE} GROUP BY entry_no HAVING COUNT(*)>1")
    for (eno,) in dups:
        rows = q(cur, f"SELECT id FROM {ENTRY_TABLE} WHERE entry_no=? ORDER BY id", (eno,))
        for k, (rid,) in enumerate(rows[1:], start=2):
            cur.execute(f"UPDATE {ENTRY_TABLE} SET entry_no=? WHERE id=?", (f"{eno}-DUP{k}", rid))
            fixes.append(f"[F5] أعيد ترقيم القيد المكرر id={rid} إلى {eno}-DUP{k}.")

    # F7: تواريخ مفقودة
    n = cur.execute(f"UPDATE {ENTRY_TABLE} SET date=created_at WHERE date IS NULL OR TRIM(CAST(date AS TEXT))=''").rowcount
    if n:
        fixes.append(f"[F7] عُوّض تاريخ {n} قيدًا من وقت الإنشاء.")

    # F8: قيم NULL في الأسطر
    n1 = cur.execute(f"UPDATE {LINE_TABLE} SET debit=0 WHERE debit IS NULL").rowcount
    n2 = cur.execute(f"UPDATE {LINE_TABLE} SET credit=0 WHERE credit IS NULL").rowcount
    if n1 or n2:
        fixes.append(f"[F8] استُبدلت قيم NULL في {n1+n2} سطر بصفر.")

    # F6a: حذف قيود الإقفال المعيبة (غير المتوازنة أو المكررة) — تُعاد بناؤها نظيفة لاحقًا
    out = []
    closes = q(cur, f"SELECT id, entry_no FROM {ENTRY_TABLE} WHERE entry_no LIKE 'CLOSE%' ORDER BY id")
    seen_years = set()
    for cid, cno in closes:
        year = cno.split("-")[-1]
        d, c = q(cur, f"SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM {LINE_TABLE} WHERE entry_id=?", (cid,))[0]
        balanced = abs(float(d) - float(c)) < 0.005
        if year in seen_years or not balanced:
            cur.execute(f"DELETE FROM {LINE_TABLE} WHERE entry_id=?", (cid,))
            cur.execute(f"DELETE FROM {ENTRY_TABLE} WHERE id=?", (cid,))
            out.append(f"[F6] حُذف قيد الإقفال المعيب/المكرر {cno} (id={cid}, متوازن={balanced}) — سيُعاد بناؤه.")
        seen_years.add(year)

    # F4: تسوية القيود غير المتوازنة المتبقية (بعد ضمان أن CLOSE المعيب حُذف لا سُوُسِّد)
    suspense_id = None
    for eid, eno, edate, desc, smod, sref, nlines, tot_d, tot_c in entry_summary(cur):
        d, c = float(tot_d or 0), float(tot_c or 0)
        if not nlines or (abs(d) < 0.005 and abs(c) < 0.005):
            continue
        diff = round(d - c, 4)
        if abs(diff) > 0.005:
            if suspense_id is None:
                suspense_id = ensure_suspense_account(cur)
            if diff > 0:   # مدين زائد → نضيف دائن تسوية
                cur.execute(f"INSERT INTO {LINE_TABLE} (entry_id, account_id, debit, credit) VALUES (?,?,?,?)",
                            (eid, suspense_id, 0, diff))
                out.append(f"[F4] القيد {eno}: أُضيف سطر دائن تسوية {fmt(diff)} على {SUSPENSE_CODE} (يجب مراجعته يدويًا).")
            else:          # دائن زائد → مدين تسوية
                amt = round(-diff, 4)
                cur.execute(f"INSERT INTO {LINE_TABLE} (entry_id, account_id, debit, credit) VALUES (?,?,?,?)",
                            (eid, suspense_id, amt, 0))
                out.append(f"[F4] القيد {eno}: أُضيف سطر مدين تسوية {fmt(amt)} على {SUSPENSE_CODE} (يجب مراجعته يدويًا).")

    # F6b: إعادة بناء قيد إقفال موحد حتى نهاية آخر سنة منتهية قبل السنة الجارية
    re_id = find_retained_earnings_id(cur)
    last_dt = q(cur, f"SELECT MAX(datetime(date)) FROM {ENTRY_TABLE}")[0][0]
    if re_id is None:
        out.append("[F6] ⚠ لا يوجد حساب أرباح محتجزة (31xx) — تخطيت إعادة بناء الإقفال؛ أنشئ الحساب ثم أعد التشغيل.")
    elif last_dt:
        cutoff_year = int(last_dt[:4]) - 1
        end_dt = f"{cutoff_year}-12-31 23:59:59"
        accmap = get_acc_map(cur)
        bal = period_balance_until(cur, end_dt)
        lines, rev_close, exp_close = [], 0.0, 0.0
        for aid, signed in bal.items():
            a = accmap.get(aid)
            if not a or a["type"] not in REVENUE_TYPES + EXPENSE_TYPES or abs(signed) < 0.005:
                continue
            if a["type"] in REVENUE_TYPES:      # رصيد دائن ⇒ signed سالب ⇒ القفل بمدين
                amt = round(-signed, 4); lines.append((aid, amt, 0)); rev_close += amt
            else:                                # مصروف ⇒ القفل بدائن
                amt = round(signed, 4); lines.append((aid, 0, amt)); exp_close += amt
        profit = round(rev_close - exp_close, 4)
        if lines and abs(profit) > 0.005:
            if profit >= 0:
                lines.append((re_id, 0, profit))
            else:
                lines.append((re_id, round(-profit, 4), 0))
            td = round(sum(l[1] for l in lines), 4); tc = round(sum(l[2] for l in lines), 4)
            if abs(td - tc) <= 0.005:
                eno = f"CLOSE-THRU-{cutoff_year}"
                cur.execute(
                    f"INSERT INTO {ENTRY_TABLE} (entry_no, date, description, source_module, source_ref, created_by, created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (eno, f"{cutoff_year+1}-01-01 00:00:00",
                     f"قيد إقفال الفترات السابقة على الأرباح المحتجزة — يُغلق المتراكم حتى نهاية {cutoff_year} فقط",
                     "manual", eno, "db-fix-script", datetime.now().isoformat(sep=" ", timespec="seconds")))
                nid = cur.lastrowid
                for aid, dd, cc in lines:
                    cur.execute(f"INSERT INTO {LINE_TABLE} (entry_id, account_id, debit, credit) VALUES (?,?,?,?)",
                                (nid, aid, dd, cc))
                out.append(f"[F6] أُنشئ {eno}: أقفال إيرادات {fmt(rev_close)}، مصروفات {fmt(exp_close)}، صافي {fmt(profit)} → للأرباح المحتجزة.")
            else:
                out.append(f"[F6] ⚠ تعذر توليد قيد إقفال متوازن (فرق {fmt(td-tc)}) — مراجعة يدوية مطلوبة.")
        elif lines:
            out.append(f"[F6] صافي الفترة حتى {cutoff_year} = صفر — لا حاجة لقيد إقفال جديد.")
        else:
            out.append(f"[F6] لا توجد أرصدة دورية متراكمة حتى {end_dt} لإقفالها.")
    fixes += out
    return fixes


def period_balance_until(cur, end_dt_str):
    """صافي الرصيد التراكمي (مدين−دائن) لكل حساب حتى تاريخ/وقت معين (inclusive)."""
    rows = q(cur, f"""
        SELECT l.account_id, COALESCE(SUM(l.debit),0)-COALESCE(SUM(l.credit),0)
        FROM {LINE_TABLE} l JOIN {ENTRY_TABLE} e ON e.id=l.entry_id
        WHERE datetime(e.date) <= datetime(?)
        GROUP BY l.account_id""", (end_dt_str,))
    return {r[0]: float(r[1]) for r in rows}


def existing_close_dates(cur):
    return [r[0] for r in q(cur, f"SELECT date FROM {ENTRY_TABLE} WHERE entry_no LIKE 'CLOSE-%'")]


def rebuild_close_entries(cur):
    out = []
    re_id = find_retained_earnings_id(cur)
    if re_id is None:
        return ["[F6] ⚠ لا يوجد حساب أرباح محتجزة (31xx) — تخطيت إعادة بناء الإقفال؛ أنشئ الحساب ثم أعد التشغيل."]

    accmap = get_acc_map(cur)
    years = sorted({int((d or "")[:4]) for d,_ in
                    [(e[2], None) for e in entry_summary(cur) if e[2]]})
    if not years:
        return out

    # حذف قيود CLOSE القديمة غير المتوازنة أو المكررة، والإبقاء على الأحدث لكل سنة إن كان سليمًا
    closes = q(cur, f"SELECT id, entry_no, date FROM {ENTRY_TABLE} WHERE entry_no LIKE 'CLOSE-%' ORDER BY id")
    seen = {}
    for cid, cno, cdate in closes:
        year = cno.split("-")[-1]
        d, c = q(cur, f"SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM {LINE_TABLE} WHERE entry_id=?", (cid,))[0]
        balanced = abs(float(d) - float(c)) < 0.005
        if year in seen or not balanced:
            cur.execute(f"DELETE FROM {LINE_TABLE} WHERE entry_id=?", (cid,))
            cur.execute(f"DELETE FROM {ENTRY_TABLE} WHERE id=?", (cid,))
            out.append(f"[F6] حُذف قيد الإقفال المعيب/المكرر {cno} (id={cid}, متوازن={balanced}).")
        else:
            seen[year] = cid

    last_entry_date = q(cur, f"SELECT MAX(datetime(date)) FROM {ENTRY_TABLE}")[0][0]
    if not last_entry_date:
        return out
    max_year = int(last_entry_date[:4])

    for year in range(min(years), max_year):   # سنوات منتهية فقط
        end_dt = f"{year}-12-31 23:59:59"
        bal = period_balance_until(cur, end_dt)
        lines = []  # (account_id, debit, credit)
        net = 0.0
        for aid, signed in bal.items():
            a = accmap.get(aid)
            if not a or a["type"] not in REVENUE_TYPES + EXPENSE_TYPES:
                continue
            if abs(signed) < 0.005:
                continue
            if a["type"] in REVENUE_TYPES:      # رصيد دائن ⇒ signed سالب
                lines.append((aid, round(-signed, 4), 0))
            else:                                # مصروف رصيد مدين ⇒ signed موجب
                lines.append((aid, 0, round(signed, 4)))
            net += -signed if a["type"] in REVENUE_TYPES else -signed * 0  # placeholder
        # صافي الربح = مجموع أقفال الإيرادات − مجموع أقفال المصروفات
        rev_close = sum(l[1] for l in lines if l[1])
        exp_close = sum(l[2] for l in lines if l[2])
        profit = round(rev_close - exp_close, 4)
        if not lines:
            continue
        if profit >= 0:
            lines.append((re_id, 0, profit))     # ربح ⇒ دائن الأرباح المحتجزة
        else:
            lines.append((re_id, round(-profit, 4), 0))  # خسارة ⇒ مدين
        total_d = round(sum(l[1] for l in lines), 4)
        total_c = round(sum(l[2] for l in lines), 4)
        if abs(total_d - total_c) > 0.005:
            out.append(f"[F6] ⚠ تعذر توليد قيد إقفال متوازن لسنة {year} (فرق {fmt(total_d-total_c)}) — مراجعة يدوية مطلوبة.")
            continue
        cur.execute(
            f"INSERT INTO {ENTRY_TABLE} (entry_no, date, description, source_module, source_ref, created_by, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (f"CLOSE-{year}", f"{year+1}-01-01 00:00:00",
             f"قيد إقفال الفترات السابقة على الأرباح المحتجزة — يُغلق المتراكم حتى نهاية {year} فقط (أُعيد بناؤه آليًا)",
             "manual", f"CLOSE-{year}", "db-fix-script", datetime.now().isoformat(sep=" ", timespec="seconds")))
        new_id = cur.lastrowid
        for aid, dd, cc in lines:
            cur.execute(f"INSERT INTO {LINE_TABLE} (entry_id, account_id, debit, credit) VALUES (?,?,?,?)",
                        (new_id, aid, dd, cc))
        out.append(f"[F6] أُنشئ قيد إقفال متوازن CLOSE-{year}: مقفَل إيرادات {fmt(rev_close)}، مصروفات {fmt(exp_close)}، صافي {fmt(profit)}.")

    # تحذير: هل توجد قيود تشغيلية مؤرخة بعد آخر إغلاق؟ (تنبيه مهني فقط)
    return out


def rebuild_payroll_accrual(cur):
    """إعادة توليد سطور قيد استحقاق المسير من تفاصيل الموظفين مباشرة (مصدر الحقيقة).
    يعمل فقط لمسيرات approved/posted المرتبطة بقيد accrual موجود؛ لا يمس القيود السليمة."""
    out = []
    if not (table_exists(cur, "hr_payroll_runs") and table_exists(cur, "hr_payroll_details")):
        return out
    acc_ids = {c: i for i, c in q(cur, f"SELECT id, code FROM {ACC_TABLE}")}
    runs = q(cur, """SELECT id, run_no, net_total, gross_total, deductions_total, accrual_entry_id
                     FROM hr_payroll_runs WHERE status IN ('approved','posted') AND accrual_entry_id IS NOT NULL""")
    for rid, run_no, n, g, dd, aid in runs:
        d_tot, c_tot = q(cur, f"""SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
                                  FROM {LINE_TABLE} WHERE entry_id=?""", (aid,))[0]
        # تحقق هل القيد الحالي يطابق التفاصيل؟ إن طابق لا نلمسه
        det = q(cur, """SELECT COALESCE(SUM(gross),0), COALESCE(SUM(net),0), COALESCE(SUM(deductions_total),0),
                               COALESCE(SUM(insurance_deduction),0), COALESCE(SUM(tax_deduction),0)
                        FROM hr_payroll_details WHERE run_id=?""", (rid,))[0]
        dg, dn, ddt, di, dt_ = [float(x or 0) for x in det]
        other = round(ddt - di - dt_, 4)
        expected_lines = [(acc_ids.get('5200'), dg, 0), (acc_ids.get('2400'), 0, dn + other),
                          (acc_ids.get('2420'), 0, di), (acc_ids.get('2430'), 0, dt_)]
        cur_lines = {(a, round(float(db),4), round(float(cr),4)) for a, db, cr in
                     q(cur, f"SELECT account_id, debit, credit FROM {LINE_TABLE} WHERE entry_id=?", (aid,))}
        exp_set = {(a, round(db,4), round(cr,4)) for a, db, cr in expected_lines if a is not None}
        if cur_lines == exp_set:
            continue
        missing = [i for i, c in enumerate(q(cur, "SELECT id FROM sqlite_master WHERE type='table'")) if False]
        # إعادة بناء السطور من التفاصيل
        cur.execute(f"DELETE FROM {LINE_TABLE} WHERE entry_id=?", (aid,))
        ok = True
        for acct_code, dbit, cred in [('5200', dg, 0), ('2400', 0, dn + other), ('2420', 0, di), ('2430', 0, dt_)]:
            a_id = acc_ids.get(acct_code)
            if a_id is None:
                out.append(f"[F9] ⚠ حساب {acct_code} غير موجود بالدليل — تخطيت إعادة بناء قيد مسير {run_no}.")
                ok = False; break
            if abs(dbit) < 0.005 and abs(cred) < 0.005:
                continue
            cur.execute(f"INSERT INTO {LINE_TABLE} (entry_id, account_id, debit, credit) VALUES (?,?,?,?)",
                        (aid, a_id, round(dbit,4), round(cred,4)))
        if ok:
            # تصفير إجماليات رأس المسير لتطابق التفاصيل (تسوية بيانات، ليست حركة دفترية)
            cur.execute("""UPDATE hr_payroll_runs SET gross_total=?, deductions_total=?, net_total=? WHERE id=?""",
                        (round(dg,4), round(ddt,4), round(dn,4), rid))
            out.append(f"[F9] أُعيد بناء قيد استحقاق المسير {run_no} من تفاصيل الموظفين: إجمالي {fmt(dg)}، صافي {fmt(dn)}، استقطاعات {fmt(ddt)}.")
    return out


# ─────────────────────────── التقارير ───────────────────────────
def print_report(title, issues, entries=None):
    print("=" * 72)
    print(title)
    print("=" * 72)
    if not issues:
        print("✓ لا توجد مشاكل — القيود سليمة ومتوازنة.")
    else:
        print(f"⚠ تم رصد {len(issues)} مشكلة:")
        for kind, eid, eno, msg, (d, c) in issues:
            print(f"  • [{kind}] {('id=%s %s' % (eid, eno)) if eid or eno!='-' else ''} {msg}")
    if entries:
        print("-" * 72)
        print(f"إجمالي القيود: {len(entries)}")
        unbal = [e for e in entries if abs(float(e[7]) - float(e[8])) > 0.005 and e[6] > 0]
        print(f"قيود غير متوازنة: {len(unbal)}")
        for e in unbal:
            print(f"   id={e[0]} {e[1]} | مدين {fmt(e[7])} / دائن {fmt(e[8])} | {e[3][:60]}")


def main():
    ap = argparse.ArgumentParser(description="فحص وتصحيح قيود اليومية وقاعدة بيانات ERP")
    ap.add_argument("--db", help="مسار ملف SQLite (افتراضي: محاولة عدة مسارات معروفة)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="فحص فقط")
    mode.add_argument("--fix", action="store_true", help="فحص + تصحيح مع نسخة احتياطية")
    args = ap.parse_args()

    path = args.db
    if not path:
        for cand in DEFAULT_DB_CANDIDATES:
            if os.path.exists(cand):
                path = cand
                break
    if not path or not os.path.exists(path):
        print(f"✗ لم يتم العثور على قاعدة البيانات. مرر المسار صراحةً:  --db \"مسار الملف\"")
        sys.exit(2)

    con = sqlite3.connect(path)
    cur = con.cursor()
    if not table_exists(cur, ENTRY_TABLE) or not table_exists(cur, LINE_TABLE):
        print("✗ الجدولان acc_journal_entries / acc_journal_lines غير موجودين — تأكد أنك تشير لقاعدة بيانات النظام الصحيح.")
        sys.exit(3)

    print(f"📂 قاعدة البيانات: {path}")

    issues_before, _ = run_checks(cur)
    entries = entry_summary(cur)
    print_report("◤ تقرير الفحص الأولي ◢", issues_before, entries)

    if args.fix:
        backup = path + ".backup-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        con.close()
        shutil.copy2(path, backup)
        print(f"\n💾 نسخة احتياطية: {backup}")
        con = sqlite3.connect(path)
        cur = con.cursor()
        fixes = apply_fixes(cur)
        con.commit()
        print("\n◤ التصحيحات المنفذة ◢")
        if fixes:
            for f in fixes:
                print("  ✔", f)
        else:
            print("  لا حاجة لأي تصحيح.")
        issues_after, _ = run_checks(cur)
        print()
        print_report("◤ تقرير الفحص بعد التصحيح ◢", issues_after, entry_summary(cur))
        if issues_after:
            print("\nℹ المشاكل المتبقية تتطلب قرارًا محاسبيًا يدويًا (راجع البنود أعلاه بالنوع DUP/UNBALANCED).")
    con.close()
    print("\nتم الانتهاء.")


if __name__ == "__main__":
    main()
