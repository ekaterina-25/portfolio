"""
Synthetic spare parts data generator for duplicate detection portfolio demo.

Generates two Excel files in the data/ subfolder:
  spare_parts_system1.xlsx  –  single-file, multi-column duplicate detection
  spare_parts_system2.xlsx  –  cross-file comparison (simulates two ERP systems)

Duplicate rate ~18 %: duplicates are detectable only by combining Name +
Description + Specification, because each variant has different fields filled —
mimicking real PIM data entry inconsistencies across users and legacy systems.
Missing values in ~35 % of rows reflect real-world data quality issues.
"""
import os
import random
import pandas as pd
import numpy as np

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Finnish translations ──────────────────────────────────────────────────────
# Used to populate description_fi for ~60 % of rows (the rest are left empty,
# mimicking real catalogs where translations are incomplete).
DESC_FI = {
    "DEEP GROOVE BALL BEARING":      "URASULJETTU KUULALAAKERI",
    "CYLINDRICAL ROLLER BEARING":    "LIERIÖRULLALAAKERI",
    "THRUST BALL BEARING":           "AKSIAALIPALLOLAAKERI",
    "TAPERED ROLLER BEARING":        "KARTIORULLALAAKERI",
    "ANGULAR CONTACT BALL BEARING":  "VIISTOKUULALAAKERI",
    "PILLOW BLOCK UNIT":             "LAAKERIPESÄYKSIKKÖ",
    "FLANGED BEARING UNIT":          "LAIPPALAAKERIRYHMÄ",
    "NEEDLE ROLLER BEARING":         "NEULARULLALAAKERI",
    "SPHERICAL ROLLER BEARING":      "ITSEOHJAUTUVA RULLALAAKERI",
    "ROTARY SHAFT SEAL":             "AKSELITIIVISTE",
    "ROTARY SHAFT SEAL FKM":         "AKSELITIIVISTE FKM",
    "O-RING SEALING":                "O-RENGAS TIIVISTE",
    "O-RING SEALING FKM":            "O-RENGAS TIIVISTE FKM",
    "FLAT GASKET FLANGE":            "LAIPPATIIVISTE",
    "SOFT CUT GASKET":               "PEHMEÄ TIIVISTE",
    "SPIRAL WOUND GASKET":           "SPIRAALITIIVISTE",
    "HEXAGON HEAD BOLT":             "KUUSIORUUVI",
    "HEXAGON NUT":                   "KUUSIOMUTTERI",
    "STUD BOLT THREADED ROD":        "TAPPIRUUVI",
    "SPRING LOCK WASHER":            "JOUSIALUSLEVY",
    "FLAT WASHER":                   "ALUSLEVY",
    "SOCKET HEAD CAP SCREW":         "SISÄKUUSIORUUVI",
    "HYDRAULIC FILTER ELEMENT":      "HYDRAULIIKKASUODATINELEMENTTI",
    "LUBE OIL FILTER ELEMENT":       "VOITELUÖLJYSUODATIN",
    "AIR PANEL FILTER":              "ILMANSUODATIN",
    "GEAR OIL FILTER":               "VAIHTEISTOÖLJYSUODATIN",
    "RETURN LINE FILTER":            "PALUULINJASUODATIN",
    "SUCTION STRAINER BASKET":       "IMUSUODATIN",
    "DUPLEX FILTER ELEMENT":         "KAKSOISPESISUODATINELEMENTTI",
    "FILLER BREATHER FILTER":        "TÄYTTÖILMANSUODATIN",
    "BALL VALVE FULL BORE":          "PALLOVENTTIILI TÄYSAUKKO",
    "GATE VALVE CAST IRON":          "LUISTIVENTTIILI VALURAUTA",
    "BUTTERFLY VALVE WAFER TYPE":    "LÄPPÄVENTTIILI",
    "CHECK VALVE SWING TYPE":        "TAKAISKUVENTTIILI",
    "PRESSURE REDUCING VALVE":       "PAINEENALENNUSVENTTIILI",
    "SAFETY RELIEF VALVE":           "VAROVENTTIILI",
    "CENTRIFUGAL PUMP END SUCTION":  "KESKIPAKOPUMPPU",
    "GEAR PUMP":                     "HAMMASPYÖRÄPUMPPU",
    "DIAPHRAGM VALVE":               "KALVOVENTTIILI",
    "CONTACTOR 3-POLE":              "KONTAKTORI 3-NAPAINEN",
    "INDUCTION MOTOR 3-PHASE":       "OIKOSULKUMOOTTORI 3-VAIHE",
    "CYLINDRICAL FUSE gG":           "SYLINTERISULAKE gG",
    "THERMAL OVERLOAD RELAY":        "YLIKUORMITUSRELE",
    "MINIATURE CIRCUIT BREAKER":     "JOHDONSUOJAKATKAISIJA",
    "MOULDED CASE CIRCUIT BREAKER":  "KOMPAKTI JOHDONSUOJAKATKAISIJA",
    "INDUCTIVE PROXIMITY SENSOR":    "INDUKTIIVINEN LÄHESTYMISANTURI",
    "VARIABLE SPEED DRIVE":          "TAAJUUSMUUTTAJA",
    "SOLENOID VALVE COIL":           "MAGNEETTIVENTTIILIKELA",
    "PRESSURE TRANSMITTER":          "PAINEANTURI",
    "RTD TEMPERATURE SENSOR":        "PT100 LÄMPÖTILA-ANTURI",
    "ELECTROMAGNETIC FLOW METER":    "MAGNEETTINEN VIRTAUSMITTARI",
    "LIMIT SWITCH":                  "RAJAKYTKIN",
    "PUSH BUTTON MOMENTARY":         "HETKELLINEN PAINIKE",
    "INDICATOR LIGHT LED":           "MERKKIVALO LED",
    "CABLE GLAND METRIC":            "KAAPELILÄPIVIENTI",
}


def get_desc_fi(desc_en: str) -> str | None:
    """
    Look up the Finnish translation for an English description.
    Handles descriptions with size suffixes like 'DEEP GROOVE BALL BEARING 25X52X15MM'
    by stripping the suffix, translating the base text, and re-attaching the suffix.
    Returns None if no translation exists.
    """
    if not desc_en:
        return None
    if desc_en in DESC_FI:
        return DESC_FI[desc_en]
    # Try removing trailing size/spec suffix (e.g. "40X80X18MM" or "25MM BORE")
    import re
    base = re.sub(r'\s+[\dX][\w.X]*$', '', desc_en).strip()
    if base in DESC_FI:
        suffix = desc_en[len(base):].strip()
        return f"{DESC_FI[base]} {suffix}"
    return None


# ── Product templates ────────────────────────────────────────────────────────
# 30 "featured" products — each generates 2 duplicate rows with different
# field combinations.  The canonical tuple is (name, description, specification).

