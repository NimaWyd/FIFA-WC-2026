"""WC 2026 venue registry and match-to-venue lookup.

Provides:
  STADIUMS      — dict keyed by city name → venue metadata
  lookup_venue  — (home, away, date) → venue dict | None
"""
from __future__ import annotations

from typing import Optional

W = "https://upload.wikimedia.org/wikipedia/commons/thumb"

STADIUMS: dict[str, dict] = {
    "Atlanta": {
        "name": "Mercedes-Benz Stadium",
        "city": "Atlanta, GA",
        "country": "USA",
        "capacity": 71000,
        "altitude_m": 320,
        "surface": "FieldTurf",
        "is_dome": True,
        "image_url": f"{W}/1/10/Mercedes_Benz_Stadium_time_lapse_capture_2017-08-13.jpg/1280px-Mercedes_Benz_Stadium_time_lapse_capture_2017-08-13.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Mercedes-Benz_Stadium",
    },
    "Boston": {
        "name": "Gillette Stadium",
        "city": "Foxborough, MA",
        "country": "USA",
        "capacity": 65878,
        "altitude_m": 22,
        "surface": "Grass",
        "is_dome": False,
        "image_url": f"{W}/d/db/Gillette_Stadium_%28Top_View%29.jpg/1280px-Gillette_Stadium_%28Top_View%29.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Gillette_Stadium",
    },
    "Dallas": {
        "name": "AT&T Stadium",
        "city": "Arlington, TX",
        "country": "USA",
        "capacity": 80000,
        "altitude_m": 170,
        "surface": "AstroTurf",
        "is_dome": True,
        "image_url": f"{W}/1/11/Arlington_June_2020_4_%28AT%26T_Stadium%29.jpg/1280px-Arlington_June_2020_4_%28AT%26T_Stadium%29.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/AT%26T_Stadium",
    },
    "Houston": {
        "name": "NRG Stadium",
        "city": "Houston, TX",
        "country": "USA",
        "capacity": 72220,
        "altitude_m": 15,
        "surface": "FieldTurf",
        "is_dome": True,
        "image_url": f"{W}/3/3e/Nrg_stadium.jpg/1280px-Nrg_stadium.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/NRG_Stadium",
    },
    "Kansas City": {
        "name": "GEHA Field at Arrowhead Stadium",
        "city": "Kansas City, MO",
        "country": "USA",
        "capacity": 76416,
        "altitude_m": 274,
        "surface": "Grass",
        "is_dome": False,
        "image_url": f"{W}/a/ac/Aerial_view_of_Arrowhead_Stadium_08-31-2013.jpg/1280px-Aerial_view_of_Arrowhead_Stadium_08-31-2013.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Arrowhead_Stadium",
    },
    "Los Angeles": {
        "name": "SoFi Stadium",
        "city": "Inglewood, CA",
        "country": "USA",
        "capacity": 70240,
        "altitude_m": 25,
        "surface": "Bermuda grass",
        "is_dome": False,
        "image_url": f"{W}/b/b3/SoFi_Stadium_2023.jpg/1280px-SoFi_Stadium_2023.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/SoFi_Stadium",
    },
    "Miami": {
        "name": "Hard Rock Stadium",
        "city": "Miami Gardens, FL",
        "country": "USA",
        "capacity": 65326,
        "altitude_m": 3,
        "surface": "Grass",
        "is_dome": False,
        "image_url": f"{W}/c/ce/Hard_Rock_Stadium_for_Super_Bowl_LIV_%2849606710103%29.jpg/1280px-Hard_Rock_Stadium_for_Super_Bowl_LIV_%2849606710103%29.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hard_Rock_Stadium",
    },
    "Mexico City": {
        "name": "Estadio Azteca",
        "city": "Mexico City",
        "country": "Mexico",
        "capacity": 87523,
        "altitude_m": 2240,
        "surface": "Grass",
        "is_dome": False,
        "image_url": f"{W}/0/07/Vista_a%C3%A9rea_del_Estadio_Azteca_-_2026_-_02.jpg/1280px-Vista_a%C3%A9rea_del_Estadio_Azteca_-_2026_-_02.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Estadio_Azteca",
    },
    "Guadalajara": {
        "name": "Estadio Akron",
        "city": "Zapopan, Jalisco",
        "country": "Mexico",
        "capacity": 49850,
        "altitude_m": 1566,
        "surface": "Grass",
        "is_dome": True,
        "image_url": f"{W}/1/10/Estadio_Akron_02-07-2022_cabecera_sur_lado_derecho_%283%29.jpg/1280px-Estadio_Akron_02-07-2022_cabecera_sur_lado_derecho_%283%29.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Estadio_Akron",
    },
    "Monterrey": {
        "name": "Estadio BBVA",
        "city": "Guadalupe, Nuevo León",
        "country": "Mexico",
        "capacity": 53500,
        "altitude_m": 538,
        "surface": "Grass",
        "is_dome": False,
        "image_url": f"{W}/5/57/Mexico_Guadalupe_Monterrey_Estadio_BBVA_Bancomer_fifa_world_cup_2026_6.JPG/1280px-Mexico_Guadalupe_Monterrey_Estadio_BBVA_Bancomer_fifa_world_cup_2026_6.JPG",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Estadio_BBVA",
    },
    "New York/New Jersey": {
        "name": "MetLife Stadium",
        "city": "East Rutherford, NJ",
        "country": "USA",
        "capacity": 82500,
        "altitude_m": 8,
        "surface": "FieldTurf",
        "is_dome": False,
        "image_url": f"{W}/0/04/Metlife_stadium_%28Aerial_view%29.jpg/1280px-Metlife_stadium_%28Aerial_view%29.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/MetLife_Stadium",
    },
    "Philadelphia": {
        "name": "Lincoln Financial Field",
        "city": "Philadelphia, PA",
        "country": "USA",
        "capacity": 69796,
        "altitude_m": 10,
        "surface": "Grass",
        "is_dome": False,
        "image_url": f"{W}/a/a1/Lincoln_Financial_Field_%28Aerial_view%29.jpg/1280px-Lincoln_Financial_Field_%28Aerial_view%29.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Lincoln_Financial_Field",
    },
    "San Francisco": {
        "name": "Levi's Stadium",
        "city": "Santa Clara, CA",
        "country": "USA",
        "capacity": 68500,
        "altitude_m": 10,
        "surface": "Grass",
        "is_dome": False,
        "image_url": f"{W}/a/a6/Levi%27s_Stadium_in_February_2016_prior_to_Super_Bowl_50_%2824398261729%29.jpg/1280px-Levi%27s_Stadium_in_February_2016_prior_to_Super_Bowl_50_%2824398261729%29.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Levi%27s_Stadium",
    },
    "Seattle": {
        "name": "Lumen Field",
        "city": "Seattle, WA",
        "country": "USA",
        "capacity": 72000,
        "altitude_m": 8,
        "surface": "FieldTurf",
        "is_dome": False,
        "image_url": f"{W}/5/53/Qwest_Field_North.jpg/1280px-Qwest_Field_North.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Lumen_Field",
    },
    "Toronto": {
        "name": "BMO Field",
        "city": "Toronto, ON",
        "country": "Canada",
        "capacity": 30000,
        "altitude_m": 76,
        "surface": "Grass",
        "is_dome": False,
        "image_url": f"{W}/9/91/Toronto_BMO_Field_in_2024.jpg/1280px-Toronto_BMO_Field_in_2024.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/BMO_Field",
    },
    "Vancouver": {
        "name": "BC Place",
        "city": "Vancouver, BC",
        "country": "Canada",
        "capacity": 54500,
        "altitude_m": 4,
        "surface": "FieldTurf",
        "is_dome": True,
        "image_url": f"{W}/f/ff/BC_Place_2015_Women%27s_FIFA_World_Cup.jpg/1280px-BC_Place_2015_Women%27s_FIFA_World_Cup.jpg",
        "wikipedia_url": "https://en.wikipedia.org/wiki/BC_Place",
    },
}

