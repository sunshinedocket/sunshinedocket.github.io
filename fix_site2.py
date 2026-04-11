#!/usr/bin/env python3
"""Targeted fixes for sunshinedocket.org"""
import glob, os
os.chdir(os.path.expanduser("~/sunshinedocket"))

# --- Fix 1: Legislature broken nav ---
with open("legislature.html") as f:
    html = f.read()

# The broken text is visible on the page - find it by the unique string
target = """< style="font-family:'DM Mono',monospace;font-size:12px;color:#5b9bd5;text-decoration:none;display:block;padding:16px 0;">"""
if target in html:
    # Remove the entire broken line including the trailing text
    start = html.find(target)
    # Find the end of this line
    end = html.find("\n", start)
    if end == -1:
        end = start + len(target) + 50
    removed = html[start:end]
    html = html[:start] + html[end:]
    print(f"Legislature: removed broken nav: {removed[:80]}...")
else:
    # Try broader search
    for line_num, line in enumerate(html.split("\n")):
        if "font-family" in line and "Sunshine Docket" in line and "<a " not in line:
            print(f"Legislature: found broken line {line_num}: {line[:80]}")
            html = html.replace(line, "")
            print("  Removed.")
            break
    else:
        print("Legislature: could not find broken nav text")

with open("legislature.html", "w") as f:
    f.write(html)

# Verify
with open("legislature.html") as f:
    top = f.read()[:3000]
if "font-family" in top.split("<header")[0] if "<header" in top else top:
    print("  WARNING: broken text may still be present")
else:
    print("  Verified: clean before <header>")

# --- Fix 2: Homepage duplicate Brandeis ---
with open("index.html") as f:
    html = f.read()
count = html.count("Sunlight is said")
if count > 1:
    # Remove first occurrence of the full epigraph div
    marker = '<div class="epigraph">'
    first = html.find(marker)
    # Find the closing </div> for this div
    close = html.find("</div>", first) + len("</div>")
    html = html[:first] + html[close:]
    with open("index.html", "w") as f:
        f.write(html)
    print(f"Homepage: removed duplicate Brandeis (was {count}, now 1)")
else:
    print(f"Homepage: Brandeis OK ({count})")

# --- Fix 3: Profile nav links ---
fixed = 0
for p in sorted(glob.glob("profiles/*.html")):
    with open(p) as f:
        html = f.read()
    orig = html
    # Fix any link pointing to legislature
    html = html.replace('href="https://sunshinedocket.org/legislature"', 'href="/"')
    html = html.replace("href='https://sunshinedocket.org/legislature'", 'href="/"')
    html = html.replace('href="/legislature"', 'href="/"')
    html = html.replace('href="/legislature.html"', 'href="/"')
    html = html.replace('href="../legislature.html"', 'href="/"')
    html = html.replace('href="../legislature"', 'href="/"')
    # Also check for relative without slash
    html = html.replace('href="legislature.html"', 'href="/"')
    html = html.replace("Back to all findings", "Sunshine Docket")
    if html != orig:
        with open(p, "w") as f:
            f.write(html)
        fixed += 1
        print(f"  Fixed: {os.path.basename(p)}")

# Check what the actual back link looks like
for p in sorted(glob.glob("profiles/*.html")):
    with open(p) as f:
        html = f.read()
    # Find all <a> tags near the top
    import re
    links = re.findall(r'<a [^>]*href="[^"]*"[^>]*>[^<]*</a>', html[:2000])
    for link in links:
        if "Back" in link or "finding" in link or "legislature" in link.lower():
            print(f"  STILL BAD in {os.path.basename(p)}: {link}")

print(f"Profiles: fixed {fixed} files")
print("\nDone. Run: git add -A && git commit -m 'fix nav' && git push")