PRODUCTS = [
    # Bearings
    {"id": "P001", "cat": "Bearings", "mfr": "SKF", "unit": "PCS",
     "can": ("BALL BEARING 6205 2RS", "DEEP GROOVE BALL BEARING", "6205-2RS1 25X52X15MM"),
     "an": ["BEARING BALL 6205 2RS", "BRG BALL 6205", "BALL BRG 6205-2RS"],
     "ad": ["BALL BEARING", "BEARING RADIAL BALL", "DEEP GROOVE BRG"],
     "as": ["6205 2RS 25X52X15", "6205-2RS SKF 25X52", "25X52X15 6205"]},
    {"id": "P002", "cat": "Bearings", "mfr": "FAG", "unit": "PCS",
     "can": ("BALL BEARING 6206 2RS", "DEEP GROOVE BALL BEARING", "6206-2RS1 30X62X16MM"),
     "an": ["BEARING BALL 6206", "BRG 6206 2RS", "BALL BRG 6206-2RS"],
     "ad": ["BALL BEARING 6206", "BEARING RADIAL", "DEEP GROOVE BRG 6206"],
     "as": ["6206 2RS 30X62X16", "6206-2RS1 FAG", "30X62X16 6206"]},
    {"id": "P003", "cat": "Bearings", "mfr": "NSK", "unit": "PCS",
     "can": ("BALL BEARING 6207 2RS", "DEEP GROOVE BALL BEARING", "6207-2RS1 35X72X17MM"),
     "an": ["BEARING BALL 6207", "BRG 6207", "BALL BRG 6207 2RS"],
     "ad": ["BALL BEARING 6207", "BEARING BALL", "BRG RADIAL 6207"],
     "as": ["6207 2RS 35X72X17", "6207-2RS NSK", "6207 2RS1 35X72"]},
    {"id": "P004", "cat": "Bearings", "mfr": "SKF", "unit": "PCS",
     "can": ("CYLINDRICAL ROLLER BEARING NU205", "CYLINDRICAL ROLLER BEARING", "NU205 ECP 25X52X15MM"),
     "an": ["ROLLER BEARING NU205", "CYL ROLLER BRG NU205", "BRG CYL NU205"],
     "ad": ["CYL ROLLER BEARING", "BEARING CYLINDRICAL ROLLER", "CYL ROLLER BRG"],
     "as": ["NU205 ECP SKF", "NU205 25X52X15", "NU 205 ECP"]},
    {"id": "P005", "cat": "Bearings", "mfr": "NSK", "unit": "PCS",
     "can": ("THRUST BEARING 51205", "THRUST BALL BEARING", "51205 25X47X15MM"),
     "an": ["BALL THRUST BEARING 51205", "BRG THRUST 51205", "AXIAL BRG 51205"],
     "ad": ["THRUST BEARING AXIAL", "AXIAL BALL BEARING", "THRUST BRG"],
     "as": ["51205 NSK 25X47X15", "51205 25X47", "51-205"]},
    {"id": "P006", "cat": "Bearings", "mfr": "FAG", "unit": "PCS",
     "can": ("BALL BEARING 6305 2RS", "DEEP GROOVE BALL BEARING", "6305-2RS1 25X62X17MM"),
     "an": ["BEARING BALL 6305 2RS", "BRG 6305", "BALL BRG 6305-2RS"],
     "ad": ["BALL BEARING 6305", "BEARING RADIAL BALL 6305", "DEEP GROOVE BRG 6305"],
     "as": ["6305 2RS 25X62X17", "6305-2RS FAG", "6305 2RS1 25X62"]},
    # Seals & Gaskets
    {"id": "P007", "cat": "Seals & Gaskets", "mfr": "SIMRIT", "unit": "PCS",
     "can": ("OIL SEAL 40X60X10 NBR", "ROTARY SHAFT SEAL", "40X60X10 NBR DIN 3760"),
     "an": ["SHAFT SEAL 40X60X10", "SEAL OIL 40-60-10", "ROTARY SEAL 40X60"],
     "ad": ["OIL SEAL", "ROTARY SHAFT SL", "SEAL ROTARY NBR"],
     "as": ["40X60X10 NBR", "40-60-10 NBR DIN3760", "D40 D60 W10 NBR"]},
    {"id": "P008", "cat": "Seals & Gaskets", "mfr": "SIMRIT", "unit": "PCS",
     "can": ("OIL SEAL 50X70X10 FKM", "ROTARY SHAFT SEAL FKM", "50X70X10 FKM DIN 3760"),
     "an": ["SHAFT SEAL 50X70X10 VITON", "SEAL OIL 50-70-10 FKM", "ROTARY SEAL FKM 50X70"],
     "ad": ["OIL SEAL FKM", "ROTARY SHAFT SL FKM", "VITON SEAL"],
     "as": ["50X70X10 FKM", "50-70-10 FKM DIN3760", "D50 D70 W10 FKM"]},
    {"id": "P009", "cat": "Seals & Gaskets", "mfr": None, "unit": "PCS",
     "can": ("O-RING 50X3 NBR", "O-RING SEALING", "50X3 NBR 70 SHORE DIN 3771"),
     "an": ["ORING 50X3 NBR", "RING SEAL 50X3", "O RING D50 W3"],
     "ad": ["O-RING NBR", "SEALING RING", "O RING"],
     "as": ["D50 W3 NBR", "50X3 NBR DIN3771", "50-3 NBR 70SH"]},
    {"id": "P010", "cat": "Seals & Gaskets", "mfr": None, "unit": "PCS",
     "can": ("O-RING 60X3 FKM", "O-RING SEALING FKM", "60X3 FKM 80 SHORE DIN 3771"),
     "an": ["ORING 60X3 FKM", "RING SEAL 60X3 VITON", "O RING D60 W3 FKM"],
     "ad": ["O-RING FKM VITON", "SEALING RING FKM", "O RING FKM"],
     "as": ["D60 W3 FKM", "60X3 FKM DIN3771", "60-3 FKM 80SH"]},
    {"id": "P011", "cat": "Seals & Gaskets", "mfr": None, "unit": "PCS",
     "can": ("FLAT GASKET DN50 EPDM", "FLAT GASKET FLANGE", "DN50 PN16 EPDM 3MM DIN 2690"),
     "an": ["FLANGE GASKET DN50 EPDM", "GASKET FLAT DN50", "GASKET DN50 3MM"],
     "ad": ["FLAT GASKET", "FLANGE GASKET", "GASKET EPDM DN50"],
     "as": ["DN50 PN16 EPDM", "DN50 3MM EPDM DIN2690", "DN50 PN16 3MM EPDM"]},
    {"id": "P030", "cat": "Seals & Gaskets", "mfr": "SIMRIT", "unit": "PCS",
     "can": ("OIL SEAL 30X50X8 NBR", "ROTARY SHAFT SEAL", "30X50X8 NBR DIN 3760"),
     "an": ["SHAFT SEAL 30X50X8", "SEAL OIL 30-50-8", "ROTARY SEAL 30X50"],
     "ad": ["OIL SEAL NBR 30X50", "ROTARY SHAFT SL", "SEAL ROTARY"],
     "as": ["30X50X8 NBR", "30-50-8 NBR DIN3760", "D30 D50 W8 NBR"]},
    # Bolts & Fasteners
    {"id": "P012", "cat": "Bolts & Fasteners", "mfr": None, "unit": "PCS",
     "can": ("HEX BOLT M8X30 8.8", "HEXAGON HEAD BOLT", "M8X30 GRADE 8.8 ISO 4014"),
     "an": ["BOLT HEX M8X30", "HEX SCR M8X30 8.8", "HEXBOLT M8X30"],
     "ad": ["HEX BOLT DIN 933", "HEXAGON BOLT", "BOLT HEX HEAD"],
     "as": ["M8 X 30 8.8", "M8X30 8.8 ISO4014", "M8X30 GR8.8"]},
    {"id": "P013", "cat": "Bolts & Fasteners", "mfr": None, "unit": "PCS",
     "can": ("HEX BOLT M10X40 8.8", "HEXAGON HEAD BOLT", "M10X40 GRADE 8.8 ISO 4014"),
     "an": ["BOLT HEX M10X40", "HEX SCR M10X40 8.8", "HEXBOLT M10X40"],
     "ad": ["HEX BOLT", "HEXAGON BOLT M10", "BOLT HEX HEAD M10"],
     "as": ["M10 X 40 8.8", "M10X40 8.8 ISO4014", "M10X40 GR8.8"]},
    {"id": "P014", "cat": "Bolts & Fasteners", "mfr": None, "unit": "PCS",
     "can": ("HEX BOLT M12X50 8.8", "HEXAGON HEAD BOLT", "M12X50 GRADE 8.8 ISO 4014 HDG"),
     "an": ["BOLT HEX M12X50", "HEX SCR M12X50 8.8", "HEXBOLT M12X50"],
     "ad": ["HEX BOLT M12", "HEXAGON BOLT M12", "BOLT M12X50"],
     "as": ["M12 X 50 8.8", "M12X50 8.8 ISO4014", "M12X50 GR8.8"]},
    {"id": "P015", "cat": "Bolts & Fasteners", "mfr": None, "unit": "PCS",
     "can": ("HEX NUT M12 8", "HEXAGON NUT", "M12 GRADE 8 ISO 4032 HDG"),
     "an": ["NUT HEX M12", "HEX NUT M12 GR8", "HEXNUT M12"],
     "ad": ["HEX NUT DIN 934", "HEXAGON NUT M12", "NUT HEX M12"],
     "as": ["M12 8 ISO4032", "M12 GR8", "M12 GRADE8 HDG"]},
    {"id": "P016", "cat": "Bolts & Fasteners", "mfr": None, "unit": "PCS",
     "can": ("STUD BOLT M16X120 B7", "STUD BOLT THREADED ROD", "M16X120 ASTM A193 B7 HDG"),
     "an": ["BOLT STUD M16X120", "THREADED ROD M16X120 B7", "STUD M16X120"],
     "ad": ["STUD BOLT", "THREADED STUD M16", "STUD BOLT A193"],
     "as": ["M16 X 120 B7", "M16X120 A193-B7", "M16X120 GRADE B7"]},
    {"id": "P017", "cat": "Bolts & Fasteners", "mfr": None, "unit": "PCS",
     "can": ("HEX BOLT M16X60 10.9", "HEXAGON HEAD BOLT", "M16X60 GRADE 10.9 ISO 4014"),
     "an": ["BOLT HEX M16X60", "HEX SCR M16X60 10.9", "HEXBOLT M16X60"],
     "ad": ["HEX BOLT HIGH TENSILE", "HEXAGON BOLT M16", "BOLT HHB M16"],
     "as": ["M16 X 60 10.9", "M16X60 10.9 ISO4014", "M16X60 GR10.9"]},
    # Filters
    {"id": "P018", "cat": "Filters", "mfr": "HYDAC", "unit": "PCS",
     "can": ("HYDRAULIC FILTER ELEMENT 10 MICRON", "HYDRAULIC FILTER ELEMENT", "10 MICRON BETA 10=200 DN20 250 BAR"),
     "an": ["HYD FILTER ELEM 10UM", "FILTER HYD 10 MICRON", "HYDAC FILTER ELEMENT 10U"],
     "ad": ["FILTER ELEMENT HYD", "HYD FILTER", "HYDRAULIC FLT ELEMENT"],
     "as": ["10UM BETA10=200", "10 MICRON 250BAR", "10U DN20 250BAR"]},
    {"id": "P019", "cat": "Filters", "mfr": "HYDAC", "unit": "PCS",
     "can": ("HYDRAULIC FILTER ELEMENT 25 MICRON", "HYDRAULIC FILTER ELEMENT", "25 MICRON BETA 25=200 DN20 250 BAR"),
     "an": ["HYD FILTER ELEM 25UM", "FILTER HYD 25 MICRON", "FILTER ELEMENT 25U"],
     "ad": ["FILTER ELEMENT HYD 25", "HYD FILTER 25U", "HYDRAULIC FLT ELEM 25"],
     "as": ["25UM BETA25=200", "25 MICRON 250BAR", "25U DN20 250BAR"]},
    {"id": "P020", "cat": "Filters", "mfr": "PARKER", "unit": "PCS",
     "can": ("OIL FILTER ELEMENT", "LUBE OIL FILTER ELEMENT", "DN50 40 MICRON 16 BAR"),
     "an": ["LUBE OIL FILTER ELEM", "FILTER ELEMENT OIL", "OIL FLT ELEMENT"],
     "ad": ["OIL FILTER", "LUBRICATING OIL FLT", "FILTER ELEMENT LUBE"],
     "as": ["DN50 40U 16BAR", "40 MICRON DN50", "40UM 16BAR DN50"]},
    # Pumps & Valves
    {"id": "P021", "cat": "Pumps & Valves", "mfr": "SPIRAX", "unit": "PCS",
     "can": ("BALL VALVE DN25 PN16", "BALL VALVE FULL BORE", "DN25 PN16 SS316 ISO 17292"),
     "an": ["VALVE BALL DN25 16BAR", "BALL VLV DN25 SS316", "FULL BORE BALL VALVE DN25"],
     "ad": ["BALL VALVE SS", "VALVE BALL STAINLESS", "BALL VLV FB"],
     "as": ["DN25 PN16 SS316", "1 INCH PN16 316SS", "DN25 16BAR SS"]},
    {"id": "P022", "cat": "Pumps & Valves", "mfr": "SPIRAX", "unit": "PCS",
     "can": ("BALL VALVE DN50 PN16", "BALL VALVE FULL BORE", "DN50 PN16 SS316 ISO 17292"),
     "an": ["VALVE BALL DN50 16BAR", "BALL VLV DN50 SS316", "FULL BORE BALL VALVE DN50"],
     "ad": ["BALL VALVE DN50 SS", "VALVE BALL STAINLESS DN50", "BALL VLV FB DN50"],
     "as": ["DN50 PN16 SS316", "2 INCH PN16 316SS", "DN50 16BAR SS"]},
    {"id": "P023", "cat": "Pumps & Valves", "mfr": "KSB", "unit": "PCS",
     "can": ("GATE VALVE DN50 PN10", "GATE VALVE CAST IRON", "DN50 PN10 GG25 DIN 3352"),
     "an": ["VALVE GATE DN50 PN10", "GATE VLV DN50 CI", "SLUICE VALVE DN50"],
     "ad": ["GATE VALVE CI", "VALVE GATE CAST IRON", "GATE VLV GG25"],
     "as": ["DN50 PN10 GG25", "DN50 10BAR CAST IRON", "DN50 PN10 DIN3352"]},
    {"id": "P024", "cat": "Pumps & Valves", "mfr": "KSB", "unit": "PCS",
     "can": ("CHECK VALVE DN40 PN16", "CHECK VALVE SWING TYPE", "DN40 PN16 CI DIN 3850"),
     "an": ["VALVE CHECK DN40 PN16", "NON-RETURN VALVE DN40", "CHECK VLV DN40"],
     "ad": ["CHECK VALVE CI", "NON-RETURN VALVE", "SWING CHECK VLV"],
     "as": ["DN40 PN16 CAST IRON", "DN40 16BAR DIN3850", "DN40 PN16 GG25"]},
    {"id": "P025", "cat": "Pumps & Valves", "mfr": "GRUNDFOS", "unit": "PCS",
     "can": ("CENTRIFUGAL PUMP 2.2KW", "CENTRIFUGAL PUMP END SUCTION", "Q=10M3/H H=20M 2.2KW 1450RPM DN50"),
     "an": ["PUMP CENTRIFUGAL 2.2KW", "END SUCTION PUMP 2.2KW", "CENTRIFUGAL PUMP DN50"],
     "ad": ["CENTRIFUGAL PUMP", "PUMP END SUCTION", "WATER PUMP CENTRIFUGAL"],
     "as": ["10M3/H 20M 2.2KW DN50", "Q10 H20 2.2KW 1450RPM", "DN50 2.2KW GRUNDFOS"]},
    # Electrical
    {"id": "P026", "cat": "Electrical", "mfr": "ABB", "unit": "PCS",
     "can": ("CONTACTOR 9A 24VDC", "CONTACTOR 3-POLE", "9A 24VDC COIL AC3 IEC 60947-4"),
     "an": ["MOTOR CONTACTOR 9A 24V", "3P CONTACTOR 9A", "CONTACTOR ABB 9A"],
     "ad": ["CONTACTOR 3P AC3", "MOTOR CONTACTOR", "CONTACTOR ELEC 3-POLE"],
     "as": ["9A 24VDC IEC60947", "9A AC3 24V COIL", "3P 9A 24VDC"]},
    {"id": "P027", "cat": "Electrical", "mfr": "ABB", "unit": "PCS",
     "can": ("ELECTRIC MOTOR 1.5KW 4P", "INDUCTION MOTOR 3-PHASE", "1.5KW 4POLE 400V 50HZ IE3 B3 IEC63"),
     "an": ["MOTOR ELEC 1.5KW 4POLE", "INDUCTION MTR 1.5KW", "3PH MOTOR 1.5KW"],
     "ad": ["ELECTRIC MOTOR 3PH", "INDUCTION MOTOR", "MTR 3-PHASE IEC"],
     "as": ["1.5KW 1500RPM 400V", "1.5KW 4P IE3 IEC63", "1.5KW 400V 50HZ 4P"]},
    {"id": "P028", "cat": "Electrical", "mfr": "BUSSMANN", "unit": "PCS",
     "can": ("FUSE 16A 500V gG", "CYLINDRICAL FUSE gG", "16A 500V gG 10X38MM IEC 60269"),
     "an": ["FUSE ELEMENT 16A 500V", "CARTRIDGE FUSE 16A gG", "FUSE 16A gG 10X38"],
     "ad": ["FUSE CYLINDRICAL", "FUSE gG 16A", "CARTRIDGE FUSE"],
     "as": ["16A gG 10X38 500V", "16A 500V 10X38 gG", "16A gG IEC60269"]},
    {"id": "P029", "cat": "Electrical", "mfr": "SICK", "unit": "PCS",
     "can": ("PROXIMITY SWITCH M18 PNP", "INDUCTIVE PROXIMITY SENSOR", "M18 10-30VDC PNP NO 5MM RANGE IP67"),
     "an": ["INDUCTIVE SENSOR M18 PNP", "PROXIMITY SENSOR 10-30V", "PROX SWITCH M18"],
     "ad": ["INDUCTIVE SENSOR", "PROXIMITY SWITCH PNP", "PROX SENSOR M18"],
     "as": ["M18 PNP NO 24VDC IP67", "M18 5MM 10-30VDC PNP", "M18 PNP NO IP67"]},
]

