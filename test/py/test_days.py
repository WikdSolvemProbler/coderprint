"""Regression checks for generator/days.py (the profile's location and time zone, which fix how commits are counted
into local days), for the coderprint.py given as the only argument. Everything is called directly on small synthetic
inputs and the place table shipped beside coderprint.py; nothing is cloned and nothing reaches the network (the
profile page reader is given fake openers and fake pages). One line per check; exit 1 on any failure.

  key   place_key folds accents and letters Unicode keeps apart, and joins runs of single letters ("U.S.A.")
  tbl   load_places reads nothing from a missing or damaged table, and the table is read once
  loc   location_places on the locations its docstring names: qualifiers choose the city, codes alone never rule a
        place out, unreadable locations give nothing, two-way names give one group per reading
  rul   zone_rules and rules_id: noon offsets across DST changes, zones alike only when their clocks change at the same
        minutes (New York and Detroit alike, Athens and Beirut not, Indianapolis and New York apart), None for no zone
  off   zone_offset at the exact second of a DST change, and for half- and quarter-hour zones
  clr   clear_zone and shared_zone on synthetic places: thresholds, unknown zones, biggest place names the zone
  lz    local_zone: the shown offset always wins and only chooses among zones with that offset at now or at seen;
        summer and winter runs differ; split locations choose nothing; failures fall back to the fixed offset or UTC
  db    zone_database
  gh    GitHubOnly follows a redirect only to https://github.com
  pg    profile_page keeps a page only from https github.com, within PROFILE_LIMIT and before the deadline
  po    profile_offset reads data-hours-ahead-of-utc: one agreed value in range and on a quarter hour, else None
  pl    profile_location keeps a string location, cut at LOCATION_LIMIT, and "" for anything else
"""
import datetime as dt
import gzip
import importlib.util
import os
import sys
import tempfile
import time
import urllib.request

SRC = os.path.abspath(sys.argv[1])
spec = importlib.util.spec_from_file_location("cp_under_test", SRC)
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

fails, passes = [], 0


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(name)
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  %s" % (detail,)), flush=True)


def utc(*args):
    return dt.datetime(*args, tzinfo=dt.timezone.utc).timestamp()


def zone_name(z):
    return getattr(z, "key", None) or str(z)


SUMMER, WINTER = utc(2024, 7, 1, 12), utc(2024, 1, 15, 12)

# ---------------------------------------------------------------- place_key
for text, want in [("São Paulo", "sao paulo"), ("sao   PAULO", "sao paulo"), ("D.C.", "dc"), ("U.S.A.", "usa"),
                   ("Washington, D.C.", "washington dc"), ("a b cd e", "ab cd e"), ("København", "kobenhavn"),
                   ("Łódź", "lodz"), ("Ærø", "aero"), ("St. John's", "st john s"), ("", ""), ("—", ""),
                   ("x 1 y", "x 1 y")]:
    got = cp.place_key(text)
    check("key  %r -> %r" % (text, want), got == want, got)

