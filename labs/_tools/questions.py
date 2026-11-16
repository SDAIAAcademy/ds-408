"""The 60 certified questions of Qamar Telecom and the 8 flawed candidates (synthetic). Read by make_case_files.py.

Each answerable question: (id, lang, area, difficulty, text, query, answer_kind, tags)
  query: {"metrics": [...], "by": [...], "where": [...], "order": "desc"|"asc", "limit": 1}
  answer_kind: "value" (one number) or "label" (the group-by value of the first row)
  tags drive the stand-in model's errors: syn (needs synonyms), desc (needs descriptions), ex (needs examples)
Each refusal: (id, lang, area, text, reason)
"""
M = lambda d: f"time.month = DATE '{d}'"  # noqa: E731
FY = "time.fiscal_year = 'FY2025-26'"


def fq(q):
    return f"time.fiscal_quarter = 'FY2025-26-Q{q}'"


ANSWERABLE = [
    # ------------------------------------------------------------------ usage
    ("U01", "en", "usage", 1, "How much data did Qamar's lines use in March 2026, in gigabytes?",
     {"metrics": ["data_gb"], "where": [M("2026-03-01")]}, "value", []),
    ("U02", "ar", "usage", 1, "كم دقيقة مكالمات صوتية سُجّلت في فبراير 2026؟",
     {"metrics": ["voice_minutes"], "where": [M("2026-02-01")]}, "value", []),
    ("U03", "en", "usage", 1, "How many lines were active in June 2026?",
     {"metrics": ["active_lines"], "where": [M("2026-06-01")]}, "value", []),
    ("U04", "ar", "usage", 1, "كم استهلكت خطوط المنطقة الغربية من الإنترنت في يناير 2026؟",
     {"metrics": ["data_gb"], "where": ["customer.region = 'WES'", M("2026-01-01")]}, "value", ["syn"]),
    ("U05", "en", "usage", 1, "What was total data usage in the Central region in May 2026?",
     {"metrics": ["data_gb"], "where": ["customer.region = 'CEN'", M("2026-05-01")]}, "value", []),
    ("U06", "ar", "usage", 2, "ما متوسط استهلاك البيانات لكل خط في يونيو 2026؟",
     {"metrics": ["data_per_line"], "where": [M("2026-06-01")]}, "value", []),
    ("U07", "en", "usage", 2, "How much data did government customers use in the fiscal year 2025-26?",
     {"metrics": ["data_gb"], "where": ["customer.segment = 'government'", FY]}, "value", ["ex"]),
    ("U08", "ar", "usage", 2, "كم عدد الخطوط النشطة لعملاء قطاع الأعمال في المنطقة الشرقية في أبريل 2026؟",
     {"metrics": ["active_lines"], "where": ["customer.segment = 'business'", "customer.region = 'EAS'", M("2026-04-01")]}, "value", []),
    ("U09", "en", "usage", 2, "What was data per active line on the Qamar Fibre 100 plan in December 2025?",
     {"metrics": ["data_per_line"], "where": ["tariff.plan_name = 'Qamar Fibre 100'", M("2025-12-01")]}, "value", []),
    ("U10", "ar", "usage", 3, "أي باقة كان لها أعلى متوسط استهلاك بيانات لكل خط في يونيو 2026؟",
     {"metrics": ["data_per_line"], "by": ["tariff.plan_name"], "where": [M("2026-06-01")], "order": "desc", "limit": 1}, "label", []),
    ("U11", "en", "usage", 3, "Which region used the most voice minutes in the fiscal year 2025-26?",
     {"metrics": ["voice_minutes"], "by": ["customer.region"], "where": [FY], "order": "desc", "limit": 1}, "label", ["ex", "unstable"]),
    ("U12", "ar", "usage", 3, "كم استهلكت الخطوط من البيانات في شهر رمضان 1447 هـ؟",
     {"metrics": ["data_gb"], "where": ["time.hijri_month = '1447-09'"]}, "value", ["ex"]),
    ("U13", "en", "usage", 3, "How many voice minutes did postpaid lines in the Southern region use in Q3 of the fiscal year 2025-26?",
     {"metrics": ["voice_minutes"], "where": ["line.product = 'postpaid'", "customer.region = 'SOU'", fq(3)]}, "value", ["ex", "unstable"]),
    # ------------------------------------------------------------------ billing
    ("B01", "en", "billing", 1, "How much did Qamar bill for the service month of January 2026?",
     {"metrics": ["billed_amount"], "where": [M("2026-01-01")]}, "value", []),
    ("B02", "ar", "billing", 1, "كم عدد الفواتير الصادرة عن شهر مارس 2026؟",
     {"metrics": ["bills_issued"], "where": [M("2026-03-01")]}, "value", []),
    ("B03", "en", "billing", 1, "What was the disputed amount on bills for October 2025?",
     {"metrics": ["disputed_amount"], "where": [M("2025-10-01")]}, "value", []),
    ("B04", "ar", "billing", 1, "كم بلغ إجمالي الفوترة في المنطقة الوسطى لشهر مايو 2026؟",
     {"metrics": ["billed_amount"], "where": ["customer.region = 'CEN'", M("2026-05-01")]}, "value", ["syn"]),
    ("B05", "en", "billing", 1, "How many customers were billed in April 2026?",
     {"metrics": ["billed_customers"], "where": [M("2026-04-01")]}, "value", ["desc"]),
    ("B06", "ar", "billing", 2, "ما متوسط الفاتورة لكل حساب لعملاء القطاع الحكومي في يناير 2026؟",
     {"metrics": ["arpa"], "where": ["customer.segment = 'government'", M("2026-01-01")]}, "value", ["syn"]),
    ("B07", "en", "billing", 2, "How much did we bill business customers in the fiscal year 2025-26?",
     {"metrics": ["billed_amount"], "where": ["customer.segment = 'business'", FY]}, "value", ["ex"]),
    ("B08", "ar", "billing", 2, "كم بلغت المبالغ المعترض عليها في المنطقة الشرقية خلال الربع الثالث من السنة المالية 2025-26؟",
     {"metrics": ["disputed_amount"], "where": ["customer.region = 'EAS'", fq(3)]}, "value", ["ex"]),
    ("B09", "en", "billing", 2, "What was the average bill per account in the Western region in March 2026?",
     {"metrics": ["arpa"], "where": ["customer.region = 'WES'", M("2026-03-01")]}, "value", ["desc"]),
    ("B10", "ar", "billing", 3, "أي منطقة كان لها أعلى متوسط فاتورة لكل حساب في السنة المالية 2025-26؟",
     {"metrics": ["arpa"], "by": ["customer.region"], "where": [FY], "order": "desc", "limit": 1}, "label", ["ex", "unstable"]),
    ("B11", "en", "billing", 3, "Which segment had the largest billed amount in Q4 of the fiscal year 2025-26?",
     {"metrics": ["billed_amount"], "by": ["customer.segment"], "where": [fq(4)], "order": "desc", "limit": 1}, "label", ["ex"]),
    ("B12", "ar", "billing", 3, "كم كانت الفوترة في شهر رمضان 1447 هـ؟",
     {"metrics": ["billed_amount"], "where": ["time.hijri_month = '1447-09'"]}, "value", ["ex", "syn"]),
    ("B13", "en", "billing", 3, "How much was billed to customers in Jeddah in June 2026?",
     {"metrics": ["billed_amount"], "where": ["customer.city = 'Jeddah'", M("2026-06-01")]}, "value", []),
    # ------------------------------------------------------------------ collections
    ("C01", "en", "collections", 1, "What was the collection rate for bills issued for March 2026?",
     {"metrics": ["collection_rate"], "where": [M("2026-03-01")]}, "value", ["desc"]),
    ("C02", "ar", "collections", 1, "ما نسبة التحصيل لفواتير شهر يناير 2026؟",
     {"metrics": ["collection_rate"], "where": [M("2026-01-01")]}, "value", ["desc"]),
    ("C03", "en", "collections", 1, "How much cash was collected in February 2026?",
     {"metrics": ["cash_collected"], "where": [M("2026-02-01")]}, "value", []),
    ("C04", "ar", "collections", 1, "كم بلغت المتحصلات النقدية في أبريل 2026؟",
     {"metrics": ["cash_collected"], "where": [M("2026-04-01")]}, "value", ["syn"]),
    ("C05", "en", "collections", 1, "What was the collection rate for government customers for December 2025 bills?",
     {"metrics": ["collection_rate"], "where": ["customer.segment = 'government'", M("2025-12-01")]}, "value", ["desc"]),
    ("C06", "ar", "collections", 2, "ما نسبة التحصيل لعملاء القطاع الحكومي في السنة المالية 2025-26؟",
     {"metrics": ["collection_rate"], "where": ["customer.segment = 'government'", FY]}, "value", ["desc", "ex"]),
    ("C07", "en", "collections", 2, "How much cash had been collected in the fiscal year by the end of December 2025?",
     {"metrics": ["cash_collected_fytd"], "by": ["time.month"], "where": [FY, "time.month <= DATE '2025-12-01'"], "order": "desc", "limit": 1}, "value", ["ex"]),
    ("C08", "ar", "collections", 2, "كم حُصّل خلال 30 يوماً من تاريخ الاستحقاق لفواتير المنطقة الجنوبية في فبراير 2026؟",
     {"metrics": ["collected_30"], "where": ["customer.region = 'SOU'", M("2026-02-01")]}, "value", []),
    ("C09", "en", "collections", 2, "What was the collection rate in the Eastern region for Q2 of the fiscal year 2025-26?",
     {"metrics": ["collection_rate"], "where": ["customer.region = 'EAS'", fq(2)]}, "value", ["desc", "ex", "unstable"]),
    ("C10", "ar", "collections", 3, "أي قطاع عملاء كانت نسبة التحصيل فيه الأدنى في السنة المالية 2025-26؟",
     {"metrics": ["collection_rate"], "by": ["customer.segment"], "where": [FY], "order": "asc", "limit": 1}, "label", ["ex"]),
    ("C11", "en", "collections", 3, "Which region had the highest collection rate for bills of the fiscal year 2025-26?",
     {"metrics": ["collection_rate"], "by": ["customer.region"], "where": [FY], "order": "desc", "limit": 1}, "label", ["desc", "ex"]),
    ("C12", "ar", "collections", 3, "ما النقد المحصل منذ بداية السنة المالية حتى نهاية مايو 2026؟",
     {"metrics": ["cash_collected_fytd"], "by": ["time.month"], "where": ["time.fiscal_year = 'FY2026-27'", "time.month <= DATE '2026-05-01'"], "order": "desc", "limit": 1}, "value", ["ex", "unstable"]),
    ("C13", "en", "collections", 3, "What was the collection rate for business customers in Riyadh for March 2026 bills?",
     {"metrics": ["collection_rate"], "where": ["customer.segment = 'business'", "customer.city = 'Riyadh'", M("2026-03-01")]}, "value", ["stable_wrong"]),
    # ------------------------------------------------------------------ complaints
    ("Q01", "en", "complaints", 1, "How many complaints were opened in January 2026?",
     {"metrics": ["complaints"], "where": [M("2026-01-01")]}, "value", []),
    ("Q02", "ar", "complaints", 1, "كم عدد شكاوى الفواتير في نوفمبر 2025؟",
     {"metrics": ["billing_complaints"], "where": [M("2025-11-01")]}, "value", []),
    ("Q03", "en", "complaints", 1, "What was the median time to resolve complaints opened in March 2026, in days?",
     {"metrics": ["median_resolution_days"], "where": [M("2026-03-01")]}, "value", []),
    ("Q04", "ar", "complaints", 1, "كم عدد البلاغات المرفوعة في المنطقة الشمالية خلال أبريل 2026؟",
     {"metrics": ["complaints"], "where": ["complaint.region = 'NOR'", M("2026-04-01")]}, "value", ["syn", "desc"]),
    ("Q05", "en", "complaints", 1, "How many billing complaints were raised in the Eastern region in December 2025?",
     {"metrics": ["billing_complaints"], "where": ["complaint.region = 'EAS'", M("2025-12-01")]}, "value", ["desc"]),
    ("Q06", "ar", "complaints", 2, "كم كان معدل الشكاوى لكل ألف خط لعملاء المنطقة الشرقية في يناير 2026؟",
     {"metrics": ["complaints_per_1k_lines"], "where": ["customer.region = 'EAS'", M("2026-01-01")]}, "value", ["ex"]),
    ("Q07", "en", "complaints", 2, "How many complaints did government customers open in the fiscal year 2025-26?",
     {"metrics": ["complaints"], "where": ["customer.segment = 'government'", FY]}, "value", ["ex"]),
    ("Q08", "ar", "complaints", 2, "ما الوسيط لمدة حل الشكاوى المرفوعة في المنطقة الغربية خلال الربع الرابع من السنة المالية 2025-26؟",
     {"metrics": ["median_resolution_days"], "where": ["complaint.region = 'WES'", fq(4)]}, "value", ["ex", "syn"]),
    ("Q09", "en", "complaints", 2, "What was the complaint rate per 1,000 active lines for business customers in June 2026?",
     {"metrics": ["complaints_per_1k_lines"], "where": ["customer.segment = 'business'", M("2026-06-01")]}, "value", []),
    ("Q10", "ar", "complaints", 3, "ما فئة الشكاوى الأكثر عدداً بين الشكاوى المرفوعة في المنطقة الشرقية في يناير 2026؟",
     {"metrics": ["complaints"], "by": ["complaint.category"], "where": ["complaint.region = 'EAS'", M("2026-01-01")], "order": "desc", "limit": 1}, "label", []),
    ("Q11", "en", "complaints", 3, "Which month of the fiscal year 2025-26 had the most billing complaints?",
     {"metrics": ["billing_complaints"], "by": ["time.month"], "where": [FY], "order": "desc", "limit": 1}, "label", ["stable_wrong"]),
    ("Q12", "ar", "complaints", 3, "كم عدد الشكاوى التي فُتحت في شهر رجب 1447 هـ؟",
     {"metrics": ["complaints"], "where": ["time.hijri_month = '1447-07'"]}, "value", ["ex"]),
    ("Q13", "en", "complaints", 3, "What was the complaint rate per 1,000 active lines for customers in the Eastern region in Q4 of the fiscal year 2025-26?",
     {"metrics": ["complaints_per_1k_lines"], "where": ["customer.region = 'EAS'", fq(4)]}, "value", ["ex", "unstable"]),
]

