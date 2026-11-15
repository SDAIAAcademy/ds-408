# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "hijridate>=2.5"]
# ///
"""Write the synthetic marts of Qamar Telecom into data/marts/ (Parquet), with a fixed seed.

    uv run python prepare_data.py

Every run writes the same rows. Nothing here is real: the organisation, the customers, their
names, numbers and identifiers are invented. The planted problems are listed in
solutions/answer_key.md.
"""
from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

import duckdb
import pandas as pd
from hijridate import Gregorian

SEED = 408
HERE = Path(__file__).resolve().parent
MARTS = HERE / "data" / "marts"
START, END = dt.date(2025, 1, 1), dt.date(2026, 6, 30)  # 18 service months; END is the data cut-off
DUP_BATCH_DAY = dt.date(2026, 3, 17)  # planted: this day's payment batch is loaded twice
PRICE_CHANGE = dt.date(2025, 10, 1)

REGIONS = [  # code, English, Arabic, share, cities
    ("CEN", "Central", "الوسطى", 0.32, ["Riyadh", "Buraidah", "Al Kharj"]),
    ("WES", "Western", "الغربية", 0.28, ["Jeddah", "Makkah", "Madinah", "Taif"]),
    ("EAS", "Eastern", "الشرقية", 0.22, ["Dammam", "Al Khobar", "Al Ahsa", "Jubail"]),
    ("SOU", "Southern", "الجنوبية", 0.11, ["Abha", "Jazan", "Najran"]),
    ("NOR", "Northern", "الشمالية", 0.07, ["Tabuk", "Hail", "Arar"]),
]
TARIFFS = [  # code, product, plan, fee before PRICE_CHANGE, fee after
    ("POST-S", "postpaid", "Qamar Postpaid S", 99, 99),
    ("POST-M", "postpaid", "Qamar Postpaid M", 149, 165),
    ("POST-L", "postpaid", "Qamar Postpaid L", 249, 249),
    ("BIZ-M", "postpaid", "Qamar Business M", 199, 199),
    ("BIZ-L", "postpaid", "Qamar Business L", 349, 349),
    ("FIB-100", "fibre", "Qamar Fibre 100", 299, 279),
    ("FIB-500", "fibre", "Qamar Fibre 500", 399, 399),
    ("PRE-15", "prepaid", "Qamar Prepaid 15", 0, 0),
]
FIRST = ["Abdullah", "Mohammed", "Fahad", "Sultan", "Khalid", "Omar", "Yousef", "Hamad", "Nawaf", "Badr",
         "Lama", "Nora", "Sara", "Reem", "Hind", "Maha", "Dana", "Rawan", "Asma", "Mashael"]
FAMILY = ["Al-Harbi", "Al-Qahtani", "Al-Ghamdi", "Al-Zahrani", "Al-Dossary", "Al-Otaibi", "Al-Mutairi",
          "Al-Shehri", "Al-Anazi", "Al-Shammari", "Al-Malki", "Al-Juhani", "Al-Subaie", "Al-Yami"]
CATEGORIES = ["billing", "network", "service", "device"]
CHANNELS = ["app", "call centre", "store", "social media"]


def months(a: dt.date, b: dt.date):
    d = dt.date(a.year, a.month, 1)
    while d <= b:
        yield d
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def month_end(m: dt.date) -> dt.date:
    nxt = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return nxt - dt.timedelta(days=1)


