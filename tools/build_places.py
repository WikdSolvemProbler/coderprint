#!/usr/bin/env python3
"""Builds places.tsv.gz, the table coderprint reads a time zone from a profile's location with, from three
GeoNames files (https://download.geonames.org/export/dump/): cities15000.txt (unzipped from
cities15000.zip), admin1CodesASCII.txt and countryInfo.txt. GeoNames data is licensed under Creative
Commons Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/), and so is the table built from it.
GeoNames provides the data as is, without warranty or any representation of accuracy, timeliness or
completeness.

    python tools/build_places.py FOLDER_HOLDING_THE_THREE_FILES

Rows are tab separated, with names already folded by coderprint.place_key and joined by "|":
    C  country code  names
    A  country code  region code  names
    P  GeoNames id  country code  region code  people  zone  names
The same three files always build the same bytes.
"""
import gzip
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("coderprint", os.path.join(HERE, "..", "coderprint.py"))
coderprint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coderprint)
key = coderprint.place_key

OTHER_NAMES_FROM = 500000   # a city this big also answers to its other Latin names: Bangalore, Bombay, Munich
LATIN = set("abcdefghijklmnopqrstuvwxyz0123456789 ")
# A big city's other name is dropped when it is some other place's own name (Changchun is also listed as
# "Cancun", Austin as "Waterloo"), except for these old names people still write for the big city.
EXONYMS = {"calcutta", "odessa", "st petersburg", "pekin", "peking"}

