#!/usr/bin/env python3
"""
Download official headshots for WA state legislators from leg.wa.gov.
Run on Williams-Mini: python3 download_legislator_photos.py

Photos saved to ./legislator_photos/ as firstname-lastname.jpg
"""

import os
import re
import time
import urllib.request
from html.parser import HTMLParser

OUTPUT_DIR = "legislator_photos"

# All 147 legislators from the WA EC Tracker
LEGISLATORS = [
    ("Peter", "Abbarno", "R", "House"),
    ("Hunter", "Abell", "R", "House"),
    ("Emily", "Alvarado", "D", "Senate"),
    ("Andrew", "Barkis", "R", "House"),
    ("Stephanie", "Barnard", "R", "House"),
    ("Jessica", "Bateman", "D", "Senate"),
    ("April", "Berg", "D", "House"),
    ("Steve", "Bergquist", "D", "House"),
    ("Adam", "Bernbaum", "D", "House"),
    ("Liz", "Berry", "D", "House"),
    ("Matt", "Boehnke", "R", "Senate"),
    ("John", "Braun", "R", "Senate"),
    ("Dan", "Bronoske", "D", "House"),
    ("Brian", "Burnett", "R", "House"),
    ("Lisa", "Callan", "D", "House"),
    ("Mike", "Chapman", "D", "Senate"),
    ("Rob", "Chase", "R", "House"),
    ("Leonard", "Christian", "R", "Senate"),
    ("Annette", "Cleveland", "D", "Senate"),
    ("April", "Connors", "R", "House"),
    ("Steve", "Conway", "D", "Senate"),
    ("Chris", "Corry", "R", "House"),
    ("Julio", "Cortes", "D", "House"),
    ("Adrian", "Cortes", "D", "Senate"),
    ("Travis", "Couture", "R", "House"),
    ("Lauren", "Davis", "D", "House"),
    ("Tom", "Dent", "R", "House"),
    ("Manka", "Dhingra", "D", "Senate"),
    ("Beth", "Doglio", "D", "House"),
    ("Brandy", "Donaghy", "D", "House"),
    ("Perry", "Dozier", "R", "Senate"),
    ("Davina", "Duerr", "D", "House"),
    ("Jeremie", "Dufault", "R", "House"),
    ("Mary", "Dye", "R", "House"),
    ("Andrew", "Engell", "R", "House"),
    ("Debra", "Entenman", "D", "House"),
    ("Carolyn", "Eslick", "R", "House"),
    ("Darya", "Farivar", "D", "House"),
    ("Jake", "Fey", "D", "House"),
    ("Joe", "Fitzgibbon", "D", "House"),
    ("Phil", "Fortunato", "R", "Senate"),
    ("Mary", "Fosse", "D", "House"),
    ("Noel", "Frame", "D", "Senate"),
    ("Chris", "Gildon", "R", "Senate"),
    ("Keith", "Goehner", "R", "Senate"),
    ("Roger", "Goodman", "D", "House"),
    ("Jenny", "Graham", "R", "House"),
    ("Mia", "Gregerson", "D", "House"),
    ("Dan", "Griffey", "R", "House"),
    ("David", "Hackney", "D", "House"),
    ("Zach", "Hall", "D", "House"),
    ("Drew", "Hansen", "D", "Senate"),
    ("Paul", "Harris", "R", "Senate"),
    ("Bob", "Hasegawa", "D", "Senate"),
    ("Natasha", "Hill", "D", "House"),
    ("Jeff", "Holy", "R", "Senate"),
    ("Victoria", "Hunt", "D", "Senate"),
    ("Cyndy", "Jacobsen", "R", "House"),
    ("Laurie", "Jinkins", "D", "House"),
    ("Claudia", "Kauffman", "D", "Senate"),
    ("Michael", "Keaton", "R", "House"),
    ("Curtis", "King", "R", "Senate"),
    ("Mark", "Klicker", "R", "House"),
    ("Shelley", "Kloba", "D", "House"),
    ("Deborah", "Krishnadasan", "D", "Senate"),
    ("Mari", "Leavitt", "D", "House"),
    ("Debra", "Lekanoff", "D", "House"),
    ("John", "Ley", "R", "House"),
    ("Marko", "Liias", "D", "Senate"),
    ("Liz", "Lovelett", "D", "Senate"),
    ("John", "Lovick", "D", "Senate"),
    ("Sam", "Low", "R", "House"),
    ("Drew", "MacEwen", "R", "Senate"),
    ("Nicole", "Macri", "D", "House"),
    ("Deb", "Manjarrez", "R", "House"),
    ("Matt", "Marshall", "R", "House"),
    ("Stephanie", "McClintock", "R", "House"),
    ("Jim", "McCune", "R", "Senate"),
    ("Joel", "McEntire", "R", "House"),
    ("Sharlett", "Mena", "D", "House"),
    ("Gloria", "Mendoza", "R", "House"),
    ("Melanie", "Morgan", "D", "House"),
    ("Ron", "Muzzall", "R", "Senate"),
    ("Greg", "Nance", "D", "House"),
    ("T'wina", "Nobles", "D", "Senate"),
    ("Edwin", "Obras", "D", "House"),
    ("Ed", "Orcutt", "R", "House"),
    ("Timm", "Ormsby", "D", "House"),
    ("Lillian", "Ortiz-Self", "D", "House"),
    ("Tina", "Orwall", "D", "Senate"),
    ("Lisa", "Parshley", "D", "House"),
    ("Dave", "Paul", "D", "House"),
    ("Jamie", "Pedersen", "D", "Senate"),
    ("Joshua", "Penner", "R", "House"),
    ("Strom", "Peterson", "D", "House"),
    ("Gerry", "Pollet", "D", "House"),
    ("Alex", "Ramel", "D", "House"),
    ("Bill", "Ramos", "D", "Senate"),
    ("Julia", "Reed", "D", "House"),
    ("Kristine", "Reeves", "D", "House"),
    ("Marcus", "Riccelli", "D", "Senate"),
    ("Adison", "Richards", "D", "House"),
    ("June", "Robinson", "D", "Senate"),
    ("Skyler", "Rude", "R", "House"),
    ("Alicia", "Rule", "D", "House"),
    ("Cindy", "Ryu", "D", "House"),
    ("Osman", "Salahuddin", "D", "House"),
    ("Rebecca", "Saldaña", "D", "Senate"),  # note: ñ
    ("Jesse", "Salomon", "D", "Senate"),
    ("Sharon Tomiko", "Santos", "D", "House"),
    ("Joe", "Schmick", "R", "House"),
    ("Suzanne", "Schmidt", "R", "House"),
    ("Mark", "Schoesler", "R", "Senate"),
    ("Shaun", "Scott", "D", "House"),
    ("Clyde", "Shavers", "D", "House"),
    ("Sharon", "Shewmake", "D", "Senate"),
    ("Shelly", "Short", "R", "Senate"),
    ("Tarra", "Simmons", "D", "House"),
    ("Vandana", "Slatter", "D", "Senate"),
    ("Larry", "Springer", "D", "House"),
    ("Derek", "Stanford", "D", "Senate"),
    ("Chris", "Stearns", "D", "House"),
    ("Mike", "Steele", "R", "House"),
    ("Drew", "Stokesbary", "R", "House"),
    ("Monica Jurado", "Stonier", "D", "House"),
    ("Chipalo", "Street", "D", "House"),
    ("David", "Stuebe", "R", "House"),
    ("Jamila", "Taylor", "D", "House"),
    ("My-Linh", "Thai", "D", "House"),
    ("Steve", "Tharinger", "D", "House"),
    ("Brianna", "Thomas", "D", "House"),
    ("Joe", "Timmons", "D", "House"),
    ("Nikki", "Torres", "R", "Senate"),
    ("Yasmin", "Trudeau", "D", "Senate"),
    ("Michelle", "Valdez", "R", "House"),
    ("Javier", "Valdez", "D", "Senate"),
    ("Mike", "Volz", "R", "House"),
    ("Keith", "Wagoner", "R", "Senate"),
    ("Amy", "Walen", "D", "House"),
    ("Jim", "Walsh", "R", "House"),
    ("Judy", "Warnick", "R", "Senate"),
    ("Kevin", "Waters", "R", "House"),
    ("Lisa", "Wellman", "D", "Senate"),
    ("Claire", "Wilson", "D", "Senate"),
    ("Jeff", "Wilson", "R", "Senate"),
    ("Sharon", "Wylie", "D", "House"),
    ("Alex", "Ybarra", "R", "House"),
    ("Janice", "Zahn", "D", "House"),
]