def build(rng: random.Random) -> dict[str, pd.DataFrame]:
    # ---------------------------------------------------------------- regions and dates
    region = pd.DataFrame([(c, e, a) for c, e, a, _, _ in REGIONS], columns=["region_code", "region_name_en", "region_name_ar"])
    days = []
    d = dt.date(2024, 1, 1)
    while d <= dt.date(2026, 12, 31):
        h = Gregorian(d.year, d.month, d.day).to_hijri()
        fy = d.year if d.month >= 4 else d.year - 1
        days.append({"date_day": d, "month_start": d.replace(day=1), "year": d.year, "month": d.month,
                     "fiscal_year": fy, "fiscal_year_label": f"FY{fy}-{(fy + 1) % 100:02d}",
                     "fiscal_quarter": (d.month - 4) % 12 // 3 + 1,
                     "hijri_year": h.year, "hijri_month": h.month, "hijri_month_name_en": h.month_name("en"),
                     "hijri_month_name_ar": h.month_name("ar")})
        d += dt.timedelta(days=1)
    date = pd.DataFrame(days)

    # ---------------------------------------------------------------- tariffs (type 2 history)
    tariff_rows, k = [], 1
    for code, product, plan, before, after in TARIFFS:
        if before == after:
            tariff_rows.append((f"T{k:02d}", code, product, plan, before, dt.date(2019, 1, 1), dt.date(9999, 12, 31), True)); k += 1
        else:
            tariff_rows.append((f"T{k:02d}", code, product, plan, before, dt.date(2019, 1, 1), PRICE_CHANGE - dt.timedelta(days=1), False)); k += 1
            tariff_rows.append((f"T{k:02d}", code, product, plan, after, PRICE_CHANGE, dt.date(9999, 12, 31), True)); k += 1
    tariff = pd.DataFrame(tariff_rows, columns=["tariff_key", "tariff_code", "product", "plan_name", "monthly_fee",
                                                "valid_from", "valid_to", "is_current"])
    fee = {}
    for r in tariff.itertuples():
        fee.setdefault(r.tariff_code, []).append((r.valid_from, r.valid_to, r.monthly_fee))

    def fee_on(code, day):
        return next(f for a, b, f in fee[code] if a <= day <= b)

    # ---------------------------------------------------------------- customers and lines
    customers, lines = [], []
    shares = [s for *_, s, _ in REGIONS]
    line_no = 1
    for i in range(1, 2401):
        reg = rng.choices(REGIONS, weights=shares)[0]
        seg = rng.choices(["consumer", "business", "government"], weights=[75, 20, 5])[0]
        joined = dt.date(2018, 1, 1) + dt.timedelta(days=rng.randrange(0, 3000))
        name = f"{rng.choice(FIRST)} {rng.choice(FAMILY)}" if seg == "consumer" else f"Synthetic {seg.title()} Account {i:04d}"
        customers.append({"customer_id": f"C{i:05d}", "segment": seg, "region_code": reg[0], "city": rng.choice(reg[4]),
                          "full_name": name, "national_id": f"{rng.choice('12')}{rng.randrange(10**8, 10**9)}",
                          "msisdn": f"9665{rng.randrange(10**7, 10**8)}",
                          "date_of_birth": (dt.date(1960, 1, 1) + dt.timedelta(days=rng.randrange(0, 15000))) if seg == "consumer" else None,
                          "joined_date": joined})
        n = rng.choices([1, 2, 3], weights=[60, 30, 10])[0]
        for _ in range(n):
            if seg == "consumer":
                code = rng.choices(["PRE-15", "POST-S", "POST-M", "POST-L", "FIB-100", "FIB-500"], weights=[38, 14, 20, 8, 15, 5])[0]
            elif seg == "business":
                code = rng.choices(["BIZ-M", "BIZ-L", "FIB-100", "FIB-500"], weights=[45, 25, 20, 10])[0]
            else:
                code = rng.choices(["BIZ-M", "BIZ-L", "FIB-500"], weights=[40, 40, 20])[0]
            first = max(joined, dt.date(2019, 1, 1))
            act = first + dt.timedelta(days=rng.randrange(0, max(1, (dt.date(2026, 5, 20) - first).days)))
            deact = act + dt.timedelta(days=rng.randrange(200, 1500)) if rng.random() < 0.18 else None
            if deact and deact > END:
                deact = None
            lines.append({"line_id": f"L{line_no:06d}", "customer_id": f"C{i:05d}", "product": next(t[1] for t in TARIFFS if t[0] == code),
                          "tariff_code": code, "activation_date": act, "deactivation_date": deact})
            line_no += 1
    customer = pd.DataFrame(customers)
    line = pd.DataFrame(lines)
    cust_by_id = {c["customer_id"]: c for c in customers}

    def active(l, m):
        return l["activation_date"] <= month_end(m) and (l["deactivation_date"] is None or l["deactivation_date"] >= m)

    # ---------------------------------------------------------------- usage per line and month
    usage = []
    for l in lines:
        for m in months(START, END):
            if not active(l, m):
                continue
            pre = l["product"] == "prepaid"
            fib = l["product"] == "fibre"
            gb = rng.lognormvariate(2.4 if pre else (5.2 if fib else 3.3), 0.5)
            usage.append({"line_id": l["line_id"], "usage_month": m, "data_gb": round(gb, 2),
                          "voice_min": 0 if fib else int(rng.lognormvariate(5.0 if pre else 5.6, 0.6)),
                          "sms": 0 if fib else int(rng.expovariate(1 / 12)),
                          "roaming_mb": int(rng.expovariate(1 / 300)) if (not fib and rng.random() < 0.08) else 0})
    usage_monthly = pd.DataFrame(usage)

    # ---------------------------------------------------------------- bills and payments
    behaviour = {  # by due, 1-30 late, 31-60 late, 61-120 late, never
        "consumer": [82, 9, 4, 2, 3], "business": [75, 12, 7, 3, 3], "government": [30, 20, 25, 22, 3]}
    bills, pays = [], []
    bill_no, pay_no = 1, 1
    lines_by_cust: dict[str, list] = {}
    for l in lines:
        lines_by_cust.setdefault(l["customer_id"], []).append(l)
    for m in months(START, END):
        issue = month_end(m) + dt.timedelta(days=3)
        due = issue + dt.timedelta(days=21)
        for cid, ls in lines_by_cust.items():
            billable = [l for l in ls if l["product"] != "prepaid" and active(l, m)]
            if not billable:
                continue
            base = sum(fee_on(l["tariff_code"], m) for l in billable)
            extra = round(rng.expovariate(1 / 25), 2) if rng.random() < 0.3 else 0.0
            amount = round((base + extra) * 1.15, 2)
            disputed = round(amount * rng.uniform(0.2, 0.6), 2) if rng.random() < 0.03 else 0.0
            bid = f"B{bill_no:07d}"; bill_no += 1
            bills.append({"bill_id": bid, "customer_id": cid, "bill_month": m, "issue_date": issue, "due_date": due,
                          "amount_due": amount, "disputed_amount": disputed})
            seg = cust_by_id[cid]["segment"]
            outcome = rng.choices(range(5), weights=behaviour[seg])[0]
            if outcome == 4:
                continue
            lag = [rng.randrange(-15, 1), rng.randrange(1, 31), rng.randrange(31, 61), rng.randrange(61, 121)][outcome]
            payable = round(amount - disputed, 2)
            parts = [payable] if rng.random() > 0.05 else [round(payable * 0.5, 2), round(payable - round(payable * 0.5, 2), 2)]
            day = due + dt.timedelta(days=lag)
            for j, amt in enumerate(parts):
                pdate = day + dt.timedelta(days=20 * j)
                if pdate <= END:
                    pays.append({"payment_id": f"P{pay_no:07d}", "bill_id": bid, "customer_id": cid, "paid_date": pdate,
                                 "amount": amt, "batch_id": f"B{pdate:%Y%m%d}", "load_no": 1}); pay_no += 1
            if disputed and rng.random() < 0.5:  # half of the disputes are found valid and credited; the rest is paid later
                pdate = due + dt.timedelta(days=45)
                if pdate <= END:
                    pays.append({"payment_id": f"P{pay_no:07d}", "bill_id": bid, "customer_id": cid, "paid_date": pdate,
                                 "amount": disputed, "batch_id": f"B{pdate:%Y%m%d}", "load_no": 1}); pay_no += 1
    for p in [p for p in pays if p["paid_date"] == DUP_BATCH_DAY]:  # planted: the batch is loaded a second time
        pays.append({**p, "payment_id": f"P{pay_no:07d}", "load_no": 2}); pay_no += 1
    bill = pd.DataFrame(bills)
    payment = pd.DataFrame(pays).sort_values(["paid_date", "payment_id"]).reset_index(drop=True)

    # ---------------------------------------------------------------- complaints
    comps, c_no = [], 1
    for l in lines:
        cust = cust_by_id[l["customer_id"]]
        for m in months(START, END):
            if not active(l, m):
                continue
            rate = 0.04
            if m >= PRICE_CHANGE and m < dt.date(2026, 1, 1) and l["tariff_code"] in ("POST-M",):
                rate += 0.05  # billing complaints after the price change
            if cust["region_code"] == "EAS" and m == dt.date(2026, 1, 1):
                rate += 0.06  # a network incident in the Eastern region
            if rng.random() >= rate:
                continue
            if m >= PRICE_CHANGE and m < dt.date(2026, 1, 1) and l["tariff_code"] == "POST-M" and rng.random() < 0.7:
                cat = "billing"
            elif cust["region_code"] == "EAS" and m == dt.date(2026, 1, 1) and rng.random() < 0.7:
                cat = "network"
            else:
                cat = rng.choices(CATEGORIES, weights=[30, 30, 28, 12])[0]
            opened = m + dt.timedelta(days=rng.randrange(0, 28))
            closed = opened + dt.timedelta(days=int(rng.expovariate(1 / 5)) + 1) if rng.random() < 0.96 else None
            if closed and closed > END:
                closed = None
            where = cust["region_code"] if rng.random() > 0.06 else rng.choice([r[0] for r in REGIONS if r[0] != cust["region_code"]])
            comps.append({"complaint_id": f"Q{c_no:06d}", "customer_id": l["customer_id"], "line_id": l["line_id"],
                          "opened_date": opened, "closed_date": closed, "category": cat, "channel": rng.choice(CHANNELS),
                          "region_code": where, "severity": rng.choices(["low", "medium", "high"], weights=[50, 38, 12])[0]})
            c_no += 1
    complaint = pd.DataFrame(comps)

    return {"dim_region": region, "dim_date": date, "dim_tariff": tariff, "dim_customer": customer, "dim_line": line,
            "fct_usage_monthly": usage_monthly, "fct_bill": bill, "fct_payment": payment, "fct_complaint": complaint}


def main() -> None:
    MARTS.mkdir(parents=True, exist_ok=True)
    tables = build(random.Random(SEED))
    con = duckdb.connect()
    for name, df in tables.items():
        con.register("t", df)
        con.execute(f"COPY (SELECT * FROM t) TO '{(MARTS / f'{name}.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
        con.unregister("t")
        print(f"{name:20s} {len(df):7d} rows")


if __name__ == "__main__":
    main()
