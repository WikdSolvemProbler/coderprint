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
    Q  country code  region code  abbreviations, which only confirm a place another part of a location names
    P  GeoNames id  country code  region code  people  zone  names  [other names]
A city's other names are names it shares with some other place's own name ("Cancun" is also listed for
Changchun); coderprint reads them only when the rest of the location points at that city. The same three
files always build the same bytes.
"""
import gzip
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("coderprint", os.path.join(HERE, "..", "coderprint.py"))
coderprint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coderprint)
key = coderprint.place_key

OTHER_NAMES_FROM = 500000   # a city this big also answers to its other names: Bangalore, Bombay, Munich, Москва
LATIN = set("abcdefghijklmnopqrstuvwxyz0123456789 ")   # other Latin names need four letters, other scripts two
# A big city's other name that is some other place's own name only counts when the rest of the location
# points at the big city, except for these, which people write for the big city alone.
EXONYMS = {"calcutta", "odessa", "st petersburg", "pekin", "peking", "hanover", "leon", "singapur", "mansoura",
           "mansourah", "sao bernardo", "matamoros", "anyang"}

# Names people write for a country that GeoNames lists under another.
COUNTRY_NAMES = {
    "US": ["usa", "us", "united states of america", "america", "the us", "the usa", "the united states"],
    "GB": ["uk", "the uk", "great britain", "britain"],
    "NL": ["netherlands", "nederland", "holland"],
    "HK": ["hong kong sar"],
    "DE": ["deutschland"], "ES": ["espana"], "BR": ["brasil"], "IT": ["italia"], "AT": ["osterreich"],
    "CH": ["schweiz", "suisse", "svizzera"], "PL": ["polska"], "TR": ["turkiye"], "SE": ["sverige"],
    "NO": ["norge"], "DK": ["danmark"], "FI": ["suomi"], "CZ": ["czech republic", "ceska republika", "cesko"],
    "KR": ["korea", "republic of korea"], "RU": ["russian federation"], "VN": ["viet nam"],
    "AE": ["uae"], "BE": ["belgie", "belgique"], "HU": ["magyarorszag"], "GR": ["hellas"],
    "HR": ["hrvatska"], "IE": ["eire"], "JP": ["nippon", "nihon"], "PH": ["pilipinas"], "AX": ["aland"],
    "RE": ["la reunion"], "TC": ["turks and caicos"],
}
# Other names people write for a region, by the region's GeoNames name; they are read like its own names.
# (US states already carry their postal codes.) Each is checked against admin1CodesASCII when the table is built.
REGION_NAMES = {
    "CA": {"Alberta": ["ab"], "British Columbia": ["bc"], "Manitoba": ["mb"], "New Brunswick": ["nb"],
           "Newfoundland and Labrador": ["nl", "newfoundland"], "Nova Scotia": ["ns"], "Ontario": ["on"],
           "Prince Edward Island": ["pe", "pei"], "Quebec": ["qc"], "Saskatchewan": ["sk"], "Yukon": ["yt"],
           "Northwest Territories": ["nt"], "Nunavut": ["nu"]},
    "AU": {"Australian Capital Territory": ["act"], "New South Wales": ["nsw"], "Northern Territory": ["nt"],
           "Queensland": ["qld"], "South Australia": ["sa"], "Tasmania": ["tas"], "Victoria": ["vic"],
           "Western Australia": ["wa"]},
    "DE": {"Bavaria": ["bayern"], "Hesse": ["hessen"], "Lower Saxony": ["niedersachsen"],
           "North Rhine-Westphalia": ["nrw", "nordrhein westfalen"], "Saxony": ["sachsen"],
           "Saxony-Anhalt": ["sachsen anhalt"], "Thuringia": ["thuringen"]},
    "IN": {"Odisha": ["orissa"]},
    "US": {"Washington": ["washington state"], "New York": ["new york state"]},
    "NG": {"Lagos": ["lagos state"]},
    # "Distrito Federal" was Mexico City's name, is Brazil's Federal District and was Caracas's district
    "MX": {"Mexico City": ["cdmx", "distrito federal"], "Mexico": ["edomex"]},
    "BR": {"Federal District": ["distrito federal"]},
    "AR": {"Buenos Aires F.D.": ["caba", "capital federal"]},
    "CH": {"Lucerne": ["luzern"], "Grisons": ["graubunden"], "Valais": ["wallis"],
           "Ticino": ["tessin"], "Vaud": ["waadt"], "Basel-City": ["basel stadt"], "Basel-Landschaft": ["baselland"]},
    "ES": {"Andalusia": ["andalucia"], "Catalonia": ["catalunya", "cataluna"],
           "Basque Country": ["euskadi", "pais vasco"], "Castille and Leon": ["castilla y leon"],
           "Castille-La Mancha": ["castilla la mancha"], "Navarre": ["navarra"],
           "Balearic Islands": ["illes balears", "islas baleares", "baleares", "mallorca"],
           "Canary Islands": ["canarias", "islas canarias", "tenerife", "gran canaria"],
           "Valencia": ["comunitat valenciana", "comunidad valenciana"], "Madrid": ["comunidad de madrid"]},
    "IT": {"Lombardy": ["lombardia"], "Tuscany": ["toscana"], "Sicily": ["sicilia"], "Sardinia": ["sardegna"],
           "Piedmont": ["piemonte"], "Apulia": ["puglia"], "The Marches": ["marche"], "Aosta Valley": ["valle d aosta"],
           "Trentino-Alto Adige": ["trentino", "sudtirol", "south tyrol"], "Basilicate": ["basilicata"],
           "Friuli Venezia Giulia": ["friuli"]},
    "FR": {"Brittany": ["bretagne"], "Normandy": ["normandie"], "Corsica": ["corse"],
           "Provence-Alpes-Cote d'Azur": ["provence", "paca", "cote d azur"], "New Aquitaine": ["nouvelle aquitaine"],
           "Bourgogne-Franche-Comte": ["bourgogne", "burgundy"], "Grand Est": ["alsace"]},
    "PL": {"Mazovia": ["mazowieckie", "mazowsze"], "Lesser Poland": ["malopolska", "malopolskie"],
           "Silesia": ["slask", "slaskie"], "Lower Silesia": ["dolny slask", "dolnoslaskie"],
           "Greater Poland": ["wielkopolska", "wielkopolskie"], "Pomerania": ["pomorze", "pomorskie", "trojmiasto"],
           "West Pomerania": ["zachodniopomorskie"], "Lodz Voivodeship": ["lodzkie"], "Podlasie": ["podlaskie"],
           "Subcarpathia": ["podkarpacie", "podkarpackie"], "Lublin": ["lubelskie"]},
    "ID": {"West Java": ["jawa barat"], "Central Java": ["jawa tengah"], "East Java": ["jawa timur"],
           "Jakarta": ["dki jakarta"], "North Sumatra": ["sumatera utara"], "West Sumatra": ["sumatera barat"],
           "South Sumatra": ["sumatera selatan"], "North Sulawesi": ["sulawesi utara"],
           "South Sulawesi": ["sulawesi selatan"], "East Kalimantan": ["kalimantan timur"],
           "West Kalimantan": ["kalimantan barat"], "South Kalimantan": ["kalimantan selatan"]},
    # Japan's informal regions, each written for several prefectures (one zone for all)
    "JP": {"Tokyo": ["kanto"], "Kanagawa": ["kanto"], "Saitama": ["kanto"], "Chiba": ["kanto"], "Ibaraki": ["kanto"],
           "Tochigi": ["kanto"], "Gunma": ["kanto"], "Osaka": ["kansai"], "Kyoto": ["kansai"], "Hyogo": ["kansai"],
           "Nara": ["kansai"], "Shiga": ["kansai"], "Wakayama": ["kansai"], "Fukuoka": ["kyushu"], "Saga": ["kyushu"],
           "Nagasaki": ["kyushu"], "Kumamoto": ["kyushu"], "Oita": ["kyushu"], "Miyazaki": ["kyushu"],
           "Kagoshima": ["kyushu"], "Aomori": ["tohoku"], "Iwate": ["tohoku"], "Miyagi": ["tohoku"],
           "Akita": ["tohoku"], "Yamagata": ["tohoku"], "Fukushima": ["tohoku"], "Kagawa": ["shikoku"],
           "Tokushima": ["shikoku"], "Ehime": ["shikoku"], "Kochi": ["shikoku"]},
    "DK": {"Central Jutland": ["midtjylland", "jylland", "jutland"],
           "North Denmark": ["nordjylland", "jylland", "jutland"],
           "South Denmark": ["syddanmark", "jylland", "jutland"], "Zealand": ["sjaelland"],
           "Capital Region": ["hovedstaden"]},
    # Philippine provinces, which GeoNames folds into their regions (one zone for all)
    "PH": {"National Capital Region": ["metro manila"], "Calabarzon": ["cavite", "laguna", "batangas", "rizal"],
           "Central Luzon": ["pampanga", "bulacan", "bataan", "zambales", "nueva ecija"],
           "Ilocos": ["pangasinan", "la union"]},
    # English ceremonial counties people write as a place, leaving out those that are also a big town elsewhere
    "GB": {"England": ["bedfordshire", "berkshire", "buckinghamshire", "cambridgeshire", "cheshire", "cornwall",
                       "cumbria", "derbyshire", "devon", "dorset", "east sussex", "essex", "gloucestershire",
                       "hampshire", "herefordshire", "hertfordshire", "isle of wight", "kent", "lancashire",
                       "leicestershire", "lincolnshire", "merseyside", "northamptonshire",
                       "northumberland", "north yorkshire", "nottinghamshire", "oxfordshire", "rutland", "shropshire",
                       "somerset", "south yorkshire", "staffordshire", "suffolk", "sussex", "tyne and wear",
                       "warwickshire", "west midlands", "west sussex", "west yorkshire", "wiltshire",
                       "worcestershire", "yorkshire"]},
}
# The short codes people write for a region beside its city ("Pune, MH", "Curitiba - PR"). They only
# confirm a place another part names, never rule one out and never stand for a place alone, because most
# are also a country's code or an ordinary word. Swiss cantons are added from their GeoNames codes.
REGION_CODES = {
    "BR": {"Acre": ["ac"], "Alagoas": ["al"], "Amapa": ["ap"], "Amazonas": ["am"], "Bahia": ["ba"], "Ceara": ["ce"],
           "Federal District": ["df"], "Espirito Santo": ["es"], "Goias": ["go"],
           "Maranhao": ["ma"], "Mato Grosso": ["mt"], "Mato Grosso do Sul": ["ms"], "Minas Gerais": ["mg"],
           "Para": ["pa"], "Paraiba": ["pb"], "Parana": ["pr"], "Pernambuco": ["pe"], "Piaui": ["pi"],
           "Rio de Janeiro": ["rj"], "Rio Grande do Norte": ["rn"], "Rio Grande do Sul": ["rs"], "Rondonia": ["ro"],
           "Roraima": ["rr"], "Santa Catarina": ["sc"], "Sao Paulo": ["sp"], "Sergipe": ["se"], "Tocantins": ["to"]},
    "IN": {"Andhra Pradesh": ["ap"], "Arunachal Pradesh": ["ar"], "Assam": ["as"], "Bihar": ["br"],
           "Chhattisgarh": ["cg", "ct"], "Goa": ["ga"], "Gujarat": ["gj"], "Haryana": ["hr", "ncr"],
           "Himachal Pradesh": ["hp"], "Jharkhand": ["jh"], "Karnataka": ["ka"], "Kerala": ["kl"],
           "Madhya Pradesh": ["mp"], "Maharashtra": ["mh"], "Manipur": ["mn"], "Meghalaya": ["ml"], "Mizoram": ["mz"],
           "Nagaland": ["nl"], "Odisha": ["od", "or"], "Punjab": ["pb"], "Rajasthan": ["rj"], "Sikkim": ["sk"],
           "Tamil Nadu": ["tn"], "Telangana": ["tg", "ts"], "Tripura": ["tr"], "Uttar Pradesh": ["up", "ncr"],
           "Uttarakhand": ["uk", "ut"], "West Bengal": ["wb"], "Delhi": ["dl", "ncr"], "Jammu and Kashmir": ["jk"],
           "Chandigarh": ["ch"], "Puducherry": ["py"], "Ladakh": ["la"]},
    "DE": {"Baden-Wurttemberg": ["bw"], "Bavaria": ["by"], "State of Berlin": ["be"], "Brandenburg": ["bb"],
           "Bremen": ["hb"], "Hamburg": ["hh"], "Mecklenburg-Vorpommern": ["mv"], "Lower Saxony": ["ni"],
           "North Rhine-Westphalia": ["nw"], "Rheinland-Pfalz": ["rp"], "Saarland": ["sl"], "Saxony": ["sn"],
           "Saxony-Anhalt": ["st"], "Schleswig-Holstein": ["sh"], "Thuringia": ["th"]},
    "MX": {"Mexico City": ["df"], "Nuevo Leon": ["nl"], "Jalisco": ["jal"],
           "Baja California": ["bc"], "Baja California Sur": ["bcs"], "Queretaro": ["qro"], "Guanajuato": ["gto"],
           "Puebla": ["pue"], "Yucatan": ["yuc"], "Quintana Roo": ["qroo"], "Sonora": ["son"], "Chihuahua": ["chih"],
           "Coahuila": ["coah"], "Aguascalientes": ["ags"], "San Luis Potosi": ["slp"], "Veracruz": ["ver"],
           "Oaxaca": ["oax"], "Michoacan": ["mich"], "Mexico": ["mex"], "Sinaloa": ["sin"],
           "Tamaulipas": ["tamps"], "Guerrero": ["gro"], "Hidalgo": ["hgo"], "Morelos": ["mor"], "Chiapas": ["chis"],
           "Tabasco": ["tab"], "Campeche": ["camp"], "Durango": ["dgo"], "Colima": ["col"], "Nayarit": ["nay"],
           "Zacatecas": ["zac"], "Tlaxcala": ["tlax"]},
    "PH": {"National Capital Region": ["ncr"]},
    "MY": {"Kuala Lumpur": ["kl"]},
    "CN": {"Beijing": ["bj"], "Shanghai": ["sh"], "Guangdong": ["gd"], "Zhejiang": ["zj"], "Jiangsu": ["js"],
           "Tianjin": ["tj"], "Chongqing": ["cq"], "Sichuan": ["sc"]},
}
CODE_COUNTRIES = {"CH"}     # countries whose GeoNames region codes are the abbreviations people write
# A region's name without the word GeoNames adds ("Quindio Department" is written "Quindio"), added when
# no other place already has that name, and not when it is an ordinary word.
REGION_SUFFIX = re.compile(r"(?:\s+(?:Department|Province|Region|Governorate|Oblast|State|District|Prefecture|"
                           r"County|Municipality|Voivodeship|Division|Krai|Kray|Republic|region|province|oblast)"
                           r"|-(?:do|si))$")
REGION_PREFIX = re.compile(r"^(?:Region of|Province of|State of|Departamento de|Provincia de)\s+")
NOT_REGION_NAMES = {"meta", "delta", "north", "south", "east", "west", "central", "northern", "southern", "eastern",
                    "western", "capital", "national capital", "coast", "islands", "island", "city", "rivers", "cesar",
                    # words and names people write for something else ("Free", "Midlands", "Gulf", "Cascades")
                    "free", "north central", "northeastern", "southeastern", "midlands", "gulf", "cascades",
                    "northern borders", "southern highlands", "western highlands", "eastern highlands", "lacs",
                    "lagunes", "valle", "isabel", "chin", "shan", "oro", "imo", "edo", "ewa", "boe", "vas", "yap",
                    "cuando", "cortes", "herrera", "granma", "kurdistan"}
# A city whose GeoNames name ends in its kind ("Gimpo-si", "Nara-shi", "Marikina City") is also written without it.
CITY_SUFFIX = {"": re.compile(r"-(?:si|shi|gun|ku|gu)$"), "PH": re.compile(r" City$")}
# Names for a city that GeoNames does not carry, or carries only among the other names of a smaller city.
CITY_NAMES = {
    ("San Francisco", "US", "CA"): ["sf", "bay area", "sf bay area", "san francisco bay area"],
    ("Los Angeles", "US", "CA"): ["la"],
    ("San Jose", "US", "CA"): ["silicon valley"],
    ("New York City", "US", "NY"): ["nyc"],
    ("St. Louis", "US", "MO"): ["saint louis"],
    ("Sankt Gallen", "CH", "SG"): ["st gallen"],
    ("Legaspi", "PH", "05"): ["legazpi", "legazpi city"],
    ("Yogyakarta", "ID", "10"): ["jogja", "jogjakarta", "yogya"],
    ("Donostia / San Sebastián", "ES", "59"): ["donostia"],
    ("Palma", "ES", "07"): ["palma de mallorca"],
    ("Florence", "IT", "16"): ["firenze"],
    ("Padua", "IT", "20"): ["padova"],
    ("Mantua", "IT", "09"): ["mantova"],
    ("Gent", "BE", "VLG"): ["ghent"],
    ("Geneva", "CH", "GE"): ["geneve", "genf"],
    ("The Hague", "NL", "11"): ["den haag", "s gravenhage"],
    ("Tel Aviv", "IL", "05"): ["tel aviv yafo", "tel aviv jaffa"],
    ("Kitchener", "CA", "08"): ["kitchener waterloo"],
    ("Braunschweig", "DE", "06"): ["brunswick"],
    ("Castelló de la Plana", "ES", "60"): ["castellon", "castellon de la plana"],
    ("Gasteiz / Vitoria", "ES", "59"): ["vitoria gasteiz"],
    ("Venice", "IT", "20"): ["venezia"],
    ("San Carlos de Bariloche", "AR", "16"): ["bariloche"],
    ("Turku", "FI", "02"): ["abo"],
    ("Århus", "DK", "18"): ["aarhus"],
    ("Mangaluru", "IN", "19"): ["mangalore"],
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
        own.update(row)
        out.append(("C", r[0], "|".join(row)))
    admin1 = list(rows(os.path.join(folder, "admin1CodesASCII.txt")))
    cities = [r for r in rows(os.path.join(folder, "cities15000.txt")) if r[17] and r[8] in countries]
    for r in admin1:
        own.update((key(r[1]), key(r[2])))
    for r in cities:
        own.update((key(r[1]), key(r[2])))
    wanted_regions = {(cc, name): extra for cc, table in REGION_NAMES.items() for name, extra in table.items()}
    wanted_codes = {(cc, name): extra for cc, table in REGION_CODES.items() for name, extra in table.items()}
    bare_region = lambda name: key(REGION_PREFIX.sub("", REGION_SUFFIX.sub("", name)))
    stripped = {}
    for r in admin1:
        bare = bare_region(r[2])
        if bare != key(r[2]) and bare not in own and bare not in NOT_REGION_NAMES:
            stripped.setdefault(bare, []).append(r[0])
    for r in admin1:
        cc, _, code = r[0].partition(".")
        own_code = [code] if cc == "US" and code.isalpha() else []
        bare = [bare_region(r[2])] if len(stripped.get(bare_region(r[2]), ())) == 1 else []
        extra = wanted_regions.pop((cc, r[2]), [])
        row = names([r[1], r[2]], own_code, bare, extra)
        out.append(("A", cc, code, "|".join(row)))
        abbreviations = [code] if cc in CODE_COUNTRIES and code.isalpha() else []
        short = [k for k in names(abbreviations, wanted_codes.pop((cc, r[2]), [])) if k not in row]
        if short:
            out.append(("Q", cc, code, "|".join(short)))
        own.update(row + short)   # a big city's other name that is also a region's ("Kanto") is only secondary
    if wanted_regions or wanted_codes:
        raise SystemExit("regions not found for the extra names: %s"
                         % ", ".join("%s %s" % k for k in list(wanted_regions) + list(wanted_codes)))
    own.update(names(*CITY_NAMES.values()))
    wanted = dict(CITY_NAMES)
    for r in cities:
        geoname_id, name, ascii_name, other, cc, region, people, zone = r[0], r[1], r[2], r[3], r[8], r[10], r[14], r[17]
        mine = {key(name), key(ascii_name)}
        first, second = [], []
        if int(people or 0) >= OTHER_NAMES_FROM:
            for n in other.split(","):
                k = key(n)
                if len(k) >= (4 if set(k) <= LATIN else 2):
                    (first if k in mine or k not in own or k in EXONYMS else second).append(k)
        for n in (name, ascii_name):
            bare = key(CITY_SUFFIX.get(cc, CITY_SUFFIX[""]).sub("", n))
            if bare != key(n) and len(bare) >= 3:
                (second if bare in own and bare not in mine else first).append(bare)
        extra = wanted.pop((name, cc, region), [])
        primary = names([name, ascii_name], first, extra)
        secondary = [k for k in names(second) if k not in primary]
        row = ("P", geoname_id, cc, region, str(int(people or 0)), zone, "|".join(primary))
        out.append(row + ("|".join(secondary),) if secondary else row)
    if wanted:
        raise SystemExit("cities not found for the extra names: %s" % ", ".join(n for n, _, _ in wanted))
    out.sort(key=lambda row: ("CAQP".index(row[0]), row[1:]))
    header = ("# Places for coderprint: GeoNames (https://www.geonames.org) cities15000, admin1CodesASCII and "
              "countryInfo, trimmed to names, populations and time zones, names folded to plain lowercase, and a "
              "few common alternative names and abbreviations added, by tools/build_places.py. Licensed under "
              "Creative Commons Attribution 4.0, https://creativecommons.org/licenses/by/4.0/. GeoNames provides "
              "the data as is, without warranty or any representation of accuracy, timeliness or completeness.\n")
    text = header + "".join("\t".join(row) + "\n" for row in out)
    target = os.path.normpath(os.path.join(HERE, "..", "places.tsv.gz"))
    with open(target, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as f:
        f.write(text.encode("utf-8"))
    print("wrote %s: %d countries, %d regions, %d region code rows, %d cities, %d bytes"
          % (target, sum(r[0] == "C" for r in out), sum(r[0] == "A" for r in out), sum(r[0] == "Q" for r in out),
             sum(r[0] == "P" for r in out), os.path.getsize(target)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