# ── Duplicate generation ──────────────────────────────────────────────────────
# Patterns for distributing product info across columns.
# Each tuple = (name_source, desc_source, spec_source)
# "can" = canonical value, "alt" = random alt value, None = field left empty.
#
# Key rule: specification is ALWAYS filled (canonical or alt format) so that
# within-group verification can compare product codes across variants.
# Description and name may be empty to simulate real PIM data quality issues.
PATTERNS = [
    ("alt",  None,  "can"),   # alt name, no description, canonical spec
    ("can",  "alt", "alt"),   # canonical name, alt description, alt spec format
    (None,   "alt", "alt"),   # no name, alt description, alt spec format
    ("alt",  "can", "alt"),   # alt name, canonical description, alt spec format
    ("can",  None,  "alt"),   # canonical name, no description, alt spec format
    (None,   None,  "can"),   # no name, no description, canonical spec only
]


def _pick(product, field, source):
    """Return a field value from a product based on the source selector."""
    if source == "can":
        return product["can"][{"name": 0, "desc": 1, "spec": 2}[field]]
    if source == "alt":
        return random.choice(product[{"name": "an", "desc": "ad", "spec": "as"}[field]])
    return None


def make_duplicate_rows(product):
    """
    Generate 2–4 duplicate variants for a product using different fill patterns.
    Each product gets a random number of variants to simulate realistic catalogs
    where the same item may appear 2, 3, or 4+ times from different sources.
    """
    rows = []
    canonical_desc_en = product["can"][1]
    n_variants = random.choices([2, 3, 4], weights=[50, 35, 15])[0]
    for ns, ds, ss in random.sample(PATTERNS, min(n_variants, len(PATTERNS))):
        desc_en = _pick(product, "desc", ds)
        # Finnish description present in ~60 % of rows, empty in the rest
        desc_fi = get_desc_fi(canonical_desc_en) if random.random() > 0.4 else None
        rows.append({
            "name":           _pick(product, "name", ns),
            "description_en": desc_en,
            "description_fi": desc_fi,
            "specification":  _pick(product, "spec", ss),
            "category":       product["cat"],
            "manufacturer":   product["mfr"] if random.random() > 0.3 else None,
            "unit":           product["unit"],
            "_source_id":     product["id"],
        })
    return rows


