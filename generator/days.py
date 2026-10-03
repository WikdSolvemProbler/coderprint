# coderprint's local days: the profile's location and time zone. coderprint.py runs this file as part of one module,
# after the parts before it in PARTS, so it uses their names freely; it is not imported on its own.


# ---------------------------------------------------------------- days


def place_key(text):
    """A place name as the place table stores it: accents dropped, case folded, anything but letters and digits
    turned into single spaces, and a run of single letters joined, so "São Paulo" and "sao paulo" are one name
    and "D.C." is "dc", as "U.S.A." is "usa"."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold().translate(FOLD_LETTERS)
    words, run = [], ""
    for word in "".join(ch if ch.isalnum() else " " for ch in text).split():
        if len(word) == 1 and word.isalpha():
            run += word
            continue
        if run:
            words.append(run)
            run = ""
        words.append(word)
    return " ".join(words + [run] if run else words)


_places = None


def load_places():
    """The place table: which countries, regions and cities each name can mean, which regions each short code
    confirms, which cities each name can mean only when the rest of the location points at them, and every city
    by country and by region. Read once; if the file is missing or damaged the table is empty, so no location is
    recognised and days stay as they would be without one."""
    global _places
    if _places is None:
        countries, regions, cities, in_country, in_region, codes, also = {}, {}, {}, {}, {}, {}, {}
        try:
            with gzip.open(PLACES_FILE, "rt", encoding="utf-8") as f:
                for line in f:
                    row = line.rstrip("\n").split("\t")
                    if row[0] == "C" and len(row) == 3:
                        for key in row[2].split("|"):
                            countries.setdefault(key, set()).add(row[1])
                    elif row[0] in ("A", "Q") and len(row) == 4:
                        for key in row[3].split("|"):
                            (regions if row[0] == "A" else codes).setdefault(key, set()).add((row[1], row[2]))
                    elif row[0] == "P" and len(row) in (7, 8):
                        place = Place(int(row[1]), row[2], row[3], int(row[4]), row[5])
                        for key in row[6].split("|"):
                            cities.setdefault(key, []).append(place)
                        for key in row[7].split("|") if len(row) == 8 else ():
                            also.setdefault(key, []).append(place)
                        in_country.setdefault(place.country, []).append(place)
                        in_region.setdefault((place.country, place.region), []).append(place)
        except (OSError, EOFError, ValueError, zlib.error):
            countries, regions, cities, in_country, in_region, codes, also = {}, {}, {}, {}, {}, {}, {}
        _places = (countries, regions, cities, in_country, in_region, codes, also)
    return _places


def location_parts(location, countries, regions, cities, codes=(), notes=None):
    """A location's parts as place keys, in order and each once. A part the table does not know as written is
    read without words around a name ("Greater London", "Based in Nairobi", "Oslo area"), split where a known
    city meets a country, region or region code ("Santa Clara CA", "Delhi NCR"), or split where it joins two
    places ("Tokyo & Seoul", "Raleigh-Durham"). Pronouns ("he/him"), words that towns happen to share but
    profiles use for something else ("Asia", "North", "Spring"), "AI" and "ML" beside a place, and words like
    "Remote" that name no place are dropped. If notes is a dict, notes["area"] gets the parts found only by
    dropping words that mark a city's surroundings ("Greater Washington"), and notes["segment"] the places each
    part belongs to, numbered: parts joined by commas or brackets are one place and what qualifies it ("Berlin,
    New Hampshire"), while a slash, bar, dash, line or "&" starts another ("SF / Berlin")."""
    known = lambda k: k in cities or k in countries or k in regions or k in codes
    area = set()

    def read(text, depth=0):   # the places a part names, each as a list of keys
        key = place_key(text)
        if not key or key in NOT_PLACES or known(key):
            return [[key]] if key else []
        for form in (key, place_key(text.replace("&", " and "))):   # "Trinidad & Tobago", "St Kitts & Nevis"
            for name in (form, re.sub(r"^st ", "saint ", form), re.sub(r"^saint ", "st ", form)):
                if known(name):
                    return [[name]]
        bare, dropped = key, False
        while not known(bare) and bare not in NOT_PLACES:
            lead = next((w for w in LEAD_WORDS if bare.startswith(w + " ")), None)
            trail = None if lead else next((w for w in TRAIL_WORDS if bare.endswith(" " + w)), None)
            if not lead and not trail:
                break
            dropped = dropped or (lead or trail) in AREA_WORDS
            bare = bare[len(lead) + 1:] if lead else bare[:-len(trail) - 1]
        if known(bare) or bare in NOT_PLACES:
            if dropped:
                area.add(bare)
            return [[bare]]
        words = bare.split()
        for k in (1, 2):
            head, tail = " ".join(words[:-k]), " ".join(words[-k:])
            if head in cities and (tail in countries or tail in regions or tail in codes):
                return [[head, tail]]
        pieces = [p for p in re.split(JOINERS, text) if p.strip()]
        if len(pieces) < 2:   # "Raleigh-Durham": a hyphen joins two places only when both are known
            pieces = [p for p in text.split("-") if p.strip()]
            pieces = pieces if all(known(place_key(p)) for p in pieces) else []
        if len(pieces) > 1 and depth == 0:
            return [place for p in pieces for place in read(p, 1)]
        return [[key]]

    bits = re.split("(%s)" % PART_SPLIT, re.sub(PRONOUNS, ",", location[:LOCATION_LIMIT]))
    parts, where, place = [], {}, 0
    for n in range(0, len(bits), 2):
        place += bool(n and re.search(SEGMENT_SPLIT, bits[n - 1]))
        for k, keys in enumerate(read(bits[n])):
            place += k > 0
            for key in keys:
                parts.append(key)
                where.setdefault(key, set()).add(place)
    parts = [p for p in dict.fromkeys(parts) if p not in NOT_PLACES]
    parts = [p for p in parts if p not in TAGS] if len(parts) > 1 else parts
    if notes is not None:
        notes["area"], notes["segment"] = area, where
    return [p for p in parts if p not in FILLER]


def location_places(location):
    """The places a profile's location names, as one group of candidate cities per place named.

    Every city in a group agrees with each other part of the location that names a country or region, so
    "Santa Clara, CA" is the one in California and "Toronto, CA" the one in Canada. A region code that is
    only a local abbreviation ("MH", "NCR", "SG" for St. Gallen) confirms a place but never rules one out,
    and alone names nothing. Parts that only name a city come first. If the other parts rule out every town
    of such a part: when one of them is itself a town ("Istanbul, Berlin") each town part is a group of its
    own; when one is a code ("Cape Town, SA", "Berlin, NH", "Monza, MB") the location is not understood and
    nothing is returned; when they are names written with the city ("Kent, UK", "Jackson, Wyoming") the city
    part is dropped and the rest is read, but not when they are another place ("Berlin / India"). A name
    counts as a town here unless it names a region that holds none of its towns and more people than they
    do ("Wyoming", "Ontario"). A city's other names that are some other place's own name ("Santa Cruz" for
    Santa Cruz de la Sierra) count only when the rest of the location points at it ("Santa Cruz, Bolivia").
    Otherwise a named region competes with towns of its name when it holds more people than they do
    ("Ontario" is the province, "Manchester" the city), a region and a country of one name compete
    ("Georgia"), and a country named alone stands for all its cities.

    Nothing is returned for what cannot be read with confidence: a code beside a word nothing knows ("Bormio
    (SO)", "Bunnik, UT", "Estes Park, CO"), since most short codes are some other country's too; a postal code
    the table cannot place ("Kent, WA 98032"); a clear city that another place's qualifier would move
    ("London / Toronto, Canada"); a region found only by dropping words that mark a city's surroundings
    ("Greater Washington"); a time of day, a time zone ("EST") or a dotted code ("N.A.") written alone; and a
    three-letter country code written alone unless in capitals ("DEU", not "Mac"). A name read two ways in
    different zones, as regions of two countries ("Punjab") or a region and a big city of the name
    ("Washington"), is one group per reading, which a shown time zone can choose between. A local abbreviation
    that names regions of a city's own country but none holding it ("Tambaú, PB") leaves that city out. A group
    that holds another group's places, as a country holds its capital, and a repeated group are dropped."""
    countries, regions, cities, in_country, in_region, codes, also = load_places()
    notes = {}
    parts = location_parts(location, countries, regions, cities, codes, notes)
    where = notes["segment"]

    def known(p):
        return p in cities or p in countries or p in regions or p in codes

    def nations(p):
        return countries.get(p, ())

    def named(p):   # names a country or region, and so rules out places elsewhere
        return p in countries or p in regions

    def is_code(p):   # a country's or region's code, as against a name ("UK", "England")
        up = p.upper()
        return (up in countries.get(p, ()) or (len(p) == 3 and p not in KEEP_CODES and p in countries)
                or any(code == up for _, code in regions.get(p, ())))

    def code(p):   # any short code: a country's or region's, a region's two-letter abbreviation, a local one
        return (p in codes and not named(p)) or (len(p) <= 3 and is_code(p)) or (len(p) == 2 and p in regions)

    def people(places):
        return sum(max(pl.people, 1) for pl in places)

    def outweighed(p):   # names a region that holds none of its towns and more people than they do ("Wyoming")
        towns = cities.get(p, ())
        return any(not any((t.country, t.region) == key for t in towns)
                   and people(in_region.get(key, ())) > people(towns) for key in sorted(regions.get(p, ())))

    parts = [p for p in parts if p not in notes["area"] or not outweighed(p)]
    lone = len(parts) == 1
    raw = [s for s in re.split(PART_SPLIT, location[:LOCATION_LIMIT]) if s.strip()]
    loud = {place_key(s) for s in raw if s.strip().isupper()}
    dotted = {place_key(s) for s in raw if re.fullmatch(r"\s*[^\W\d_](?:\s*\.\s*[^\W\d_])+\s*\.?\s*", s)}
    if lone and (parts[0] in LONE_WORDS or parts[0] in dotted and (code(parts[0]) or len(parts[0]) < 3
                                                                  and parts[0] not in countries)):
        return []
    if lone and len(parts[0]) == 3 and parts[0] in countries and parts[0] not in KEEP_CODES | loud:
        return []
    unknown = [i for i, p in enumerate(parts) if not known(p)]
    if any(len(w) >= 3 and any(c.isdigit() for c in w) for i in unknown for w in parts[i].split()):
        return []
    if unknown and all(code(p) for p in parts if known(p)):
        return []

    def only_code(p):   # a local abbreviation beside other parts, which only confirms
        return p in codes and not named(p) and not lone

    def short_code(p):   # a country's code that is also a region's ("CO" is Colombia and Colorado)
        return not lone and len(p) <= 3 and p in countries and (p in regions or p in codes)

    def read(parts):
        judges = {q: (frozenset(nations(q)), frozenset(regions.get(q, ())) | frozenset(codes.get(q, ())))
                  for q in parts if named(q)}
        others = [[judges[q] for j, q in enumerate(parts) if j != i and q in judges] for i in range(len(parts))]
        near = [[judges[q] for j, q in enumerate(parts) if j != i and q in judges
                 and where.get(q, set()) & where.get(parts[i], set())] for i in range(len(parts))]

        def agrees(place, i, among=others):
            key = (place.country, place.region)
            return all(place.country in ns or key in rs for ns, rs in among[i])

        def towns(i, p, table, ns=()):
            return {pl.id: pl for pl in table.get(p, ()) if (not ns or pl.country in ns) and agrees(pl, i)}

        def fitting(i, p):   # a country's name is a town abroad only if the rest points there ("Armenia, Quindio")
            found = towns(i, p, cities, nations(p))
            if found or not others[i]:
                return found
            return towns(i, p, also, nations(p)) or towns(i, p, cities)

        # each part's own towns, whatever the other parts say, for when they rule each other out; a part that
        # names a region outweighing its towns ("Washington", "Oregon") is not read as those towns
        own = {p: {pl.id: pl for pl in cities.get(p, ()) if not nations(p) or pl.country in nations(p)}
               for p in parts if not only_code(p)}
        town = [p for p in parts if own.get(p) and not outweighed(p)]
        city = [i for i, p in enumerate(parts) if p in cities and not named(p) and not only_code(p)]
        if city:
            groups = [fitting(i, parts[i]) for i in city]
            for i, group in zip(city, groups):   # another place's qualifier moved a clear city elsewhere
                if group and len(near[i]) < len(others[i]):   # ("London / Toronto, Canada" is not London, Ontario)
                    plain = clear_zone([pl for pl in cities.get(parts[i], ()) if agrees(pl, i, near)])
                    moved = clear_zone(group.values())
                    if plain and (moved is None or rules_id(moved) != rules_id(plain)):
                        return []
            if all(groups):
                return groups
            rulers = [q for q in parts if named(q)]
            if any(q in town for q in rulers):   # a part that rules the city out is a town itself
                return [own[p] for p in town]
            out = {i for i, g in zip(city, groups) if not g}
            if any(is_code(q) or code(q) for q in rulers):
                return []
            if any(not where.get(parts[i], set()) & where.get(q, set()) for i in out for q in rulers):
                return []   # the city and what rules it out are two places ("Berlin / India")
            return read([p for i, p in enumerate(parts) if i not in out])
        groups, found = [], False
        for i, p in enumerate(parts):
            if not named(p):
                continue
            group = {} if found else fitting(i, p)   # "Kent, Washington": the first part is the town
            found = found or bool(group)
            if short_code(p):   # beside other parts, "CO" or "LA" is read only as a town ("LA, CA")
                groups += [group] if group else []
                continue
            alone, lands = people(group.values()), {}
            for key in sorted(regions.get(p, ())):   # each region of the name that outweighs its towns, by country
                if not any((pl.country, pl.region) == key for pl in group.values()):
                    pool = {pl.id: pl for pl in in_region.get(key, ()) if agrees(pl, i)}
                    if people(pool.values()) > alone:
                        lands.setdefault(key[0], {}).update(pool)
            pools = {k: pl for land in lands.values() for k, pl in land.items()}
            zone = clear_zone(list(group.values()) + list(pools.values())) if pools else None
            # a name read two ways in different zones is one group per reading, which a shown time zone can choose
            # between: regions of two countries ("Punjab"), or a region and a big city of the name ("Washington")
            if len({rules_id(z) if z else None for z in map(clear_zone, map(dict.values, lands.values()))}) > 1:
                groups += [g for g in [group] + list(lands.values()) if g]
                continue
            if pools and any(pl.people >= BIG_TOWN and (zone is None or rules_id(pl.zone) != rules_id(zone))
                             for pl in group.values()):
                groups.append(group)
                group = {}
            group.update(pools)
            if p in regions:
                group.update((pl.id, pl) for cc in sorted(nations(p)) for pl in in_country.get(cc, ())
                             if agrees(pl, i))
            if group:
                groups.append(group)
        if groups:
            return groups
        if len(town) > 1:   # named places that rule each other out ("Tokyo, Seoul"), not "Washington, Oregon"
            return [own[p] for p in town]
        for i, p in enumerate(parts):
            land = {pl.id: pl for cc in sorted(nations(p)) for pl in in_country.get(cc, ()) if agrees(pl, i)}
            if short_code(p):
                area = {pl.id: pl for key in sorted(codes.get(p, ())) for pl in in_region.get(key, ())
                        if agrees(pl, i)}
                a, n = people(area.values()), people(land.values())
                land = {} if p in regions or CODE_SHARE * n <= a <= 2 * n else area if a > n else land
            if land:
                groups.append(land)
        if not groups and not any(named(p) or p in cities for p in parts):
            groups = [{pl.id: pl for key in sorted(codes[p]) for pl in in_region.get(key, ())}
                      for p in parts if only_code(p)]
        return groups

    groups = []
    for group in read(parts):
        for p in parts:   # a local abbreviation keeps the places it confirms, if it confirms any, and a group
            if only_code(p):   # it contradicts, one in its country but none in its regions, is not read ("Tambaú, PB")
                hit = {k: pl for k, pl in group.items() if (pl.country, pl.region) in codes[p]}
                lands = {cc for cc, _ in codes[p]}
                group = hit or ({} if any(pl.country in lands for pl in group.values()) else group)
        if group:
            groups.append(group)
    sets = [frozenset(g) for g in groups]
    return [list(g.values()) for k, g in enumerate(groups)
            if sets[k] not in sets[:k] and not any(s < sets[k] for s in sets)]


_rules, _rule_ids = {}, {}


def zone_rules(zone):
    """A zone's offset from UTC, in minutes, at noon UTC on every day of RULES_DAYS, or None if this
    machine has no rules for it. The offset is read once a week and on every day of a week in which it
    changes, so a change undone within the same week would not be seen; no zone in the place table has had
    one since 2005."""
    got = _zone(zone)
    return got and got[1]


def rules_id(zone):
    """A small number that two zones share exactly when they count days alike: their zone_rules are equal and
    their clocks change at the same minutes, so Asia/Beirut, which changes at local midnight, is not
    Europe/Athens, which changes at 01:00 UTC on the same days. None if the machine has no rules for it."""
    got = _zone(zone)
    return got and got[0]


def _zone(zone):
    if zone not in _rules:
        try:
            tz, seen = zoneinfo.ZoneInfo(zone), {}
            epoch = dt.date(1970, 1, 1).toordinal()

            def offset(minute):   # the zone's offset from UTC, in minutes, at a minute counted from 1970
                if minute not in seen:
                    seen[minute] = int(dt.datetime.fromtimestamp(minute * 60, tz).utcoffset().total_seconds()) // 60
                return seen[minute]

            def noon(day):
                return offset((day - epoch) * 1440 + 720)

            first, last = RULES_DAYS[0], RULES_DAYS[1] - 1
            rules, changes = [], []
            for start in range(first, last, 7):
                end = min(start + 7, last)
                if noon(start) == noon(end):
                    rules += [noon(start)] * (end - start)
                    continue
                for day in range(start, end):
                    rules.append(noon(day))
                    if noon(day) != noon(day + 1):   # the first minute after this noon with the next noon's offset
                        lo, hi = (day - epoch) * 1440 + 720, (day + 1 - epoch) * 1440 + 720
                        while hi - lo > 1:
                            mid = (lo + hi) // 2
                            lo, hi = (mid, hi) if offset(mid) == noon(day) else (lo, mid)
                        changes.append(hi)
            rules = tuple(rules + [noon(last)])
            _rules[zone] = _rule_ids.setdefault((rules, tuple(changes)), (len(_rule_ids), rules))
        except (AttributeError, ValueError, OSError, KeyError, OverflowError):   # KeyError: ZoneInfoNotFoundError
            _rules[zone] = None
    return _rules[zone]


def clear_zone(places):
    """The zone whose rules cover at least CLEAR_SHARE of the people in these places, or None. Zones that
    count days alike are one here, as America/New_York and America/Detroit are; the zone named is the one
    of its biggest place."""
    people, biggest = {}, {}
    for place in places:
        rid = rules_id(place.zone)
        if rid is None:
            continue
        n = max(place.people, 1)
        people[rid] = people.get(rid, 0) + n
        if (n, place.zone) > biggest.get(rid, (0, "")):
            biggest[rid] = (n, place.zone)
    if not people:
        return None
    top = max(people, key=people.get)
    return biggest[top][1] if people[top] >= CLEAR_SHARE * sum(people.values()) else None


def zone_offset(zone, now):
    """A zone's offset from UTC at now, in minutes."""
    return int(dt.datetime.fromtimestamp(now, zoneinfo.ZoneInfo(zone)).utcoffset().total_seconds()) // 60


def shared_zone(groups):
    """With several places named, the zone whose rules cover at least JOINT_SHARE of the people of every one
    of them, when exactly one zone's rules do ("Cambridge / Boston" is Boston's), named by its biggest place;
    otherwise None."""
    common = None
    for group in groups:
        people = {}
        for place in group:
            rid = rules_id(place.zone)
            if rid is not None:
                people[rid] = people.get(rid, 0) + max(place.people, 1)
        total = sum(people.values())
        share = {rid for rid, n in people.items() if n >= JOINT_SHARE * total}
        common = share if common is None else common & share
    if not common or len(common) != 1:
        return None
    rid = common.pop()
    return max(((max(p.people, 1), p.zone) for g in groups for p in g if rules_id(p.zone) == rid))[1]


def local_zone(offset, location, now, seen=None):
    """The time zone days are counted in. offset is the profile's shown time zone, in minutes from UTC,
    read at seen, and always wins: the location only chooses among the zones with that offset then, which
    fixes daylight saving for past days, and "USA" at UTC-7 in summer is Los Angeles because that zone's
    rules cover 75% of the people there, so the choice can differ between a summer and a winter run. A
    location that names places in different zones ("SF / NYC") chooses nothing, and one that names places a
    zone covers well ("Cambridge / Boston") chooses that zone. With no shown time zone, the location's own
    zone. With neither, or no clear answer, the shown offset fixed for all past days, so their daylight
    saving is ignored, or UTC."""
    try:
        groups = location_places(location) if location else []
        if offset is not None:
            instants, fits = {now, now if seen is None else seen}, {}
            for zone in {p.zone for g in groups for p in g}:
                fits[zone] = rules_id(zone) is not None and any(zone_offset(zone, t) == offset for t in instants)
            groups = [[p for p in g if fits[p.zone]] for g in groups]
            sets = [frozenset(p.id for p in g) for g in groups]
            groups = [g for k, g in enumerate(groups) if g and sets[k] not in sets[:k]]
        zones = [clear_zone(g) for g in groups]
        if zones and all(zones) and len({rules_id(z) for z in zones}) == 1:
            biggest = max(range(len(groups)), key=lambda k: sum(max(p.people, 1) for p in groups[k]))
            return zoneinfo.ZoneInfo(zones[biggest])
        zone = shared_zone(groups) if len(groups) > 1 else None
        if zone:
            return zoneinfo.ZoneInfo(zone)
    except Exception:   # this only refines how days are counted, so nothing in it may stop the run
        pass
    if offset is not None:
        return dt.timezone(dt.timedelta(minutes=offset))
    return dt.timezone.utc


def zone_database():
    """Whether this Python has time zone rules at all (Windows needs the tzdata package for them)."""
    try:
        zoneinfo.ZoneInfo("America/New_York")
        return True
    except Exception:
        return False


class GitHubOnly(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to another https page on github.com; any other is refused as an error."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != "https" or target.hostname != "github.com":
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def profile_page(owner, deadline, into):
    """Reads the owner's public profile page into the list into, as (bytes, when read), unless it is not
    from github.com over https, is larger than PROFILE_LIMIT or is not all read by deadline. Each read waits
    at most until deadline, so a page sent slowly cannot outlast it."""
    request = urllib.request.Request("https://github.com/" + owner, headers={"User-Agent": "coderprint"})
    body = bytearray()
    try:
        with urllib.request.build_opener(GitHubOnly).open(request, timeout=PROFILE_TIMEOUT) as page:
            final = urllib.parse.urlsplit(page.geturl())
            if final.scheme != "https" or final.hostname != "github.com":
                return
            while len(body) <= PROFILE_LIMIT:
                left = deadline - time.monotonic()
                if left <= 0:
                    return
                try:
                    page.fp.raw._sock.settimeout(left)
                except AttributeError:
                    pass
                chunk = page.read1(1 << 16)
                if not chunk:
                    break
                body += chunk
    except Exception:   # any failure to read is a page not read
        return
    if len(body) <= PROFILE_LIMIT and time.monotonic() <= deadline:
        into.append((bytes(body), time.time()))


def profile_offset(owner):
    """The offset from UTC, in minutes, of the local time GitHub shows on the owner's public profile, and
    when it was read; None when the profile shows none, shows two that differ, or cannot be read within
    PROFILE_TIMEOUT, redirects and slow replies included. The page is fetched signed out, as any visitor
    sees it, and only over https from github.com."""
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner or ""):
        return None
    deadline, read = time.monotonic() + PROFILE_TIMEOUT, []
    reader = threading.Thread(target=profile_page, args=(owner, deadline, read), daemon=True)
    reader.start()
    reader.join(max(0.0, deadline - time.monotonic()) + 0.5)
    if not read:
        return None
    body, seen = read[0]
    found = set()
    at = body.find(b"<profile-timezone")
    while at >= 0:   # every element, each byte scanned a bounded number of times
        after = at + 1   # not an element (a longer tag's name, or text): look again from the next byte
        if body[at + 17:at + 18] in (b" ", b"\t", b"\r", b"\n", b"/", b">"):   # not <profile-timezone-tooltip>
            end = body.find(b">", at, at + 2048)
            if end < 0:   # a tag left open: go on from the last tag begun within reach, else past it
                end = at + 2048
                after = body.rfind(b"<", at + 1, end)
                after = after if after >= 0 else end
            else:
                after = end
            m = re.search(rb'\sdata-hours-ahead-of-utc="([^"]*)"', body[at:end])
            if m:
                number = re.fullmatch(rb"[-+]?[0-9]{1,2}(?:\.[0-9]{1,4})?", m.group(1))
                minutes = float(number.group()) * 60 if number else None
                good = minutes is not None and minutes == round(minutes) and -720 <= minutes <= 840
                found.add(int(round(minutes)) if good and not round(minutes) % 15 else None)
        at = body.find(b"<profile-timezone", max(after, at + 1))
    if len(found) != 1 or None in found:
        return None
    return found.pop(), seen


def profile_location(owner):
    """The location on the owner's public profile, or "" when there is none or it cannot be read. Reading the
    profile is what RESERVE is kept for, so the query may use it, all but what drawing and writing need."""
    try:
        data = gql("query($owner: String!) { repositoryOwner(login: $owner) { "
                   "... on User { location } ... on Organization { location } } }",
                   timeout=LOCATION_TIMEOUT, reserve=RESERVE - PROFILE_TIMEOUT - LOCATION_TIMEOUT, owner=owner)
    except (RuntimeError, ValueError):
        return ""
    found = data.get("repositoryOwner") if isinstance(data, dict) else None
    location = found.get("location") if isinstance(found, dict) else None
    return location[:LOCATION_LIMIT] if isinstance(location, str) else ""
