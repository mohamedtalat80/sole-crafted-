import json
import os
import django
from tqdm import tqdm

# ربط إعدادات django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shoe_ecommerce.settings")
django.setup()

from orders.models import Country, State, City  # غيّر your_app باسم تطبيقك

# List of Middle East country ISO2 codes
MIDDLE_EAST_ISO2 = [
    "AE", "BH", "CY", "EG", "IR", "IQ", "IL", "JO", "KW", "LB", "OM", "PS", "QA", "SA", "SY", "TR", "YE"
]

def import_data():
    # Import only Middle East countries
    with open("data/countries.json", encoding="utf-8") as f:
        countries = json.load(f)
        me_countries = [c for c in countries if c["iso2"] in MIDDLE_EAST_ISO2]
        for c in tqdm(me_countries, desc="Importing countries"):
            Country.objects.get_or_create(
                name=c["name"],
                iso2=c["iso2"]
            )
    print("✅ countries imported")

    # Build a mapping of iso2 to country id for later use
    iso2_to_id = {c["iso2"]: c["id"] for c in me_countries if "id" in c}
    me_country_ids = set(iso2_to_id.values())

    # Import only states in Middle East countries
    with open("data/states.json", encoding="utf-8") as f:
        states = json.load(f)
        me_states = [s for s in states if s["country_code"] in MIDDLE_EAST_ISO2]
        for s in tqdm(me_states, desc="Importing states"):
            country = Country.objects.filter(iso2=s["country_code"]).first()
            if country:
                State.objects.get_or_create(
                    name=s["name"],
                    country=country
                )
    print("✅ states imported")

    # Import only cities in Middle East countries (by country_id)
    with open("data/cities.json", encoding="utf-8") as f:
        cities = json.load(f)
        me_cities = [ci for ci in cities if ci.get("country_id") in me_country_ids]
        for ci in tqdm(me_cities, desc="Importing cities"):
            state = State.objects.filter(id=ci["state_id"]).first()
            if state:
                City.objects.get_or_create(
                    name=ci["name"],
                    state=state
                )
    print("✅ cities imported")

if __name__ == "__main__":
    import_data()