# ---------------------------------------------------------------- load_places
real_file, real_places = cp.PLACES_FILE, cp._places
tmp = tempfile.mkdtemp(prefix="days-")
try:
    for label, setup in [("missing", None), ("not gzip", b"C\tDE\tgermany\n"), ("truncated gzip", "trunc")]:
        path = os.path.join(tmp, label.replace(" ", "_") + ".gz")
        if setup == "trunc":
            data = gzip.compress(b"C\tDE\tgermany\n" * 1000)
            setup = data[:len(data) // 2]
        if setup is not None:
            with open(path, "wb") as f:
                f.write(setup)
        cp.PLACES_FILE, cp._places = path, None
        table = cp.load_places()
        check("tbl  a %s table is empty" % label, table == ({},) * 7, [len(t) for t in table])
        check("tbl  a %s table recognises no location" % label, cp.location_places("Paris, France") == [])
    path = os.path.join(tmp, "bad_number.gz")
    with open(path, "wb") as f:
        f.write(gzip.compress(b"C\tFR\tfrance\nP\tnot-a-number\tFR\t11\t100\tEurope/Paris\tparis\n"))
    cp.PLACES_FILE, cp._places = path, None
    check("tbl  a row with a bad number empties the whole table", cp.load_places() == ({},) * 7)
    path = os.path.join(tmp, "tiny.gz")
    with open(path, "wb") as f:
        f.write(gzip.compress("C\tFR\tfrance|fr\nA\tFR\t11\tile de france|idf\nQ\tFR\t11\tidf\n"
                              "P\t7\tFR\t11\t2000000\tEurope/Paris\tparis\tlutece\nbogus line\n"
                              "P\t8\tUS\tTX\t25000\tAmerica/Chicago\tparis\n".encode()))
    cp.PLACES_FILE, cp._places = path, None
    countries, regions, cities, in_country, in_region, codes, also = cp.load_places()
    check("tbl  countries by every key", countries == {"france": {"FR"}, "fr": {"FR"}}, countries)
    check("tbl  regions and codes", regions == {"ile de france": {("FR", "11")}, "idf": {("FR", "11")}}
          and codes == {"idf": {("FR", "11")}}, (regions, codes))
    check("tbl  cities by name, other names apart",
          [p.id for p in cities["paris"]] == [7, 8] and [p.id for p in also["lutece"]] == [7]
          and cities["paris"][1] == cp.Place(8, "US", "TX", 25000, "America/Chicago"), (cities, also))
    check("tbl  cities by country and by region", sorted(in_country) == ["FR", "US"]
          and [p.id for p in in_region[("FR", "11")]] == [7], (in_country, in_region))
    check("tbl  read once", cp.load_places() is cp.load_places())
finally:
    cp.PLACES_FILE, cp._places = real_file, real_places


# ---------------------------------------------------------------- location_places
def zones(location):
    return [cp.clear_zone(g) for g in cp.location_places(location)]


def shape(location):
    return [len(g) for g in cp.location_places(location)]


cases = [
    # qualifiers choose the city
    ("Santa Clara, CA", ["America/Los_Angeles"]), ("Toronto, CA", ["America/Toronto"]),
    ("Kent, Washington", ["America/Los_Angeles"]), ("LA, CA", ["America/Los_Angeles"]),
    ("Santa Cruz, Bolivia", ["America/La_Paz"]), ("Armenia, Quindio", ["America/Bogota"]),
    ("Mumbai, MH", ["Asia/Kolkata"]), ("Delhi NCR", ["Asia/Kolkata"]),
    # words around a name, and joiners
    ("Based in Nairobi", ["Africa/Nairobi"]), ("Oslo area", ["Europe/Oslo"]), ("he/him, Paris", ["Europe/Paris"]),
    ("Trinidad & Tobago", ["America/Port_of_Spain"]), ("St Kitts & Nevis", ["America/St_Kitts"]),
    ("Raleigh-Durham", ["America/New_York"]), ("Paris AI", ["Europe/Paris"]),
    # several places
    ("Istanbul, Berlin", ["Europe/Istanbul", "Europe/Berlin"]), ("Tokyo, Seoul", ["Asia/Tokyo", "Asia/Seoul"]),
    ("Tokyo & Seoul", ["Asia/Tokyo", "Asia/Seoul"]), ("SF / Berlin", ["America/Los_Angeles", "Europe/Berlin"]),
    ("SF / NYC", ["America/Los_Angeles", "America/New_York"]),
    # regions and countries
    ("Wyoming", ["America/Denver"]), ("Jackson, Wyoming", ["America/Denver"]), ("Ontario", ["America/Toronto"]),
    ("Manchester", ["Europe/London"]), ("Germany", ["Europe/Berlin"]), ("Kent, UK", ["Europe/London"]),
    ("DEU", ["Europe/Berlin"]), ("Georgia", [None]),
    # two readings in two zones
    ("Punjab", ["Asia/Kolkata", "Asia/Karachi"]), ("Washington", ["America/New_York", "America/Los_Angeles"]),
    # nothing read with confidence
    ("Cape Town, SA", []), ("Berlin, NH", []), ("Monza, MB", []), ("Berlin / India", []), ("Bormio (SO)", []),
    ("Bunnik, UT", []), ("Kent, WA 98032", []), ("London / Toronto, Canada", []), ("Greater Washington", []),
    ("EST", []), ("N.A.", []), ("Mac", []), ("Tambaú, PB", []), ("Remote", []), ("Asia", []), ("NCR", []),
    # a country's code that is also a region's, beside a word nothing knows, is read with the rest
    ("Xyzzy, CO, Colombia", ["America/Bogota"]), ("Xyzzy, CO, USA", ["America/Denver"]),
    ("Xyzzy, PE, Peru", ["America/Lima"]), ("Xyzzy, CA, Canada", [None]),
    ("Washington, Oregon", []), ("Xyzzy, US", []), ("Xyzzy, DE", []), ("", []),
]
for location, want in cases:
    got = zones(location)
    check("loc  %r -> %s" % (location, want), got == want, got)
check("loc  'Kent, UK' is every Kent in the UK", shape("Kent, UK") == [747] or shape("Kent, UK")[0] > 1,
      shape("Kent, UK"))
check("loc  a country alone stands for its cities", shape("Germany")[0] > 100, shape("Germany"))
check("loc  'USA' spans zones, so no clear zone", zones("USA") == [None] and shape("USA")[0] > 1000)
check("loc  a lone 3-letter code counts in capitals only", zones("deu") == [] and zones("DEU") == ["Europe/Berlin"])
check("loc  'usa' in any case", zones("usa") == [None])
check("loc  a lone time of day is nothing", zones("PM") == [] and zones("UTC") == [])
check("loc  a location is read only to LOCATION_LIMIT", zones("x" * cp.LOCATION_LIMIT + ", Paris") == [])
check("loc  a repeated place is one group", zones("Paris / Paris") == ["Europe/Paris"])
check("loc  a country and its capital: the capital is dropped", zones("Berlin, Germany") == ["Europe/Berlin"]
      and shape("Berlin, Germany") == shape("Berlin"), shape("Berlin, Germany"))
parts = cp.location_parts("Greater London; Oslo & Lima", *cp.load_places()[:3], cp.load_places()[5], notes := {})
check("loc  location_parts: segments and areas", parts == ["london", "oslo", "lima"]
      and notes["area"] == {"london"} and notes["segment"] == {"london": {0}, "oslo": {1}, "lima": {2}},
      (parts, notes))
parts = cp.location_parts("Berlin, New Hampshire / AI", *cp.load_places()[:3], cp.load_places()[5], notes := {})
check("loc  location_parts: commas qualify, slashes part, tags beside a place go", parts == ["berlin", "new hampshire"]
      and notes["segment"]["berlin"] == notes["segment"]["new hampshire"] == {0}, (parts, notes))

# ---------------------------------------------------------------- zone_rules, rules_id
first = cp.RULES_DAYS[0]


def noon(zone, y, m, d):
    return cp.zone_rules(zone)[dt.date(y, m, d).toordinal() - first]


ny = cp.zone_rules("America/New_York")
check("rul  one offset per day of RULES_DAYS", len(ny) == cp.RULES_DAYS[1] - first, len(ny))
check("rul  UTC is 0 every day", set(cp.zone_rules("UTC")) == {0})
check("rul  New York winter and summer", noon("America/New_York", 2020, 1, 1) == -300
      and noon("America/New_York", 2020, 7, 1) == -240)
# 2020-03-08: clocks went forward at 07:00 UTC, so noon UTC that day is already summer time
check("rul  New York around its spring change", [noon("America/New_York", 2020, 3, d) for d in (7, 8, 9)]
      == [-300, -240, -240])
# 2020-11-01: back at 06:00 UTC, so noon UTC that day is winter time
check("rul  New York around its autumn change", [noon("America/New_York", 2020, 10, 31), noon("America/New_York",
                                                  2020, 11, 1)] == [-240, -300])
check("rul  London around its change (01:00 UTC)", [noon("Europe/London", 2021, 3, d) for d in (27, 28)] == [0, 60])
check("rul  Sydney, southern summer", noon("Australia/Sydney", 2021, 1, 1) == 660
      and noon("Australia/Sydney", 2021, 7, 1) == 600)
check("rul  Lord Howe's half-hour change", noon("Australia/Lord_Howe", 2021, 1, 1) == 660
      and noon("Australia/Lord_Howe", 2021, 7, 1) == 630)
check("rul  Kathmandu", set(cp.zone_rules("Asia/Kathmandu")) == {345})
check("rul  Samoa skipped 2011-12-30", noon("Pacific/Apia", 2011, 12, 29) == -600
      and noon("Pacific/Apia", 2011, 12, 31) == 840, (noon("Pacific/Apia", 2011, 12, 29),
                                                       noon("Pacific/Apia", 2011, 12, 31)))
check("rul  no rules for an unknown zone", cp.zone_rules("Not/AZone") is None and cp.rules_id("Not/AZone") is None)
check("rul  no rules for a malformed zone", cp.rules_id("../etc") is None and cp.rules_id("") is None)
check("rul  New York and Detroit count days alike", cp.rules_id("America/New_York") == cp.rules_id("America/Detroit"))
check("rul  Indianapolis parted from New York before 2006",
      cp.rules_id("America/Indiana/Indianapolis") != cp.rules_id("America/New_York"))
check("rul  Athens and Beirut: same noons, different minutes",
      cp.rules_id("Europe/Athens") != cp.rules_id("Asia/Beirut"))
check("rul  New York and Toronto alike, Phoenix and Denver not",
      cp.rules_id("America/Toronto") == cp.rules_id("America/New_York")
      and cp.rules_id("America/Phoenix") != cp.rules_id("America/Denver"))
check("rul  rules_id is a small int, stable", isinstance(cp.rules_id("Asia/Tokyo"), int)
      and cp.rules_id("Asia/Tokyo") == cp.rules_id("Asia/Tokyo") == cp.rules_id("Asia/Seoul"))

# ---------------------------------------------------------------- zone_offset
change = utc(2021, 3, 14, 7)   # New York springs forward at 07:00 UTC
check("off  the second before a spring change", cp.zone_offset("America/New_York", change - 1) == -300)
check("off  the second of a spring change", cp.zone_offset("America/New_York", change) == -240)
back = utc(2021, 11, 7, 6)     # and falls back at 06:00 UTC
check("off  around an autumn change", (cp.zone_offset("America/New_York", back - 1),
                                       cp.zone_offset("America/New_York", back)) == (-240, -300))
check("off  half and quarter hours", (cp.zone_offset("Asia/Kolkata", SUMMER), cp.zone_offset("Asia/Kathmandu", SUMMER),
                                      cp.zone_offset("America/St_Johns", WINTER)) == (330, 345, -210))
check("off  the far east", cp.zone_offset("Pacific/Kiritimati", SUMMER) == 840)
check("off  the epoch west of UTC", cp.zone_offset("America/Los_Angeles", 0) == -480)

# ---------------------------------------------------------------- clear_zone, shared_zone
P = cp.Place
NY, DET, LA, CHI = "America/New_York", "America/Detroit", "America/Los_Angeles", "America/Chicago"
check("clr  no places, no zone", cp.clear_zone([]) is None)
check("clr  only unknown zones, no zone", cp.clear_zone([P(1, "XX", "", 10, "Not/AZone")]) is None)
check("clr  one place", cp.clear_zone([P(1, "US", "NY", 10, NY)]) == NY)
check("clr  exactly CLEAR_SHARE is clear", cp.clear_zone([P(1, "US", "", 75, NY), P(2, "US", "", 25, LA)]) == NY)
check("clr  under CLEAR_SHARE is not", cp.clear_zone([P(1, "US", "", 74, NY), P(2, "US", "", 26, LA)]) is None)
check("clr  zones alike pool, named by the biggest place",
      cp.clear_zone([P(1, "US", "", 40, NY), P(2, "US", "", 45, DET), P(3, "US", "", 15, LA)]) == DET)
check("clr  people count at least 1 each", cp.clear_zone([P(1, "US", "", 0, NY)] * 3 + [P(2, "US", "", 0, LA)]) == NY)
check("clr  unknown zones are not counted",
      cp.clear_zone([P(1, "US", "", 10, NY), P(2, "XX", "", 1000, "Not/AZone")]) == NY)
check("clr  equal people: the zone named sorts last", cp.clear_zone([P(1, "US", "", 5, NY), P(2, "US", "", 5, DET)])
      == NY)
cam = [P(1, "US", "MA", 100, NY), P(2, "GB", "ENG", 120, "Europe/London")]
bos = [P(3, "US", "MA", 600, NY)]
check("shz  'Cambridge / Boston' shares Boston's zone", cp.shared_zone([cam, bos]) == NY)
check("shz  under JOINT_SHARE of one group is not shared",
      cp.shared_zone([[P(1, "US", "", 24, NY), P(2, "GB", "", 76, "Europe/London")], bos]) is None)
check("shz  exactly JOINT_SHARE is shared",
      cp.shared_zone([[P(1, "US", "", 25, NY), P(2, "GB", "", 75, "Europe/London")], bos]) == NY)
check("shz  two zones in common is none", cp.shared_zone([cam, cam]) is None)
check("shz  nothing in common is none", cp.shared_zone([[P(1, "US", "", 1, NY)], [P(2, "US", "", 1, LA)]]) is None)
check("shz  zones alike are one, named by the biggest place",
      cp.shared_zone([[P(1, "US", "", 10, NY)], [P(2, "US", "", 50, DET)]]) == DET)
check("shz  no groups, no zone", cp.shared_zone([]) is None)

# ---------------------------------------------------------------- local_zone
for args, want in [
    ((None, "", SUMMER), "UTC"), ((-420, "", SUMMER), "UTC-07:00"), ((330, "", SUMMER), "UTC+05:30"),
    ((None, "Paris, France", SUMMER), "Europe/Paris"), ((60, "Paris, France", WINTER), "Europe/Paris"),
    ((120, "Paris, France", SUMMER), "Europe/Paris"), ((120, "Paris, France", WINTER), "UTC+02:00"),
    ((-420, "USA", SUMMER), "America/Los_Angeles"), ((-420, "USA", WINTER), "UTC-07:00"),
    ((-360, "USA", WINTER), "America/Chicago"), ((-300, "USA", WINTER), "America/New_York"),
    ((-420, "USA", WINTER, SUMMER), "UTC-07:00"), ((-480, "USA", WINTER, SUMMER), "America/Los_Angeles"),
    ((None, "SF / NYC", SUMMER), "UTC"), ((-420, "SF / NYC", SUMMER), "America/Los_Angeles"),
    ((-240, "SF / NYC", SUMMER), "America/New_York"), ((60, "SF / NYC", WINTER), "UTC+01:00"),
    ((None, "Cambridge / Boston", SUMMER), "America/New_York"),
    ((None, "Washington", SUMMER), "UTC"), ((-240, "Washington", SUMMER), "America/New_York"),
    ((-420, "Washington", SUMMER), "America/Los_Angeles"), ((330, "Punjab", SUMMER), "Asia/Kolkata"),
    ((300, "Punjab", SUMMER), "Asia/Karachi"), ((240, "Georgia", SUMMER), "Asia/Tbilisi"),
    ((-240, "Georgia", SUMMER), "America/New_York"), ((None, "Georgia", SUMMER), "UTC"),
    ((None, "Remote", SUMMER), "UTC"), ((None, "Istanbul, Berlin", SUMMER), "UTC"),
]:
    got = zone_name(cp.local_zone(*args))
    check("lz   local_zone%r -> %s" % (args[:2] + (("summer" if args[2] == SUMMER else "winter"),)
                                       + tuple("seen" for _ in args[3:]), want), got == want, got)
# the shown offset fixes past days' daylight saving through the chosen zone
paris = cp.local_zone(60, "Paris, France", WINTER)
check("lz   the chosen zone keeps summer time for past days",
      dt.datetime.fromtimestamp(SUMMER, paris).utcoffset() == dt.timedelta(hours=2))
fixed = cp.local_zone(60, "", WINTER)
check("lz   a fixed offset ignores summer time", dt.datetime.fromtimestamp(SUMMER, fixed).utcoffset()
      == dt.timedelta(hours=1))
# a day boundary: 23:30 UTC on 2024-07-01 is already 2 July in Paris, 1 July at the fixed winter offset +01:00
late = utc(2024, 7, 1, 23, 30)
check("lz   day bucketing at midnight differs by zone", (dt.datetime.fromtimestamp(late, paris).date(),
      dt.datetime.fromtimestamp(late, fixed).date()) == (dt.date(2024, 7, 2), dt.date(2024, 7, 2))
      and dt.datetime.fromtimestamp(utc(2024, 7, 1, 22, 30), paris).date() == dt.date(2024, 7, 2)
      and dt.datetime.fromtimestamp(utc(2024, 7, 1, 22, 30), fixed).date() == dt.date(2024, 7, 1))
real = cp.location_places


def broken(location):
    raise ValueError("boom")


cp.location_places = broken
try:
    check("lz   a failure in the location falls back to the offset", zone_name(cp.local_zone(-300, "x", SUMMER))
          == "UTC-05:00")
    check("lz   a failure in the location with no offset is UTC", zone_name(cp.local_zone(None, "x", SUMMER)) == "UTC")
finally:
    cp.location_places = real

# ---------------------------------------------------------------- zone_database
check("db   this Python has zone rules", cp.zone_database() is True)
real_zi = cp.zoneinfo


class NoRules:
    @staticmethod
    def ZoneInfo(name):
        raise real_zi.ZoneInfoNotFoundError(name)


cp.zoneinfo = NoRules
try:
    check("db   no rules is False", cp.zone_database() is False)
finally:
    cp.zoneinfo = real_zi

# ---------------------------------------------------------------- GitHubOnly
handler = cp.GitHubOnly()
req = urllib.request.Request("https://github.com/someone")
for url, follows in [("https://github.com/other", True), ("http://github.com/other", False),
                     ("https://gist.github.com/x", False), ("https://evil.example/github.com", False),
                     ("https://github.com.evil.example/", False), ("ftp://github.com/x", False)]:
    got = handler.redirect_request(req, None, 302, "Found", {}, url)
    ok = (got is not None and got.full_url == url) if follows else got is None
    check("gh   redirect to %s %s" % (url, "followed" if follows else "refused"), ok, got)


# ---------------------------------------------------------------- profile_page
class FakePage:
    def __init__(self, url, chunks, delay=0.0):
        self.url, self.chunks, self.delay, self.fp = url, list(chunks), delay, None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def geturl(self):
        return self.url

    def read1(self, n):
        time.sleep(self.delay)
        return self.chunks.pop(0) if self.chunks else b""


def with_opener(page, deadline_in=5.0, limit=None):
    real_build, real_limit = urllib.request.build_opener, cp.PROFILE_LIMIT
    seen = {}

    class Opener:
        def open(self, request, timeout=None):
            seen["url"], seen["agent"] = request.full_url, request.get_header("User-agent")
            if isinstance(page, Exception):
                raise page
            return page

    urllib.request.build_opener = lambda *handlers: seen.setdefault("handlers", handlers) and Opener()
    if limit is not None:
        cp.PROFILE_LIMIT = limit
    into = []
    try:
        cp.profile_page("someone", time.monotonic() + deadline_in, into)
    finally:
        urllib.request.build_opener, cp.PROFILE_LIMIT = real_build, real_limit
    return into, seen


into, seen = with_opener(FakePage("https://github.com/someone", [b"<html>", b"body</html>"]))
check("pg   a page is read whole", len(into) == 1 and into[0][0] == b"<html>body</html>"
      and abs(into[0][1] - time.time()) < 5, into)
check("pg   asks https://github.com/<owner> as coderprint, redirects through GitHubOnly",
      seen.get("url") == "https://github.com/someone" and seen.get("agent") == "coderprint"
      and seen.get("handlers") == (cp.GitHubOnly,), seen)
check("pg   a page ending elsewhere is not kept",
      with_opener(FakePage("https://example.com/someone", [b"x"]))[0] == [])
check("pg   a page over http is not kept", with_opener(FakePage("http://github.com/someone", [b"x"]))[0] == [])
check("pg   a page over PROFILE_LIMIT is not kept",
      with_opener(FakePage("https://github.com/someone", [b"x" * 6, b"y" * 6]), limit=10)[0] == [])
check("pg   a page of exactly PROFILE_LIMIT is kept",
      with_opener(FakePage("https://github.com/someone", [b"x" * 5, b"y" * 5]), limit=10)[0][0][0] == b"x" * 5 + b"y" * 5)
check("pg   a page past its deadline is not kept",
      with_opener(FakePage("https://github.com/someone", [b"a", b"b", b"c"], delay=0.15), deadline_in=0.2)[0] == [])
check("pg   a deadline already past reads nothing",
      with_opener(FakePage("https://github.com/someone", [b"a"]), deadline_in=-1)[0] == [])
check("pg   a failure to open is a page not read", with_opener(OSError("refused"))[0] == [])


# ---------------------------------------------------------------- profile_offset
def offset_of(body, owner="someone"):
    real_page = cp.profile_page
    cp.profile_page = lambda o, deadline, into: body is not None and into.append((body, 1234.5))
    try:
        return cp.profile_offset(owner)
    finally:
        cp.profile_page = real_page


tz = b'<profile-timezone class="x" data-hours-ahead-of-utc="%s">'
for value, want in [(b"5.5", 330), (b"-7", -420), (b"-7.0", -420), (b"+1", 60), (b"0", 0), (b"5.75", 345),
                    (b"14", 840), (b"-12", -720), (b"-3.5", -210), (b"14.25", None), (b"-12.25", None),
                    (b"5.1", None), (b"5.12345", None), (b"100", None), (b"", None), (b"abc", None),
                    (b"1e1", None)]:
    got = offset_of(b"<html>" + tz % value + b"</profile-timezone></html>")
    check("po   data-hours-ahead-of-utc=%r -> %s" % (value.decode(), want),
          got == ((want, 1234.5) if want is not None else None), got)
check("po   no element, no offset", offset_of(b"<html><p>hi</p></html>") is None)
check("po   the page not read, no offset", offset_of(None) is None)
check("po   two agreeing elements", offset_of(tz % b"2" + b"..." + tz % b"2.0") == (120, 1234.5))
check("po   two differing elements, no offset", offset_of(tz % b"2" + tz % b"3") is None)
check("po   a bad element beside a good one, no offset", offset_of(tz % b"2" + tz % b"x") is None)
check("po   an element without the attribute is skipped",
      offset_of(b"<profile-timezone>" + tz % b"-5") == (-300, 1234.5))
check("po   the tooltip element is not read",
      offset_of(b'<profile-timezone-tooltip data-hours-ahead-of-utc="9">' + tz % b"1") == (60, 1234.5))
check("po   the attribute outside the tag is not read",
      offset_of(b'<profile-timezone> data-hours-ahead-of-utc="9"') is None)
check("po   a self-closing tag", offset_of(b'<profile-timezone\ndata-hours-ahead-of-utc="3"/>') == (180, 1234.5))
check("po   a tag left open reaches 2048 bytes at most",
      offset_of(b'<profile-timezone ' + b" " * 2100 + b'data-hours-ahead-of-utc="3">') is None)
check("po   a tag left open goes on from the next tag",
      offset_of(b'<profile-timezone data-hours-ahead-of-utc="4" ' + b"x" * 100 + tz % b"4" + b"z" * 3000)
      == (240, 1234.5))
check("po   an attribute name must stand alone",
      offset_of(b'<profile-timezone xdata-hours-ahead-of-utc="4">') is None)
for owner in ["", None, "a" * 40, "bad/owner", "a b", "../x", "ok\n"]:
    called = []
    real_page = cp.profile_page
    cp.profile_page = lambda o, d, into: called.append(o)
    try:
        got = cp.profile_offset(owner)
    finally:
        cp.profile_page = real_page
    check("po   owner %r is not looked up" % (owner,), got is None and called == [], (got, called))
check("po   a 39-character owner is", offset_of(tz % b"1", "a" * 39) == (60, 1234.5))

# ---------------------------------------------------------------- profile_location
real_gql = cp.gql


def location_of(answer):
    def fake(query, **kw):
        if isinstance(answer, Exception):
            raise answer
        return answer
    cp.gql = fake
    try:
        return cp.profile_location("someone")
    finally:
        cp.gql = real_gql


for answer, want in [({"repositoryOwner": {"location": "Paris"}}, "Paris"),
                     ({"repositoryOwner": {"location": "x" * 300}}, "x" * cp.LOCATION_LIMIT),
                     ({"repositoryOwner": {"location": None}}, ""), ({"repositoryOwner": None}, ""),
                     ({"repositoryOwner": {"location": 7}}, ""), ({}, ""), ([], ""), (None, ""),
                     (RuntimeError("down"), ""), (ValueError("bad json"), "")]:
    got = location_of(answer)
    check("pl   %s -> %r" % (type(answer).__name__ if isinstance(answer, Exception) else repr(answer)[:40],
                             want[:12]), got == want, got)

print("%d passed, %d failed%s" % (passes, len(fails), (": " + ", ".join(fails)) if fails else ""))
sys.exit(1 if fails else 0)