# ── Unique filler items ───────────────────────────────────────────────────────
# Items that appear only once — represent the non-duplicate majority.

def _brg(series, d, D, B, mfr):
    return ("Bearings",
            f"BALL BEARING {series} 2RS", f"DEEP GROOVE BALL BEARING {d}X{D}X{B}MM",
            f"{series}-2RS1 {d}X{D}X{B}MM", mfr, "PCS")

def _bolt(m, l, grade, hdg=False):
    suffix = " HDG" if hdg else ""
    return ("Bolts & Fasteners",
            f"HEX BOLT M{m}X{l} {grade}", f"HEXAGON HEAD BOLT M{m}X{l} {grade}",
            f"M{m}X{l} GRADE {grade} ISO 4014{suffix}", None, "PCS")

def _seal(d1, d2, w, mat):
    return ("Seals & Gaskets",
            f"OIL SEAL {d1}X{d2}X{w} {mat}", f"ROTARY SHAFT SEAL {d1}X{d2}X{w} {mat}",
            f"{d1}X{d2}X{w} {mat} DIN 3760", "SIMRIT", "PCS")

def _oring(d, w, mat):
    return ("Seals & Gaskets",
            f"O-RING {d}X{w} {mat}", f"O-RING SEALING {d}X{w} {mat}",
            f"{d}X{w} {mat} DIN 3771", None, "PCS")


