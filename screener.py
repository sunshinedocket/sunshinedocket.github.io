#!/usr/bin/env python3
# Run with: python3 screener.py --year 2025
"""
Sunshine Docket Legislative Screener Engine v4
All fixes: scoring calibration, fuzzy matching, district parsing,
slug generation, apostrophe escaping.

Usage:
    python3 screener.py [--year 2025] [--output screener_results.json]
    python3 screener.py --skip-contributions

Requirements:
    pip3 install requests
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip3 install requests")
    sys.exit(1)

# ---------------------------------------------------------------
# Config
# ---------------------------------------------------------------

BASE = "https://data.wa.gov/resource"
F1_URL = f"{BASE}/ehbc-shxw.json"
CONTRIB_URL = f"{BASE}/kv7h-kjye.json"
LOB_URL = f"{BASE}/xhn7-64im.json"

INCOME_MIDPOINTS = {
    "$0-$30,000": 15000, "$0-$30K": 15000,
    "0-29999": 15000, "0-30000": 15000,
    "$30,000-$60,000": 45000, "$30K-$60K": 45000,
    "30000-59999": 45000, "30000-60000": 45000,
    "$60,000-$100,000": 80000, "$60K-$100K": 80000,
    "60000-99999": 80000, "60000-100000": 80000,
    "$100,000-$200,000": 150000, "$100K-$200K": 150000,
    "100000-199999": 150000, "100000-200000": 150000,
    "$200,000-$500,000": 350000, "$200K-$500K": 350000,
    "200000-499999": 350000, "200000-500000": 350000,
    "$500,000-$750,000": 625000, "$500K-$750K": 625000,
    "500000-749999": 625000, "500000-750000": 625000,
    "$750,000 and over": 900000, "$750K and over": 900000,
    "750000": 900000,
}

# Keywords that identify legislative/government income (should NOT be scored)
GOV_KEYWORDS = [
    "house of representatives", "wa house", "washington house",
    "state representative", "state house",
    "senate", "wa senate", "washington senate", "state senator",
    "state senate", "legislature",
    # Government employers
    "wa state", "state of washington", "state of wa",
    "washington state", "dept of", "department of",
    "city of", "county of", "port of",
    "school district", "fire district", "water district",
    "public utility", "transit authority",
    "university of washington", "washington state university",
    "central washington", "eastern washington", "western washington",
    "the evergreen state", "evergreen state college",
    # Retirement/benefits
    "retirement", "pension", "pers", "trs", "leoff", "sers",
    "social security", "disability",
    # Military/federal
    "united states", "u.s.", "us army", "us navy", "us air force",
    "us marine", "veterans affairs", "dept of defense",
    "federal government", "usda", "usps",
]

# Generic income descriptions that should NOT match against lobbyist employers
SKIP_INCOME_NAMES = [
    "rent", "rental", "rental income", "interest", "dividends",
    "capital gains", "royalties", "farm income", "self",
    "social security", "pension", "retirement", "disability",
    "unemployment", "alimony", "child support", "trust",
    "investment", "investments", "savings", "ira", "401k",
    "annuity", "insurance", "stipend", "per diem", "honorarium",
    "n/a", "none", "na", "see prior year",
]

RATE_DELAY = 0.3


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def api_get(url, params, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            time.sleep(RATE_DELAY)
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [WARN] API failed: {e}")
                return []
            time.sleep(1)
    return []


def paginated(url, params, limit=1000, cap=50000):
    out = []
    offset = 0
    while offset < cap:
        p = {**params, "$limit": limit, "$offset": offset}
        batch = api_get(url, p)
        if not batch:
            break
        out.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
        print(f"  ... fetched {len(out)} records")
    return out


def safe_data(field):
    """Handle both {data: [...]} dict and plain list formats in F1 JSON."""
    if isinstance(field, list):
        return field
    if isinstance(field, dict):
        return field.get("data", [])
    return []


def parse_band(s):
    if not s:
        return 0
    s_clean = s.strip().replace("$", "").replace(",", "").replace(" ", "").lower()
    for pattern, mid in INCOME_MIDPOINTS.items():
        if pattern.lower().replace("$", "").replace(",", "").replace(" ", "") in s_clean:
            return mid
    # Try to extract raw numbers
    nums = re.findall(r'(\d+)', s_clean)
    if len(nums) >= 2:
        return (int(nums[0]) + int(nums[1])) // 2
    if nums:
        return int(nums[0])
    return 0


def is_gov_income(name_str):
    """Check if an income source name looks like government/legislative income."""
    lower = name_str.lower()
    for kw in GOV_KEYWORDS:
        if kw in lower:
            return True
    return False


def is_skip_income(name_str):
    """Check if an income source name is too generic to match against lobbyists."""
    lower = name_str.strip().lower()
    for skip in SKIP_INCOME_NAMES:
        if lower == skip or lower.startswith(skip + " "):
            return True
    # Also skip very short names (1-2 chars)
    if len(lower) <= 2:
        return True
    return False


def detect_chamber(entry):
    """Detect if this income entry is WA state legislative pay.
    
    Must be specific enough to exclude:
    - Federal: 'United States Senate', 'United States House of Representatives'
    - Staff/interns: 'INTERN', 'AIDE', 'STAFF', 'SECRETARY', 'COUNSEL'
    - Student government: 'Associated Students', 'Student Association'
    - Professional staff: 'PROFESSIONAL STAFF'
    """
    if not isinstance(entry, dict):
        return None

    name = entry.get("name", "").lower().strip()
    role = entry.get("why", "").lower().strip()

    # EXCLUDE federal government
    if "united states" in name or name.startswith("u.s.") or name.startswith("us "):
        return None

    # EXCLUDE non-member roles (staff, interns, aides, etc.)
    non_member_roles = ["intern", "aide", "staff", "secretary", "counsel",
                        "analyst", "director", "coordinator", "clerk",
                        "advisor", "consultant", "fellow", "assistant",
                        "professional", "attorney", "lobbyist"]
    for excl in non_member_roles:
        if excl in role:
            return None

    # Must come from a WA state source (require "washington" or "state" in name)
    is_wa_state = ("washington" in name or "state of wa" in name
                   or name.startswith("wa ") or "wa state" in name)

    if not is_wa_state:
        return None

    # Now check for chamber indicators
    if any(kw in name for kw in ["senate"]) or "senator" in role:
        return "senate"
    if any(kw in name for kw in ["house"]) or "representative" in role:
        return "house"

    # Catch "State of Washington" + "State Senator" / "State Representative"
    if "state senator" in role:
        return "senate"
    if "state representative" in role:
        return "house"

    return None


def sql_escape(s):
    """Escape/strip characters that break Socrata SoQL queries."""
    if not s:
        return s
    # Strip parenthetical content: "ALICIA J RULE (Alicia Rule)" -> "ALICIA J RULE"
    s = re.sub(r'\s*\([^)]*\)', '', s)
    # Escape single quotes
    s = s.replace("'", "''")
    # Strip any remaining problematic chars
    s = s.replace('"', '').replace('\\', '')
    return s.strip()


def make_slug(name):
    """Generate URL slug, stripping middle initials and suffixes."""
    name = name.strip()
    if "," in name:
        parts = name.split(",")
        last = parts[0].strip()
        first_parts = parts[1].strip().split() if len(parts) > 1 else []
        # Take only first name, skip middle initials
        first = first_parts[0] if first_parts else ""
        slug = f"{first}-{last}".lower()
    else:
        words = name.split()
        if len(words) >= 2:
            first = words[0]
            last = words[-1]
            slug = f"{first}-{last}".lower()
        else:
            slug = name.lower()
    # Clean: only lowercase letters, numbers, hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def extract_district(offices_str):
    """Extract district number from various office format strings."""
    if not offices_str:
        return ""
    s = str(offices_str)
    # Try "District 36" or "district 36" or "Dist. 36" or "Dist 36"
    m = re.findall(r'(?:district|dist\.?)\s*(\d{1,2})', s, re.I)
    if m:
        return m[0]
    # Try "36th District" or "36th Dist"
    m = re.findall(r'(\d{1,2})(?:st|nd|rd|th)\s*(?:district|dist)', s, re.I)
    if m:
        return m[0]
    # Try "LD 36" or "LD36"
    m = re.findall(r'LD\s*(\d{1,2})', s, re.I)
    if m:
        return m[0]
    # Try standalone numbers in plausible range if "position" is nearby
    m = re.findall(r'(\d{1,2})', s)
    for n in m:
        if 1 <= int(n) <= 49:
            return n
    return ""


# ---------------------------------------------------------------
# Stage 1: Pull F1 filings
# ---------------------------------------------------------------

def pull_filings(year):
    print(f"\n[1/6] Pulling F1 filings for CY{year} + CY{year - 1} (merging both)...")

    # Pull target year
    params = {
        "$where": f"period_start >= '{year}-01-01' AND period_start <= '{year}-12-31'",
        "$order": "name ASC",
    }
    current = paginated(F1_URL, params)
    print(f"  CY{year}: {len(current)} filings")

    # Pull prior year (many legislators may not have filed for target year yet)
    params_prior = {
        "$where": f"period_start >= '{year-1}-01-01' AND period_start <= '{year-1}-12-31'",
        "$order": "name ASC",
    }
    prior = paginated(F1_URL, params_prior)
    print(f"  CY{year - 1}: {len(prior)} filings")

    # Merge: prefer newer filing when same filer_id exists in both
    by_filer = {}
    for f in prior:
        fid = f.get("filer_id", "")
        if fid:
            by_filer[fid] = f
    # Current year overwrites prior year
    for f in current:
        fid = f.get("filer_id", "")
        if fid:
            by_filer[fid] = f
    # Also include filings without filer_id from both (keyed by name)
    for f in prior + current:
        fid = f.get("filer_id", "")
        if not fid:
            name = f.get("name", "")
            by_filer[f"_name_{name}"] = f

    merged = list(by_filer.values())
    print(f"  Merged (deduplicated): {len(merged)} filings")
    return merged


# ---------------------------------------------------------------
# Stage 2: Extract legislators
# ---------------------------------------------------------------

def extract_legislators(filings):
    print(f"\n[2/6] Identifying legislators from {len(filings)} filings...")
    legislators = []

    for filing in filings:
        try:
            raw = filing.get("json", "{}")
            stmt_json = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue

        try:
            stmt = stmt_json.get("statement", {})
            if not isinstance(stmt, dict):
                continue

            income_data = safe_data(stmt.get("income", []))
            offices_raw = filing.get("offices", "")

            # Detect if this person is a legislator
            chamber = None
            leg_income = 0
            for entry in income_data:
                if not isinstance(entry, dict):
                    continue
                c = detect_chamber(entry)
                if c:
                    chamber = c
                    leg_income = parse_band(entry.get("income", ""))
                    break

            # Fallback: check offices field for STATE SENATOR/STATE REPRESENTATIVE title
            if not chamber:
                try:
                    offices_list = json.loads(offices_raw) if isinstance(offices_raw, str) else offices_raw
                    if isinstance(offices_list, list):
                        for ofc in offices_list:
                            if not isinstance(ofc, dict):
                                continue
                            title = ofc.get("office", "").upper()
                            juris = ofc.get("jurisdiction", "").upper()
                            if title == "STATE SENATOR":
                                chamber = "senate"
                                break
                            elif title in ("STATE REPRESENTATIVE", "STATE REP"):
                                chamber = "house"
                                break
                            # Also catch variations like "REPRESENTATIVE" with LEG DISTRICT jurisdiction
                            elif "LEG DISTRICT" in juris:
                                if "SENATE" in juris:
                                    chamber = "senate"
                                    break
                                elif "HOUSE" in juris:
                                    chamber = "house"
                                    break
                except (json.JSONDecodeError, TypeError):
                    pass

            if not chamber:
                continue

            name = filing.get("name", "Unknown")
            filer_id = filing.get("filer_id", "")
            submission_id = filing.get("id", "")
            period_start = filing.get("period_start", "")
            period_end = filing.get("period_end", "")
            offices = offices_raw

            # Income sources
            income_sources = []
            for entry in income_data:
                if not isinstance(entry, dict):
                    continue
                income_sources.append({
                    "who": entry.get("who", []),
                    "name": entry.get("name", ""),
                    "role": entry.get("why", ""),
                    "band": entry.get("income", ""),
                    "midpoint": parse_band(entry.get("income", "")),
                    "is_filer": "filer" in str(entry.get("who", [])).lower(),
                    "is_spouse": "spouse" in str(entry.get("who", [])).lower(),
                })

            # Business associations
            businesses = []
            for biz in safe_data(stmt.get("business_associations", [])):
                if not isinstance(biz, dict):
                    continue
                has_agency = False
                agency_payments = []
                bp_list = biz.get("business_payments", [])
                if not isinstance(bp_list, list):
                    bp_list = []
                for bp in bp_list:
                    if not isinstance(bp, dict):
                        continue
                    if bp.get("agency_name"):
                        has_agency = True
                        agency_payments.append({
                            "agency": bp.get("agency_name", ""),
                            "purpose": bp.get("purpose", ""),
                        })
                businesses.append({
                    "name": biz.get("legal_name", ""),
                    "ownership": biz.get("ownership_pct", ""),
                    "who": biz.get("who", []),
                    "description": biz.get("nature_of_business", ""),
                    "has_agency_payments": has_agency,
                    "agency_payments": agency_payments,
                })

            # Lobbying connections
            lobbies = []
            for lob in safe_data(stmt.get("lobbies", [])):
                if not isinstance(lob, dict):
                    continue
                lobbies.append({
                    "who": lob.get("who", []),
                    "entity": lob.get("lobby_entity_name", ""),
                })

            # Real estate
            real_estate = []
            for prop in safe_data(stmt.get("real_estate", [])):
                if not isinstance(prop, dict):
                    continue
                real_estate.append({
                    "location": prop.get("location_city_county", ""),
                    "value": prop.get("fair_market_value", ""),
                })

            party = "Unknown"
            district = extract_district(offices)

            legislators.append({
                "name": name,
                "filer_id": filer_id,
                "submission_id": submission_id,
                "chamber": chamber,
                "party": party,
                "district": district,
                "period": f"{period_start[:10] if period_start else ''} to {period_end[:10] if period_end else ''}",
                "leg_income": leg_income,
                "income_sources": income_sources,
                "businesses": businesses,
                "lobbies": lobbies,
                "real_estate": real_estate,
                "offices": offices,
            })

        except Exception as e:
            n = filing.get("name", "unknown")
            print(f"  [WARN] Skipped {n}: {e}")
            continue

    print(f"  Identified {len(legislators)} legislators")
    h = sum(1 for l in legislators if l["chamber"] == "house")
    s = sum(1 for l in legislators if l["chamber"] == "senate")
    d = sum(1 for l in legislators if l.get("district"))
    print(f"  House: {h}, Senate: {s}, With district: {d}")
    return legislators


# ---------------------------------------------------------------
# Stage 3: Lobbyist cross-reference
# ---------------------------------------------------------------

def pull_lobbyists(year):
    print(f"\n[3/6] Pulling lobbyist registrations for {year}...")
    params = {
        "$where": f"employment_year = '{year}'",
        "$select": "lobbyist_name,employer_name,employment_year",
    }
    recs = paginated(LOB_URL, params)
    print(f"  Found {len(recs)} registrations")
    lookup = {}
    for r in recs:
        emp = (r.get("employer_name") or "").strip().upper()
        lname = (r.get("lobbyist_name") or "").strip()
        if emp and len(emp) > 3:  # Skip very short employer names
            lookup.setdefault(emp, set()).add(lname)
    return {k: list(v) for k, v in lookup.items()}


def fuzzy(a, b, threshold=0.8):
    """Token overlap matching with higher threshold to reduce false positives."""
    ta = set(w for w in a.split() if len(w) > 2)  # Skip short tokens
    tb = set(w for w in b.split() if len(w) > 2)
    if not ta or not tb or len(ta) < 2 or len(tb) < 2:
        return False  # Require at least 2 meaningful tokens
    overlap = len(ta & tb)
    smaller = min(len(ta), len(tb))
    return (overlap / smaller) >= threshold


def match_lobbyists(legislators, emp_lobs):
    print("  Cross-referencing income sources against lobbyist employers...")
    for leg in legislators:
        matches = []
        seen_employers = set()  # Deduplicate matches

        for src in leg["income_sources"]:
            sn = (src.get("name") or "").strip()
            if not sn or len(sn) <= 3:
                continue
            # Skip government and generic income
            if is_gov_income(sn) or is_skip_income(sn):
                continue
            sn_upper = sn.upper()
            for emp, lobs in emp_lobs.items():
                if emp in seen_employers:
                    continue
                # Exact substring match (at least 4 chars of overlap)
                if len(sn_upper) >= 4 and (sn_upper in emp or emp in sn_upper):
                    seen_employers.add(emp)
                    matches.append({
                        "income_source": src.get("name"),
                        "employer_match": emp,
                        "lobbyist_count": len(lobs),
                        "lobbyists": lobs[:5],
                        "who": src.get("who"),
                        "income_band": src.get("band"),
                    })
                elif fuzzy(sn_upper, emp):
                    seen_employers.add(emp)
                    matches.append({
                        "income_source": src.get("name"),
                        "employer_match": emp,
                        "lobbyist_count": len(lobs),
                        "lobbyists": lobs[:5],
                        "who": src.get("who"),
                        "income_band": src.get("band"),
                    })

        for biz in leg["businesses"]:
            bn = (biz.get("name") or "").strip()
            if not bn or len(bn) <= 3 or is_skip_income(bn):
                continue
            bn_upper = bn.upper()
            for emp, lobs in emp_lobs.items():
                if emp in seen_employers:
                    continue
                if len(bn_upper) >= 4 and (bn_upper in emp or emp in bn_upper):
                    seen_employers.add(emp)
                    matches.append({
                        "income_source": f"Business: {biz.get('name')}",
                        "employer_match": emp,
                        "lobbyist_count": len(lobs),
                        "lobbyists": lobs[:5],
                        "who": biz.get("who"),
                        "income_band": "N/A (business)",
                    })
                elif fuzzy(bn_upper, emp):
                    seen_employers.add(emp)
                    matches.append({
                        "income_source": f"Business: {biz.get('name')}",
                        "employer_match": emp,
                        "lobbyist_count": len(lobs),
                        "lobbyists": lobs[:5],
                        "who": biz.get("who"),
                        "income_band": "N/A (business)",
                    })

        leg["lobbyist_matches"] = matches

    ct = sum(1 for l in legislators if l["lobbyist_matches"])
    print(f"  {ct} legislators have lobbyist-connected income sources")


# ---------------------------------------------------------------
# Stage 4: Campaign contributions
# ---------------------------------------------------------------

def pull_contributions(legislators):
    print(f"\n[4/6] Pulling contributions for {len(legislators)} legislators...")
    for i, leg in enumerate(legislators):
        name = leg["name"]
        parts = name.split(",")
        if len(parts) >= 2:
            last = parts[0].strip()
            first = parts[1].strip().split()[0]
        else:
            words = name.split()
            last = words[-1] if words else name
            first = words[0] if len(words) > 1 else ""

        # Skip if last name is too short (causes overly broad API queries)
        if len(last) < 3:
            leg["campaign"] = {"filer_name": None, "total_raised": 0,
                               "total_contributions": 0, "top_org_donors": []}
            continue

        # Escape for SoQL
        last_esc = sql_escape(last)

        params = {
            "$select": "filer_name,sum(amount) as total,count(*) as num",
            "$where": f"filer_name like '%{last_esc}%' AND contributor_category != 'Individual'",
            "$group": "filer_name",
            "$order": "total DESC",
            "$limit": "5",
        }
        results = api_get(CONTRIB_URL, params)

        best_filer = None
        best_total = 0
        for r in results:
            fn = (r.get("filer_name") or "").upper()
            if last.upper() in fn and (not first or first.upper()[:3] in fn):
                t = float(r.get("total", 0))
                if t > best_total:
                    best_total = t
                    best_filer = r.get("filer_name")

        if best_filer:
            filer_esc = sql_escape(best_filer)
            p2 = {
                "$select": "contributor_name,sum(amount) as total,count(*) as num",
                "$where": f"filer_name = '{filer_esc}' AND contributor_category != 'Individual'",
                "$group": "contributor_name",
                "$order": "total DESC",
                "$limit": "10",
            }
            top = api_get(CONTRIB_URL, p2)

            p3 = {
                "$select": "sum(amount) as total,count(*) as num",
                "$where": f"filer_name = '{filer_esc}'",
            }
            tot = api_get(CONTRIB_URL, p3)

            leg["campaign"] = {
                "filer_name": best_filer,
                "total_raised": float(tot[0].get("total", 0)) if tot else 0,
                "total_contributions": int(tot[0].get("num", 0)) if tot else 0,
                "top_org_donors": [
                    {"name": d.get("contributor_name", ""), "total": float(d.get("total", 0))}
                    for d in (top or [])
                ],
            }

            # Detect party from donor names
            dn = " ".join(d.get("contributor_name", "").upper() for d in (top or []))
            if "REPUBLICAN" in dn or "GOP" in dn:
                leg["party"] = "R"
            elif "DEMOCRAT" in dn:
                leg["party"] = "D"
        else:
            leg["campaign"] = {
                "filer_name": None, "total_raised": 0,
                "total_contributions": 0, "top_org_donors": [],
            }

        if (i + 1) % 10 == 0:
            print(f"  ... {i + 1}/{len(legislators)}")

    print("  Done.")


# ---------------------------------------------------------------
# Stage 5: Scoring (CALIBRATED)
# ---------------------------------------------------------------

def fmt_k(n):
    """Format a number as compact currency: 100000 -> $100K, 1500000 -> $1.5M"""
    if n >= 1000000:
        m = n / 1000000
        return f"${m:.1f}M" if m != int(m) else f"${int(m)}M"
    if n >= 1000:
        k = n / 1000
        return f"${k:.0f}K"
    return f"${n:,.0f}"


def fmt_band(band):
    """Format an income band: '100000-199999' -> '$100K-$200K'"""
    if not band or not isinstance(band, str):
        return band or ""
    parts = band.replace(",", "").split("-")
    if len(parts) == 2:
        try:
            lo = int(parts[0])
            hi = int(parts[1]) + 1  # 199999 -> 200000
            return f"{fmt_k(lo)}-{fmt_k(hi)}"
        except ValueError:
            pass
    return band

def score_all(legislators):
    print(f"\n[5/6] Scoring {len(legislators)} legislators...")
    for leg in legislators:
        score = 0
        flags = []

        # 1. Lobbyist in household (10 pts, max once)
        if leg["lobbies"]:
            score += 10
            for lob in leg["lobbies"]:
                ent = lob.get("entity", "")
                if ent:
                    flags.append(f"Registered lobbyist in household: {ent}")

        # 2. Spouse income > $100K from non-government source (5 pts, max once)
        spouse_flagged = False
        for src in leg["income_sources"]:
            if src["is_spouse"] and src["midpoint"] >= 100000 and not spouse_flagged:
                sn = src.get("name", "")
                if not is_gov_income(sn):
                    score += 5
                    flags.append(f"Spouse income {fmt_band(src['band'])} from {sn}")
                    spouse_flagged = True

        # 3. Outside filer income > $30K from non-government source
        #    (3 pts each, max 4 sources = 12 pts cap)
        outside_count = 0
        for src in leg["income_sources"]:
            if outside_count >= 4:
                break
            if src["is_filer"] and src["midpoint"] >= 30000:
                sn = src.get("name", "")
                if not is_gov_income(sn) and not is_skip_income(sn):
                    score += 3
                    outside_count += 1
                    flags.append(f"Outside income {fmt_band(src['band'])} from {sn}")

        # 4. Business with agency payments (8 pts, max once)
        agency_flagged = False
        for biz in leg["businesses"]:
            if biz["has_agency_payments"] and not agency_flagged:
                score += 8
                agency_flagged = True
                ags = [a["agency"] for a in biz["agency_payments"][:3]]
                flags.append(f"Business '{biz['name']}' receives from: {', '.join(ags)}")

        # 5. Income source matches lobbyist employer
        #    (4 pts each, max 3 matches = 12 pts cap)
        lob_count = 0
        for m in leg.get("lobbyist_matches", []):
            if lob_count >= 3:
                break
            score += 4
            lob_count += 1
            flags.append(
                f"Income '{m['income_source']}' linked to lobbyist employer "
                f"'{m['employer_match']}' ({m['lobbyist_count']} lobbyists)"
            )

        # 6. Complex business picture (2 pts, once)
        if len(leg["businesses"]) >= 5:
            score += 2
            flags.append(f"{len(leg['businesses'])} business associations (complex)")

        # 7. High fundraising (1 pt, once)
        raised = leg.get("campaign", {}).get("total_raised", 0)
        if raised > 500000:
            score += 1
            flags.append(f"Career fundraising: {fmt_k(raised)}")

        # Max theoretical score: 10 + 5 + 12 + 8 + 12 + 2 + 1 = 50
        # Badge thresholds
        if score >= 10:
            badge = "conflict"
        elif score >= 5:
            badge = "review"
        elif score >= 2:
            badge = "monitoring"
        else:
            badge = "clean"

        leg["score"] = score
        leg["badge"] = badge
        leg["flags"] = flags
        if flags:
            leg["summary"] = flags[0]
        else:
            leg["summary"] = "No significant conflicts identified in current filing."

    legislators.sort(key=lambda l: (-l["score"], l["name"]))

    dist = {}
    for l in legislators:
        dist[l["badge"]] = dist.get(l["badge"], 0) + 1
    print("  Results:")
    for b, c in sorted(dist.items()):
        print(f"    {b}: {c}")


# ---------------------------------------------------------------
# Roster loading (party + classification)
# ---------------------------------------------------------------

def load_roster():
    """Load roster.json if it exists. Returns a dict of name_key -> {party, chamber, district}."""
    roster_path = Path("roster.json")
    if not roster_path.exists():
        print("  roster.json not found. Run pull_roster.py first for party data.")
        print("  Continuing without roster (party detection via contributions only).")
        return {}
    with open(roster_path) as f:
        data = json.load(f)
    members = data.get("members", [])
    lookup = {}
    info_template = lambda m: {"party": m["party"], "chamber": m.get("chamber", ""),
                                "district": m.get("district", "")}
    for m in members:
        info = info_template(m)
        # Index by name_key
        key = m.get("name_key", "").lower().strip()
        if key:
            lookup[key] = info
        # Index by "last first" (reverse)
        parts = key.split()
        if len(parts) >= 2:
            lookup[f"{parts[-1]} {parts[0]}"] = info
        # Index by explicit first_name + last_name (most reliable from API)
        first = m.get("first_name", "").lower().strip()
        last = m.get("last_name", "").lower().strip()
        if first and last:
            lookup[f"{first} {last}"] = info
            lookup[f"{last} {first}"] = info
            # Also just last name for fallback (risky but catches edge cases)
            # Don't do this - too many collisions
    print(f"  Loaded roster: {len(members)} members ({data.get('pulled_date', '?')})")
    return lookup


NICKNAMES = {
    "elizabeth": ["liz", "beth", "betty"],
    "liz": ["elizabeth"],
    "andrew": ["andy", "drew"],
    "andy": ["andrew"],
    "drew": ["andrew"],
    "james": ["jim", "jimmy"],
    "jim": ["james"],
    "william": ["bill", "will", "billy"],
    "bill": ["william"],
    "robert": ["bob", "rob", "bobby"],
    "bob": ["robert"],
    "richard": ["dick", "rick"],
    "dick": ["richard"],
    "thomas": ["tom", "tommy"],
    "tom": ["thomas"],
    "joseph": ["joe"],
    "joe": ["joseph"],
    "michael": ["mike"],
    "mike": ["michael"],
    "christopher": ["chris"],
    "chris": ["christopher"],
    "edward": ["ed", "ted"],
    "ed": ["edward"],
    "margaret": ["peggy", "maggie"],
    "patricia": ["pat", "patty"],
    "pat": ["patricia"],
    "katherine": ["kate", "kathy"],
    "catherine": ["kate", "kathy"],
    "samuel": ["sam"],
    "sam": ["samuel"],
    "daniel": ["dan", "danny"],
    "dan": ["daniel"],
    "timothy": ["tim"],
    "tim": ["timothy"],
    "matthew": ["matt"],
    "matt": ["matthew"],
    "jennifer": ["jen", "jenny"],
    "jessica": ["jess", "jessie"],
    "stephanie": ["steph"],
    "benjamin": ["ben"],
    "ben": ["benjamin"],
    "nicholas": ["nick"],
    "nick": ["nicholas"],
    "jonathan": ["jon"],
    "jon": ["jonathan"],
    "joshua": ["josh"],
    "josh": ["joshua"],
    "larry": ["lawrence"],
    "lawrence": ["larry"],
    "steve": ["steven", "stephen"],
    "steven": ["steve"],
    "stephen": ["steve"],
}


def match_roster_name(name, roster):
    """Try to match a legislator name against the roster, including nicknames."""
    if not roster:
        return None
    # Clean the name
    clean = name.strip().lower()
    # Remove suffixes like "III", "Jr", "Sr"
    clean = re.sub(r'\s+(iii|ii|iv|jr|sr)\.?$', '', clean, flags=re.I)

    def try_keys(first, last):
        """Try first-last, last-first, and nickname variants."""
        for f in [first] + NICKNAMES.get(first, []):
            key1 = f"{f} {last}"
            if key1 in roster:
                return roster[key1]
            key2 = f"{last} {f}"
            if key2 in roster:
                return roster[key2]
        return None

    # Handle "Last, First Middle" format
    if "," in clean:
        parts = clean.split(",")
        last = parts[0].strip()
        first_parts = parts[1].strip().split() if len(parts) > 1 else []
        first = first_parts[0] if first_parts else ""
        if first and last:
            return try_keys(first, last)
    else:
        # "First Middle Last" format
        parts = clean.split()
        if len(parts) >= 2:
            first = parts[0]
            last = parts[-1]
            result = try_keys(first, last)
            if result:
                return result
    return None


def classify_legislators(legislators, roster):
    """Set party from roster and classify as Incumbent/Candidate/Former."""
    print("\n[5.5/6] Classifying legislators...")
    incumbents = 0
    former = 0
    candidates = 0
    party_set = 0

    for leg in legislators:
        # Try to match against roster
        match = match_roster_name(leg["name"], roster)

        # Set party from roster (overrides contribution-based detection)
        if match:
            leg["party"] = match["party"]
            party_set += 1

        # Classification: roster is ground truth for incumbents
        if match:
            # In the official roster = currently serving
            leg["classification"] = "incumbent"
            incumbents += 1
        elif leg.get("leg_income", 0) > 0:
            # Has legislative pay but NOT in current roster = former member
            leg["classification"] = "former"
            former += 1
        else:
            # Not in roster, no legislative pay = candidate or other
            leg["classification"] = "candidate"
            candidates += 1

    # Count remaining unknowns
    unknown_party = sum(1 for l in legislators if l["party"] == "Unknown")

    print(f"  Incumbents: {incumbents}")
    print(f"  Former: {former}")
    print(f"  Candidates: {candidates}")
    print(f"  Party set from roster: {party_set}")
    print(f"  Party still unknown: {unknown_party}")


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sunshine Docket Screener v4")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--output", type=str, default="screener_results.json")
    parser.add_argument("--skip-contributions", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("SUNSHINE DOCKET LEGISLATIVE SCREENER v5")
    print(f"Target year: CY{args.year}")
    print(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    filings = pull_filings(args.year)
    if not filings:
        print("ERROR: No filings found.")
        sys.exit(1)

    legislators = extract_legislators(filings)
    if not legislators:
        print("ERROR: No legislators found.")
        sys.exit(1)

    emp_lobs = pull_lobbyists(args.year)
    prior = pull_lobbyists(args.year - 1)
    for k, v in prior.items():
        if k not in emp_lobs:
            emp_lobs[k] = v
    match_lobbyists(legislators, emp_lobs)

    if not args.skip_contributions:
        pull_contributions(legislators)
    else:
        print("\n[4/6] Skipping contributions (--skip-contributions)")
        for leg in legislators:
            leg["campaign"] = {"filer_name": None, "total_raised": 0,
                               "total_contributions": 0, "top_org_donors": []}

    score_all(legislators)

    # Load roster for party + classification
    roster = load_roster()
    classify_legislators(legislators, roster)

    # VALIDATION: Remove false positives (staff, interns, student govt, etc.)
    # Keep only: roster matches (incumbent), confirmed legislative pay (former),
    # and people with explicit legislative office titles (candidate)
    before = len(legislators)
    validated = []
    excluded = []
    for leg in legislators:
        cl = leg.get("classification", "unknown")
        if cl == "incumbent":
            # In the roster, always keep
            validated.append(leg)
        elif cl == "former":
            # Has legislative income, not in roster. Keep only if leg_income
            # was detected from a credible source (detect_chamber passed)
            if leg.get("leg_income", 0) > 0:
                validated.append(leg)
            else:
                excluded.append(leg["name"])
        elif cl == "candidate":
            # No legislative income but has offices field match.
            # Keep only if they have a district number (indicates real filing)
            if leg.get("district") and leg["district"] != "0":
                validated.append(leg)
            else:
                excluded.append(leg["name"])
        else:
            excluded.append(leg["name"])

    if excluded:
        print(f"\n  Excluded {len(excluded)} non-legislators (staff/interns/other):")
        for n in excluded[:10]:
            print(f"    - {n}")
        if len(excluded) > 10:
            print(f"    ... and {len(excluded) - 10} more")

    legislators = validated
    print(f"  Validated: {before} -> {len(legislators)} legislators")

    for leg in legislators:
        leg["slug"] = make_slug(leg["name"])

    output = {
        "meta": {
            "run_date": datetime.now().isoformat(),
            "target_year": args.year,
            "total_filings": len(filings),
            "total_legislators": len(legislators),
            "score_distribution": {},
            "classification_distribution": {},
        },
        "legislators": legislators,
    }
    for leg in legislators:
        b = leg["badge"]
        output["meta"]["score_distribution"][b] = output["meta"]["score_distribution"].get(b, 0) + 1
        c = leg.get("classification", "unknown")
        output["meta"]["classification_distribution"][c] = output["meta"]["classification_distribution"].get(c, 0) + 1

    out_path = Path(args.output)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    incumb = sum(1 for l in legislators if l.get("classification") == "incumbent")
    fmr = sum(1 for l in legislators if l.get("classification") == "former")
    cands = sum(1 for l in legislators if l.get("classification") == "candidate")
    print(f"\n{'=' * 60}")
    print(f"Written to: {out_path}")
    print(f"Legislators: {len(legislators)} ({incumb} incumbent, {fmr} former, {cands} candidates)")
    dists_found = sum(1 for l in legislators if l.get("district"))
    print(f"With district numbers: {dists_found}")
    d_count = sum(1 for l in legislators if l["party"] == "D")
    r_count = sum(1 for l in legislators if l["party"] == "R")
    u_count = sum(1 for l in legislators if l["party"] == "Unknown")
    print(f"Party: D={d_count} R={r_count} Unknown={u_count}")
    print(f"{'=' * 60}")

    print(f"\nTop 20:")
    print(f"{'Score':<6} {'Badge':<10} {'Type':<10} {'Party':<4} {'Name':<28} {'Dist':<5} {'Top Flag'}")
    print("-" * 100)
    for leg in legislators[:20]:
        fl = leg["flags"][0][:30] if leg["flags"] else "Clean"
        d = leg.get("district", "")
        p = leg.get("party", "?")
        cl = leg.get("classification", "?")[:9]
        print(f"{leg['score']:<6} {leg['badge']:<10} {cl:<10} {p:<4} {leg['name'][:26]:<28} "
              f"{d:<5} {fl}")


if __name__ == "__main__":
    main()