# Names people write for a country that GeoNames lists under another.
COUNTRY_NAMES = {
    "US": ["usa", "us", "u s", "u s a", "united states of america", "america", "the us", "the usa", "the united states"],
    "GB": ["uk", "u k", "the uk", "great britain", "britain"],
    "NL": ["netherlands", "nederland", "holland"],
    "HK": ["hong kong sar"],
    "DE": ["deutschland"], "ES": ["espana"], "BR": ["brasil"], "IT": ["italia"], "AT": ["osterreich"],
    "CH": ["schweiz", "suisse", "svizzera"], "PL": ["polska"], "TR": ["turkiye"], "SE": ["sverige"],
    "NO": ["norge"], "DK": ["danmark"], "FI": ["suomi"], "CZ": ["czech republic", "ceska republika", "cesko"],
    "KR": ["korea", "republic of korea"], "RU": ["russian federation"], "VN": ["viet nam"],
    "AE": ["uae", "u a e"], "BE": ["belgie", "belgique"], "HU": ["magyarorszag"], "GR": ["hellas"],
    "HR": ["hrvatska"], "IE": ["eire"], "JP": ["nippon", "nihon"], "PH": ["pilipinas"],
}
# The abbreviations and local names people write for a region, by the region's GeoNames name, for
# countries whose GeoNames region codes are numbers. (US states already carry their postal codes.) Each
# name is checked against admin1CodesASCII when the table is built.
REGION_NAMES = {
    "CA": {"Alberta": ["ab"], "British Columbia": ["bc"], "Manitoba": ["mb"], "New Brunswick": ["nb"],
           "Newfoundland and Labrador": ["nl"], "Nova Scotia": ["ns"], "Ontario": ["on"],
           "Prince Edward Island": ["pe", "pei"], "Quebec": ["qc"], "Saskatchewan": ["sk"], "Yukon": ["yt"],
           "Northwest Territories": ["nt"], "Nunavut": ["nu"]},
    "AU": {"Australian Capital Territory": ["act"], "New South Wales": ["nsw"], "Northern Territory": ["nt"],
           "Queensland": ["qld"], "South Australia": ["sa"], "Tasmania": ["tas"], "Victoria": ["vic"],
           "Western Australia": ["wa"]},
    "BR": {"Acre": ["ac"], "Alagoas": ["al"], "Amapa": ["ap"], "Amazonas": ["am"], "Bahia": ["ba"], "Ceara": ["ce"],
           "Federal District": ["df", "distrito federal"], "Espirito Santo": ["es"], "Goias": ["go"],
           "Maranhao": ["ma"], "Mato Grosso": ["mt"], "Mato Grosso do Sul": ["ms"], "Minas Gerais": ["mg"],
           "Para": ["pa"], "Paraiba": ["pb"], "Parana": ["pr"], "Pernambuco": ["pe"], "Piaui": ["pi"],
           "Rio de Janeiro": ["rj"], "Rio Grande do Norte": ["rn"], "Rio Grande do Sul": ["rs"], "Rondonia": ["ro"],
           "Roraima": ["rr"], "Santa Catarina": ["sc"], "Sao Paulo": ["sp"], "Sergipe": ["se"], "Tocantins": ["to"]},
    "IN": {"Andhra Pradesh": ["ap"], "Arunachal Pradesh": ["ar"], "Assam": ["as"], "Bihar": ["br"],
           "Chhattisgarh": ["cg", "ct"], "Goa": ["ga"], "Gujarat": ["gj"], "Haryana": ["hr"],
           "Himachal Pradesh": ["hp"], "Jharkhand": ["jh"], "Karnataka": ["ka"], "Kerala": ["kl"],
           "Madhya Pradesh": ["mp"], "Maharashtra": ["mh"], "Manipur": ["mn"], "Meghalaya": ["ml"], "Mizoram": ["mz"],
           "Nagaland": ["nl"], "Odisha": ["od", "or", "orissa"], "Punjab": ["pb"], "Rajasthan": ["rj"], "Sikkim": ["sk"],
           "Tamil Nadu": ["tn"], "Telangana": ["tg", "ts"], "Tripura": ["tr"], "Uttar Pradesh": ["up"],
           "Uttarakhand": ["uk", "ut"], "West Bengal": ["wb"], "Delhi": ["dl", "ncr"], "Jammu and Kashmir": ["jk"],
           "Chandigarh": ["ch"], "Puducherry": ["py"], "Ladakh": ["la"]},
    "DE": {"Baden-Wurttemberg": ["bw"], "Bavaria": ["by", "bayern"], "State of Berlin": ["be"],
           "Brandenburg": ["bb"], "Bremen": ["hb"], "Hamburg": ["hh"], "Hesse": ["he", "hessen"],
           "Mecklenburg-Vorpommern": ["mv"], "Lower Saxony": ["ni", "niedersachsen"],
           "North Rhine-Westphalia": ["nw", "nrw", "nordrhein westfalen"], "Rheinland-Pfalz": ["rp"],
           "Saarland": ["sl"], "Saxony": ["sn", "sachsen"], "Saxony-Anhalt": ["st", "sachsen anhalt"],
           "Schleswig-Holstein": ["sh"], "Thuringia": ["th", "thuringen"]},
    "MX": {"Mexico City": ["cdmx"], "Nuevo Leon": ["nl"], "Jalisco": ["jal"], "Baja California": ["bc"],
           "Baja California Sur": ["bcs"], "Queretaro": ["qro"], "Guanajuato": ["gto"], "Puebla": ["pue"],
           "Yucatan": ["yuc"], "Quintana Roo": ["qroo"], "Sonora": ["son"], "Chihuahua": ["chih"],
           "Coahuila": ["coah"], "Aguascalientes": ["ags"], "San Luis Potosi": ["slp"], "Veracruz": ["ver"],
           "Oaxaca": ["oax"], "Michoacan": ["mich"], "Mexico": ["edomex"], "Sinaloa": ["sin"],
           "Tamaulipas": ["tamps"], "Guerrero": ["gro"], "Hidalgo": ["hgo"], "Morelos": ["mor"], "Chiapas": ["chis"],
           "Tabasco": ["tab"], "Campeche": ["camp"], "Durango": ["dgo"], "Colima": ["col"], "Nayarit": ["nay"],
           "Zacatecas": ["zac"], "Tlaxcala": ["tlax"]},
}
# Names for a city that GeoNames does not carry, or carries only in forms shorter than four letters.
CITY_NAMES = {
    ("San Francisco", "US", "CA"): ["sf", "bay area", "sf bay area", "san francisco bay area"],
    ("San Jose", "US", "CA"): ["silicon valley"],
    ("New York City", "US", "NY"): ["nyc"],
    ("St. Louis", "US", "MO"): ["saint louis"],
}