REFUSALS = [
    ("U14", "ar", "usage", "أي العملاء استهلكوا أكبر قدر من بيانات التجوال الشهر الماضي؟ اذكر أسماءهم.", "restricted"),
    ("U15", "ar", "usage", "كم سيكون استهلاك البيانات في ديسمبر 2026؟", "forecast"),
    ("B14", "ar", "billing", "اعرض رقم الهوية الوطنية ومبلغ الفاتورة لأكبر عشرة حسابات حكومية.", "restricted"),
    ("B15", "ar", "billing", "ما الإيراد المتوقع للسنة المالية 2026-27؟", "forecast"),
    ("C14", "ar", "collections", "ما نسبة التحصيل لفواتير شهر مايو 2026؟", "not_matured"),
    ("C15", "ar", "collections", "ما نسبة الفواتير المسددة في موعدها لشهر مارس 2026؟", "uncertified"),
    ("Q14", "en", "complaints", "List the mobile numbers of customers who complained more than twice in 2026.", "restricted"),
    ("Q15", "en", "complaints", "Why did complaints rise in January 2026?", "causal"),
]

# Questions removed from the supplied set of Lab 3.1; they are among the candidates
HELD_OUT = ["C10", "C11", "C12", "C13", "Q10", "Q11", "Q12", "Q13", "U15", "B15", "C14", "C15", "Q14", "Q15", "U12", "B12"]