class PhotoURLParser(HTMLParser):
    """Extract the memberphoto URL from a legislator page."""
    def __init__(self):
        super().__init__()
        self.photo_url = None

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            attrs_dict = dict(attrs)
            src = attrs_dict.get("src", "")
            if "memberphoto" in src:
                self.photo_url = src


def slug(first, last):
    """Build the URL slug: first-last, lowercase, ASCII-safe."""
    name = f"{first}-{last}"
    # Handle special characters
    name = name.replace("'", "").replace("ñ", "n")
    # Collapse spaces to hyphens
    name = re.sub(r"\s+", "-", name)
    return name.lower()


def filename(first, last, party, chamber):
    """Build a clean filename for the photo."""
    clean = slug(first, last)
    return f"{clean}.jpg"


def fetch_page(url):
    """Fetch a URL and return the text content."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def download_file(url, dest):
    """Download a file to disk."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        with open(dest, "wb") as f:
            f.write(resp.read())


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    success = 0
    failed = []

    for i, (first, last, party, chamber) in enumerate(LEGISLATORS, 1):
        name_slug = slug(first, last)
        page_url = f"https://leg.wa.gov/legislators/member/{name_slug}"
        out_file = os.path.join(OUTPUT_DIR, filename(first, last, party, chamber))

        if os.path.exists(out_file):
            print(f"[{i}/{len(LEGISLATORS)}] SKIP (exists): {first} {last}")
            success += 1
            continue

        print(f"[{i}/{len(LEGISLATORS)}] {first} {last} ... ", end="", flush=True)

        try:
            html = fetch_page(page_url)
            parser = PhotoURLParser()
            parser.feed(html)

            if not parser.photo_url:
                print("NO PHOTO FOUND")
                failed.append((first, last, "no photo tag"))
                continue

            photo_url = parser.photo_url
            if photo_url.startswith("/"):
                photo_url = f"https://leg.wa.gov{photo_url}"

            download_file(photo_url, out_file)
            size_kb = os.path.getsize(out_file) / 1024
            print(f"OK ({size_kb:.0f} KB)")
            success += 1

        except Exception as e:
            print(f"ERROR: {e}")
            failed.append((first, last, str(e)))

        # Be polite
        time.sleep(0.5)

    print(f"\nDone: {success} downloaded, {len(failed)} failed")
    if failed:
        print("\nFailed:")
        for first, last, reason in failed:
            print(f"  {first} {last}: {reason}")


if __name__ == "__main__":
    main()
