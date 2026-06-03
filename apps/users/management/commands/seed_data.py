"""
Management command: seed_data

Fills the database with realistic Omarine data — Red Sea / Hurghada marine tourism context.

Usage:
    python manage.py seed_data
    python manage.py seed_data --flush   # wipes seed-created data first (keeps real users)
"""
import io
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _jpeg(name: str, color=(30, 144, 255), size=(400, 300)) -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="JPEG", quality=85)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def _pdf(name: str) -> SimpleUploadedFile:
    content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def ok(msg):  return f"  \033[32m[ok]\033[0m {msg}"
def skip(msg): return f"  \033[33m[skip]\033[0m {msg}"
def fix(msg):  return f"  \033[36m[fix]\033[0m {msg}"


# ─────────────────────────────────────────────────────────────────────────────
# Slot builders
# ─────────────────────────────────────────────────────────────────────────────

def _full_day_slots(days=("sunday", "monday", "tuesday", "wednesday", "thursday"), cap=20, captain="Ahmed Khalil"):
    return [
        {"day": d, "duration_type": "full_day", "start_time": "08:00", "end_time": "16:00",
         "current_capacity": cap, "captain": captain}
        for d in days
    ]


def _both_slots(days, full_cap=20, half_cap=15, captain="Mohamed Nasser"):
    slots = []
    for d in days:
        slots.append({"day": d, "duration_type": "full_day", "start_time": "08:00",
                      "end_time": "16:30", "current_capacity": full_cap, "captain": captain})
        slots.append({"day": d, "duration_type": "half_day", "start_time": "08:00",
                      "end_time": "12:30", "current_capacity": half_cap, "captain": captain})
    return slots