UNIQUE_ITEMS = [
    # ── Bearings ─────────────────────────────────────────────────────────────
    # Deep groove ball bearings — clearly different sizes from featured 6205/6206/6207/6305
    _brg("6208", 40, 80, 18, "SKF"),
    _brg("6310", 50, 110, 27, "NSK"),
    _brg("6004", 20, 42, 12, "FAG"),
    _brg("6006", 30, 55, 13, "SKF"),
    _brg("6012", 60, 95, 18, "NSK"),
    # Different bearing types
    ("Bearings", "ANGULAR CONTACT BEARING 7208 BECBP", "ANGULAR CONTACT BALL BEARING 40X80X18MM",
     "7208 BECBP 40X80X18MM", "SKF", "PCS"),
    ("Bearings", "ANGULAR CONTACT BEARING 7212 BECBP", "ANGULAR CONTACT BALL BEARING 60X110X22MM",
     "7212 BECBP 60X110X22MM", "FAG", "PCS"),
    ("Bearings", "SELF-ALIGNING BALL BEARING 1206", "SELF-ALIGNING BALL BEARING 30X62X16MM",
     "1206 ETN9 30X62X16MM", "SKF", "PCS"),
    ("Bearings", "TAPERED ROLLER BEARING 30208", "TAPERED ROLLER BEARING 40X80X20MM",
     "30208 A 40X80X20MM", "SKF", "PCS"),
    ("Bearings", "TAPERED ROLLER BEARING 30212", "TAPERED ROLLER BEARING 60X110X24MM",
     "30212 A 60X110X24MM", "FAG", "PCS"),
    ("Bearings", "CYLINDRICAL ROLLER BEARING NU207", "CYLINDRICAL ROLLER BEARING 35X72X17MM",
     "NU207 ECP 35X72X17MM", "FAG", "PCS"),
    ("Bearings", "CYLINDRICAL ROLLER BEARING NU210", "CYLINDRICAL ROLLER BEARING 50X90X20MM",
     "NU210 ECP 50X90X20MM", "SKF", "PCS"),
    ("Bearings", "SPHERICAL ROLLER BEARING 22208 E", "SPHERICAL ROLLER BEARING 40X80X23MM",
     "22208 E 40X80X23MM", "FAG", "PCS"),
    ("Bearings", "SPHERICAL ROLLER BEARING 22215 E", "SPHERICAL ROLLER BEARING 75X130X31MM",
     "22215 E 75X130X31MM", "SKF", "PCS"),
    ("Bearings", "NEEDLE ROLLER BEARING HK2020", "NEEDLE ROLLER BEARING 20X26X20MM",
     "HK2020 20X26X20MM", "SKF", "PCS"),
    ("Bearings", "PILLOW BLOCK BEARING UCP206", "PILLOW BLOCK UNIT 30MM BORE",
     "UCP206 30MM BORE", "SNR", "PCS"),
    ("Bearings", "PILLOW BLOCK BEARING UCP210", "PILLOW BLOCK UNIT 50MM BORE",
     "UCP210 50MM BORE", "NSK", "PCS"),
    ("Bearings", "FLANGED BEARING UCF207 35MM", "FLANGED BEARING UNIT 35MM BORE",
     "UCF207 35MM BORE", "NSK", "PCS"),

    # ── Seals & Gaskets ───────────────────────────────────────────────────────
    # Oil seals — different sizes and materials from featured 40x60 and 50x70
    _seal(25, 40, 7, "NBR"),
    _seal(35, 55, 10, "NBR"),
    _seal(55, 75, 10, "FKM"),
    _seal(70, 100, 13, "FKM"),
    _seal(80, 110, 13, "NBR"),
    _seal(100, 130, 13, "FKM"),
    # O-rings — different sizes from featured 50x3 and 60x3
    _oring(32, 3, "NBR"),
    _oring(45, 3, "NBR"),
    _oring(75, 4, "EPDM"),
    _oring(80, 4, "FKM"),
    _oring(110, 4, "NBR"),
    _oring(140, 5, "EPDM"),
    # Gaskets and other seals
    ("Seals & Gaskets", "FLAT GASKET DN80 EPDM PN16", "FLAT GASKET FLANGE DN80 PN16 EPDM",
     "DN80 PN16 EPDM 3MM DIN 2690", None, "PCS"),
    ("Seals & Gaskets", "FLAT GASKET DN100 EPDM PN16", "FLAT GASKET FLANGE DN100 PN16 EPDM",
     "DN100 PN16 EPDM 3MM DIN 2690", None, "PCS"),
    ("Seals & Gaskets", "SPIRAL WOUND GASKET DN50 PN40", "SPIRAL WOUND GASKET SS316 GRAPHITE",
     "DN50 PN40 SS316-GRAPHITE", None, "PCS"),
    ("Seals & Gaskets", "SPIRAL WOUND GASKET DN100 PN40", "SPIRAL WOUND GASKET SS316 GRAPHITE",
     "DN100 PN40 SS316-GRAPHITE", None, "PCS"),
    ("Seals & Gaskets", "MECHANICAL SEAL 30MM", "MECHANICAL SHAFT SEAL 30MM SS304 CARBON",
     "30MM SS304 CARBON CERAMIC NBR", "BURGMANN", "PCS"),
    ("Seals & Gaskets", "MECHANICAL SEAL 40MM", "MECHANICAL SHAFT SEAL 40MM SS304 CARBON",
     "40MM SS304 CARBON CERAMIC NBR", "BURGMANN", "PCS"),
    ("Seals & Gaskets", "V-RING SEAL 40MM", "V-RING AXIAL SEAL 40MM NBR",
     "40MM NBR V-RING DIN 3760", "TRELLEBORG", "PCS"),
    ("Seals & Gaskets", "KLINGERIT GASKET DN65 PN16", "SOFT CUT GASKET DN65 PN16",
     "DN65 PN16 KLINGERIT 2MM", None, "PCS"),

    # ── Bolts & Fasteners ─────────────────────────────────────────────────────
    # Different bolt sizes clearly distinct from featured M8x30, M10x40, M12x50
    _bolt(6, 20, "8.8"),
    _bolt(8, 25, "8.8"),
    _bolt(16, 80, "10.9"),
    _bolt(20, 100, "8.8", True),
    _bolt(24, 160, "8.8", True),
    ("Bolts & Fasteners", "HEX NUT M16 GRADE 10", "HEXAGON NUT M16 GRADE 10",
     "M16 GRADE 10 ISO 4032", None, "PCS"),
    ("Bolts & Fasteners", "HEX NUT M20 GRADE 8 HDG", "HEXAGON NUT M20 GRADE 8 HDG",
     "M20 GRADE 8 ISO 4032 HDG", None, "PCS"),
    ("Bolts & Fasteners", "STUD BOLT M20X150 B7 HDG", "STUD BOLT THREADED ROD M20X150 ASTM B7",
     "M20X150 ASTM A193 B7 HDG", None, "PCS"),
    ("Bolts & Fasteners", "STUD BOLT M24X200 B7 HDG", "STUD BOLT THREADED ROD M24X200 ASTM B7",
     "M24X200 ASTM A193 B7 HDG", None, "PCS"),
    ("Bolts & Fasteners", "SOCKET HEAD CAP SCREW M8X25 12.9", "SOCKET HEAD CAP SCREW M8X25",
     "M8X25 GRADE 12.9 SS316 ISO 4762", None, "PCS"),
    ("Bolts & Fasteners", "SOCKET HEAD CAP SCREW M12X40 12.9", "SOCKET HEAD CAP SCREW M12X40",
     "M12X40 GRADE 12.9 SS316 ISO 4762", None, "PCS"),
    ("Bolts & Fasteners", "SPRING WASHER M12 SS304", "SPRING LOCK WASHER M12 SS304",
     "M12 SS304 DIN 127", None, "PCS"),
    ("Bolts & Fasteners", "FLAT WASHER M16 SS304", "FLAT WASHER M16 SS304",
     "M16 SS304 DIN 125", None, "PCS"),
    ("Bolts & Fasteners", "EYE BOLT M16 SS316", "EYE BOLT LIFTING M16 SS316",
     "M16 SS316 DIN 580", None, "PCS"),
    ("Bolts & Fasteners", "U-BOLT DN50 SS316", "U-BOLT PIPE CLAMP DN50 SS316",
     "DN50 SS316 DIN 3570 M10", None, "PCS"),
    ("Bolts & Fasteners", "ANCHOR BOLT M16X150", "ANCHOR BOLT CHEMICAL M16X150",
     "M16X150 ZINC PLATED HILTI", None, "PCS"),
    ("Bolts & Fasteners", "RIVET NUT M8 SS304", "RIVET NUT INSERT M8 SS304",
     "M8 SS304 DIN 7337", None, "PCS"),

    # ── Filters ───────────────────────────────────────────────────────────────
    ("Filters", "AIR FILTER ELEMENT G4 595X595", "AIR PANEL FILTER 595X595X96MM G4",
     "595X595X96MM G4 EN 779", "CAMFIL", "PCS"),
    ("Filters", "AIR FILTER ELEMENT F7 595X595", "AIR PANEL FILTER 595X595X96MM F7",
     "595X595X96MM F7 EN 779", "CAMFIL", "PCS"),
    ("Filters", "HYDRAULIC FILTER ELEMENT 6 MICRON", "HYDRAULIC FILTER ELEMENT 6 MICRON 250 BAR",
     "6 MICRON BETA 6=200 DN20 250 BAR", "HYDAC", "PCS"),
    ("Filters", "RETURN LINE FILTER ELEMENT DN50", "RETURN LINE FILTER DN50 10 MICRON",
     "DN50 10 MICRON 6 BAR", "HYDAC", "PCS"),
    ("Filters", "BREATHER FILTER 1 INCH 25UM", "FILLER BREATHER FILTER 1 INCH 25 MICRON",
     "1 INCH 25 MICRON IP65", "HYDAC", "PCS"),
    ("Filters", "GEAR OIL FILTER ELEMENT DN40", "GEAR OIL FILTER DN40 25 MICRON",
     "DN40 25 MICRON 10 BAR", "PARKER", "PCS"),
    ("Filters", "SUCTION STRAINER DN65 SS316", "SUCTION STRAINER BASKET DN65 SS316",
     "DN65 0.5MM MESH SS316", "PARKER", "PCS"),
    ("Filters", "DUPLEX FILTER ELEMENT DN50 PN16", "DUPLEX FILTER ELEMENT DN50 10 MICRON",
     "DN50 10 MICRON PN16", "PARKER", "PCS"),
    ("Filters", "COALESCENT FILTER ELEMENT 40UM", "COMPRESSED AIR COALESCENT FILTER 40 MICRON",
     "1/2 INCH 40 MICRON 16 BAR", "PARKER", "PCS"),

    # ── Pumps & Valves ────────────────────────────────────────────────────────
    ("Pumps & Valves", "GATE VALVE DN100 PN10 GG25", "GATE VALVE CAST IRON DN100 PN10",
     "DN100 PN10 GG25 DIN 3352", "KSB", "PCS"),
    ("Pumps & Valves", "GATE VALVE DN150 PN10 GG25", "GATE VALVE CAST IRON DN150 PN10",
     "DN150 PN10 GG25 DIN 3352", "KSB", "PCS"),
    ("Pumps & Valves", "BALL VALVE DN80 PN16 SS316", "BALL VALVE FULL BORE DN80 PN16 SS316",
     "DN80 PN16 SS316 ISO 17292", "SPIRAX", "PCS"),
    ("Pumps & Valves", "BUTTERFLY VALVE DN150 PN10 CI", "BUTTERFLY VALVE WAFER TYPE DN150 PN10",
     "DN150 PN10 CI DISC SS316", "TYCO", "PCS"),
    ("Pumps & Valves", "BUTTERFLY VALVE DN200 PN10 CI", "BUTTERFLY VALVE WAFER TYPE DN200 PN10",
     "DN200 PN10 CI DISC SS316", "TYCO", "PCS"),
    ("Pumps & Valves", "GLOBE VALVE DN40 PN16 BRONZE", "GLOBE VALVE BRONZE DN40 PN16",
     "DN40 PN16 BRONZE DIN 3356", "KSB", "PCS"),
    ("Pumps & Valves", "GLOBE VALVE DN65 PN16 BRONZE", "GLOBE VALVE BRONZE DN65 PN16",
     "DN65 PN16 BRONZE DIN 3356", "KSB", "PCS"),
    ("Pumps & Valves", "SAFETY RELIEF VALVE DN25 6BAR", "SAFETY RELIEF VALVE DN25 SET 6 BAR",
     "DN25 SET 6 BAR STAINLESS", "SPIRAX", "PCS"),
    ("Pumps & Valves", "PRESSURE REDUCING VALVE DN32 PN16", "PRESSURE REDUCING VALVE DN32",
     "DN32 PN16 OUTLET 2-8 BAR", "SPIRAX", "PCS"),
    ("Pumps & Valves", "CENTRIFUGAL PUMP 4KW DN65", "CENTRIFUGAL PUMP END SUCTION 4KW",
     "Q=15M3/H H=25M 4KW 1450RPM DN65", "GRUNDFOS", "PCS"),
    ("Pumps & Valves", "CENTRIFUGAL PUMP 7.5KW DN80", "CENTRIFUGAL PUMP END SUCTION 7.5KW",
     "Q=25M3/H H=30M 7.5KW 1450RPM DN80", "GRUNDFOS", "PCS"),
    ("Pumps & Valves", "GEAR PUMP 5.5KW 8M3H", "GEAR PUMP Q=8M3/H 10 BAR",
     "Q=8M3/H 10 BAR 5.5KW 1450RPM", "ROPER", "PCS"),
    ("Pumps & Valves", "DIAPHRAGM VALVE DN25 EPDM", "DIAPHRAGM VALVE DN25 EPDM LINER",
     "DN25 PN10 EPDM LINER SS316", "ITT", "PCS"),
    ("Pumps & Valves", "NEEDLE VALVE DN10 SS316", "NEEDLE VALVE DN10 SS316 PN160",
     "DN10 PN160 SS316 ISO 29490", "SWAGELOK", "PCS"),
    ("Pumps & Valves", "STRAINER Y-TYPE DN50 PN16", "STRAINER Y-TYPE SS316 DN50",
     "DN50 PN16 SS316 MESH 1MM", "KSB", "PCS"),

    # ── Electrical ────────────────────────────────────────────────────────────
    ("Electrical", "CONTACTOR 12A 230VAC 3P", "CONTACTOR 3-POLE 12A 230VAC",
     "12A 230VAC COIL AC3 IEC 60947-4", "SCHNEIDER", "PCS"),
    ("Electrical", "CIRCUIT BREAKER 63A 3P MCCB", "MOULDED CASE CIRCUIT BREAKER 63A 3P",
     "63A 3P 25KA IEC 60947-2", "ABB", "PCS"),
    ("Electrical", "ELECTRIC MOTOR 4KW 4P IE3", "INDUCTION MOTOR 3-PHASE 4KW 4POLE",
     "4KW 4POLE 400V 50HZ IE3 B3 IEC80", "SIEMENS", "PCS"),
    ("Electrical", "ELECTRIC MOTOR 7.5KW 4P IE3", "INDUCTION MOTOR 3-PHASE 7.5KW 4POLE",
     "7.5KW 4POLE 400V 50HZ IE3 B3 IEC112", "ABB", "PCS"),
    ("Electrical", "ELECTRIC MOTOR 11KW 4P IE3", "INDUCTION MOTOR 3-PHASE 11KW 4POLE",
     "11KW 4POLE 400V 50HZ IE3 B3 IEC132", "SIEMENS", "PCS"),
    ("Electrical", "FREQUENCY CONVERTER 1.5KW 3PH", "VARIABLE SPEED DRIVE 1.5KW 3PH",
     "1.5KW 3PH 400V IP20 IEC 61800", "ABB", "PCS"),
    ("Electrical", "FREQUENCY CONVERTER 7.5KW 3PH", "VARIABLE SPEED DRIVE 7.5KW 3PH",
     "7.5KW 3PH 400V IP20 IEC 61800", "SIEMENS", "PCS"),
    ("Electrical", "FUSE 63A 500V gG 22X58MM", "CYLINDRICAL FUSE 63A gG 22X58MM",
     "63A 500V gG 22X58MM IEC 60269", "BUSSMANN", "PCS"),
    ("Electrical", "FUSE 100A 500V gG 22X58MM", "CYLINDRICAL FUSE 100A gG 22X58MM",
     "100A 500V gG 22X58MM IEC 60269", "BUSSMANN", "PCS"),
    ("Electrical", "PRESSURE TRANSMITTER 0-10 BAR 4-20MA", "PRESSURE TRANSMITTER 0-10 BAR",
     "0-10 BAR 4-20MA 24VDC 1/4 NPT IP67", "ENDRESS+HAUSER", "PCS"),
    ("Electrical", "PRESSURE TRANSMITTER 0-40 BAR 4-20MA", "PRESSURE TRANSMITTER 0-40 BAR",
     "0-40 BAR 4-20MA 24VDC 1/4 NPT IP67", "ENDRESS+HAUSER", "PCS"),
    ("Electrical", "TEMPERATURE SENSOR PT100 CLASS B", "RTD TEMPERATURE SENSOR PT100",
     "PT100 CLASS B -50 TO 200C 6MM PROBE", "ENDRESS+HAUSER", "PCS"),
    ("Electrical", "THERMOCOUPLE TYPE K 6MM", "THERMOCOUPLE TYPE K MINERAL INSULATED",
     "TYPE K 6MM MI -200 TO 1200C IP67", "ENDRESS+HAUSER", "PCS"),
    ("Electrical", "FLOW METER DN50 ELECTROMAGNETIC", "ELECTROMAGNETIC FLOW METER DN50",
     "DN50 4-20MA 24VDC IP67 SS316 LINER", "ENDRESS+HAUSER", "PCS"),
    ("Electrical", "FLOW METER DN80 ELECTROMAGNETIC", "ELECTROMAGNETIC FLOW METER DN80",
     "DN80 4-20MA 24VDC IP67 SS316 LINER", "ENDRESS+HAUSER", "PCS"),
    ("Electrical", "LEVEL TRANSMITTER ULTRASONIC DN1.5", "LEVEL TRANSMITTER ULTRASONIC",
     "0-5M 4-20MA 24VDC IP67 1.5 INCH", "ENDRESS+HAUSER", "PCS"),
    ("Electrical", "SOLENOID VALVE 24VDC 6W DIN43650", "SOLENOID VALVE COIL 24VDC",
     "24VDC 6W IP65 DIN 43650", "PARKER", "PCS"),
    ("Electrical", "LIMIT SWITCH PLUNGER IP67", "LIMIT SWITCH PLUNGER ACTUATOR IP67",
     "10A 240VAC PLUNGER ACTUATOR IP67", "SICK", "PCS"),
    ("Electrical", "LIMIT SWITCH ROLLER LEVER IP67", "LIMIT SWITCH ROLLER LEVER IP67",
     "10A 240VAC ROLLER LEVER ACTUATOR IP67", "SICK", "PCS"),
    ("Electrical", "PUSH BUTTON GREEN 22MM MOMENTARY", "PUSH BUTTON MOMENTARY GREEN 22MM",
     "22MM GREEN IP66 IEC 60947-5-1", "SCHNEIDER", "PCS"),
    ("Electrical", "EMERGENCY STOP BUTTON 40MM", "EMERGENCY STOP MUSHROOM HEAD 40MM",
     "40MM RED MUSHROOM IP65 IEC 60947-5-5", "SCHNEIDER", "PCS"),
    ("Electrical", "CABLE GLAND M20 IP68", "CABLE GLAND METRIC M20 IP68",
     "M20 IP68 PA6 NYLON 6-12MM CABLE", None, "PCS"),
    ("Electrical", "CABLE GLAND M32 IP68", "CABLE GLAND METRIC M32 IP68",
     "M32 IP68 PA6 NYLON 13-21MM CABLE", None, "PCS"),
    ("Electrical", "POWER SUPPLY 24VDC 5A", "POWER SUPPLY UNIT 24VDC 5A",
     "24VDC 5A 120W DIN RAIL IEC 61558", "MEANWELL", "PCS"),
    ("Electrical", "SIGNAL ISOLATOR 4-20MA", "SIGNAL ISOLATOR LOOP POWERED 4-20MA",
     "4-20MA INPUT 4-20MA OUTPUT 24VDC IP20", "PHOENIX", "PCS"),

    # ── Mechanical Transmission ───────────────────────────────────────────────
    ("Mechanical", "V-BELT SPB 2500", "V-BELT SPB PROFILE 2500MM",
     "SPB 2500 ISO 4184", None, "PCS"),
    ("Mechanical", "V-BELT SPC 3550", "V-BELT SPC PROFILE 3550MM",
     "SPC 3550 ISO 4184", None, "PCS"),
    ("Mechanical", "TIMING BELT 1440-8M-30", "TIMING BELT 1440MM 8M PITCH 30MM WIDE",
     "1440-8M-30 HTD", None, "PCS"),
    ("Mechanical", "ROLLER CHAIN 16B-1 3M", "ROLLER CHAIN 16B-1 SIMPLEX 3 METRE",
     "16B-1 3M BS 228 SS316", None, "M"),
    ("Mechanical", "ROLLER CHAIN 12B-1 5M", "ROLLER CHAIN 12B-1 SIMPLEX 5 METRE",
     "12B-1 5M BS 228", None, "M"),
    ("Mechanical", "FLEXIBLE COUPLING JAW 28MM", "FLEXIBLE JAW COUPLING 28MM BORE",
     "28MM BORE MAX 95NM 3000RPM POLYURETHANE", "KTR", "PCS"),
    ("Mechanical", "FLEXIBLE COUPLING JAW 42MM", "FLEXIBLE JAW COUPLING 42MM BORE",
     "42MM BORE MAX 210NM 2500RPM POLYURETHANE", "KTR", "PCS"),
    ("Mechanical", "GEAR COUPLING GE50 FLANGE", "GEAR COUPLING DN50 FLANGED",
     "GE50 DN50 MAX 1000NM STEEL", "FLENDER", "PCS"),
    ("Mechanical", "CHAIN COUPLING 6018 STEEL", "CHAIN COUPLING DOUBLE ROLLER CHAIN",
     "6018 12B-2 MAX 500NM 1500RPM", "TSUBAKI", "PCS"),
    ("Mechanical", "BELT TENSIONER ROLLER 35X15MM", "BELT TENSIONER ROLLER BEARING",
     "35X15MM 6203-2RS SPRING LOADED", "SKF", "PCS"),

    # ── Pipe Fittings ─────────────────────────────────────────────────────────
    ("Pipe Fittings", "ELBOW 90 DN50 PN16 SS316", "ELBOW 90 DEGREE DN50 PN16 SS316",
     "DN50 PN16 SS316 BUTT WELD DIN 2605", None, "PCS"),
    ("Pipe Fittings", "ELBOW 90 DN100 PN16 SS316", "ELBOW 90 DEGREE DN100 PN16 SS316",
     "DN100 PN16 SS316 BUTT WELD DIN 2605", None, "PCS"),
    ("Pipe Fittings", "TEE EQUAL DN50 PN16 SS316", "TEE EQUAL DN50 SS316 BUTT WELD",
     "DN50 PN16 SS316 BUTT WELD DIN 2615", None, "PCS"),
    ("Pipe Fittings", "REDUCER DN65-DN50 SS316", "REDUCER CONCENTRIC DN65-DN50 SS316",
     "DN65-DN50 SS316 BUTT WELD DIN 2616", None, "PCS"),
    ("Pipe Fittings", "SLIP-ON FLANGE DN50 PN16 SS316", "SLIP-ON FLANGE DN50 PN16 SS316",
     "DN50 PN16 SS316L DIN 2576", None, "PCS"),
    ("Pipe Fittings", "SLIP-ON FLANGE DN100 PN16 SS316", "SLIP-ON FLANGE DN100 PN16 SS316",
     "DN100 PN16 SS316L DIN 2576", None, "PCS"),
    ("Pipe Fittings", "BLIND FLANGE DN80 PN16 SS316", "BLIND FLANGE DN80 PN16 SS316",
     "DN80 PN16 SS316 DIN 2527", None, "PCS"),
    ("Pipe Fittings", "EXPANSION JOINT DN50 PN10 EPDM", "RUBBER EXPANSION JOINT DN50 PN10",
     "DN50 PN10 EPDM FLANGED", "ELAFLEX", "PCS"),
    ("Pipe Fittings", "SIGHT GLASS DN50 PN16 SS316", "SIGHT GLASS DN50 SS316 BOROSILICATE",
     "DN50 PN16 SS316 BOROSILICATE GLASS", None, "PCS"),
    ("Pipe Fittings", "PIPE SS316L DN50 SCH10 6M", "PIPE STAINLESS STEEL DN50 SCH10 6M",
     "DN50 SCH10 SS316L ASTM A312 6M", None, "M"),

    # ── Lubrication ───────────────────────────────────────────────────────────
    ("Lubrication", "GREASE NLGI 2 LITHIUM 18KG", "MULTI-PURPOSE LITHIUM GREASE NLGI 2",
     "NLGI 2 LITHIUM THICKENER -30 TO 120C 18KG", "SHELL", "KG"),
    ("Lubrication", "HYDRAULIC OIL HM46 200L", "HYDRAULIC OIL ISO VG 46 200L",
     "ISO VG 46 HM DIN 51524-2 200L DRUM", "SHELL", "L"),
    ("Lubrication", "GEAR OIL CLP220 200L", "GEAR OIL ISO VG 220 200L",
     "ISO VG 220 CLP DIN 51517-3 200L DRUM", "MOBIL", "L"),
    ("Lubrication", "COMPRESSOR OIL VDL100 20L", "COMPRESSOR OIL ISO VG 100 20L",
     "ISO VG 100 VDL DIN 51506 20L CAN", "CASTROL", "L"),
    ("Lubrication", "CHAIN LUBRICANT SPRAY 400ML", "CHAIN AND WIRE ROPE LUBRICANT SPRAY",
     "400ML AEROSOL PTFE CHAIN LUBE", "ROCOL", "PCS"),
    ("Lubrication", "MOLY PASTE ANTI-SEIZE 500G", "ANTI-SEIZE PASTE MOLYBDENUM DISULPHIDE",
     "500G MOS2 -180 TO 450C HIGH PRESSURE", "MOLYKOTE", "PCS"),
]