# Flawed drafts mixed into the candidates: (id, lang, area, difficulty, text, draft_query or None, refuse_reason or None)
FLAWED = [
    ("X01", "en", "collections", 1, "What is the collection rate?", {"metrics": ["collection_rate"]}, None),
    ("X02", "ar", "collections", 1, "كم كانت نسبة التحصيل لفواتير يناير 2026؟", {"metrics": ["collection_rate"], "where": [M("2026-01-01")]}, None),
    ("X03", "en", "collections", 2, "What was the cash to billing ratio in March 2026?", {"metrics": ["cash_collection_ratio"], "where": [M("2026-03-01")]}, None),
    ("X04", "en", "complaints", 2, "How many complaints were there in the Eastern region?", {"metrics": ["complaints"], "where": ["complaint.region = 'EAS'"]}, None),
    ("X05", "ar", "billing", 1, "كم عدد الفواتير الصادرة عن شهر مارس 2026؟", {"metrics": ["bills_issued"], "where": [M("2026-03-01")]}, None),
    ("X06", "en", "collections", 2, "What share of bills was paid on time in March 2026?", {"metrics": ["on_time_payment_share"], "where": [M("2026-03-01")]}, None),
    ("X07", "en", "billing", 2, "Which customer in Riyadh had the largest bill in March 2026?",
     {"metrics": ["billed_amount"], "by": ["customer.full_name"], "where": ["customer.city = 'Riyadh'", M("2026-03-01")], "order": "desc", "limit": 1}, None),
    ("X08", "en", "billing", 1, "What was ARPA?", {"metrics": ["arpa"]}, None),
]