def _rent_slots(days, captain="Karim Adel"):
    return [
        {"day": d, "start_time": "07:00", "end_time": "20:00", "captain": captain}
        for d in days
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Command
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seed the database with realistic Omarine / Red Sea marine tourism data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete seed-created records before re-seeding (safe — skips real users)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Omarine Seed Data ===\n"))
        self._seed_currencies()
        self._seed_boat_types()
        self._seed_amenities()
        self._seed_destinations()
        self._seed_trip_includes()
        self._seed_trip_categories()
        self._seed_rent_categories()
        self._seed_onboarding_screens()
        self._seed_faqs()
        self._seed_about_us()
        self._seed_privacy_policy()
        self._seed_terms_and_conditions()
        self._seed_report_types()
        self._seed_owners_and_content()
        self._seed_customers_and_bookings()
        self._update_placeholder_trips()
        self.stdout.write(self.style.SUCCESS("\n=== Seed complete ===\n"))

    # ─── Currencies ──────────────────────────────────────────────────────────

    def _seed_currencies(self):
        self.stdout.write("\n[Currencies]")
        from apps.currencies.models import Currency

        # Fix USDA → USD
        Currency.objects.filter(code="USDA").update(code="USD", name="US Dollar", symbol="$")
        self.stdout.write(fix("Renamed USDA → USD"))

        data = [
            ("Egyptian Pound", "EGP", "E£"),
            ("US Dollar",      "USD", "$"),
            ("Euro",           "EUR", "€"),
            ("British Pound",  "GBP", "£"),
            ("Saudi Riyal",    "SAR", "﷼"),
        ]
        for name, code, symbol in data:
            _, created = Currency.objects.update_or_create(
                code=code, defaults={"name": name, "symbol": symbol, "is_active": True}
            )
            self.stdout.write(ok(f"{code} {symbol}") if created else skip(f"{code} already exists"))

    # ─── Boat Types ──────────────────────────────────────────────────────────

    def _seed_boat_types(self):
        self.stdout.write("\n[Boat Types]")
        from apps.boats.models import BoatType

        # Fix "Speedboat2" → Catamaran
        BoatType.objects.filter(name="Speedboat2").update(name="Catamaran")
        self.stdout.write(fix("Renamed Speedboat2 → Catamaran"))

        colors = {
            "Speedboat":      (220, 50,  50),
            "Catamaran":      (0,   120, 180),
            "Yacht":          (30,  60,  120),
            "Motor Yacht":    (0,   80,  160),
            "Sailing Boat":   (255, 165, 0),
            "Glass Bottom":   (0,   180, 200),
            "Felucca":        (160, 82,  45),
            "Fishing Boat":   (50,  100, 50),
        }
        for name, color in colors.items():
            bt, created = BoatType.objects.get_or_create(
                name=name,
                defaults={"is_active": True,
                          "image": _jpeg(f"boat_type_{name.lower().replace(' ', '_')}.jpg", color)}
            )
            self.stdout.write(ok(name) if created else skip(name))

    # ─── Amenities ───────────────────────────────────────────────────────────

    def _seed_amenities(self):
        self.stdout.write("\n[Amenities]")
        from apps.amenities.models import Amenity

        # Delete bad placeholder amenities ("1", "air conditioning2")
        bad = Amenity.objects.filter(name__in=["1", "air conditioning2"])
        if bad.exists():
            bad.delete()
            self.stdout.write(fix("Deleted placeholder amenities"))

        amenity_names = [
            "air conditioning", "life jackets", "snorkeling gear", "fishing equipment",
            "bbq grill", "towels", "underwater camera", "kayak", "paddleboard",
            "wifi", "sun deck", "bathroom", "kitchen", "cooler box", "music system",
            "first aid kit", "life rings", "anchor", "binoculars", "flippers",
            "wetsuit", "diving equipment", "satellite tv", "generator",
        ]
        for name in amenity_names:
            _, created = Amenity.objects.get_or_create(name=name)
            self.stdout.write(ok(name) if created else skip(name))

    # ─── Destinations ────────────────────────────────────────────────────────

    def _seed_destinations(self):
        self.stdout.write("\n[Destinations]")
        from apps.destination.models import Destination

        destinations = [
            {
                "name": "Hurghada",
                "description": (
                    "Hurghada is Egypt's premier Red Sea resort city, renowned for its crystal-clear "
                    "turquoise waters, vibrant coral reefs, and world-class water sports. Located on "
                    "the western shore of the Red Sea, it offers year-round sunshine and warm waters "
                    "perfect for snorkeling, diving, and boat excursions. The Hurghada Marina serves "
                    "as the main departure point for day trips to nearby islands and diving sites."
                ),
                "color": (0, 150, 200),
            },
            {
                "name": "Giftun Island",
                "description": (
                    "Giftun Island is a protected national park in the Red Sea, just 45 minutes by "
                    "boat from Hurghada Marina. Famous for its pristine white-sand beaches, "
                    "spectacular coral gardens, and abundant marine life including sea turtles, "
                    "dolphins, and hundreds of tropical fish species. The island is split into "
                    "Big Giftun and Small Giftun, both offering exceptional snorkeling and diving."
                ),
                "color": (255, 200, 50),
            },
            {
                "name": "El Gouna",
                "description": (
                    "El Gouna is an award-winning eco-friendly resort town located 22 km north of "
                    "Hurghada. Built on a series of lagoons and islands, it offers a unique "
                    "Mediterranean-meets-Red Sea atmosphere. The town has its own marina, several "
                    "world-class dive centers, and is a favourite destination for kitesurfing "
                    "enthusiasts. The calm lagoon waters make it ideal for sailing and water sports."
                ),
                "color": (50, 120, 80),
            },
            {
                "name": "Soma Bay",
                "description": (
                    "Soma Bay is an exclusive peninsula 45 km south of Hurghada, surrounded on "
                    "three sides by the Red Sea. Home to luxury resorts and a world-class thalasso "
                    "spa, it is prized for its untouched coral reefs, deep blue waters, and strong "
                    "consistent winds ideal for kite and windsurfing. The house reef runs directly "
                    "off the beach, making snorkeling and shore diving easily accessible."
                ),
                "color": (0, 80, 160),
            },
            {
                "name": "Marsa Alam",
                "description": (
                    "Marsa Alam is a tranquil coastal town in Egypt's Southern Red Sea Governorate, "
                    "240 km south of Hurghada. Known for its pristine and less-visited dive sites, "
                    "dugong sightings, and sea turtle nesting grounds at Wadi El Gemal National "
                    "Park. The waters here are exceptionally clear with visibility often exceeding "
                    "30 metres, making it a paradise for serious divers and underwater photographers."
                ),
                "color": (30, 100, 150),
            },
            {
                "name": "Orange Bay",
                "description": (
                    "Orange Bay is a stunning private island located in the Red Sea near Hurghada, "
                    "accessible only by boat. The island features powder-white sandy beaches, "
                    "crystal-clear shallow waters ideal for families, and beautiful house reefs "
                    "teeming with colourful fish. It is one of the most popular destinations for "
                    "day-trip boat excursions from Hurghada Marina."
                ),
                "color": (255, 140, 0),
            },
            {
                "name": "Mahmya Island",
                "description": (
                    "Mahmya is a private island paradise operated within the Giftun Island National "
                    "Park. It offers organised beach day trips with sunbeds, parasols, water sports, "
                    "and snorkeling activities. The island has a dedicated snorkeling reef with "
                    "impressive coral formations and a wide variety of fish. Transfer is by "
                    "traditional motorised dhow or speedboat from Hurghada Marina."
                ),
                "color": (100, 200, 100),
            },
        ]

        for d in destinations:
            dest, created = Destination.objects.get_or_create(
                name=d["name"],
                defaults={
                    "description": d["description"],
                    "image": _jpeg(f"destination_{d['name'].lower().replace(' ', '_')}.jpg", d["color"]),
                    "is_active": True,
                },
            )
            self.stdout.write(ok(d["name"]) if created else skip(d["name"]))

    # ─── Trip Includes ───────────────────────────────────────────────────────

    def _seed_trip_includes(self):
        self.stdout.write("\n[Trip Includes]")
        from apps.trips.models import TripInclude

        includes = [
            ("Snorkeling Equipment",  (0,   180, 200), "ar", "معدات الغطس", "es", "Equipo de snorkel"),
            ("Lunch & Soft Drinks",   (200, 120, 0),   "ar", "غداء ومشروبات غازية", "es", "Almuerzo y refrescos"),
            ("Life Jackets",          (220, 50,  50),  "ar", "سترات النجاة", "es", "Chalecos salvavidas"),
            ("Towels",                (60,  160, 80),  "ar", "مناشف", "es", "Toallas"),
            ("Underwater Camera",     (90,  60,  180), "ar", "كاميرا تحت الماء", "es", "Cámara subacuática"),
            ("Captain & Crew",        (0,   80,  160), "ar", "الربان والطاقم", "es", "Capitán y tripulación"),
            ("Fishing Gear",          (120, 80,  40),  "ar", "معدات الصيد", "es", "Equipo de pesca"),
            ("BBQ Grill",             (180, 80,  20),  "ar", "شواية بي بي كيو", "es", "Parrilla BBQ"),
            ("Kayak",                 (0,   160, 120), "ar", "كاياك", "es", "Kayak"),
            ("Paddleboard",           (50,  120, 200), "ar", "لوح باددل", "es", "Paddleboard"),
            ("Safety Equipment",      (200, 0,   0),   "ar", "معدات السلامة", "es", "Equipo de seguridad"),
            ("Hotel Transfer",        (80,  40,  120), "ar", "نقل من الفندق", "es", "Traslado al hotel"),
            ("Guided Tour",           (20,  120, 80),  "ar", "جولة مع مرشد سياحي", "es", "Visita guiada"),
            ("Mineral Water",         (100, 180, 220), "ar", "مياه معدنية", "es", "Agua mineral"),
        ]
        from apps.trips.models import TripIncludeTranslation
        for row in includes:
            title, color, lang1, t1, lang2, t2 = row
            inc, created = TripInclude.objects.get_or_create(
                title=title,
                defaults={"image": _jpeg(f"include_{title[:8].lower().replace(' ', '_')}.jpg", color),
                          "is_active": True},
            )
            self.stdout.write(ok(title) if created else skip(title))
            for lang, translated in [(lang1, t1), (lang2, t2)]:
                TripIncludeTranslation.objects.get_or_create(
                    include=inc, language=lang, defaults={"title": translated}
                )

    # ─── Trip Categories ─────────────────────────────────────────────────────

    def _seed_trip_categories(self):
        self.stdout.write("\n[Trip Categories]")
        from apps.trips.models import TripCategory, TripCategoryTranslation

        categories = [
            ("Snorkeling & Diving",  (0,   180, 220), "ar", "الغطس والسباحة", "fr", "Plongée & Snorkeling"),
            ("Fishing Tours",        (80,  60,  20),  "ar", "جولات الصيد", "fr", "Excursions de pêche"),
            ("Sunset Cruises",       (220, 120, 0),   "ar", "رحلات غروب الشمس", "fr", "Croisières coucher de soleil"),
            ("Island Tours",         (255, 200, 50),  "ar", "جولات الجزر", "fr", "Excursions sur les îles"),
            ("Dolphin Watching",     (0,   120, 180), "ar", "مشاهدة الدلافين", "fr", "Observation des dauphins"),
            ("Family Trips",         (100, 200, 100), "ar", "رحلات عائلية", "fr", "Voyages en famille"),
            ("Adventure Trips",      (200, 50,  50),  "ar", "رحلات مغامرة", "fr", "Voyages d'aventure"),
            ("Relaxing Cruises",     (150, 100, 200), "ar", "رحلات استرخاء", "fr", "Croisières détente"),
            ("Party Boats",          (200, 0,   100), "ar", "قوارب الحفلات", "fr", "Bateaux festifs"),
            ("Water Sports",         (0,   160, 220), "ar", "الرياضات المائية", "fr", "Sports nautiques"),
        ]
        for row in categories:
            title, color, l1, t1, l2, t2 = row
            cat, created = TripCategory.objects.get_or_create(
                title=title,
                defaults={"image": _jpeg(f"cat_{title[:8].lower().replace(' &', '').replace(' ', '_')}.jpg", color),
                          "is_active": True},
            )
            self.stdout.write(ok(title) if created else skip(title))
            for lang, translated in [(l1, t1), (l2, t2)]:
                TripCategoryTranslation.objects.get_or_create(
                    category=cat, language=lang, defaults={"title": translated}
                )

    # ─── Rent Categories ─────────────────────────────────────────────────────

    def _seed_rent_categories(self):
        self.stdout.write("\n[Rent Categories]")
        from apps.rents.models import RentCategory, RentCategoryTranslation

        # Fix bad names
        RentCategory.objects.filter(title="Luxury Yachts1").update(title="Private Charter")
        RentCategory.objects.filter(title="Yacht").update(title="Yacht Charter")
        self.stdout.write(fix("Fixed RentCategory names"))

        categories = [
            ("Yacht Charter",       (30,  60,  120), "ar", "تأجير اليخوت", "fr", "Location de yacht"),
            ("Private Charter",     (0,   80,  160), "ar", "تأجير خاص", "fr", "Charte privée"),
            ("Luxury Yachts",       (100, 50,  150), "ar", "يخوت فاخرة", "fr", "Yachts de luxe"),
            ("Speedboat Rental",    (220, 50,  50),  "ar", "تأجير قارب سريع", "fr", "Location hors-bord"),
            ("Catamaran Rental",    (0,   150, 130), "ar", "تأجير كاتاماران", "fr", "Location catamaran"),
            ("Fishing Charter",     (80,  60,  20),  "ar", "رحلة صيد مستأجرة", "fr", "Bateau de pêche"),
            ("Sailing Charter",     (255, 165, 0),   "ar", "تأجير شراعي", "fr", "Charter voilier"),
        ]
        for row in categories:
            title, color, l1, t1, l2, t2 = row
            cat, created = RentCategory.objects.get_or_create(
                title=title,
                defaults={"image": _jpeg(f"rentcat_{title[:8].lower().replace(' ', '_')}.jpg", color),
                          "is_active": True},
            )
            self.stdout.write(ok(title) if created else skip(title))
            for lang, translated in [(l1, t1), (l2, t2)]:
                RentCategoryTranslation.objects.get_or_create(
                    category=cat, language=lang, defaults={"title": translated}
                )

    # ─── Onboarding Screens ──────────────────────────────────────────────────

    def _seed_onboarding_screens(self):
        self.stdout.write("\n[Onboarding Screens]")
        from apps.onboarding.models import OnboardingScreen, OnboardingScreenTranslation

        screens = [
            # Customer screens
            {
                "title": "Discover the Red Sea",
                "description": (
                    "Explore hundreds of boat trips, snorkeling adventures, and private charters "
                    "across Egypt's most stunning Red Sea destinations."
                ),
                "user_type": "customer",
                "order": 1,
                "color": (0, 120, 200),
                "translations": {
                    "ar": ("اكتشف البحر الأحمر",
                           "استكشف مئات الرحلات البحرية وجولات الغطس والرحلات الخاصة في أجمل وجهات البحر الأحمر في مصر."),
                    "fr": ("Découvrez la Mer Rouge",
                           "Explorez des centaines d'excursions en bateau, d'aventures de snorkeling et de charters privés."),
                    "de": ("Entdecken Sie das Rote Meer",
                           "Erkunden Sie Hunderte von Bootstouren, Schnorchelaventeuern und Privatchartern am Roten Meer."),
                    "ru": ("Откройте для себя Красное море",
                           "Изучите сотни лодочных прогулок, снорклинга и частных чартеров на Красном море."),
                },
            },
            {
                "title": "Book Instantly, Pay on Board",
                "description": (
                    "Reserve your spot in seconds. All bookings are cash-on-board — "
                    "no upfront payment required. Flexible cancellation up to 24 hours before."
                ),
                "user_type": "customer",
                "order": 2,
                "color": (0, 160, 130),
                "translations": {
                    "ar": ("احجز فوراً، ادفع على المتن",
                           "احجز مكانك في ثوانٍ. جميع الحجوزات نقدًا على المتن — لا دفع مسبق. إلغاء مرن حتى 24 ساعة قبل."),
                    "fr": ("Réservez instantanément, payez à bord",
                           "Réservez votre place en quelques secondes. Paiement en espèces à bord, aucun paiement préalable."),
                    "de": ("Sofort buchen, an Bord zahlen",
                           "Reservieren Sie Ihren Platz in Sekunden. Zahlung in bar an Bord — keine Vorauszahlung erforderlich."),
                    "ru": ("Бронируйте мгновенно, платите на борту",
                           "Забронируйте место за секунды. Оплата наличными на борту — без предоплаты."),
                },
            },
            {
                "title": "Luxury & Comfort, One Tap Away",
                "description": (
                    "From intimate sunset cruises to full-day island tours — "
                    "find the perfect sea experience tailored to your budget and group size."
                ),
                "user_type": "customer",
                "order": 3,
                "color": (180, 100, 20),
                "translations": {
                    "ar": ("الفخامة والراحة بلمسة واحدة",
                           "من رحلات غروب الشمس الحميمة إلى جولات الجزر ليوم كامل — اعثر على تجربة البحر المثالية."),
                    "fr": ("Luxe et confort, en un tap",
                           "Des croisières au coucher du soleil aux excursions sur les îles pour toute la journée."),
                    "de": ("Luxus und Komfort, ein Tap entfernt",
                           "Von intimen Sonnenuntergangskreuzfahrten bis zu ganztägigen Inseltouren."),
                    "ru": ("Роскошь и комфорт в одно касание",
                           "От интимных закатных круизов до полнодневных островных туров."),
                },
            },
            # Owner screens
            {
                "title": "List Your Boat, Earn More",
                "description": (
                    "Join hundreds of boat owners across the Red Sea. "
                    "List your vessel, set your own prices, and start receiving bookings today."
                ),
                "user_type": "owner",
                "order": 1,
                "color": (20, 60, 120),
                "translations": {
                    "ar": ("أدرج قاربك، اكسب أكثر",
                           "انضم إلى مئات أصحاب القوارب عبر البحر الأحمر. أدرج قاربك، حدد أسعارك، وابدأ باستقبال الحجوزات."),
                    "fr": ("Inscrivez votre bateau, gagnez plus",
                           "Rejoignez des centaines de propriétaires de bateaux en mer Rouge."),
                },
            },
            {
                "title": "Manage Bookings with Ease",
                "description": (
                    "Accept or decline booking requests, track your schedule, "
                    "and communicate with guests — all from one simple dashboard."
                ),
                "user_type": "owner",
                "order": 2,
                "color": (0, 100, 160),
                "translations": {
                    "ar": ("إدارة الحجوزات بسهولة",
                           "قبول أو رفض طلبات الحجز وتتبع جدولك والتواصل مع الضيوف — كل ذلك من لوحة تحكم واحدة."),
                    "fr": ("Gérez vos réservations facilement",
                           "Acceptez ou refusez les demandes de réservation et communiquez avec vos clients."),
                },
            },
            {
                "title": "Grow Your Marine Business",
                "description": (
                    "Get discovered by thousands of travellers visiting the Red Sea every month. "
                    "Build your reputation through verified reviews and ratings."
                ),
                "user_type": "owner",
                "order": 3,
                "color": (0, 130, 100),
                "translations": {
                    "ar": ("طوّر عملك البحري",
                           "اجعل آلاف المسافرين يكتشفونك كل شهر. ابنِ سمعتك من خلال التقييمات والمراجعات الموثقة."),
                    "fr": ("Développez votre activité maritime",
                           "Soyez découvert par des milliers de voyageurs visitant la mer Rouge chaque mois."),
                },
            },
        ]

        for s in screens:
            # Check if a screen with same title and user_type already exists
            existing = OnboardingScreen.objects.filter(
                title=s["title"], user_type=s["user_type"]
            ).first()
            if existing:
                self.stdout.write(skip(f"{s['user_type'].upper()} screen #{s['order']}: {s['title'][:40]}"))
                screen = existing
            else:
                screen = OnboardingScreen.objects.create(
                    title=s["title"],
                    description=s["description"],
                    user_type=s["user_type"],
                    order=s["order"],
                    is_active=True,
                    image=_jpeg(f"onboard_{s['user_type']}_{s['order']}.jpg", s["color"], (800, 600)),
                )
                self.stdout.write(ok(f"{s['user_type'].upper()} screen #{s['order']}: {s['title'][:40]}"))

            for lang, (title, desc) in s.get("translations", {}).items():
                OnboardingScreenTranslation.objects.get_or_create(
                    screen=screen, language=lang,
                    defaults={"title": title, "description": desc},
                )

    # ─── FAQs ────────────────────────────────────────────────────────────────

    def _seed_faqs(self):
        self.stdout.write("\n[FAQs]")
        from apps.FAQ.models import FAQ, FAQTranslation

        # Remove placeholder "string" FAQs
        bad = FAQ.objects.filter(question="string")
        if bad.exists():
            cnt = bad.count()
            bad.delete()
            self.stdout.write(fix(f"Deleted {cnt} placeholder FAQs"))

        customer_faqs = [
            (1, "How do I book a trip or boat?",
             "Browse available trips and rentals, select your preferred date and time, choose your guest count, and tap 'Book Now'. You'll receive a confirmation with your booking reference code instantly. Payment is made in cash on the day of the trip.",
             "كيف أحجز رحلة أو قاربًا؟",
             "تصفح الرحلات والإيجارات المتاحة، اختر تاريخك ووقتك المفضلين، حدد عدد ضيوفك، واضغط على 'احجز الآن'. ستتلقى تأكيدًا برمز الحجز الخاص بك فورًا. الدفع نقدًا في يوم الرحلة."),
            (2, "Can I cancel or modify my booking?",
             "Yes. You can cancel your booking free of charge up to 24 hours before the scheduled start time. Cancellations made less than 24 hours in advance may be subject to the operator's cancellation policy. To modify a booking, cancel it and rebook with the new details.",
             "هل يمكنني إلغاء أو تعديل حجزي؟",
             "نعم. يمكنك إلغاء حجزك مجانًا حتى 24 ساعة قبل وقت البدء المقرر. قد تخضع الإلغاءات التي تتم قبل أقل من 24 ساعة لسياسة الإلغاء الخاصة بالمشغل."),
            (3, "Do I need an account to browse trips?",
             "No. You can browse all available trips and rentals without creating an account. However, you need to sign up to make a booking, save favourites, and access your booking history.",
             "هل أحتاج إلى حساب لتصفح الرحلات؟",
             "لا. يمكنك تصفح جميع الرحلات والإيجارات المتاحة دون إنشاء حساب. ومع ذلك، تحتاج إلى التسجيل لإجراء حجز وحفظ المفضلات والوصول إلى سجل حجوزاتك."),
            (4, "What is included in the trip price?",
             "Inclusions vary by listing and are displayed on each trip's detail page under the 'What's Included' section. Common inclusions are snorkeling equipment, life jackets, and lunch. Always review the inclusions before booking.",
             "ما المدرج في سعر الرحلة؟",
             "تختلف المشمولات حسب القائمة وتُعرض في صفحة تفاصيل كل رحلة تحت قسم 'ما المدرج'. المشمولات الشائعة هي معدات الغطس وسترات النجاة والغداء."),
            (5, "Is it safe to book through Omarine?",
             "Yes. All boat owners and operators listed on Omarine are verified by our team. Boats must hold valid navigation licenses and safety certificates. We also collect and display verified customer reviews so you can make an informed decision.",
             "هل الحجز عبر Omarine آمن؟",
             "نعم. جميع أصحاب القوارب والمشغلين المدرجين على Omarine موثقون من قِبل فريقنا. يجب أن تحمل القوارب رخص ملاحة وشهادات سلامة سارية."),
            (6, "What happens if the trip is cancelled due to weather?",
             "If a trip is cancelled by the operator due to bad weather or safety concerns, you will receive a full refund or the option to reschedule. The operator will notify you as early as possible — usually at least 2 hours before departure.",
             "ماذا يحدث إذا ألغيت الرحلة بسبب الطقس؟",
             "إذا ألغى المشغل الرحلة بسبب سوء الطقس أو مخاوف السلامة، ستحصل على استرداد كامل أو خيار إعادة الجدولة."),
            (7, "How do I leave a review?",
             "After your trip is marked as completed, you can leave a review from the 'My Bookings' section in the app. Your rating and comment help other travellers make better choices.",
             "كيف أترك تقييمًا؟",
             "بعد وضع علامة اكتمال رحلتك، يمكنك ترك تقييم من قسم 'حجوزاتي' في التطبيق."),
            (8, "Can I book for a large group?",
             "Yes. Each listing shows the maximum capacity. For groups larger than the listed capacity, contact the operator directly to arrange a private charter or multiple boats.",
             "هل يمكنني الحجز لمجموعة كبيرة؟",
             "نعم. تعرض كل قائمة الحد الأقصى للسعة. بالنسبة للمجموعات الأكبر من السعة المدرجة، تواصل مع المشغل مباشرة لترتيب رحلة خاصة."),
        ]

        owner_faqs = [
            (1, "How do I list my boat on Omarine?",
             "Create an owner account, complete your profile verification, upload your boat's navigation license and construction certificate, then create your first listing. Our team reviews all submissions within 2-3 business days.",
             "كيف أدرج قاربي على Omarine؟",
             "أنشئ حساب مالك، أكمل التحقق من ملفك الشخصي، ارفع رخصة الملاحة وشهادة إنشاء القارب، ثم أنشئ أول قائمة لك."),
            (2, "What documents do I need to register?",
             "You need: a valid national ID or passport, the boat's navigation license, the boat construction certificate, and either your tax card or commercial registration document.",
             "ما المستندات التي أحتاجها للتسجيل؟",
             "تحتاج إلى: هوية وطنية سارية أو جواز سفر، رخصة الملاحة، شهادة إنشاء القارب، وبطاقة ضريبية أو سجل تجاري."),
            (3, "How long does the verification process take?",
             "Our team typically reviews and responds to new owner applications within 2-3 business days. You will be notified via email and in-app notification once your account is approved or if additional documents are required.",
             "كم يستغرق وقت عملية التحقق؟",
             "يراجع فريقنا عادةً طلبات الملاك الجدد ويرد عليها في غضون 2-3 أيام عمل."),
            (4, "How do I set my pricing?",
             "You have full control over your pricing. Set different rates for full-day and half-day trips, hourly and daily rates for rentals, and separate prices for adults and children. Prices are displayed in the currency you choose.",
             "كيف أحدد أسعاري؟",
             "لديك تحكم كامل في تسعيرك. حدد أسعارًا مختلفة لرحلات اليوم الكامل ونصف اليوم والإيجار بالساعة واليوم."),
            (5, "How do I get paid?",
             "All payments are collected in cash by you directly from the customer on the day of the trip or rental. Omarine does not handle payments — we connect you with customers and handle the booking logistics.",
             "كيف أتلقى الدفع؟",
             "تُجمع جميع المدفوعات نقدًا منك مباشرة من العميل في يوم الرحلة أو الإيجار."),
            (6, "Can I reject or cancel a booking?",
             "Yes. You can decline booking requests before confirming them. Once confirmed, cancellations should only be made for valid reasons such as weather, safety, or mechanical issues. Frequent unjustified cancellations may affect your listing's visibility.",
             "هل يمكنني رفض أو إلغاء حجز؟",
             "نعم. يمكنك رفض طلبات الحجز قبل تأكيدها. بمجرد التأكيد، يجب إجراء الإلغاءات لأسباب وجيهة فقط."),
            (7, "How do customer reviews work?",
             "Customers can leave a review after their trip is completed. Reviews are verified — only customers with confirmed bookings can review your listing. You can respond to reviews from your owner dashboard.",
             "كيف تعمل تقييمات العملاء؟",
             "يمكن للعملاء ترك تقييم بعد اكتمال رحلتهم. التقييمات موثقة — فقط العملاء الذين لديهم حجوزات مؤكدة يمكنهم تقييم قائمتك."),
        ]

        for order, question, answer, ar_q, ar_a in customer_faqs:
            faq, created = FAQ.objects.get_or_create(
                question=question,
                defaults={"answer": answer, "user_type": "customer",
                          "display_order": order, "is_active": True},
            )
            self.stdout.write(ok(f"Customer FAQ: {question[:50]}") if created else skip(question[:50]))
            FAQTranslation.objects.get_or_create(
                faq=faq, language="ar",
                defaults={"question": ar_q, "answer": ar_a},
            )

        for order, question, answer, ar_q, ar_a in owner_faqs:
            faq, created = FAQ.objects.get_or_create(
                question=question,
                defaults={"answer": answer, "user_type": "owner",
                          "display_order": order, "is_active": True},
            )
            self.stdout.write(ok(f"Owner FAQ: {question[:50]}") if created else skip(question[:50]))
            FAQTranslation.objects.get_or_create(
                faq=faq, language="ar",
                defaults={"question": ar_q, "answer": ar_a},
            )

    # ─── About Us ────────────────────────────────────────────────────────────

    def _seed_about_us(self):
        self.stdout.write("\n[About Us]")
        from apps.about_us.models import AboutUs, Value, AboutUsTranslation, ValueTranslation

        if AboutUs.objects.exists():
            self.stdout.write(skip("AboutUs already exists"))
            about = AboutUs.objects.first()
        else:
            about = AboutUs.objects.create(
                title="About Omarine — Your Red Sea Experience Platform",
                description=(
                    "Omarine is Egypt's leading digital marketplace connecting travellers with "
                    "the finest boat trips, snorkeling adventures, fishing tours, and private "
                    "charters across the Red Sea.\n\n"
                    "Founded in Hurghada, we work with a hand-picked network of verified boat "
                    "owners and marine operators who share our commitment to safety, quality, "
                    "and exceptional guest experiences. Whether you're planning a family "
                    "snorkeling day, a romantic sunset cruise, or an adrenaline-packed fishing "
                    "expedition, Omarine helps you discover, compare, and book instantly.\n\n"
                    "Our platform is built on trust: every operator undergoes rigorous "
                    "document verification, every boat holds a valid navigation license, and "
                    "every review comes from a verified booking. We believe the Red Sea's "
                    "breathtaking marine world should be accessible to everyone — safely, "
                    "affordably, and without hassle."
                ),
            )
            self.stdout.write(ok("AboutUs created"))

            AboutUsTranslation.objects.get_or_create(
                about_us=about, language="ar",
                defaults={
                    "title": "عن Omarine — منصتك لتجربة البحر الأحمر",
                    "description": (
                        "Omarine هي السوق الرقمي الرائد في مصر الذي يربط المسافرين بأفضل رحلات القوارب "
                        "وجولات الغطس والصيد والرحلات الخاصة عبر البحر الأحمر.\n\n"
                        "تأسست في الغردقة، ونعمل مع شبكة مختارة بعناية من أصحاب القوارب والمشغلين "
                        "البحريين الموثقين الذين يشاركوننا التزامنا بالسلامة والجودة وتجارب الضيوف الاستثنائية."
                    ),
                },
            )

        values_data = [
            ("Safety First",
             "Every boat on our platform holds a current navigation license and safety certification. "
             "We conduct annual document reviews and suspend listings that fail to maintain compliance.",
             (200, 50, 50),
             "ar", "السلامة أولاً",
             "كل قارب على منصتنا يحمل رخصة ملاحة سارية وشهادة سلامة."),
            ("Verified Operators",
             "We personally vet every boat owner before they can list on Omarine. "
             "National ID, tax documents, and marine licenses are all verified by our team.",
             (0, 120, 180),
             "ar", "مشغلون موثقون",
             "نقوم شخصياً بفحص كل مالك قارب قبل أن يتمكن من الإدراج على Omarine."),
            ("Transparent Pricing",
             "The price you see is the price you pay — in cash on board. "
             "No hidden fees, no service charges, no surprises.",
             (0, 150, 100),
             "ar", "أسعار شفافة",
             "السعر الذي تراه هو السعر الذي تدفعه — نقدًا على المتن. لا رسوم خفية."),
            ("Authentic Reviews",
             "Only customers with confirmed, completed bookings can leave reviews. "
             "We don't allow paid reviews or fake ratings — what you read is what real guests experienced.",
             (150, 100, 200),
             "ar", "تقييمات حقيقية",
             "فقط العملاء الذين لديهم حجوزات مؤكدة ومكتملة يمكنهم ترك تقييمات."),
            ("Local Expertise",
             "We're a Red Sea company, built by people who grew up diving these reefs. "
             "Our local knowledge helps us curate the best experiences and support our operator community.",
             (220, 140, 0),
             "ar", "خبرة محلية",
             "نحن شركة على البحر الأحمر، بنيت من قِبل أشخاص نشأوا وهم يغوصون في هذه الشعاب."),
        ]

        for title, desc, color, lang, ar_title, ar_desc in values_data:
            val, created = Value.objects.get_or_create(
                about_us=about, title=title,
                defaults={"description": desc,
                          "icon": _jpeg(f"value_{title[:6].lower().replace(' ', '_')}.jpg", color, (100, 100))},
            )
            self.stdout.write(ok(f"Value: {title}") if created else skip(f"Value: {title}"))
            ValueTranslation.objects.get_or_create(
                value=val, language=lang,
                defaults={"title": ar_title, "description": ar_desc},
            )

    # ─── Privacy Policy ──────────────────────────────────────────────────────

    def _seed_privacy_policy(self):
        self.stdout.write("\n[Privacy Policy]")
        from apps.privacy_policy.models import PrivacyPolicy, PrivacyPolicyTranslation

        sections = [
            (1, "Information We Collect",
             "We collect information you provide directly when you create an account, make a booking, or contact us. This includes your name, email address, phone number, date of birth, and profile photo. We also collect device information, IP addresses, and usage data to improve our services.",
             "ar", "المعلومات التي نجمعها",
             "نجمع المعلومات التي تقدمها مباشرةً عند إنشاء حساب أو إجراء حجز أو التواصل معنا."),
            (2, "Data Security",
             "We implement industry-standard security measures to protect your personal data, including HTTPS encryption for all data in transit, secure password hashing (bcrypt), and access controls that limit who can view your data within our organisation.",
             "ar", "أمان البيانات",
             "نطبق معايير أمان صناعية لحماية بياناتك الشخصية، بما في ذلك تشفير HTTPS لجميع البيانات أثناء النقل."),
            (3, "How We Use Your Information",
             "We use your information to process bookings, send booking confirmations and reminders, facilitate communication between you and boat operators, improve our platform, send marketing communications (with your consent), and comply with legal obligations.",
             "ar", "كيف نستخدم معلوماتك",
             "نستخدم معلوماتك لمعالجة الحجوزات وإرسال التأكيدات والتذكيرات وتسهيل التواصل بينك وبين مشغلي القوارب."),
            (4, "Information Sharing",
             "We do not sell your personal data. We share your information only with boat operators when you make a booking (name, phone, guest count), payment processors if applicable, and legal authorities when required by law.",
             "ar", "مشاركة المعلومات",
             "لا نبيع بياناتك الشخصية. نشارك معلوماتك فقط مع مشغلي القوارب عند إجراء حجز."),
            (5, "Your Rights",
             "You have the right to access the personal data we hold about you, correct inaccurate data, request deletion of your account and data, withdraw consent for marketing communications, and lodge a complaint with the relevant data protection authority.",
             "ar", "حقوقك",
             "لديك الحق في الوصول إلى بياناتك الشخصية، وتصحيح البيانات غير الدقيقة، وطلب حذف حسابك وبياناتك."),
            (6, "Cookies & Tracking",
             "We use essential cookies to keep you logged in and remember your preferences. We also use analytics cookies to understand how our platform is used. You can opt out of non-essential cookies in your browser settings.",
             "ar", "ملفات تعريف الارتباط والتتبع",
             "نستخدم ملفات تعريف الارتباط الأساسية لإبقائك مسجلاً الدخول وتذكر تفضيلاتك."),
            (7, "Contact Us",
             "For any privacy-related questions or to exercise your data rights, contact our Privacy Team at privacy@omarine.app or write to us at: Omarine, Hurghada Marina, Red Sea Governorate, Egypt.",
             "ar", "تواصل معنا",
             "لأي أسئلة تتعلق بالخصوصية أو لممارسة حقوق بياناتك، تواصل مع فريق الخصوصية لدينا على privacy@omarine.app."),
        ]

        for order, title, content, lang, ar_title, ar_content in sections:
            pp, created = PrivacyPolicy.objects.get_or_create(
                title=title,
                defaults={"content": content, "display_order": order, "is_active": True},
            )
            self.stdout.write(ok(title[:50]) if created else skip(title[:50]))
            PrivacyPolicyTranslation.objects.get_or_create(
                privacy_policy=pp, language=lang,
                defaults={"title": ar_title, "content": ar_content},
            )

    # ─── Terms & Conditions ──────────────────────────────────────────────────

    def _seed_terms_and_conditions(self):
        self.stdout.write("\n[Terms & Conditions]")
        from apps.terms_and_conditions.models import TermsAndConditions, TermsAndConditionsTranslation

        sections = [
            (1, "Eligibility",
             "You must be at least 18 years old to create an account and make bookings on Omarine. By registering, you confirm that the information you provide is accurate and up to date. Omarine reserves the right to suspend or terminate accounts that provide false information.",
             "ar", "الأهلية",
             "يجب أن يكون عمرك 18 عامًا على الأقل لإنشاء حساب وإجراء حجوزات على Omarine."),
            (2, "Bookings & Prices",
             "Prices displayed are per-person rates in the currency shown. Bookings are confirmed upon receiving a confirmation code. All payments are made in cash to the operator on the day of the activity. Omarine is not a party to the financial transaction between customer and operator.",
             "ar", "الحجوزات والأسعار",
             "الأسعار المعروضة هي أسعار لكل شخص بالعملة المبينة. تُؤكد الحجوزات عند استلام رمز التأكيد."),
            (3, "Cancellation Policy",
             "Customers may cancel bookings free of charge up to 24 hours before the scheduled start time. Cancellations within 24 hours are subject to the individual operator's policy. Operators may cancel due to weather or safety — customers will receive a full refund or reschedule option.",
             "ar", "سياسة الإلغاء",
             "يمكن للعملاء إلغاء الحجوزات مجانًا حتى 24 ساعة قبل وقت البدء المقرر."),
            (4, "Availability",
             "All listings are subject to availability. Omarine does not guarantee that a listing will be available on any specific date. We recommend booking in advance, especially during peak season (October–April).",
             "ar", "التوفر",
             "جميع القوائم رهينة بالتوفر. لا تضمن Omarine توفر قائمة في أي تاريخ محدد."),
            (5, "Safety & Liability",
             "All operators on Omarine are required to hold valid navigation licenses and comply with Egyptian maritime safety regulations. Omarine acts as a marketplace and is not directly liable for the quality, safety, or conduct of any listed activity. Participation in water activities carries inherent risk.",
             "ar", "السلامة والمسؤولية",
             "يُطلب من جميع المشغلين على Omarine الحصول على رخص ملاحة سارية والامتثال للوائح السلامة البحرية المصرية."),
            (6, "Operator Obligations",
             "Operators agree to maintain valid boat licenses, provide the services described in their listings, honour confirmed bookings, comply with all applicable safety regulations, and treat all guests with respect regardless of nationality, religion, or gender.",
             "ar", "التزامات المشغل",
             "يوافق المشغلون على الحفاظ على رخص القوارب الصالحة وتقديم الخدمات الموضحة في قوائمهم."),
            (7, "Updates",
             "Omarine reserves the right to update these Terms & Conditions at any time. Users will be notified of significant changes via email or in-app notification. Continued use of the platform after changes constitutes acceptance of the updated terms.",
             "ar", "التحديثات",
             "تحتفظ Omarine بحق تحديث هذه الشروط والأحكام في أي وقت."),
        ]

        for order, title, content, lang, ar_title, ar_content in sections:
            tc, created = TermsAndConditions.objects.get_or_create(
                title=title,
                defaults={"content": content, "display_order": order, "is_active": True},
            )
            self.stdout.write(ok(title[:50]) if created else skip(title[:50]))
            TermsAndConditionsTranslation.objects.get_or_create(
                terms_and_conditions=tc, language=lang,
                defaults={"title": ar_title, "content": ar_content},
            )

    # ─── Report Types ────────────────────────────────────────────────────────

    def _seed_report_types(self):
        self.stdout.write("\n[Report Types]")
        from apps.reports.models import SystemReportType, BookingReportType

        system_types = [
            "App Bug", "Payment Issue", "Account Problem", "Safety Concern",
            "Content Violation", "Inappropriate Behaviour", "Technical Issue", "Other",
        ]
        for t in system_types:
            _, created = SystemReportType.objects.get_or_create(type=t, defaults={"is_active": True})
            self.stdout.write(ok(f"SystemReportType: {t}") if created else skip(t))

        booking_types = [
            "Service Quality", "No-show", "Cancellation Dispute", "Safety Issue",
            "Price Dispute", "Communication Problem", "Boat Condition", "Other",
        ]
        for t in booking_types:
            _, created = BookingReportType.objects.get_or_create(type=t, defaults={"is_active": True})
            self.stdout.write(ok(f"BookingReportType: {t}") if created else skip(t))

    # ─── Owners + Companies + Boats + Trips + Rents ──────────────────────────

    def _seed_owners_and_content(self):
        self.stdout.write("\n[Owners, Boats, Trips & Rents]")
        from apps.users.models import CustomUser, OwnerProfile
        from apps.owner.models import Company
        from apps.boats.models import Boat, BoatType, BoatSpecification
        from apps.amenities.models import Amenity
        from apps.currencies.models import Currency
        from apps.trips.models import Trip, TripCategory, TripImage, TripTranslation, TripInclude
        from apps.rents.models import Rent, RentCategory, RentImage, RentTranslation
        from apps.destination.models import Destination

        egp = Currency.objects.get(code="EGP")
        usd = Currency.objects.get(code="USD")
        amenity_map = {a.name: a for a in Amenity.objects.all()}
        get_amenities = lambda *names: [amenity_map[n] for n in names if n in amenity_map]

        # ── Owner 1: Hassan Omar — Hurghada Marine Tours ──────────────────
        user1_email = "hassan.omar@omarine.com"
        if not CustomUser.objects.filter(email=user1_email).exists():
            user1 = CustomUser.objects.create_user(
                email=user1_email, full_name="Hassan Omar",
                password="Omarine@2025!", account_type="owner", is_verified=True,
                phone_number="+201012345678", gender="male", date_of_birth="1982-06-15",
                address="Hurghada Marina, Red Sea, Egypt",
            )
            owner1: OwnerProfile = OwnerProfile.objects.get(user=user1)
            owner1.verification_status = "approved"
            owner1.save()
            self.stdout.write(ok(f"Owner 1: {user1_email}"))

            Company.objects.create(
                owner=owner1,
                company_name="Hurghada Marine Tours LLC",
                company_phone="+20653456789",
                website="https://www.hurghada-marine.com",
                address="Marina Blvd, Block 3, Hurghada Marina, Red Sea Governorate, Egypt",
                company_logo=_jpeg("hmt_logo.jpg", (0, 80, 160)),
                commercial_record=_pdf("hmt_commercial.pdf"),
                tax_id=_pdf("hmt_tax.pdf"),
            )

            yacht_type = BoatType.objects.filter(name="Yacht").first()
            catamaran_type = BoatType.objects.filter(name="Catamaran").first()
            speedboat_type = BoatType.objects.filter(name="Speedboat").first()

            # Boat A: Luxury Catamaran
            boat_a = Boat.objects.create(
                owner=owner1, boat_type=catamaran_type,
                boat_name="Blue Horizon",
                navigation_license=_pdf("nav_blue_horizon.pdf"),
                boat_construction_certificate=_pdf("cert_blue_horizon.pdf"),
                verification_status="approved",
            )
            BoatSpecification.objects.create(
                boat=boat_a, year=2019, length=Decimal("18.5"), make="Lagoon",
                model="450 F", capacity=20, staterooms=4, bathrooms=4,
            )
            boat_a.amenities.set(get_amenities("snorkeling gear", "life jackets", "towels",
                                               "sun deck", "bathroom", "air conditioning",
                                               "music system", "cooler box", "first aid kit"))

            # Boat B: Speedboat
            boat_b = Boat.objects.create(
                owner=owner1, boat_type=speedboat_type,
                boat_name="Red Arrow",
                navigation_license=_pdf("nav_red_arrow.pdf"),
                boat_construction_certificate=_pdf("cert_red_arrow.pdf"),
                verification_status="approved",
            )
            BoatSpecification.objects.create(
                boat=boat_b, year=2021, length=Decimal("9.2"), make="Bayliner",
                model="VR5", capacity=8, staterooms=0, bathrooms=1,
            )
            boat_b.amenities.set(get_amenities("snorkeling gear", "life jackets", "first aid kit", "cooler box"))

            snorkel_cat = TripCategory.objects.filter(title="Snorkeling & Diving").first()
            island_cat = TripCategory.objects.filter(title="Island Tours").first()
            sunset_cat = TripCategory.objects.filter(title="Sunset Cruises").first()
            fishing_cat = TripCategory.objects.filter(title="Fishing Tours").first()

            includes_all = TripInclude.objects.filter(
                title__in=["Snorkeling Equipment", "Lunch & Soft Drinks", "Life Jackets",
                           "Towels", "Captain & Crew", "Mineral Water"]
            )
            includes_basic = TripInclude.objects.filter(
                title__in=["Snorkeling Equipment", "Life Jackets", "Mineral Water", "Captain & Crew"]
            )
            includes_fishing = TripInclude.objects.filter(
                title__in=["Fishing Gear", "Life Jackets", "Captain & Crew", "Mineral Water", "BBQ Grill"]
            )

            # Trip 1: Giftun Island Full Day
            t1 = Trip.objects.create(
                owner=owner1, category=snorkel_cat,
                name="Giftun Island Snorkeling Full-Day Trip",
                description=(
                    "Sail from Hurghada Marina to the breathtaking Giftun Island National Park — "
                    "one of Egypt's most spectacular protected marine areas. Explore two world-class "
                    "snorkeling sites with vibrant coral reefs teeming with parrotfish, butterflyfish, "
                    "and moray eels. After snorkeling, relax on the pristine white-sand beach of "
                    "Small Giftun with a BBQ lunch, fresh fruit, and cold drinks. Our PADI-certified "
                    "guides accompany you throughout the day to ensure safety and enhance your experience."
                ),
                important_notes=(
                    "Guests must be able to swim. Children under 5 are not permitted for safety reasons. "
                    "Please bring reef-safe sunscreen, a hat, and a change of clothes. "
                    "Trips depart from Hurghada Marina Gate 5 — arrive 15 minutes early. "
                    "The trip may be rescheduled in case of severe weather — full refund will be issued."
                ),
                location_name="Giftun Island National Park, Red Sea, Egypt",
                latitude=Decimal("27.182500"), longitude=Decimal("33.940833"),
                duration_type="both",
                price_adult_full_day=Decimal("650.00"), price_kid_full_day=Decimal("350.00"),
                price_adult_half_day=Decimal("400.00"), price_kid_half_day=Decimal("220.00"),
                currency=egp, max_capacity=20, is_active=True,
                available_days=_both_slots(
                    ("sunday", "monday", "tuesday", "wednesday", "thursday"),
                    full_cap=20, half_cap=14, captain="Ahmed Khalil"
                ),
            )
            t1.includes.set(includes_all)
            for order, color in enumerate([(0,180,220),(255,210,100),(0,80,160),(30,160,90),(220,80,30)]):
                TripImage.objects.create(trip=t1, image=_jpeg(f"giftun_{order+1}.jpg", color), order=order)
            TripTranslation.objects.get_or_create(trip=t1, language="ar", defaults={
                "name": "رحلة الغطس ليوم كامل في جزيرة جفتون",
                "description": "أبحر من مرسى الغردقة إلى المياه النقية حول جزيرة جفتون — إحدى أكثر المناطق البحرية المحمية روعةً في مصر. استكشف موقعين للغطس العالميين مع شعاب مرجانية نابضة بالحياة.",
                "important_notes": "يجب أن يكون الضيوف قادرين على السباحة. لا يُسمح للأطفال دون سن 5 سنوات لأسباب أمنية.",
            })
            self.stdout.write(ok(f"Trip: {t1.name[:50]}"))

            # Trip 2: Orange Bay
            t2 = Trip.objects.create(
                owner=owner1, category=island_cat,
                name="Orange Bay Island Beach Day",
                description=(
                    "Escape to the exclusive Orange Bay Island — a pristine paradise accessible only "
                    "by boat. Spend the day on powder-white sand beaches with crystal-clear shallow "
                    "water ideal for swimming, snorkeling, and water games. The island features "
                    "dedicated snorkeling reefs with magnificent coral formations and colourful fish. "
                    "Enjoy a freshly prepared lunch on board before exploring the island's tranquil "
                    "coves and turquoise lagoons."
                ),
                important_notes=(
                    "Sunscreen (reef-safe recommended), hat, and flip-flops advised. "
                    "Shade areas available on the beach. Children welcome — shallow areas ideal for families. "
                    "No private beach vendors — all facilities provided by our crew."
                ),
                location_name="Orange Bay Island, Red Sea, Egypt",
                latitude=Decimal("27.198611"), longitude=Decimal("33.875000"),
                duration_type="full_day",
                price_adult_full_day=Decimal("550.00"), price_kid_full_day=Decimal("300.00"),
                currency=egp, max_capacity=18, is_active=True,
                available_days=_full_day_slots(
                    ("sunday", "tuesday", "thursday", "saturday"), cap=18, captain="Mostafa Saeed"
                ),
            )
            t2.includes.set(includes_all)
            for order, color in enumerate([(255,140,0),(0,180,200),(255,210,100),(30,160,90)]):
                TripImage.objects.create(trip=t2, image=_jpeg(f"orange_bay_{order+1}.jpg", color), order=order)
            TripTranslation.objects.get_or_create(trip=t2, language="ar", defaults={
                "name": "يوم في جزيرة أورانج باي",
                "description": "اهرب إلى جزيرة Orange Bay الحصرية — جنة لا يمكن الوصول إليها إلا بالقارب. اقضِ اليوم على شواطئ رملية ناصعة البياض.",
                "important_notes": "يُنصح بواقٍ شمسي (يفضل صديق للشعاب المرجانية) وقبعة وشباشب.",
            })
            self.stdout.write(ok(f"Trip: {t2.name[:50]}"))

            # Trip 3: Sunset Cruise
            t3 = Trip.objects.create(
                owner=owner1, category=sunset_cat,
                name="Red Sea Romantic Sunset Cruise",
                description=(
                    "Watch the sun melt into the Red Sea horizon aboard our elegant catamaran. "
                    "This 3-hour evening cruise departs Hurghada Marina at 5:30 PM and sails to "
                    "the best vantage points for the spectacular Red Sea sunset. Enjoy live music, "
                    "a complimentary welcome drink, and a mezze platter as the sky turns shades of "
                    "orange, pink, and crimson. Perfect for couples, special occasions, and anyone "
                    "seeking a magical end to their Red Sea day."
                ),
                important_notes=(
                    "Minimum age 12 years. Smart-casual attire recommended (no swimwear). "
                    "Alcohol available at extra cost. Departs Gate 5, Hurghada Marina at 17:30 sharp. "
                    "Photography is encouraged — the colours at sunset are extraordinary."
                ),
                location_name="Hurghada Marina, Red Sea, Egypt",
                latitude=Decimal("27.218700"), longitude=Decimal("33.837100"),
                duration_type="half_day",
                price_adult_half_day=Decimal("480.00"), price_kid_half_day=Decimal("280.00"),
                currency=egp, max_capacity=16, is_active=True,
                available_days=[
                    {"day": d, "duration_type": "half_day", "start_time": "17:30",
                     "end_time": "20:30", "current_capacity": 16, "captain": "Omar Nasser"}
                    for d in ("tuesday", "thursday", "friday", "saturday", "sunday")
                ],
            )
            t3.includes.set(TripInclude.objects.filter(title__in=["Life Jackets", "Captain & Crew", "Mineral Water"]))
            for order, color in enumerate([(220,80,30),(255,165,0),(180,60,20),(220,120,0)]):
                TripImage.objects.create(trip=t3, image=_jpeg(f"sunset_{order+1}.jpg", color), order=order)
            TripTranslation.objects.get_or_create(trip=t3, language="ar", defaults={
                "name": "رحلة غروب شمس رومانسية في البحر الأحمر",
                "description": "شاهد الشمس تغوص في أفق البحر الأحمر على متن كاتاماراننا الأنيق. تنطلق هذه الرحلة المسائية من مرسى الغردقة في تمام الساعة 5:30 مساءً.",
                "important_notes": "الحد الأدنى للعمر 12 سنة. يُنصح بارتداء ملابس غير رسمية أنيقة.",
            })
            self.stdout.write(ok(f"Trip: {t3.name[:50]}"))

            # Trip 4: Fishing
            t4 = Trip.objects.create(
                owner=owner1, category=fishing_cat,
                name="Deep Sea Fishing Adventure",
                description=(
                    "Join our experienced fishing captain for a thrilling half-day deep-sea fishing "
                    "expedition in the Red Sea. Target species include tuna, barracuda, mackerel, "
                    "and dorado. All fishing equipment is provided including rods, reels, bait, and "
                    "tackle. After the catch, we'll fire up the onboard BBQ grill so you can enjoy "
                    "your fresh catch with sea views. Suitable for beginners and experienced anglers alike."
                ),
                important_notes=(
                    "Motion sickness tablets recommended — bring your own. "
                    "Wear closed-toe shoes on the boat. "
                    "All fish caught belong to the guests — we can assist with packaging for transport. "
                    "No fishing license required for recreational fishing in these waters."
                ),
                location_name="Red Sea Open Waters, Hurghada",
                latitude=Decimal("27.350000"), longitude=Decimal("34.050000"),
                duration_type="half_day",
                price_adult_half_day=Decimal("750.00"),
                currency=egp, max_capacity=8, is_active=True,
                available_days=[
                    {"day": d, "duration_type": "half_day", "start_time": "06:00",
                     "end_time": "12:00", "current_capacity": 8, "captain": "Karim Ali"}
                    for d in ("monday", "wednesday", "friday", "saturday")
                ],
            )
            t4.includes.set(includes_fishing)
            for order, color in enumerate([(50,100,50),(0,80,160),(80,60,20)]):
                TripImage.objects.create(trip=t4, image=_jpeg(f"fishing_{order+1}.jpg", color), order=order)
            self.stdout.write(ok(f"Trip: {t4.name[:50]}"))

            # Rent 1: Luxury Catamaran
            rent_cat1 = RentCategory.objects.filter(title="Catamaran Rental").first() or RentCategory.objects.first()
            dest_hurghada = Destination.objects.filter(name="Hurghada").first()
            r1 = Rent.objects.create(
                owner=owner1, boat=boat_a, category=rent_cat1, destination=dest_hurghada,
                name="Luxury Catamaran 'Blue Horizon' — Private Charter",
                description=(
                    "Charter our stunning 18.5-metre Lagoon 450F catamaran exclusively for your "
                    "group. Perfect for private parties, corporate events, family gatherings, and "
                    "wedding celebrations. The Blue Horizon features 4 spacious staterooms, 4 "
                    "bathrooms, a fully equipped galley, a large shaded cockpit, and an expansive "
                    "trampolene net for sunbathing. Take her anywhere in the Red Sea — our captain "
                    "will plan the perfect route based on your preferences."
                ),
                important_notes=(
                    "Minimum charter: 4 hours. Fuel included for routes within 50 nautical miles of Hurghada Marina. "
                    "Catering options available at additional cost — contact us 48 hours in advance. "
                    "Maximum 20 guests. Skipper is mandatory (included in price)."
                ),
                location_name="Hurghada Marina, Red Sea, Egypt",
                latitude=Decimal("27.218700"), longitude=Decimal("33.837100"),
                duration_type="both",
                price_per_hour=Decimal("1200.00"), price_per_day=Decimal("8500.00"),
                hours_per_day=8, currency=egp, max_capacity=20, is_active=True,
                available_days=_rent_slots(
                    ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"),
                    captain="Ahmed Khalil"
                ),
            )
            for order, color in enumerate([(0,80,160),(0,160,200),(255,210,100),(30,120,80)]):
                RentImage.objects.create(rent=r1, image=_jpeg(f"blue_horizon_{order+1}.jpg", color), order=order)
            RentTranslation.objects.get_or_create(rent=r1, language="ar", defaults={
                "name": "كاتاماران فاخر 'بلو هورايزون' — تأجير خاص",
                "description": "استأجر كاتاماراننا المذهل Lagoon 450F حصريًا لمجموعتك. مثالي للحفلات الخاصة والفعاليات المؤسسية والتجمعات العائلية.",
                "important_notes": "الحد الأدنى للتأجير 4 ساعات. الوقود مدرج للمسارات ضمن 50 ميلًا بحريًا من مرسى الغردقة.",
            })
            self.stdout.write(ok(f"Rent: {r1.name[:50]}"))

            # Rent 2: Speedboat
            rent_cat2 = RentCategory.objects.filter(title="Speedboat Rental").first() or RentCategory.objects.first()
            r2 = Rent.objects.create(
                owner=owner1, boat=boat_b, category=rent_cat2, destination=dest_hurghada,
                name="Speedboat 'Red Arrow' — Hourly Private Rental",
                description=(
                    "Rent our powerful 9.2-metre Bayliner VR5 speedboat for an exhilarating "
                    "private adventure. Perfect for fast island hops, wake-boarding, water-skiing, "
                    "or simply exploring hidden coves and reefs at your own pace. The Red Arrow "
                    "seats up to 8 passengers and is equipped with the latest safety gear. "
                    "Our experienced captain handles navigation so you can focus on the thrill."
                ),
                important_notes=(
                    "Minimum hire: 2 hours. Guests cannot drive the boat — captain mandatory. "
                    "Snorkeling masks available on request. "
                    "Watersports equipment (skis, wakeboard) available at extra cost."
                ),
                location_name="Hurghada Marina, Red Sea, Egypt",
                latitude=Decimal("27.218700"), longitude=Decimal("33.837100"),
                duration_type="hourly",
                price_per_hour=Decimal("550.00"),
                currency=egp, max_capacity=8, is_active=True,
                available_days=_rent_slots(
                    ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"),
                    captain="Mostafa Saeed"
                ),
            )
            for order, color in enumerate([(220,50,50),(0,80,160),(255,165,0)]):
                RentImage.objects.create(rent=r2, image=_jpeg(f"red_arrow_{order+1}.jpg", color), order=order)
            self.stdout.write(ok(f"Rent: {r2.name[:50]}"))

        else:
            self.stdout.write(skip(f"Owner 1 ({user1_email}) already exists — skipping their content"))

        # ── Owner 2: Nour El Baher Tours ─────────────────────────────────────
        user2_email = "captain.nour@omarine.com"
        if not CustomUser.objects.filter(email=user2_email).exists():
            user2 = CustomUser.objects.create_user(
                email=user2_email, full_name="Nour El Baher",
                password="Omarine@2025!", account_type="owner", is_verified=True,
                phone_number="+201109876543", gender="male", date_of_birth="1978-03-22",
                address="El Gouna Marina, Red Sea, Egypt",
            )
            owner2: OwnerProfile = OwnerProfile.objects.get(user=user2)
            owner2.verification_status = "approved"
            owner2.save()
            self.stdout.write(ok(f"Owner 2: {user2_email}"))

            Company.objects.create(
                owner=owner2,
                company_name="Nour El Baher Marine Services",
                company_phone="+20653987654",
                website="https://www.nour-elbaher.com",
                address="El Gouna Marina, Red Sea Governorate, Egypt",
                company_logo=_jpeg("neb_logo.jpg", (0, 160, 120)),
                commercial_record=_pdf("neb_commercial.pdf"),
                tax_id=_pdf("neb_tax.pdf"),
            )

            motor_yacht_type = BoatType.objects.filter(name="Motor Yacht").first()
            sailing_type = BoatType.objects.filter(name="Sailing Boat").first()

            boat_c = Boat.objects.create(
                owner=owner2, boat_type=motor_yacht_type,
                boat_name="Nour Star",
                navigation_license=_pdf("nav_nour_star.pdf"),
                boat_construction_certificate=_pdf("cert_nour_star.pdf"),
                verification_status="approved",
            )
            BoatSpecification.objects.create(
                boat=boat_c, year=2017, length=Decimal("24.0"), make="Azimut",
                model="50", capacity=12, staterooms=3, bathrooms=3,
            )
            boat_c.amenities.set(get_amenities("air conditioning", "life jackets", "wifi",
                                               "satellite tv", "sun deck", "bathroom",
                                               "kitchen", "music system", "first aid kit",
                                               "underwater camera"))

            boat_d = Boat.objects.create(
                owner=owner2, boat_type=sailing_type,
                boat_name="Desert Wind",
                navigation_license=_pdf("nav_desert_wind.pdf"),
                boat_construction_certificate=_pdf("cert_desert_wind.pdf"),
                verification_status="approved",
            )
            BoatSpecification.objects.create(
                boat=boat_d, year=2015, length=Decimal("14.0"), make="Beneteau",
                model="Oceanis 45", capacity=10, staterooms=3, bathrooms=2,
            )
            boat_d.amenities.set(get_amenities("life jackets", "snorkeling gear", "towels",
                                               "cooler box", "first aid kit", "music system"))

            dolphin_cat = TripCategory.objects.filter(title="Dolphin Watching").first()
            adventure_cat = TripCategory.objects.filter(title="Adventure Trips").first()
            family_cat = TripCategory.objects.filter(title="Family Trips").first()
            dest_gouna = Destination.objects.filter(name="El Gouna").first()

            # Trip: Dolphin Watching at Sataya Reef
            t5 = Trip.objects.create(
                owner=owner2, category=dolphin_cat,
                name="Dolphin House — Sunrise Dolphin Watching Tour",
                description=(
                    "Dolphins await! Join us at first light for our legendary early-morning "
                    "expedition to Sha'ab El Erg — known as 'Dolphin House' — where a resident "
                    "pod of spinner dolphins makes their home. Swim alongside these magnificent "
                    "creatures in their natural habitat as they leap and spin around the boat. "
                    "After the dolphin encounter, we visit a stunning coral garden for snorkeling "
                    "before returning to El Gouna marina for breakfast (included)."
                ),
                important_notes=(
                    "Departure is at 6:00 AM — please be at the marina by 5:45 AM. "
                    "Dolphins are wild animals — sightings are highly likely but not 100% guaranteed. "
                    "No touching or chasing dolphins — our guides enforce responsible wildlife guidelines. "
                    "Bring a towel, light jacket, and camera."
                ),
                location_name="Sha'ab El Erg (Dolphin House), Red Sea, Egypt",
                latitude=Decimal("27.350000"), longitude=Decimal("33.720000"),
                duration_type="half_day",
                price_adult_half_day=Decimal("95.00"),
                currency=usd, max_capacity=12, is_active=True,
                available_days=[
                    {"day": d, "duration_type": "half_day", "start_time": "06:00",
                     "end_time": "11:00", "current_capacity": 12, "captain": "Walid Ibrahim"}
                    for d in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
                ],
            )
            t5.includes.set(TripInclude.objects.filter(
                title__in=["Snorkeling Equipment", "Life Jackets", "Mineral Water", "Captain & Crew", "Guided Tour"]
            ))
            for order, color in enumerate([(0,120,180),(30,160,200),(255,210,100),(0,160,130)]):
                TripImage.objects.create(trip=t5, image=_jpeg(f"dolphins_{order+1}.jpg", color), order=order)
            TripTranslation.objects.get_or_create(trip=t5, language="ar", defaults={
                "name": "رحلة مشاهدة الدلافين عند الشروق في 'بيت الدلافين'",
                "description": "انضم إلينا عند الفجر لرحلتنا الصباحية الأسطورية إلى شعاب El Erg — المعروف بـ'بيت الدلافين' — حيث يسكن قرد من الدلافين الغازية.",
                "important_notes": "الإقلاع في الساعة 6:00 صباحًا — يرجى التواجد في المرسى في الساعة 5:45.",
            })
            self.stdout.write(ok(f"Trip: {t5.name[:50]}"))

            # Trip: Sailing Sunset
            t6 = Trip.objects.create(
                owner=owner2, category=sunset_cat if 'sunset_cat' in dir() else TripCategory.objects.first(),
                name="Traditional Sailing Dhow — Sunset & Stars",
                description=(
                    "Experience the ancient magic of Red Sea sailing aboard our beautifully restored "
                    "traditional wooden dhow. Depart El Gouna marina at golden hour and sail "
                    "silently across the glassy evening sea as the sun sinks below the horizon. "
                    "As darkness falls, far from city lights, the Red Sea sky reveals thousands of "
                    "stars. The journey ends with mint tea, Egyptian sweets, and stories from our "
                    "experienced crew who have sailed these waters for generations."
                ),
                important_notes=(
                    "This is a quiet, traditional experience — not suitable for loud parties. "
                    "Bring a light jacket as evenings can be breezy. "
                    "No snorkeling on this trip — it is a pure sailing experience."
                ),
                location_name="El Gouna Marina, Red Sea, Egypt",
                latitude=Decimal("27.385800"), longitude=Decimal("33.674200"),
                duration_type="half_day",
                price_adult_half_day=Decimal("65.00"),
                currency=usd, max_capacity=10, is_active=True,
                available_days=[
                    {"day": d, "duration_type": "half_day", "start_time": "16:30",
                     "end_time": "20:00", "current_capacity": 10, "captain": "Hassan Barakat"}
                    for d in ("tuesday", "thursday", "saturday", "sunday")
                ],
            )
            t6.includes.set(TripInclude.objects.filter(
                title__in=["Life Jackets", "Captain & Crew", "Mineral Water"]
            ))
            for order, color in enumerate([(255,165,0),(180,80,20),(30,30,80),(100,60,20)]):
                TripImage.objects.create(trip=t6, image=_jpeg(f"dhow_sail_{order+1}.jpg", color), order=order)
            self.stdout.write(ok(f"Trip: {t6.name[:50]}"))

            # Rent: Motor Yacht
            rent_cat_yacht = RentCategory.objects.filter(title="Yacht Charter").first()
            r3 = Rent.objects.create(
                owner=owner2, boat=boat_c, category=rent_cat_yacht, destination=dest_gouna,
                name="Motor Yacht 'Nour Star' — Luxury Private Charter",
                description=(
                    "Charter the magnificent Azimut 50 'Nour Star' for an unparalleled Red Sea "
                    "experience. This 24-metre motor yacht is the pinnacle of luxury afloat — "
                    "featuring a spacious sundeck with sunbeds, a fully air-conditioned salon with "
                    "satellite TV, a state-of-the-art sound system, and a galley stocked with "
                    "your preferred beverages and snacks. Whether you're hosting a corporate event, "
                    "celebrating a special milestone, or seeking total privacy, the Nour Star delivers."
                ),
                important_notes=(
                    "Minimum charter: 6 hours. Professional catering available (advance notice required). "
                    "Maximum 12 guests for daytime charter; 8 overnight. "
                    "Overnight stays available — contact us for custom pricing."
                ),
                location_name="El Gouna Marina, Red Sea, Egypt",
                latitude=Decimal("27.385800"), longitude=Decimal("33.674200"),
                duration_type="both",
                price_per_hour=Decimal("250.00"), price_per_day=Decimal("1600.00"),
                hours_per_day=8, currency=usd, max_capacity=12, is_active=True,
                available_days=_rent_slots(
                    ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"),
                    captain="Walid Ibrahim"
                ),
            )
            for order, color in enumerate([(30,60,120),(0,120,180),(255,210,100),(0,80,60)]):
                RentImage.objects.create(rent=r3, image=_jpeg(f"nour_star_{order+1}.jpg", color), order=order)
            RentTranslation.objects.get_or_create(rent=r3, language="ar", defaults={
                "name": "يخت موتوري 'نور ستار' — تأجير خاص فاخر",
                "description": "استأجر يخت Azimut 50 الرائع 'نور ستار' لتجربة لا مثيل لها في البحر الأحمر. هذا اليخت البالغ طوله 24 مترًا هو قمة الفخامة.",
                "important_notes": "الحد الأدنى للتأجير 6 ساعات. خدمات تقديم الطعام المهنية متاحة بإشعار مسبق.",
            })
            self.stdout.write(ok(f"Rent: {r3.name[:50]}"))

        else:
            self.stdout.write(skip(f"Owner 2 ({user2_email}) already exists — skipping their content"))

    # ─── Customers + Bookings ────────────────────────────────────────────────

    def _seed_customers_and_bookings(self):
        self.stdout.write("\n[Customers, Bookings & Reviews]")
        from apps.users.models import CustomUser, CustomerProfile
        from apps.currencies.models import Currency
        from apps.trips.models import Trip
        from apps.rents.models import Rent
        from apps.bookings.models import Booking
        from apps.reviews.models import Review
        from apps.favorites.models import Favorite
        from apps.notifications.models import Notification
        import datetime

        egp = Currency.objects.get(code="EGP")
        usd = Currency.objects.filter(code="USD").first()

        customers_data = [
            ("sofia.mueller@gmail.com",  "Sofia Mueller",  "+49123456789",  "female", "1990-07-22", "Munich, Germany"),
            ("james.carter@icloud.com",  "James Carter",   "+447911123456", "male",   "1985-11-08", "London, UK"),
            ("amira.hassan@yahoo.com",   "Amira Hassan",   "+201234567890", "female", "1995-03-14", "Cairo, Egypt"),
            ("oleg.petrov@mail.ru",      "Oleg Petrov",    "+79161234567",  "male",   "1980-09-30", "Moscow, Russia"),
            ("marie.dubois@orange.fr",   "Marie Dubois",   "+33612345678",  "female", "1992-05-19", "Paris, France"),
        ]

        created_customers = []
        for email, name, phone, gender, dob, address in customers_data:
            if CustomUser.objects.filter(email=email).exists():
                self.stdout.write(skip(f"Customer: {email}"))
                created_customers.append(CustomUser.objects.get(email=email))
            else:
                cust = CustomUser.objects.create_user(
                    email=email, full_name=name, password="Omarine@2025!",
                    account_type="customer", is_verified=True,
                    phone_number=phone, gender=gender, date_of_birth=dob, address=address,
                )
                created_customers.append(cust)
                self.stdout.write(ok(f"Customer: {email}"))

        # ── Bookings for seeded trips ─────────────────────────────────────
        try:
            t1 = Trip.objects.filter(name="Giftun Island Snorkeling Full-Day Trip").first()
            t2 = Trip.objects.filter(name="Orange Bay Island Beach Day").first()
            t3 = Trip.objects.filter(name="Red Sea Romantic Sunset Cruise").first()
            t5 = Trip.objects.filter(name="Dolphin House — Sunrise Dolphin Watching Tour").first()
            r1 = Rent.objects.filter(name__startswith="Luxury Catamaran").first()
            r3 = Rent.objects.filter(name__startswith="Motor Yacht").first()
        except Exception:
            self.stdout.write(self.style.WARNING("  Some trips/rents not found — skipping bookings"))
            return

        bookings_spec = [
            # (customer_idx, type, trip_or_rent, date, start, end, adults, kids, total, currency, status, dur_type)
            (0, "trip", t1, "2026-04-20", "08:00", "16:30", 2, 1, Decimal("1650.00"), egp, "confirmed", "full_day"),
            (1, "trip", t1, "2026-04-22", "08:00", "12:30", 2, 0, Decimal("800.00"), egp, "confirmed", "half_day"),
            (2, "trip", t2, "2026-04-25", "08:00", "16:00", 4, 2, Decimal("2800.00"), egp, "pending", "full_day"),
            (3, "trip", t5, "2026-04-18", "06:00", "11:00", 3, 0, Decimal("285.00"), usd or egp, "completed", "half_day"),
            (4, "trip", t3, "2026-04-26", "17:30", "20:30", 2, 0, Decimal("960.00"), egp, "confirmed", "half_day"),
            (0, "rent", r1, "2026-05-01", "09:00", "17:00", 8, 4, Decimal("8500.00"), egp, "confirmed", "daily"),
            (1, "rent", r3, "2026-04-30", "10:00", "18:00", 6, 2, Decimal("1600.00"), usd or egp, "pending", "daily"),
            (2, "trip", t1, "2026-03-15", "08:00", "16:30", 2, 0, Decimal("1300.00"), egp, "completed", "full_day"),
            (3, "trip", t5, "2026-03-10", "06:00", "11:00", 2, 1, Decimal("285.00"), usd or egp, "completed", "half_day"),
            (4, "trip", t2, "2026-03-20", "08:00", "16:00", 3, 1, Decimal("1950.00"), egp, "completed", "full_day"),
        ]

        created_bookings = []
        for spec in bookings_spec:
            ci, btype, listing, date_str, start, end, adults, kids, total, curr, status, dur = spec
            if listing is None:
                continue
            customer = created_customers[ci]

            # Check if booking already exists for this customer + listing + date
            existing = Booking.objects.filter(
                customer=customer,
                booking_date=datetime.date.fromisoformat(date_str),
                booking_type=btype,
            )
            if btype == "trip":
                existing = existing.filter(trip=listing)
            else:
                existing = existing.filter(rent=listing)

            if existing.exists():
                self.stdout.write(skip(f"Booking for {customer.email} on {date_str}"))
                created_bookings.append(existing.first())
                continue

            b = Booking(
                customer=customer,
                booking_type=btype,
                booking_date=datetime.date.fromisoformat(date_str),
                start_time=datetime.time.fromisoformat(start),
                end_time=datetime.time.fromisoformat(end),
                duration_type=dur,
                adults_count=adults, kids_count=kids,
                total_price=total, currency=curr,
                payment_method="cash", payment_status="pending" if status == "pending" else "paid",
                status=status,
                timezone="Africa/Cairo",
            )
            if btype == "trip":
                b.trip = listing
            else:
                b.rent = listing
                b.hours = 8
            b.save()
            created_bookings.append(b)
            self.stdout.write(ok(f"Booking: {customer.email} — {btype} on {date_str} [{status}]"))

        # ── Reviews for completed bookings ─────────────────────────────
        reviews_data = [
            # (customer_idx, trip_name, rating, comment)
            (3, "Dolphin House — Sunrise Dolphin Watching Tour", Decimal("5.0"),
             "Absolutely magical experience! We swam with a pod of about 30 spinner dolphins for nearly 45 minutes. Captain Walid was knowledgeable and respectful of the animals — no chasing, just patient waiting and the dolphins came right to us. The early wake-up is 100% worth it. Already booked for next year."),
            (2, "Giftun Island Snorkeling Full-Day Trip", Decimal("4.5"),
             "Beautiful trip to Giftun Island. The coral reefs were stunning and we saw sea turtles, lionfish, and so many colourful fish. Lunch was delicious — fresh grilled fish on the beach. My only minor note is that the boat was slightly crowded (18 people) but nothing that ruined the experience. Ahmed (captain) was excellent."),
            (4, "Orange Bay Island Beach Day", Decimal("5.0"),
             "Orange Bay is paradise! The beach is absolutely pristine and the water is so clear you can see the bottom even in 5 metres. Great family trip — my kids (8 and 11) loved it. The crew were attentive and friendly. We'll definitely come back."),
            (3, "Dolphin House — Sunrise Dolphin Watching Tour", Decimal("4.5"),
             "Amazing morning out on the water. We saw dolphins within the first 20 minutes which was exciting. The snorkeling after was also great. The only thing was it was a very early start (5:45 AM!) but once you're on the water you forget about sleep immediately."),
        ]

        for ci, trip_name, rating, comment in reviews_data:
            customer = created_customers[ci]
            trip = Trip.objects.filter(name=trip_name).first()
            if not trip:
                continue
            if Review.objects.filter(reviewer=customer, trip=trip).exists():
                self.stdout.write(skip(f"Review by {customer.email} on {trip_name[:30]}"))
                continue
            Review.objects.create(reviewer=customer, trip=trip, rating=rating, comment=comment)
            self.stdout.write(ok(f"Review: {customer.email} → {trip_name[:40]} [{rating}★]"))

        # ── Favorites ─────────────────────────────────────────────────
        fav_data = [
            (0, "trip", "Giftun Island Snorkeling Full-Day Trip"),
            (0, "trip", "Red Sea Romantic Sunset Cruise"),
            (1, "trip", "Dolphin House — Sunrise Dolphin Watching Tour"),
            (1, "rent", "Luxury Catamaran 'Blue Horizon' — Private Charter"),
            (2, "trip", "Orange Bay Island Beach Day"),
            (3, "trip", "Deep Sea Fishing Adventure"),
            (4, "trip", "Traditional Sailing Dhow — Sunset & Stars"),
        ]

        for ci, ftype, name in fav_data:
            customer = created_customers[ci]
            if ftype == "trip":
                listing = Trip.objects.filter(name=name).first()
            else:
                listing = Rent.objects.filter(name__startswith=name[:30]).first()
            if not listing:
                continue
            kwargs = {"user": customer, "product_type": ftype}
            if ftype == "trip":
                kwargs["trip"] = listing
                if Favorite.objects.filter(user=customer, trip=listing).exists():
                    self.stdout.write(skip(f"Fav: {customer.email} → {name[:30]}"))
                    continue
            else:
                kwargs["rent"] = listing
                if Favorite.objects.filter(user=customer, rent=listing).exists():
                    self.stdout.write(skip(f"Fav: {customer.email} → {name[:30]}"))
                    continue
            Favorite.objects.create(**kwargs)
            self.stdout.write(ok(f"Fav: {customer.email} → {name[:30]}"))

        # ── Notifications ─────────────────────────────────────────────
        if created_customers:
            notif_data = [
                (0, "booking_confirmed", "Booking Confirmed!", "Your booking for Giftun Island Snorkeling Full-Day Trip on April 20 is confirmed. See you at the marina!", {"booking_ref": "BK-SEED0001"}),
                (1, "booking_confirmed", "Booking Confirmed!", "Your booking for Dolphin House Tour on April 18 is confirmed. Departure at 6:00 AM.", {"booking_ref": "BK-SEED0002"}),
                (2, "booking_pending", "Booking Received", "We've received your booking request for Orange Bay on April 25. The operator will confirm shortly.", {"booking_ref": "BK-SEED0003"}),
                (3, "review_reminder", "How was your trip?", "You recently completed a Dolphin House tour. Share your experience — it helps other travellers!", {}),
                (4, "trip_reminder", "Your trip is tomorrow!", "Reminder: Your Red Sea Romantic Sunset Cruise departs tomorrow at 17:30 from Gate 5, Hurghada Marina.", {}),
            ]
            for ci, ntype, title, message, data in notif_data:
                customer = created_customers[ci]
                if not Notification.objects.filter(user=customer, type=ntype, title=title).exists():
                    Notification.objects.create(user=customer, type=ntype, title=title, message=message, data=data)
                    self.stdout.write(ok(f"Notification: {customer.email} — {title[:40]}"))

    # ─── Update Placeholder Trips ────────────────────────────────────────────

    def _update_placeholder_trips(self):
        """Give realistic names/data to the test trips that are linked to real bookings."""
        self.stdout.write("\n[Updating Placeholder Trips]")
        from apps.trips.models import Trip, TripCategory, TripTranslation
        from apps.currencies.models import Currency
        from decimal import Decimal

        egp = Currency.objects.filter(code="EGP").first()
        snorkel_cat = TripCategory.objects.filter(title="Snorkeling & Diving").first()
        island_cat = TripCategory.objects.filter(title="Island Tours").first()
        fishing_cat = TripCategory.objects.filter(title="Fishing Tours").first()
        relaxing_cat = TripCategory.objects.filter(title="Relaxing Cruises").first()
        family_cat = TripCategory.objects.filter(title="Family Trips").first()
        sunset_cat = TripCategory.objects.filter(title="Sunset Cruises").first()
        adventure_cat = TripCategory.objects.filter(title="Adventure Trips").first()

        # Real trip data for placeholder trips
        trip_updates = {
            35: {
                "name": "Mahmya Island Full-Day Beach & Snorkel",
                "description": "A full-day escape to Mahmya — the Red Sea's most beautiful private island. Enjoy pristine white beaches, excellent house reef snorkeling, sunbeds, and fresh seafood lunch. The island operates a strict environmental policy: no plastic, no noise, just natural beauty.",
                "important_notes": "Reef-safe sunscreen only. Arrive at pier by 7:45 AM. Sunbeds included. No outside food.",
                "location_name": "Mahmya Island, Red Sea, Egypt",
                "latitude": Decimal("27.197778"), "longitude": Decimal("33.898333"),
                "category": island_cat,
                "price_adult_full_day": Decimal("700.00"), "price_kid_full_day": Decimal("380.00"),
                "price_adult_half_day": None, "price_kid_half_day": None,
                "duration_type": "full_day",
                "available_days": [{"day": d, "duration_type": "full_day", "start_time": "08:00", "end_time": "16:30", "current_capacity": 25, "captain": "Yasser Fouad"} for d in ("sunday","monday","tuesday","wednesday","thursday","friday","saturday")],
            },
            34: {
                "name": "Shaab El Erg Snorkeling & Dolphin Watch",
                "description": "Head out to the legendary Shaab El Erg reef — home to resident spinner dolphins and one of Hurghada's finest snorkeling sites. With luck, you'll swim alongside dolphins in their natural habitat before exploring the spectacular coral gardens.",
                "important_notes": "Early departure (7:00 AM). Dolphins are wild — sightings not guaranteed. Bring towel and reef-safe sunscreen.",
                "location_name": "Shaab El Erg, Red Sea, Egypt",
                "latitude": Decimal("27.350000"), "longitude": Decimal("33.720000"),
                "category": snorkel_cat,
                "price_adult_full_day": None, "price_kid_full_day": None,
                "price_adult_half_day": Decimal("620.00"), "price_kid_half_day": Decimal("340.00"),
                "duration_type": "half_day",
                "available_days": [{"day": d, "duration_type": "half_day", "start_time": "07:00", "end_time": "12:00", "current_capacity": 20, "captain": "Karim Farouk"} for d in ("monday","wednesday","friday","saturday","sunday")],
            },
            33: {
                "name": "Paradise Island & Coral Garden Snorkeling",
                "description": "Sail to Paradise Island — a stunning stretch of white sand surrounded by turquoise shallows — then dive into the vibrant coral gardens of Abu Ramada Island. Two incredible snorkeling sites, beach time, and a hot lunch make this the perfect Red Sea day.",
                "important_notes": "Suitable for all ages including non-swimmers (life jackets provided). Departs 8:00 AM from Hurghada Marina.",
                "location_name": "Paradise Island, Red Sea, Egypt",
                "latitude": Decimal("27.145000"), "longitude": Decimal("33.915000"),
                "category": island_cat,
                "price_adult_full_day": Decimal("580.00"), "price_kid_full_day": Decimal("320.00"),
                "price_adult_half_day": None, "price_kid_half_day": None,
                "duration_type": "full_day",
                "available_days": [{"day": d, "duration_type": "full_day", "start_time": "08:00", "end_time": "15:30", "current_capacity": 22, "captain": "Amr Hassan"} for d in ("sunday","tuesday","thursday","saturday")],
            },
        }

        # Names for the batch of NAME trips (22-32)
        name_trips = [
            (32, "Glass Bottom Boat Coral Reef Tour", snorkel_cat, Decimal("350.00"), Decimal("200.00"), None, None, "full_day", "27.218700", "33.837100", "Hurghada Marina Reef, Red Sea"),
            (31, "Red Sea Family Snorkeling Adventure", family_cat, Decimal("520.00"), Decimal("280.00"), None, None, "full_day", "27.182500", "33.940833", "Giftun Seagate, Red Sea"),
            (30, "Hurghada Sunset Party Cruise", sunset_cat, None, None, Decimal("430.00"), Decimal("250.00"), "half_day", "27.218700", "33.837100", "Hurghada Marina, Red Sea"),
            (29, "Abu Ramada Island Snorkeling Day Trip", snorkel_cat, Decimal("600.00"), Decimal("330.00"), None, None, "full_day", "27.145000", "33.915000", "Abu Ramada Island, Red Sea"),
            (28, "Red Sea Fishing & BBQ Half Day Tour", fishing_cat, None, None, Decimal("680.00"), None, "half_day", "27.350000", "34.050000", "Red Sea Open Waters, Hurghada"),
            (25, "Relaxing Snorkeling & Beach Combo", relaxing_cat, Decimal("480.00"), Decimal("270.00"), Decimal("300.00"), Decimal("180.00"), "both", "27.182500", "33.940833", "Giftun Island Area, Red Sea"),
            (24, "Private Island Beach Escape", island_cat, Decimal("650.00"), Decimal("360.00"), None, None, "full_day", "27.198611", "33.875000", "Orange Bay Area, Red Sea"),
            (23, "Red Sea Snorkeling Discovery Tour", snorkel_cat, None, None, Decimal("390.00"), Decimal("220.00"), "half_day", "27.182500", "33.940833", "Giftun Reef, Red Sea"),
            (22, "Sailing & Snorkeling Half Day Adventure", adventure_cat, None, None, Decimal("450.00"), Decimal("250.00"), "half_day", "27.218700", "33.837100", "Hurghada Offshore Reefs"),
            (21, "Coral Garden Exploration Tour", snorkel_cat, Decimal("520.00"), Decimal("290.00"), None, None, "full_day", "27.145000", "33.915000", "Abu Ramada Reef, Red Sea"),
            (6, "Giftun Island Classic Snorkeling Trip", snorkel_cat, Decimal("550.00"), Decimal("300.00"), Decimal("350.00"), Decimal("200.00"), "both", "27.182500", "33.940833", "Giftun Island, Red Sea"),
        ]

        # Update specific trips
        for pk, updates in trip_updates.items():
            try:
                t = Trip.objects.get(pk=pk)
                for field, val in updates.items():
                    setattr(t, field, val)
                t.save()
                self.stdout.write(ok(f"Updated Trip [{pk}]: {updates['name'][:50]}"))
            except Trip.DoesNotExist:
                pass

        # Update batch trips
        for pk, name, cat, p_af, p_kf, p_ah, p_kh, dur, lat, lon, loc in name_trips:
            try:
                t = Trip.objects.get(pk=pk)
                t.name = name
                t.category = cat
                t.location_name = loc
                t.latitude = Decimal(lat)
                t.longitude = Decimal(lon)
                t.price_adult_full_day = p_af
                t.price_kid_full_day = p_kf
                t.price_adult_half_day = p_ah
                t.price_kid_half_day = p_kh
                t.duration_type = dur
                if not t.description or t.description in ("description", "desc", ""):
                    t.description = f"An exciting Red Sea experience — {name}. Explore the stunning marine life and beautiful landscapes of the Hurghada coast."
                if not t.currency_id:
                    t.currency = egp
                if not t.max_capacity or t.max_capacity > 200:
                    t.max_capacity = 20
                if not t.available_days:
                    t.available_days = [{"day": d, "duration_type": dur if dur != "both" else "full_day", "start_time": "08:00", "end_time": "16:00", "current_capacity": 20, "captain": "Captain"} for d in ("sunday", "monday", "wednesday", "friday")]
                t.save()
                self.stdout.write(ok(f"Updated Trip [{pk}]: {name[:50]}"))
            except Trip.DoesNotExist:
                pass

        # Fix "string" trip (pk=6)
        try:
            t6 = Trip.objects.get(pk=6, name__in=["string", "Giftun Island Classic Snorkeling Trip"])
            if t6.name == "string":
                t6.name = "Giftun Island Classic Snorkeling Trip"
                t6.location_name = "Giftun Island, Red Sea, Egypt"
                t6.latitude = Decimal("27.182500")
                t6.longitude = Decimal("33.940833")
                t6.save()
                self.stdout.write(ok("Fixed 'string' trip → Giftun Island Classic Snorkeling Trip"))
        except Trip.DoesNotExist:
            pass

        self.stdout.write(ok("Placeholder trip updates complete"))