def rows(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                yield line.rstrip("\n").split("\t")


def names(*groups):
    """Each name folded once, in order, dropping blanks and repeats."""
    out = []
    for group in groups:
        for name in group:
            k = key(name)
            if k and k not in out:
                out.append(k)
    return out


def main(folder):
    out, own = [], set()
    countries = set()
    for r in rows(os.path.join(folder, "countryInfo.txt")):
        countries.add(r[0])
        row = names([r[4], r[0], r[1]], COUNTRY_NAMES.get(r[0], []))
        own.add(key(r[4]))
        out.append(("C", r[0], "|".join(row)))
    wanted_regions = {(cc, name): extra for cc, table in REGION_NAMES.items() for name, extra in table.items()}
    for r in rows(os.path.join(folder, "admin1CodesASCII.txt")):
        cc, _, code = r[0].partition(".")
        own.update((key(r[1]), key(r[2])))
        own_code = [code] if cc == "US" and code.isalpha() else []
        extra = wanted_regions.pop((cc, r[2]), [])
        out.append(("A", cc, code, "|".join(names([r[1], r[2]], own_code, extra))))
    if wanted_regions:
        raise SystemExit("regions not found for the extra names: %s" % ", ".join("%s %s" % k for k in wanted_regions))
    cities = [r for r in rows(os.path.join(folder, "cities15000.txt")) if r[17] and r[8] in countries]
    for r in cities:
        own.update((key(r[1]), key(r[2])))
    wanted = dict(CITY_NAMES)
    for r in cities:
        geoname_id, name, ascii_name, other, cc, region, people, zone = r[0], r[1], r[2], r[3], r[8], r[10], r[14], r[17]
        mine = {key(name), key(ascii_name)}
        others = []
        if int(people or 0) >= OTHER_NAMES_FROM:
            for n in other.split(","):
                k = key(n)
                if len(k) >= 4 and set(k) <= LATIN and (k not in own or k in mine or k in EXONYMS):
                    others.append(n)
        extra = wanted.pop((name, cc, region), [])
        out.append(("P", geoname_id, cc, region, str(int(people or 0)), zone,
                    "|".join(names([name, ascii_name], others, extra))))
    if wanted:
        raise SystemExit("cities not found for the extra names: %s" % ", ".join(n for n, _, _ in wanted))
    out.sort(key=lambda row: (row[0] != "C", row[0] != "A", row[1:]))
    header = ("# Places for coderprint: GeoNames (https://www.geonames.org) cities15000, admin1CodesASCII and "
              "countryInfo, trimmed to names, populations and time zones, names folded to plain lowercase, and a "
              "few common alternative names added, by tools/build_places.py. Licensed under Creative Commons "
              "Attribution 4.0, https://creativecommons.org/licenses/by/4.0/. GeoNames provides the data as is, "
              "without warranty or any representation of accuracy, timeliness or completeness.\n")
    text = header + "".join("\t".join(row) + "\n" for row in out)
    target = os.path.normpath(os.path.join(HERE, "..", "places.tsv.gz"))
    with open(target, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as f:
        f.write(text.encode("utf-8"))
    print("wrote %s: %d countries, %d regions, %d cities, %d bytes"
          % (target, sum(r[0] == "C" for r in out), sum(r[0] == "A" for r in out),
             sum(r[0] == "P" for r in out), os.path.getsize(target)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
