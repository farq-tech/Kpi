#!/usr/bin/env python3
"""يستخرج من متتبع المانحين: data/raw/donors.csv و donor_fit.csv و data/org/assignments.csv.
تشغيل:  python3 tools/import_xlsx.py
ربط البنود بالوظائف مكتوب صراحةً أدناه حتى يمكن مراجعته وتعديله."""
import csv, pathlib, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
wb = openpyxl.load_workbook(ROOT / "data/source/donor-tracker-2026-11-20.xlsx", data_only=False)

UNIT = {"المدير التنفيذي": "EXEC", "مدير البرامج": "PROG", "مدير التطوير": "DEV", "فريق التطوير": "DEV",
        "المالية": "FIN", "تقنية المعلومات": "IT", "الإعلام": "MEDIA", "الموارد البشرية": "HR", "العلاقات": "REL"}

def rows(sheet, first, last_col=None):
    for r in wb[sheet].iter_rows(min_row=first, values_only=True):
        if r[0] is not None and (len(r) < 2 or r[1] is not None):
            yield r

# --- الجهات المانحة
donors = []
for r in wb["قاعدة الجهات"].iter_rows(min_row=7, values_only=True):
    if not r[1]:
        continue
    donors.append({"id": f"D{int(r[0]):02d}", "name": r[1], "category": r[2], "fit": r[5], "priority": r[14],
                   "status": r[15], "window_open": r[16], "owner": UNIT[r[19]], "next_step": r[20]})

# --- مصفوفة الملاءمة
fit_ws = wb["مصفوفة المشاريع"]
hdr = [c for c in next(fit_ws.iter_rows(min_row=6, max_row=6, values_only=True))]
fit = []
for r in fit_ws.iter_rows(min_row=7, values_only=True):
    if not r[0]:
        continue
    for i, mark in enumerate(r[1:], start=1):
        fit.append({"donor": r[0], "program_id": f"P{i:02d}", "program": hdr[i], "fit": mark})

# --- الإسنادات: (المصدر، البند، الوظيفة، الوحدة)
A = []
def add(src, item, fn, owner):
    A.append({"source": src, "item": item, "function_id": fn, "unit_id": UNIT[owner]})

# ملف الجهوزية — الوظيفة لكل مستند (يدوي)
READY_FN = ["F02", "F02", "F02", "F02", "F02", "F02", "F01", "F03", "F04", "F11", "F05", "F01", "F03", "F13", "F08",
            "F10", "F12", "F13", "F18", "F01"]
ready = [r for r in wb["ملف الجهوزية"].iter_rows(min_row=7, max_row=26, values_only=True)]
assert len(ready) == len(READY_FN) and all(r[3] for r in ready), "تغيّر شكل ورقة الجهوزية"
for r, fn in zip(ready, READY_FN):
    add("ملف الجهوزية", r[0], fn, r[3])

# تقويم المنح (يدوي لكل صف)
CAL_FN = ["F09", "F17", "F18", "F08", "F08", "F17", "F08", "F08", "F08", "F08", "F09", "F17", "F15", "F07", "F18", "F08"]
cal = [r for r in wb["تقويم المنح"].iter_rows(min_row=7, max_row=22, values_only=True)]
assert len(cal) == len(CAL_FN) and all(r[4] for r in cal), "تغيّر شكل ورقة التقويم"
for r, fn in zip(cal, CAL_FN):
    add("تقويم المنح", f"{r[1]} — {r[2]}", fn, r[4])

# خطة 90 يومًا
PLAN_FN = ["F07", "F08", "F09", "F08", "F07", "F17"]
plan = [r for r in wb["خطة 90 يومًا"].iter_rows(min_row=7, max_row=12, values_only=True)]
assert len(plan) == len(PLAN_FN) and all(r[5] for r in plan), "تغيّر شكل ورقة الخطة"
for r, fn in zip(plan, PLAN_FN):
    add("خطة 90 يومًا", f"{r[0]} ({r[1]})", fn, r[5])

# ملكية المانحين = إدارة علاقة المانح
for d in donors:
    A.append({"source": "قاعدة الجهات", "item": d["name"], "function_id": "F09", "unit_id": d["owner"]})

def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)

dump(ROOT / "data/raw/donors.csv", donors)
dump(ROOT / "data/raw/donor_fit.csv", fit)
dump(ROOT / "data/org/assignments.csv", A)
print(f"donors={len(donors)} fit={len(fit)} assignments={len(A)}")