# (home, away, date) → venue city — built from the full WC 2026 group schedule
_MATCH_VENUE: dict[tuple[str, str, str], str] = {
    # Group A
    ("Mexico", "South Africa", "2026-06-11"): "Mexico City",
    ("Korea Republic", "Czechia", "2026-06-12"): "Guadalajara",
    ("Mexico", "Korea Republic", "2026-06-18"): "Guadalajara",
    ("Czechia", "South Africa", "2026-06-18"): "Atlanta",
    ("Czechia", "Mexico", "2026-06-25"): "Mexico City",
    ("South Africa", "Korea Republic", "2026-06-25"): "Monterrey",
    # Group B
    ("Canada", "Bosnia and Herzegovina", "2026-06-12"): "Toronto",
    ("Qatar", "Switzerland", "2026-06-13"): "San Francisco",
    ("Switzerland", "Bosnia and Herzegovina", "2026-06-18"): "Los Angeles",
    ("Canada", "Qatar", "2026-06-18"): "Vancouver",
    ("Switzerland", "Canada", "2026-06-24"): "Vancouver",
    ("Bosnia and Herzegovina", "Qatar", "2026-06-24"): "Seattle",
    # Group C
    ("Brazil", "Morocco", "2026-06-13"): "New York/New Jersey",
    ("Haiti", "Scotland", "2026-06-13"): "Boston",
    ("Scotland", "Morocco", "2026-06-19"): "Boston",
    ("Brazil", "Haiti", "2026-06-19"): "Philadelphia",
    ("Morocco", "Haiti", "2026-06-24"): "Atlanta",
    ("Scotland", "Brazil", "2026-06-24"): "Miami",
    # Group D
    ("United States", "Paraguay", "2026-06-12"): "Los Angeles",
    ("Australia", "Turkey", "2026-06-14"): "Vancouver",
    ("United States", "Australia", "2026-06-19"): "Seattle",
    ("Turkey", "Paraguay", "2026-06-19"): "San Francisco",
    ("Turkey", "United States", "2026-06-25"): "Los Angeles",
    ("Paraguay", "Australia", "2026-06-25"): "San Francisco",
    # Group E
    ("Germany", "Curaçao", "2026-06-14"): "Houston",
    ("Côte d'Ivoire", "Ecuador", "2026-06-14"): "Philadelphia",
    ("Germany", "Côte d'Ivoire", "2026-06-20"): "Toronto",
    ("Ecuador", "Curaçao", "2026-06-20"): "Kansas City",
    ("Ecuador", "Germany", "2026-06-25"): "New York/New Jersey",
    ("Curaçao", "Côte d'Ivoire", "2026-06-25"): "Philadelphia",
    # Group F
    ("Netherlands", "Japan", "2026-06-14"): "Dallas",
    ("Sweden", "Tunisia", "2026-06-14"): "Monterrey",
    ("Netherlands", "Sweden", "2026-06-20"): "Houston",
    ("Tunisia", "Japan", "2026-06-20"): "Monterrey",
    ("Tunisia", "Netherlands", "2026-06-25"): "Kansas City",
    ("Japan", "Sweden", "2026-06-25"): "Dallas",
    # Group G
    ("Belgium", "Egypt", "2026-06-15"): "Seattle",
    ("IR Iran", "New Zealand", "2026-06-15"): "Los Angeles",
    ("Belgium", "IR Iran", "2026-06-21"): "Los Angeles",
    ("New Zealand", "Egypt", "2026-06-21"): "Vancouver",
    ("New Zealand", "Belgium", "2026-06-26"): "Vancouver",
    ("Egypt", "IR Iran", "2026-06-26"): "Seattle",
    # Group H
    ("Spain", "Cape Verde Islands", "2026-06-15"): "Atlanta",
    ("Saudi Arabia", "Uruguay", "2026-06-15"): "Miami",
    ("Spain", "Saudi Arabia", "2026-06-21"): "Atlanta",
    ("Uruguay", "Cape Verde Islands", "2026-06-21"): "Miami",
    ("Uruguay", "Spain", "2026-06-26"): "Guadalajara",
    ("Cape Verde Islands", "Saudi Arabia", "2026-06-26"): "Houston",
    # Group I
    ("France", "Senegal", "2026-06-16"): "New York/New Jersey",
    ("Iraq", "Norway", "2026-06-16"): "Boston",
    ("France", "Iraq", "2026-06-22"): "Philadelphia",
    ("Norway", "Senegal", "2026-06-22"): "New York/New Jersey",
    ("Norway", "France", "2026-06-26"): "Boston",
    ("Senegal", "Iraq", "2026-06-26"): "Toronto",
    # Group J
    ("Argentina", "Algeria", "2026-06-16"): "Kansas City",
    ("Austria", "Jordan", "2026-06-16"): "San Francisco",
    ("Argentina", "Austria", "2026-06-22"): "Dallas",
    ("Jordan", "Algeria", "2026-06-22"): "San Francisco",
    ("Jordan", "Argentina", "2026-06-27"): "Dallas",
    ("Algeria", "Austria", "2026-06-27"): "Kansas City",
    # Group K
    ("Portugal", "DR Congo", "2026-06-17"): "Houston",
    ("Uzbekistan", "Colombia", "2026-06-17"): "Mexico City",
    ("Portugal", "Uzbekistan", "2026-06-23"): "Houston",
    ("Colombia", "DR Congo", "2026-06-23"): "Guadalajara",
    ("Colombia", "Portugal", "2026-06-27"): "Miami",
    ("DR Congo", "Uzbekistan", "2026-06-27"): "Atlanta",
    # Group L
    ("England", "Croatia", "2026-06-17"): "Dallas",
    ("Ghana", "Panama", "2026-06-17"): "Toronto",
    ("England", "Ghana", "2026-06-23"): "Boston",
    ("Panama", "Croatia", "2026-06-23"): "Toronto",
    ("Panama", "England", "2026-06-27"): "New York/New Jersey",
    ("Croatia", "Ghana", "2026-06-27"): "Philadelphia",
}


