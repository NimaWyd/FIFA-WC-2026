"""Retry FotMob image downloads for players not found in the first pass."""
import requests, json, sys, time
from urllib.parse import quote
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"}
OUT_DIR = Path("frontend/public/players")
FOTMOB_IMAGE = "https://images.fotmob.com/image_resources/playerimages/{id}.png"


def search(q):
    try:
        r = requests.get(f"https://apigw.fotmob.com/searchapi/suggest?term={quote(q)}", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return []
        results = []
        for group in r.json().get("squadMemberSuggest", []):
            for opt in group.get("options", []):
                payload = opt.get("payload", {})
                if not payload.get("isCoach"):
                    results.append({"name": opt.get("text", "").split("|")[0], "id": str(payload.get("id", ""))})
        return results[:8]
    except:
        return []


def download(fotmob_id, dest):
    url = FOTMOB_IMAGE.format(id=fotmob_id)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 1500:
            dest.write_bytes(r.content)
            return True
    except:
        pass
    return False


# Confirmed matches from first pass (sofascore_id -> fotmob_id)
confirmed = {
    "1088274": ("497540",  "Jesus Gomez"),
    "869792":  ("1785055", "Gabriel Magalhaes"),
    "1544387": ("1807873", "Keeto Thermoncy"),
    "802719":  ("694558",  "Dom Hyam"),
    "262911":  ("357880",  "Andy Robertson"),
    "226986":  ("316544",  "Irfan Can Kahveci"),
    "2018130": ("1718458", "Abdelmouhib Chamakh"),
    "2018330": ("1721242", "Raed Chikhaoui"),
    "918547":  ("653688",  "El Mahdi Soliman"),
    "918913":  ("1836163", "Hamdy Fathy"),
    "880622":  ("849334",  "Ahmed Fatouh"),
    "295361":  ("513492",  "Mahmoud Trezeguet"),
    "2200929": ("1797171", "Aqtay Abdallah"),
    "871355":  ("872575",  "Ali Nemati"),
    "2195590": ("1844610", "Amirhossein Mahmoudi"),
    "1001675": ("1958455", "Joao Paulo"),
    "147138":  ("1435553", "Pico"),
    "974087":  ("130747",  "Manu Kone"),
    "1471764": ("1451265", "Malick Diouf"),
    "2427970": ("1798782", "Bara Ndiaye"),
    "876600":  ("813055",  "Mousa Al-Tamari"),
    "988351":  ("1935515", "Samu Costa"),
    "830431":  ("732282",  "Trincao"),
    "1391541": ("1428153", "Mukau"),
    "1607635": ("852071",  "Juan Camilo Hernandez"),
    "980634":  ("1107910", "Tino Livramento"),
}

# Second pass: players still missing, with alternative search terms
second_pass = [
    ("Dan Burn",                    "England",           "99090",   ["Daniel Burn England", "Burn Newcastle"]),
    ("Abdallah Al-Fakhouri",        "Jordan",            "974747",  ["Al-Fakhouri Jordan", "Abdallah Fakhouri"]),
    ("Mohammad Abualnadi",          "Jordan",            "1158813", ["Abualnadi Jordan", "Mohammed Abualnadi"]),
    ("Yousef Abu Al-Jazar",         "Jordan",            "995678",  ["Abu Al Jazar", "Yousef Abualjazar"]),
    ("Husam Abu Dahab",             "Jordan",            "1218720", ["Husam Abou Dahab", "Abu Dahab Jordan"]),
    ("Yazan Al-Arab",               "Jordan",            "888906",  ["Yazan Al Arab", "Yazan Arab Jordan"]),
    ("Mohammad Abu Taha",           "Jordan",            "986341",  ["Mohammed Abu Taha", "Abu Taha Jordan"]),
    ("Nizar Al-Rashdan",            "Jordan",            "1014324", ["Al Rashdan Jordan", "Nizar Rashdan"]),
    ("Al-Hashmi Al-Hussain",        "Qatar",             "1148402", ["Al Hashmi Qatar", "Hashmi Hussain Qatar"]),
    ("Bassam Al-Rawi",              "Qatar",             "1144626", ["Bassam Rawi Qatar", "Bassam Al Rawi"]),
    ("Rayyan Al-Ali",               "Qatar",             "1501526", ["Rayyan Ali Qatar"]),
    ("Lucas Mendes",                "Qatar",             "243199",  ["Lucas Mendes Qatar", "Lucas Mendes Al Duhail"]),
    ("Homam Al-Amin",               "Qatar",             "933433",  ["Homam Amin Qatar"]),
    ("Tahsin Mohammed",             "Qatar",             "1501518", ["Tahsin Mohammed Qatar"]),
    ("Ahmed Al-Ganehi",             "Qatar",             "936542",  ["Al Ganehi Qatar", "Ahmed Ganehi"]),
    ("Jo Yu-Min",                   "Korea Republic",    "1026122", ["Jo Yumin", "Jo Yu Min Korea"]),
    ("Um Ji-Sung",                  "Korea Republic",    "1002508", ["Um Jisung", "Ji Sung Um Korea"]),
    ("Roger Ibañez",                "Brazil",            "888949",  ["Roger Ibanez Braga", "Roger Ibanez Brazil"]),
    ("Pape Matar Sarr",             "Senegal",           "1002711", ["Pape Matar Sarr Tottenham", "Pape Matar"]),
    ("Moustapha Mbow",              "Senegal",           "982319",  ["Mbow Senegal", "Mustapha Mbow"]),
    ("Juan Camilo Portilla",        "Colombia",          "980580",  ["Portilla Colombia", "Camilo Portilla Cucho"]),
    ("Mohamed Amine Ben Hamida",    "Tunisia",           "1000809", ["Ben Hamida Tunisia", "Amine Ben Hamida"]),
    ("Nabil Emad",                  "Egypt",             "918505",  ["Nabil Emad Egypt", "Nabil Emad Zamalek"]),
    ("Ahmed Zizo",                  "Egypt",             "547494",  ["Ahmed Zizo Egypt", "Zizo Egypt"]),
    ("Matt Garbett",                "New Zealand",       "1002607", ["Matthew Garbett New Zealand"]),
    ("Eli Just",                    "New Zealand",       "905267",  ["Eli Just NZ", "Eli Just Wellington"]),
    ("CJ dos Santos",               "Cape Verde Islands","906020",  ["CJ Santos Cape Verde", "Carlos dos Santos Cape Verde"]),
    ("Gilson Benchimol",            "Cape Verde Islands","1111215", ["Benchimol Cape Verde", "Gilson Benchimol"]),
    ("Carl Fred Saintil",           "Haiti",             "1002387", ["Carl Saintil Haiti", "Carl Fred Saintil"]),
    ("Woodensky Pierre",            "Haiti",             "1384367", ["Woodensky Pierre Haiti"]),
    ("Avazbek Ulmasaliev",          "Uzbekistan",        "978392",  ["Ulmasaliev Uzbekistan"]),
    ("Rustamjon Ashurmatov",        "Uzbekistan",        "358822",  ["Ashurmatov", "Rustam Ashurmatov"]),
    ("Umarbek Eshmurodov",          "Uzbekistan",        "893000",  ["Eshmurodov Uzbekistan"]),
    ("Muhammadrasul Abdumajidov",   "Uzbekistan",        "1489504", ["Abdumajidov Uzbekistan"]),
    ("Diyor Ortikboev",             "Uzbekistan",        "1199039", ["Ortikboev Uzbekistan"]),
    ("Nodirbek Abdurazzokov",       "Uzbekistan",        "1113128", ["Abdurazzokov Uzbekistan"]),
    ("Sardorbek Rakhmonov",         "Uzbekistan",        "1651894", ["Rakhmonov Uzbekistan"]),
    ("Jamshid Iskanderov",          "Uzbekistan",        "785512",  ["Iskanderov Uzbekistan"]),
    ("Azizjon Ganiev",              "Uzbekistan",        "793857",  ["Ganiev Uzbekistan"]),
    ("Abbosek Fayzullaev",          "Uzbekistan",        "1118429", ["Fayzullaev Uzbekistan", "Abbosbek Fayzullaev"]),
    ("Munir El Kajoui",             "Morocco",           "141967",  ["Munir Kajoui", "El Kajoui Morocco GK"]),
]

downloaded = 0

print("=== Downloading confirmed matches ===")
for sid, (fotmob_id, name) in confirmed.items():
    dest = OUT_DIR / f"p{sid}.jpg"
    if dest.exists():
        print(f"SKIP  {name}")
        continue
    if download(fotmob_id, dest):
        downloaded += 1
        print(f"OK    {name} -> p{sid}.jpg")
    else:
        print(f"FAIL  {name} (id={fotmob_id})")
    time.sleep(0.2)

print("\n=== Second pass with alternative names ===")
for name, team, sid, variants in second_pass:
    dest = OUT_DIR / f"p{sid}.jpg"
    if dest.exists():
        print(f"SKIP  {name}")
        continue
    fotmob_id = None
    found_as = None
    for v in variants:
        results = search(v)
        time.sleep(0.3)
        if results:
            fotmob_id = results[0]["id"]
            found_as = results[0]["name"]
            break
    if fotmob_id:
        if download(fotmob_id, dest):
            downloaded += 1
            print(f"OK    {name} -> [{found_as}] p{sid}.jpg")
        else:
            print(f"FAIL_DL {name}")
    else:
        print(f"MISS  {name} [{team}]")

print(f"\nTotal downloaded: {downloaded}")