# ── Row assembly ──────────────────────────────────────────────────────────────

def apply_missing_values(df, cols, rate=0.18):
    """Randomly set ~rate fraction of values to None in given columns."""
    for col in cols:
        mask = np.random.random(len(df)) < rate
        df.loc[mask, col] = None
    return df


def build_system1() -> pd.DataFrame:
    rows = []

    # Duplicate rows (2 variants per featured product)
    for prod in PRODUCTS:
        rows.extend(make_duplicate_rows(prod))

    # Unique filler rows — description_fi added via lookup (~60 % filled)
    for cat, name, desc_en, spec, mfr, unit in UNIQUE_ITEMS:
        rows.append({
            "name":           name,
            "description_en": desc_en,
            "description_fi": get_desc_fi(desc_en) if random.random() > 0.4 else None,
            "specification":  spec,
            "category":       cat,
            "manufacturer":   mfr,
            "unit":           unit,
            "_source_id":     None,
        })

    df = pd.DataFrame(rows)

    # Add random missing values to manufacturer (~40 % missing is realistic)
    df.loc[np.random.random(len(df)) < 0.40, "manufacturer"] = None

    # Add random missing values to text fields for unique rows
    unique_mask = df["_source_id"].isna()
    for col in ["name", "description_en", "description_fi", "specification"]:
        miss = unique_mask & (np.random.random(len(df)) < 0.12)
        df.loc[miss, col] = None

    df = df.drop(columns=["_source_id"]).sample(frac=1, random_state=42).reset_index(drop=True)
    df.insert(0, "item_id", [f"ITM-{i:05d}" for i in range(10001, 10001 + len(df))])
    return df