# City-to-altitude lookup for major international football cities.
# Covers all high-altitude nations whose matches appear in results.csv.
# Sea-level / low-altitude cities are intentionally omitted (default = 0).
CITY_ALTITUDE_M: dict[str, int] = {
    # Bolivia
    "El Alto": 4150,
    "La Paz": 3625,
    "Sucre": 2750,
    "Cochabamba": 2570,
    "Potosí": 3967,
    # Ecuador
    "Quito": 2850,
    "Cuenca": 2560,
    "Ambato": 2577,
    "Latacunga": 2785,
    "Riobamba": 2754,
    # Colombia
    "Bogotá": 2640,
    "Bogota": 2640,
    "Manizales": 2153,
    "Armenia": 1540,
    "Pereira": 1411,
    "Medellín": 1495,
    "Medellin": 1495,
    "Bucaramanga": 959,
    "Cali": 1000,
    # Mexico
    "Mexico City": 2240,
    "Toluca": 2667,
    "Puebla": 2135,
    "Guadalajara": 1566,
    "Zapopan": 1560,
    "Querétaro": 1827,
    "Queretaro": 1827,
    "León": 1884,
    "Leon": 1884,
    "Irapuato": 1724,
    "Nezahualcóyotl": 2240,
    "San Luis Potosí": 1877,
    "Aguascalientes": 1888,
    "Zacatecas": 2496,
    "Monterrey": 538,
    # Peru
    "Arequipa": 2335,
    "Cusco": 3399,
    "Puno": 3827,
    # Venezuela
    "Mérida": 1625,
    "Merida": 1625,
    # China / Asia (some high-altitude venues)
    "Kunming": 1895,
    "Chengdu": 500,
    # Ethiopia
    "Addis Ababa": 2355,
    # Kenya
    "Nairobi": 1795,
    # United States
    "Denver": 1609,
    # Canada — all near sea-level; intentionally excluded
}


def altitude_from_city(city: str) -> int:
    """Return altitude in metres for a city name, or 0 if unknown / sea-level."""
    return CITY_ALTITUDE_M.get(city, 0)


def lookup_venue(home: str, away: str, date: str) -> Optional[dict]:
    """Return venue metadata dict for a scheduled WC 2026 group match, or None."""
    city = _MATCH_VENUE.get((home, away, date))
    if city is None:
        return None
    stadium = STADIUMS.get(city)
    if stadium is None:
        return None
    return {"venue_city": city, **stadium}
