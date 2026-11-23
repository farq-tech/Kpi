#!/usr/bin/env python3
"""تحليل التصميم التنظيمي (OD) من data/org و data/raw. يكتب docs/od-findings.md. بلا مكتبات خارجية."""
import csv, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
def load(p):
    with open(ROOT / p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

units = {u["unit_id"]: u for u in load("data/org/units.csv")}
funcs = {f["function_id"]: f for f in load("data/org/functions.csv")}
asg = load("data/org/assignments.csv")
donors = {d["id"]: d for d in load("data/raw/donors.csv")}
fit = load("data/raw/donor_fit.csv")
groups = load("data/org/donor_groups.csv")
progs = load("data/org/programs.csv")
N = lambda u: units[u]["name_ar"]
out = []
w = out.append

def table(head, rows):
    w("| " + " | ".join(head) + " |"); w("|" + "---|" * len(head))
    for r in rows: w("| " + " | ".join(str(c) for c in r) + " |")
    w("")

w("# نتائج تحليل التصميم التنظيمي (مُولَّد آليًا)\n")
w("> المصدر: متتبع المانحين (20 نوفمبر 2026). الإسنادات **مستخلصة من الملف**، وليست هيكلًا معتمدًا. أعد التوليد بـ `python3 tools/od_analysis.py` بعد كل تعديل على `data/`.\n")

# 1) حِمل الوحدات
by_unit = collections.Counter(a["unit_id"] for a in asg)
total = len(asg)
w(f"## 1) حِمل الوحدات ({total} إسنادًا)\n")
table(["الوحدة", "عدد البنود", "النسبة", "وظائف متميزة"],
      [(N(u), c, f"{c/total:.0%}", len({a['function_id'] for a in asg if a['unit_id']==u}))
       for u, c in by_unit.most_common()])

# 2) مصفوفة وظيفة × وحدة
w("## 2) مصفوفة الوظائف × الوحدات (عدد البنود)\n")
uids = list(units)
rows = []
for fid, f in funcs.items():
    cnt = collections.Counter(a["unit_id"] for a in asg if a["function_id"] == fid)
    rows.append((f"{fid} {f['name_ar']}", *[cnt.get(u, "") for u in uids], len(cnt)))
table(["الوظيفة", *[N(u) for u in uids], "عدد الوحدات"], rows)

# 3) ازدواج/تضارب: وظيفة بأكثر من وحدة
w("## 3) وظائف موزعة على أكثر من وحدة (مرشحة للازدواج أو التضارب)\n")
split = []
for fid, f in funcs.items():
    cnt = collections.Counter(a["unit_id"] for a in asg if a["function_id"] == fid)
    if len(cnt) >= 2:
        split.append((len(cnt), fid, f["name_ar"], "؛ ".join(f"{N(u)} ({c})" for u, c in cnt.most_common())))
split.sort(reverse=True)
table(["الوظيفة", "عدد الوحدات", "التوزيع"], [(f"{fid} {n}", k, d) for k, fid, n, d in split])

# 4) وظائف بلا مالك
w("## 4) وظائف بلا أي دليل على مالك (فجوات)\n")
owned = {a["function_id"] for a in asg}
table(["الوظيفة", "المجموعة"], [(f"{fid} {f['name_ar']}", f["group"]) for fid, f in funcs.items() if fid not in owned])

# 5) ملكية المانحين
w("## 5) ملكية علاقات المانحين\n")
dc = collections.defaultdict(list)
for d in donors.values(): dc[d["owner"]].append(d)
table(["الوحدة", "كل الجهات", "أولوية أ", "أولوية ب", "أولوية ج"],
      [(N(u), len(l), *[sum(x["priority"] == p for x in l) for p in "أبج"]) for u, l in sorted(dc.items(), key=lambda kv: -len(kv[1]))])
w(f"عدد الوحدات التي تملك علاقات مانحين: **{len(dc)}** من {len(units)}.\n")

# 6) مجموعات العائلات
w("## 6) مجموعات المانحين المترابطة وتعارض المالك\n")
rows = []
for g in groups:
    ids = g["donor_ids"].split(";")
    owners = sorted({N(donors[i]["owner"]) for i in ids})
    rows.append((g["name_ar"], "؛ ".join(f"{donors[i]['name']} [{N(donors[i]['owner'])}]" for i in ids),
                 "⚠ أكثر من مالك" if len(owners) > 1 else "مالك واحد", g["confidence"]))
table(["المجموعة", "الجهات [المالك]", "الحالة", "الثقة"], rows)

# 7) المانحون ذوو الأولوية أ وب
w("## 7) المانحون ذوو الأولوية أ وب ومالكوهم\n")
pw = {"أ": 3, "ب": 2, "ج": 1}
rows = []
for d in sorted(donors.values(), key=lambda d: (-pw[d["priority"]], d["id"])):
    if d["priority"] == "أ" or d["priority"] == "ب":
        rows.append((d["name"], d["priority"], d["window_open"], N(d["owner"])))
table(["الجهة", "الأولوية", "نافذة مفتوحة؟", "المالك"], rows)

# 8) تغطية المشاريع
w("## 8) تغطية المشاريع بالمانحين (من مصفوفة الملاءمة)\n")
cov = collections.defaultdict(lambda: collections.Counter())
for r in fit: cov[r["program"]][r["fit"]] += 1
table(["المشروع", "✓ مناسب", "○ ممكن", "— غير مناسب"],
      sorted(([p, c["✓"], c["○"], c["—"]] for p, c in cov.items()), key=lambda x: -(x[1]*2+x[2])))

(ROOT / "docs/od-findings.md").write_text("\n".join(out), encoding="utf-8")
print("wrote docs/od-findings.md")