def build_system2(system1_df: pd.DataFrame) -> pd.DataFrame:
    """
    Simulates a second ERP system's catalog.
    ~80 items overlap with system1 (same products, reformatted).
    ~200 items are unique to system2.
    """
    rows = []
    overlap_products = random.sample(PRODUCTS, min(25, len(PRODUCTS)))

    # Overlapping items: reformat by shuffling which field holds the information
    for prod in overlap_products:
        canonical_desc_en = prod["can"][1]
        # System2 tends to put more info in 'name', less in 'description_en'
        rows.append({
            "name":           random.choice(prod["an"]),
            "description_en": prod["can"][2],        # spec goes into description
            "description_fi": get_desc_fi(canonical_desc_en) if random.random() > 0.4 else None,
            "specification":  prod["can"][1],         # description goes into spec
            "category":       prod["cat"],
            "manufacturer":   prod["mfr"] if random.random() > 0.4 else None,
            "unit":           prod["unit"],
        })
        # Add a second variant for some products
        if random.random() > 0.5:
            desc_en_alt = random.choice(prod["ad"])
            rows.append({
                "name":           prod["can"][0],
                "description_en": desc_en_alt,
                "description_fi": get_desc_fi(prod["can"][1]) if random.random() > 0.4 else None,
                "specification":  random.choice(prod["as"]),
                "category":       prod["cat"],
                "manufacturer":   None,
                "unit":           prod["unit"],
            })

    # Unique items (subset of UNIQUE_ITEMS, different selection from system1)
    unique_sample = random.sample(UNIQUE_ITEMS, min(200, len(UNIQUE_ITEMS)))
    for cat, name, desc_en, spec, mfr, unit in unique_sample:
        rows.append({
            "name":           name,
            "description_en": desc_en,
            "description_fi": get_desc_fi(desc_en) if random.random() > 0.4 else None,
            "specification":  spec,
            "category":       cat,
            "manufacturer":   mfr,
            "unit":           unit,
        })

    df = pd.DataFrame(rows)
    df.loc[np.random.random(len(df)) < 0.40, "manufacturer"] = None
    for col in ["name", "description_en", "description_fi", "specification"]:
        df.loc[np.random.random(len(df)) < 0.12, col] = None

    df = df.sample(frac=1, random_state=99).reset_index(drop=True)
    df.insert(0, "item_id", [f"SYS2-{i:05d}" for i in range(20001, 20001 + len(df))])
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    sys1 = build_system1()
    sys2 = build_system2(sys1)

    path1 = os.path.join(OUTPUT_DIR, "spare_parts_system1.xlsx")
    path2 = os.path.join(OUTPUT_DIR, "spare_parts_system2.xlsx")

    sys1.to_excel(path1, index=False, sheet_name="Items")
    sys2.to_excel(path2, index=False, sheet_name="Items")

    dup_count = sys1.duplicated(subset=["name", "description_en", "specification"], keep=False).sum()
    print(f"System 1: {len(sys1)} rows, ~{dup_count} rows with shared name/desc/spec combo")
    print(f"System 2: {len(sys2)} rows")
    print(f"Saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
