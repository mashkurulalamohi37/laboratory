"""Bangladesh geography reference data (seeded in every environment, idempotent).

All 8 divisions and 64 districts. Upazila/thana and area coverage is currently limited to
the Dhaka and Chattogram metropolitan thanas used by the launch centres; import the full
BBS geocode list before opening home collection outside those areas.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text import slugify
from app.modules.geo.models import Area, District, Division, Upazila

# division: (name_bn, [(district, district_bn), ...])
DIVISIONS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "Barishal": (
        "বরিশাল",
        [
            ("Barguna", "বরগুনা"),
            ("Barishal", "বরিশাল"),
            ("Bhola", "ভোলা"),
            ("Jhalokati", "ঝালকাঠি"),
            ("Patuakhali", "পটুয়াখালী"),
            ("Pirojpur", "পিরোজপুর"),
        ],
    ),
    "Chattogram": (
        "চট্টগ্রাম",
        [
            ("Bandarban", "বান্দরবান"),
            ("Brahmanbaria", "ব্রাহ্মণবাড়িয়া"),
            ("Chandpur", "চাঁদপুর"),
            ("Chattogram", "চট্টগ্রাম"),
            ("Cox's Bazar", "কক্সবাজার"),
            ("Cumilla", "কুমিল্লা"),
            ("Feni", "ফেনী"),
            ("Khagrachhari", "খাগড়াছড়ি"),
            ("Lakshmipur", "লক্ষ্মীপুর"),
            ("Noakhali", "নোয়াখালী"),
            ("Rangamati", "রাঙ্গামাটি"),
        ],
    ),
    "Dhaka": (
        "ঢাকা",
        [
            ("Dhaka", "ঢাকা"),
            ("Faridpur", "ফরিদপুর"),
            ("Gazipur", "গাজীপুর"),
            ("Gopalganj", "গোপালগঞ্জ"),
            ("Kishoreganj", "কিশোরগঞ্জ"),
            ("Madaripur", "মাদারীপুর"),
            ("Manikganj", "মানিকগঞ্জ"),
            ("Munshiganj", "মুন্সিগঞ্জ"),
            ("Narayanganj", "নারায়ণগঞ্জ"),
            ("Narsingdi", "নরসিংদী"),
            ("Rajbari", "রাজবাড়ী"),
            ("Shariatpur", "শরীয়তপুর"),
            ("Tangail", "টাঙ্গাইল"),
        ],
    ),
    "Khulna": (
        "খুলনা",
        [
            ("Bagerhat", "বাগেরহাট"),
            ("Chuadanga", "চুয়াডাঙ্গা"),
            ("Jashore", "যশোর"),
            ("Jhenaidah", "ঝিনাইদহ"),
            ("Khulna", "খুলনা"),
            ("Kushtia", "কুষ্টিয়া"),
            ("Magura", "মাগুরা"),
            ("Meherpur", "মেহেরপুর"),
            ("Narail", "নড়াইল"),
            ("Satkhira", "সাতক্ষীরা"),
        ],
    ),
    "Mymensingh": (
        "ময়মনসিংহ",
        [
            ("Jamalpur", "জামালপুর"),
            ("Mymensingh", "ময়মনসিংহ"),
            ("Netrokona", "নেত্রকোণা"),
            ("Sherpur", "শেরপুর"),
        ],
    ),
    "Rajshahi": (
        "রাজশাহী",
        [
            ("Bogura", "বগুড়া"),
            ("Chapai Nawabganj", "চাঁপাইনবাবগঞ্জ"),
            ("Joypurhat", "জয়পুরহাট"),
            ("Naogaon", "নওগাঁ"),
            ("Natore", "নাটোর"),
            ("Pabna", "পাবনা"),
            ("Rajshahi", "রাজশাহী"),
            ("Sirajganj", "সিরাজগঞ্জ"),
        ],
    ),
    "Rangpur": (
        "রংপুর",
        [
            ("Dinajpur", "দিনাজপুর"),
            ("Gaibandha", "গাইবান্ধা"),
            ("Kurigram", "কুড়িগ্রাম"),
            ("Lalmonirhat", "লালমনিরহাট"),
            ("Nilphamari", "নীলফামারী"),
            ("Panchagarh", "পঞ্চগড়"),
            ("Rangpur", "রংপুর"),
            ("Thakurgaon", "ঠাকুরগাঁও"),
        ],
    ),
    "Sylhet": (
        "সিলেট",
        [
            ("Habiganj", "হবিগঞ্জ"),
            ("Moulvibazar", "মৌলভীবাজার"),
            ("Sunamganj", "সুনামগঞ্জ"),
            ("Sylhet", "সিলেট"),
        ],
    ),
}

# district: [(thana/upazila, bn, [(area, area_bn, postcode | None), ...]), ...]
UPAZILAS: dict[str, list[tuple[str, str, list[tuple[str, str, str | None]]]]] = {
    "Dhaka": [
        (
            "Dhanmondi",
            "ধানমন্ডি",
            [
                ("Dhanmondi R/A", "ধানমন্ডি আ/এ", None),
                ("Jigatola", "জিগাতলা", None),
                ("Kalabagan", "কলাবাগান", None),
            ],
        ),
        (
            "Gulshan",
            "গুলশান",
            [
                ("Gulshan 1", "গুলশান ১", "1212"),
                ("Gulshan 2", "গুলশান ২", "1212"),
                ("Niketan", "নিকেতন", "1212"),
            ],
        ),
        (
            "Banani",
            "বনানী",
            [("Banani", "বনানী", "1213"), ("Banani DOHS", "বনানী ডিওএইচএস", None)],
        ),
        (
            "Mirpur",
            "মিরপুর",
            [
                ("Mirpur 1", "মিরপুর ১", "1216"),
                ("Mirpur 2", "মিরপুর ২", "1216"),
                ("Mirpur 10", "মিরপুর ১০", "1216"),
            ],
        ),
        (
            "Pallabi",
            "পল্লবী",
            [("Mirpur 11", "মিরপুর ১১", "1216"), ("Mirpur 12", "মিরপুর ১২", "1216")],
        ),
        (
            "Uttara",
            "উত্তরা",
            [
                ("Uttara Sector 3", "উত্তরা সেক্টর ৩", "1230"),
                ("Uttara Sector 7", "উত্তরা সেক্টর ৭", "1230"),
                ("Uttara Sector 10", "উত্তরা সেক্টর ১০", "1230"),
            ],
        ),
        (
            "Mohammadpur",
            "মোহাম্মদপুর",
            [
                ("Mohammadpur", "মোহাম্মদপুর", "1207"),
                ("Lalmatia", "লালমাটিয়া", "1207"),
                ("Shyamoli", "শ্যামলী", None),
            ],
        ),
        ("Tejgaon", "তেজগাঁও", [("Farmgate", "ফার্মগেট", None), ("Tejgaon I/A", "তেজগাঁও শি/এ", None)]),
        ("Badda", "বাড্ডা", [("Merul Badda", "মেরুল বাড্ডা", None), ("Uttar Badda", "উত্তর বাড্ডা", None)]),
        ("Motijheel", "মতিঝিল", [("Motijheel C/A", "মতিঝিল বা/এ", "1000")]),
        ("Ramna", "রমনা", [("Shantinagar", "শান্তিনগর", None), ("Eskaton", "ইস্কাটন", None)]),
        ("Khilgaon", "খিলগাঁও", [("Khilgaon", "খিলগাঁও", None), ("Basabo", "বাসাবো", None)]),
        ("Savar", "সাভার", []),
        ("Keraniganj", "কেরাণীগঞ্জ", []),
    ],
    "Chattogram": [
        (
            "Panchlaish",
            "পাঁচলাইশ",
            [("GEC Circle", "জিইসি মোড়", None), ("Nasirabad", "নাসিরাবাদ", None)],
        ),
        ("Double Mooring", "ডবলমুরিং", [("Agrabad", "আগ্রাবাদ", None)]),
        ("Kotwali", "কোতোয়ালী", []),
        ("Khulshi", "খুলশী", []),
        ("Halishahar", "হালিশহর", []),
    ],
}


def _code(*parts: str) -> str:
    return "-".join(slugify(p) for p in parts)


async def _upsert(session: AsyncSession, model: type, code: str, **fields: object) -> object:
    row = await session.scalar(select(model).where(model.code == code))  # type: ignore[attr-defined]
    if row is None:
        row = model(code=code, **fields)
        session.add(row)
        await session.flush()
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    return row


async def seed_geo(session: AsyncSession) -> tuple[int, int, int, int]:
    counts = [0, 0, 0, 0]
    districts: dict[str, District] = {}
    for division_name, (division_bn, district_rows) in DIVISIONS.items():
        division = await _upsert(
            session, Division, _code(division_name), name=division_name, name_bn=division_bn
        )
        assert isinstance(division, Division)
        counts[0] += 1
        for name, name_bn in district_rows:
            district = await _upsert(
                session, District, _code(name), name=name, name_bn=name_bn, division_id=division.id
            )
            assert isinstance(district, District)
            districts[name] = district
            counts[1] += 1
    for district_name, upazilas in UPAZILAS.items():
        district = districts[district_name]
        for name, name_bn, areas in upazilas:
            upazila = await _upsert(
                session,
                Upazila,
                _code(district_name, name),
                name=name,
                name_bn=name_bn,
                district_id=district.id,
            )
            assert isinstance(upazila, Upazila)
            counts[2] += 1
            for area, area_bn, postcode in areas:
                await _upsert(
                    session,
                    Area,
                    _code(district_name, name, area),
                    name=area,
                    name_bn=area_bn,
                    upazila_id=upazila.id,
                    postcode=postcode,
                )
                counts[3] += 1
    return counts[0], counts[1], counts[2], counts[3]
