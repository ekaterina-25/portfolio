import pandas as pd
import random
import os

random.seed(42)

# ---------------------------------------------------------------------------
# Reference data — category_index (~90 rows) and name_index (~45 rows)
# ---------------------------------------------------------------------------

# (code, full_category_label, base_name)
CATEGORIES = [
    # Bearings
    ("100110", "DEEP GROOVE BALL BEARING",          "BALL BEARING"),
    ("100120", "ANGULAR CONTACT BALL BEARING",      "BALL BEARING"),
    ("100130", "THRUST BALL BEARING",               "BALL BEARING"),
    ("100210", "CYLINDRICAL ROLLER BEARING",        "ROLLER BEARING"),
    ("100220", "SPHERICAL ROLLER BEARING",          "ROLLER BEARING"),
    ("100230", "TAPERED ROLLER BEARING",            "ROLLER BEARING"),
    ("100240", "NEEDLE ROLLER BEARING",             "ROLLER BEARING"),
    ("100310", "PLAIN BEARING BUSH",                "PLAIN BEARING"),
    ("100320", "SPHERICAL PLAIN BEARING",           "PLAIN BEARING"),
    ("100410", "PILLOW BLOCK UNIT",                 "BEARING UNIT"),
    ("100420", "FLANGED BEARING UNIT",              "BEARING UNIT"),
    ("100430", "CARTRIDGE BEARING UNIT",            "BEARING UNIT"),
    # Seals
    ("200110", "RADIAL SHAFT SEAL",                 "SHAFT SEAL"),
    ("200120", "AXIAL SHAFT SEAL",                  "SHAFT SEAL"),
    ("200210", "O-RING",                            "O-RING"),
    ("200220", "O-RING CORD",                       "O-RING"),
    ("200310", "FLAT GASKET",                       "GASKET"),
    ("200320", "SPIRAL WOUND GASKET",               "GASKET"),
    ("200330", "RING JOINT GASKET",                 "GASKET"),
    ("200410", "MECHANICAL SEAL",                   "MECHANICAL SEAL"),
    ("200420", "CARTRIDGE MECHANICAL SEAL",         "MECHANICAL SEAL"),
    ("200510", "PISTON SEAL",                       "HYDRAULIC SEAL"),
    ("200520", "ROD SEAL",                          "HYDRAULIC SEAL"),
    ("200530", "WIPER SEAL",                        "HYDRAULIC SEAL"),
    # Fasteners
    ("300110", "HEX HEAD BOLT",                     "BOLT"),
    ("300120", "SOCKET HEAD BOLT",                  "BOLT"),
    ("300130", "STUD BOLT",                         "BOLT"),
    ("300140", "EYE BOLT",                          "BOLT"),
    ("300210", "HEX NUT",                           "NUT"),
    ("300220", "SELF-LOCKING NUT",                  "NUT"),
    ("300230", "WING NUT",                          "NUT"),
    ("300310", "FLAT WASHER",                       "WASHER"),
    ("300320", "SPRING WASHER",                     "WASHER"),
    ("300410", "MACHINE SCREW",                     "SCREW"),
    ("300420", "SET SCREW",                         "SCREW"),
    # Filters
    ("400110", "HYDRAULIC FILTER ELEMENT",          "FILTER ELEMENT"),
    ("400120", "RETURN LINE FILTER ELEMENT",        "FILTER ELEMENT"),
    ("400210", "AIR FILTER CARTRIDGE",              "FILTER CARTRIDGE"),
    ("400220", "OIL MIST FILTER CARTRIDGE",         "FILTER CARTRIDGE"),
    ("400310", "STRAINER BASKET",                   "STRAINER"),
    ("400410", "BREATHER FILTER",                   "BREATHER"),
    # Valves
    ("500110", "BALL VALVE",                        "VALVE"),
    ("500120", "BUTTERFLY VALVE",                   "VALVE"),
    ("500130", "GLOBE VALVE",                       "VALVE"),
    ("500210", "GATE VALVE",                        "VALVE"),
    ("500310", "CHECK VALVE",                       "VALVE"),
    ("500320", "SWING CHECK VALVE",                 "VALVE"),
    ("500410", "SAFETY RELIEF VALVE",               "SAFETY VALVE"),
    ("500420", "PRESSURE RELIEF VALVE",             "SAFETY VALVE"),
    ("500510", "SOLENOID VALVE",                    "CONTROL VALVE"),
    ("500520", "PROPORTIONAL VALVE",                "CONTROL VALVE"),
    # Power transmission
    ("600110", "V-BELT",                            "BELT"),
    ("600120", "FLAT BELT",                         "BELT"),
    ("600210", "TIMING BELT",                       "TOOTHED BELT"),
    ("600220", "POLY V-BELT",                       "TOOTHED BELT"),
    ("600310", "ROLLER CHAIN",                      "CHAIN"),
    ("600320", "CONVEYOR CHAIN",                    "CHAIN"),
    ("600410", "CHAIN SPROCKET",                    "SPROCKET"),
    ("600420", "TAPER LOCK SPROCKET",               "SPROCKET"),
    ("600510", "GEAR COUPLING",                     "COUPLING"),
    ("600520", "JAW COUPLING",                      "COUPLING"),
    ("600530", "DISC COUPLING",                     "COUPLING"),
    ("600610", "V-BELT PULLEY",                     "PULLEY"),
    ("600620", "TAPER LOCK PULLEY",                 "PULLEY"),
    # Pumps & motors (only components, not complete units)
    ("700110", "CENTRIFUGAL PUMP IMPELLER",         "PUMP PART"),
    ("700120", "PUMP WEAR RING",                    "PUMP PART"),
    ("700130", "PUMP SHAFT SLEEVE",                 "PUMP PART"),
    ("700210", "GEAR PUMP ELEMENT",                 "PUMP ELEMENT"),
    ("700310", "HYDRAULIC MOTOR SEAL KIT",          "SEAL KIT"),
    ("700320", "PUMP SEAL KIT",                     "SEAL KIT"),
    # Instrumentation
    ("800110", "PRESSURE GAUGE",                    "GAUGE"),
    ("800120", "DIFFERENTIAL PRESSURE GAUGE",       "GAUGE"),
    ("800210", "TEMPERATURE SENSOR PT100",          "SENSOR"),
    ("800220", "VIBRATION SENSOR",                  "SENSOR"),
    ("800310", "FLOW METER",                        "METER"),
    ("800320", "LEVEL INDICATOR",                   "INDICATOR"),
    # Lubrication
    ("900110", "GREASE NIPPLE",                     "FITTING"),
    ("900120", "HYDRAULIC FITTING",                 "FITTING"),
    ("900130", "PIPE CONNECTOR",                    "FITTING"),
    ("900210", "GREASE CARTRIDGE",                  "LUBRICANT"),
    ("900220", "OIL CAN",                           "LUBRICANT"),
    ("900310", "LUBRICATION PUMP",                  "LUBRICANT DEVICE"),
    # Electrical components (MRO level)
    ("950110", "FUSE",                              "FUSE"),
    ("950120", "CIRCUIT BREAKER",                   "FUSE"),
    ("950210", "CONTACTOR",                         "SWITCH"),
    ("950220", "RELAY",                             "SWITCH"),
    ("950310", "PROXIMITY SENSOR",                  "SENSOR"),
    ("950320", "LIMIT SWITCH",                      "SWITCH"),
]

LABEL_FI = {
    "BALL BEARING":         "KUULALAAKERI",
    "ROLLER BEARING":       "RULLALAAKERI",
    "PLAIN BEARING":        "LIUKULAAKERI",
    "BEARING UNIT":         "LAAKERIYKSIKKO",
    "SHAFT SEAL":           "AKSELITIIVISTE",
    "O-RING":               "O-RENGAS",
    "GASKET":               "TIIVISTE",
    "MECHANICAL SEAL":      "MEKAANINEN TIIVISTE",
    "HYDRAULIC SEAL":       "HYDRAULIIKKATIIVISTE",
    "BOLT":                 "RUUVI",
    "NUT":                  "MUTTERI",
    "WASHER":               "ALUSLEVY",
    "SCREW":                "RUUVI",
    "FILTER ELEMENT":       "SUODATINELEMENTTI",
    "FILTER CARTRIDGE":     "SUODATINPATRUUNA",
    "STRAINER":             "SIHTI",
    "BREATHER":             "ILMAUSSUODATIN",
    "VALVE":                "VENTTIILI",
    "SAFETY VALVE":         "VAROVENTTIILI",
    "CONTROL VALVE":        "OHJAUSVENTTIILI",
    "BELT":                 "HIHNA",
    "TOOTHED BELT":         "HAMMASHIHNA",
    "CHAIN":                "KETJU",
    "SPROCKET":             "KETJUPYORA",
    "COUPLING":             "KYTKIN",
    "PULLEY":               "HIHNAPYORA",
    "PUMP PART":            "PUMPUN OSA",
    "PUMP ELEMENT":         "PUMPPUELEMENTTI",
    "SEAL KIT":             "TIIVISTESARJA",
    "GAUGE":                "MITTARI",
    "SENSOR":               "ANTURI",
    "METER":                "VIRTAUSMITTARI",
    "INDICATOR":            "ILMAISIN",
    "FITTING":              "LIITIN",
    "LUBRICANT":            "VOITELUAINE",
    "LUBRICANT DEVICE":     "VOITELULAITE",
    "FUSE":                 "SULAKE",
    "SWITCH":               "KYTKIN",
}

LABEL_DE = {
    "BALL BEARING":         "KUGELLAGER",
    "ROLLER BEARING":       "ROLLENLAGER",
    "PLAIN BEARING":        "GLEITLAGER",
    "BEARING UNIT":         "LAGEREINHEIT",
    "SHAFT SEAL":           "WELLENDICHTRING",
    "O-RING":               "O-RING",
    "GASKET":               "DICHTUNG",
    "MECHANICAL SEAL":      "GLEITRINGDICHTUNG",
    "HYDRAULIC SEAL":       "HYDRAULIKDICHTUNG",
    "BOLT":                 "SCHRAUBE",
    "NUT":                  "MUTTER",
    "WASHER":               "UNTERLEGSCHEIBE",
    "SCREW":                "SCHRAUBE",
    "FILTER ELEMENT":       "FILTERELEMENT",
    "FILTER CARTRIDGE":     "FILTERPATRONE",
    "STRAINER":             "SIEB",
    "BREATHER":             "BELUEFTUNGSFILTER",
    "VALVE":                "VENTIL",
    "SAFETY VALVE":         "SICHERHEITSVENTIL",
    "CONTROL VALVE":        "REGELVENTIL",
    "BELT":                 "RIEMEN",
    "TOOTHED BELT":         "ZAHNRIEMEN",
    "CHAIN":                "KETTE",
    "SPROCKET":             "KETTENRAD",
    "COUPLING":             "KUPPLUNG",
    "PULLEY":               "RIEMENSCHEIBE",
    "PUMP PART":            "PUMPENTEIL",
    "PUMP ELEMENT":         "PUMPENELEMENT",
    "SEAL KIT":             "DICHTSATZ",
    "GAUGE":                "MANOMETER",
    "SENSOR":               "SENSOR",
    "METER":                "DURCHFLUSSMESSER",
    "INDICATOR":            "ANZEIGER",
    "FITTING":              "ANSCHLUSS",
    "LUBRICANT":            "SCHMIERSTOFF",
    "LUBRICANT DEVICE":     "SCHMIERGERAET",
    "FUSE":                 "SICHERUNG",
    "SWITCH":               "SCHALTER",
}

DESIGNATORS = {
    "DEEP GROOVE BALL BEARING":          ["6204 2RS", "6205 ZZ", "6206 2RS", "6207 ZZ", "6208 2RS", "6301 2RS", "6305 ZZ"],
    "ANGULAR CONTACT BALL BEARING":      ["7204 B", "7205 B", "7206 BEP", "7208 BECBP"],
    "THRUST BALL BEARING":               ["51104", "51105", "51106", "51108"],
    "CYLINDRICAL ROLLER BEARING":        ["NU204 E", "NU205 E", "NJ206 E", "NU208 E"],
    "SPHERICAL ROLLER BEARING":          ["22210 E", "22211 E", "22212 K", "22215 K"],
    "TAPERED ROLLER BEARING":            ["30204", "30205", "30206", "32208"],
    "NEEDLE ROLLER BEARING":             ["NK28/20", "NK35/20", "NK42/20", "HK2516"],
    "PLAIN BEARING BUSH":                ["GE25 TXE", "GE30 TXE", "GE35 TXE", "GE40 TXE"],
    "SPHERICAL PLAIN BEARING":           ["GE25 TXE-2LS", "GE30 TXE-2LS", "GE40 TXE-2LS"],
    "PILLOW BLOCK UNIT":                 ["UCF205", "UCF206", "UCF207", "UCF208"],
    "FLANGED BEARING UNIT":              ["UCF205-16", "UCF206-18", "UCFL207"],
    "CARTRIDGE BEARING UNIT":            ["UCFC205", "UCFC206", "UCFC207"],
    "RADIAL SHAFT SEAL":                 ["30X52X10 FKM", "40X62X10 NBR", "50X72X12 NBR", "60X80X12 FKM"],
    "AXIAL SHAFT SEAL":                  ["AX25X37X6", "AX32X45X8", "AX40X55X8"],
    "O-RING":                            ["25X3 NBR70", "32X3 FKM70", "40X4 NBR70", "50X4 FKM80", "60X5 EPDM70"],
    "O-RING CORD":                       ["4MM NBR70", "5MM FKM70", "6MM EPDM70"],
    "FLAT GASKET":                       ["DN50 PN16", "DN65 PN16", "DN80 PN10", "DN100 PN10"],
    "SPIRAL WOUND GASKET":               ["DN50 PN40", "DN65 PN40", "DN80 PN40"],
    "RING JOINT GASKET":                 ["R24 SOFT IRON", "R26 SOFT IRON", "R31 SS316"],
    "MECHANICAL SEAL":                   ["TYPE21 DN25", "TYPE21 DN32", "TYPE21 DN40", "TYPE21 DN50"],
    "CARTRIDGE MECHANICAL SEAL":         ["CDSA-25", "CDSA-32", "CDSA-40", "CDSA-50"],
    "PISTON SEAL":                       ["40X50X10", "50X60X10", "63X75X12", "80X95X12"],
    "ROD SEAL":                          ["25X35X10", "32X42X10", "40X52X10", "50X62X10"],
    "WIPER SEAL":                        ["25X33X7", "32X40X7", "40X50X8", "50X62X8"],
    "HEX HEAD BOLT":                     ["M8X30 A2", "M10X40 A2", "M12X50 A4", "M16X60 A4", "M20X80 A4"],
    "SOCKET HEAD BOLT":                  ["M6X20 A2", "M8X25 A2", "M10X35 A4", "M12X40 A4"],
    "STUD BOLT":                         ["M12X60 A2", "M16X80 A4", "M20X100 A4"],
    "EYE BOLT":                          ["M8 A2", "M10 A2", "M12 A4", "M16 A4"],
    "HEX NUT":                           ["M8 A2", "M10 A2", "M12 A4", "M16 A4", "M20 A4"],
    "SELF-LOCKING NUT":                  ["M8 A2", "M10 A2", "M12 A4"],
    "WING NUT":                          ["M6 A2", "M8 A2", "M10 A2"],
    "FLAT WASHER":                       ["M8 A2", "M10 A2", "M12 A4", "M16 A4"],
    "SPRING WASHER":                     ["M8 A2", "M10 A2", "M12 A4"],
    "MACHINE SCREW":                     ["M4X12 A2", "M5X16 A2", "M6X20 A4"],
    "SET SCREW":                         ["M6X10 A2", "M8X10 A2", "M10X12 A4"],
    "HYDRAULIC FILTER ELEMENT":          ["HF-25-10", "HF-40-10", "HF-63-10", "HF-100-6"],
    "RETURN LINE FILTER ELEMENT":        ["RL-40-10", "RL-63-10", "RL-100-6"],
    "AIR FILTER CARTRIDGE":              ["AF-100-D", "AF-150-D", "AF-200-D", "AF-250-D"],
    "OIL MIST FILTER CARTRIDGE":         ["OM-50-D", "OM-100-D", "OM-150-D"],
    "STRAINER BASKET":                   ["DN50 0.5MM", "DN65 0.5MM", "DN80 1MM"],
    "BREATHER FILTER":                   ["BF-10-3", "BF-20-3", "BF-40-3"],
    "BALL VALVE":                        ["DN25 PN16", "DN32 PN16", "DN40 PN16", "DN50 PN16", "DN65 PN10"],
    "BUTTERFLY VALVE":                   ["DN80 PN10", "DN100 PN10", "DN150 PN10"],
    "GLOBE VALVE":                       ["DN25 PN16", "DN40 PN16", "DN50 PN16"],
    "GATE VALVE":                        ["DN50 PN10", "DN65 PN10", "DN80 PN10", "DN100 PN10"],
    "CHECK VALVE":                       ["DN25 PN16", "DN40 PN16", "DN50 PN10", "DN80 PN10"],
    "SWING CHECK VALVE":                 ["DN50 PN10", "DN80 PN10", "DN100 PN10"],
    "SAFETY RELIEF VALVE":               ["DN25 3.0BAR", "DN25 6.0BAR", "DN32 10.0BAR"],
    "PRESSURE RELIEF VALVE":             ["DN15 10BAR", "DN20 16BAR", "DN25 25BAR"],
    "SOLENOID VALVE":                    ["24VDC 2W DN10", "24VDC 2W DN15", "230VAC 3W DN20"],
    "PROPORTIONAL VALVE":                ["4WREE6 24V", "4WREE10 24V"],
    "V-BELT":                            ["SPZ-800", "SPA-1000", "SPB-1250", "SPC-1500", "A-1060"],
    "FLAT BELT":                         ["100X3-3000", "150X4-4000", "200X5-5000"],
    "TIMING BELT":                       ["T5-500", "T5-750", "T10-600", "T10-1000", "AT5-630"],
    "POLY V-BELT":                       ["PJ-762-6", "PJ-1016-8", "PL-2032-6"],
    "ROLLER CHAIN":                      ["08B-1 2000MM", "10B-1 2000MM", "12B-1 3000MM"],
    "CONVEYOR CHAIN":                    ["CC200 2000MM", "CC300 3000MM"],
    "CHAIN SPROCKET":                    ["08B Z20", "10B Z20", "12B Z16"],
    "TAPER LOCK SPROCKET":               ["08B TL1210 Z20", "10B TL1610 Z20"],
    "GEAR COUPLING":                     ["GC-40 BORE25", "GC-50 BORE32", "GC-65 BORE40"],
    "JAW COUPLING":                      ["L090 BORE25", "L095 BORE32", "L100 BORE40"],
    "DISC COUPLING":                     ["DC-50 BORE25", "DC-65 BORE32", "DC-80 BORE40"],
    "V-BELT PULLEY":                     ["SPA 2GR D100", "SPB 2GR D125", "SPC 3GR D200"],
    "TAPER LOCK PULLEY":                 ["SPA TL1610 D100", "SPB TL2012 D125"],
    "CENTRIFUGAL PUMP IMPELLER":         ["IMP-80-250 SS316", "IMP-100-315 SS316"],
    "PUMP WEAR RING":                    ["WR-80 SS316", "WR-100 SS316"],
    "PUMP SHAFT SLEEVE":                 ["SL-50X80 SS316", "SL-65X100 SS316"],
    "GEAR PUMP ELEMENT":                 ["GPE-20CC", "GPE-32CC", "GPE-50CC"],
    "HYDRAULIC MOTOR SEAL KIT":          ["SK-HM-010", "SK-HM-015", "SK-HM-020"],
    "PUMP SEAL KIT":                     ["SK-CP-080", "SK-CP-100", "SK-CP-125"],
    "PRESSURE GAUGE":                    ["PG-63-10BAR", "PG-63-16BAR", "PG-100-25BAR"],
    "DIFFERENTIAL PRESSURE GAUGE":       ["DPG-40-1BAR", "DPG-63-2.5BAR"],
    "TEMPERATURE SENSOR PT100":          ["PT100 4-20MA", "PT100 0-10V", "PT100 HART"],
    "VIBRATION SENSOR":                  ["VS-100-IEPE", "VS-100-4-20MA"],
    "FLOW METER":                        ["FM-DN25 4-20MA", "FM-DN40 HART", "FM-DN50 4-20MA"],
    "LEVEL INDICATOR":                   ["LI-500MM", "LI-1000MM", "LI-1500MM"],
    "GREASE NIPPLE":                     ["M6 45DEG", "M8 STRAIGHT", "M10 90DEG"],
    "HYDRAULIC FITTING":                 ["SAE6000 1/4IN", "SAE6000 3/8IN", "SAE6000 1/2IN"],
    "PIPE CONNECTOR":                    ["DN15 SS316", "DN20 SS316", "DN25 CS"],
    "GREASE CARTRIDGE":                  ["400G EP2", "500G EP2-LT", "400G FOOD GRADE"],
    "OIL CAN":                           ["1L VG68", "5L VG46", "20L VG100"],
    "LUBRICATION PUMP":                  ["LP-12V-4L", "LP-24V-8L"],
    "FUSE":                              ["6A 500V gL", "10A 500V gG", "16A 500V gL"],
    "CIRCUIT BREAKER":                   ["6A 1P C-CURVE", "10A 3P B-CURVE", "16A 3P C-CURVE"],
    "CONTACTOR":                         ["LC1D09 24VDC", "LC1D18 24VDC", "LC1D32 24VDC"],
    "RELAY":                             ["CR-P024DC2 24VDC", "CR-P110AC2 110VAC"],
    "PROXIMITY SENSOR":                  ["PNP NO 12MM NPN", "PNP NO 18MM NPN", "PNP NC 30MM"],
    "LIMIT SWITCH":                      ["LS-SPDT-IP67", "LS-DPDT-IP67"],
}

MFR_PARTS = {
    "DEEP GROOVE BALL BEARING":     ["SKF-6204-2RS1", "FAG-6204-2RSR", "NSK-6204DDU", "NTN-6204LLU"],
    "ANGULAR CONTACT BALL BEARING": ["SKF-7204-BECBP", "FAG-7204-B-JP"],
    "THRUST BALL BEARING":          ["SKF-51104", "FAG-51104"],
    "CYLINDRICAL ROLLER BEARING":   ["SKF-NU204-ECP", "FAG-NU204-E-JP"],
    "SPHERICAL ROLLER BEARING":     ["SKF-22210-E", "FAG-22210-E1", "NSK-22210CME4"],
    "TAPERED ROLLER BEARING":       ["SKF-30204-J2", "FAG-30204-A"],
    "NEEDLE ROLLER BEARING":        ["SKF-NK28/20", "INA-NK28/20"],
    "PLAIN BEARING BUSH":           ["SKF-GE25-TXE-2LS", "INA-GE25-TXE2LS"],
    "SPHERICAL PLAIN BEARING":      ["SKF-GE25-TXE-2LS", "INA-GE30-TXE2LS"],
    "PILLOW BLOCK UNIT":            ["SKF-SY505M", "SNR-UCF205"],
    "FLANGED BEARING UNIT":         ["SKF-FY505M", "SNR-UCF206"],
    "CARTRIDGE BEARING UNIT":       ["SKF-SYNT50L", "SNR-UCFC205"],
    "RADIAL SHAFT SEAL":            ["SKF-30X52X10-HMS5", "NOK-TC-30-52-10"],
    "AXIAL SHAFT SEAL":             ["SKF-AXW-25", "NOK-AX-25-37-6"],
    "O-RING":                       ["OR-NBR70-25X3", "OR-FKM70-32X3", "OR-EPDM70-40X4"],
    "O-RING CORD":                  ["ORC-4MM-NBR", "ORC-5MM-FKM"],
    "FLAT GASKET":                  ["KL-PTFE-DN50-PN16", "KL-NBR-DN65-PN16"],
    "SPIRAL WOUND GASKET":          ["SWG-SS316-DN50", "SWG-SS316-DN65"],
    "RING JOINT GASKET":            ["RJG-R24-SI", "RJG-R26-SI"],
    "MECHANICAL SEAL":              ["BM-TYPE21-25", "FS-CDPH-25"],
    "CARTRIDGE MECHANICAL SEAL":    ["BM-CDA-25", "FS-CDSA-32"],
    "PISTON SEAL":                  ["PS-PTFE-40X50X10", "PS-PU-50X60X10"],
    "ROD SEAL":                     ["RS-PU-25X35X10", "RS-PTFE-32X42X10"],
    "WIPER SEAL":                   ["WS-PU-25X33X7", "WS-NBR-32X40X7"],
    "HEX HEAD BOLT":                ["DIN933-M8X30-A2", "DIN931-M12X50-A4"],
    "SOCKET HEAD BOLT":             ["DIN912-M8X25-A2", "DIN912-M10X35-A4"],
    "STUD BOLT":                    ["DIN939-M12X60-A2", "DIN939-M16X80-A4"],
    "EYE BOLT":                     ["DIN580-M8-A2", "DIN580-M10-A4"],
    "HEX NUT":                      ["DIN934-M8-A2", "DIN934-M12-A4"],
    "SELF-LOCKING NUT":             ["DIN985-M8-A2", "DIN985-M12-A4"],
    "WING NUT":                     ["DIN315-M6-A2", "DIN315-M8-A2"],
    "FLAT WASHER":                  ["DIN125-M8-A2", "DIN125-M12-A4"],
    "SPRING WASHER":                ["DIN127-M8-A2", "DIN127-M12-A4"],
    "MACHINE SCREW":                ["DIN84-M4X12-A2", "DIN84-M6X20-A4"],
    "SET SCREW":                    ["DIN913-M6X10-A2", "DIN913-M8X10-A2"],
    "HYDRAULIC FILTER ELEMENT":     ["Parker-HF25-10MIC", "Hydac-HF40-10MIC"],
    "RETURN LINE FILTER ELEMENT":   ["Parker-RL40-10MIC", "Hydac-RL63-10MIC"],
    "AIR FILTER CARTRIDGE":         ["Donaldson-P100", "Mann-AF150"],
    "OIL MIST FILTER CARTRIDGE":    ["Donaldson-OM50", "Mann-OM100"],
    "STRAINER BASKET":              ["STR-DN50-CS", "STR-DN65-SS316"],
    "BREATHER FILTER":              ["BF-10-3-MIC", "BF-20-3-MIC"],
    "BALL VALVE":                   ["VBP-SS-DN25-PN16", "VBP-CS-DN50-PN16"],
    "BUTTERFLY VALVE":              ["VBF-CI-DN80-PN10", "VBF-CI-DN100-PN10"],
    "GLOBE VALVE":                  ["VGL-SS-DN25-PN16", "VGL-CI-DN50-PN16"],
    "GATE VALVE":                   ["VGT-CI-DN50-PN10", "VGT-CI-DN80-PN10"],
    "CHECK VALVE":                  ["VCK-SS-DN25-PN16", "VCK-CI-DN50-PN10"],
    "SWING CHECK VALVE":            ["VSCV-CI-DN50-PN10", "VSCV-CI-DN100-PN10"],
    "SAFETY RELIEF VALVE":          ["SRV-SS-3.0BAR", "SRV-SS-6.0BAR"],
    "PRESSURE RELIEF VALVE":        ["PRV-SS-10BAR", "PRV-CS-16BAR"],
    "SOLENOID VALVE":               ["ASCO-8262-24VDC", "SMC-VX210-24VDC"],
    "PROPORTIONAL VALVE":           ["Bosch-4WREE6-24V", "Moog-D633-24V"],
    "V-BELT":                       ["Continental-SPZ800", "Gates-SPA1000"],
    "FLAT BELT":                    ["Habasit-100X3-EP", "Siegling-150X4"],
    "TIMING BELT":                  ["Continental-T5-500", "Gates-T10-600"],
    "POLY V-BELT":                  ["Continental-PJ762-6", "Gates-PJ1016-8"],
    "ROLLER CHAIN":                 ["Renold-08B-2000", "Iwis-10B-2000"],
    "CONVEYOR CHAIN":               ["Renold-CC200-2000", "Rexnord-CC300-3000"],
    "CHAIN SPROCKET":               ["Martin-08B-Z20", "Tsubaki-10B-Z20"],
    "TAPER LOCK SPROCKET":          ["Martin-08B-TL-Z20", "Tsubaki-TL1610-Z20"],
    "GEAR COUPLING":                ["Rexnord-GC40-25", "Bibby-GC50-32"],
    "JAW COUPLING":                 ["KTR-L090-25", "Rexnord-L095-32"],
    "DISC COUPLING":                ["Rexnord-DC50-25", "KTR-DC65-32"],
    "V-BELT PULLEY":                ["Fenner-SPA-D100", "Browning-SPB-D125"],
    "TAPER LOCK PULLEY":            ["Fenner-TL1610-D100", "Browning-TL2012-D125"],
    "CENTRIFUGAL PUMP IMPELLER":    ["IMP-80-SS316", "IMP-100-SS316"],
    "PUMP WEAR RING":               ["WR-80-SS316", "WR-100-SS316"],
    "PUMP SHAFT SLEEVE":            ["SL-50X80-SS316", "SL-65X100-SS316"],
    "GEAR PUMP ELEMENT":            ["Bosch-GPE20", "Parker-GPE32"],
    "HYDRAULIC MOTOR SEAL KIT":     ["Bosch-SK-HM010", "Parker-SK-HM015"],
    "PUMP SEAL KIT":                ["Grundfos-SK-CP080", "ITT-SK-CP100"],
    "PRESSURE GAUGE":               ["Wika-213-10BAR", "Wika-213-16BAR"],
    "DIFFERENTIAL PRESSURE GAUGE":  ["Wika-732-1BAR", "Ashcroft-DP-2.5BAR"],
    "TEMPERATURE SENSOR PT100":     ["Endress-TSP400", "Jumo-PT100-4-20MA"],
    "VIBRATION SENSOR":             ["SKF-CMSS2200", "Emerson-VS-IEPE"],
    "FLOW METER":                   ["Endress-FM-DN25", "Siemens-FM-DN40"],
    "LEVEL INDICATOR":              ["Wika-LI-500", "Orion-LI-1000"],
    "GREASE NIPPLE":                ["DIN71412-M6-45", "DIN71412-M8-ST"],
    "HYDRAULIC FITTING":            ["Parker-SAE6000-1/4", "Eaton-SAE6000-3/8"],
    "PIPE CONNECTOR":               ["PP-DN15-SS316", "PP-DN20-SS316"],
    "GREASE CARTRIDGE":             ["SKF-LGEP2-0.4", "Shell-EP2-400G"],
    "OIL CAN":                      ["Mobil-VG68-1L", "Shell-VG46-5L"],
    "LUBRICATION PUMP":             ["SKF-LP-12V-4L", "Beka-LP-24V-8L"],
    "FUSE":                         ["Legrand-6A-500V", "Bussmann-10A-500V"],
    "CIRCUIT BREAKER":              ["Schneider-6A-1P", "ABB-10A-3P"],
    "CONTACTOR":                    ["Schneider-LC1D09", "ABB-AF09-30"],
    "RELAY":                        ["Phoenix-CRP-P024", "Schneider-RXM2LB2"],
    "PROXIMITY SENSOR":             ["Pepperl-NBN12-12", "Turck-Bi6U-18"],
    "LIMIT SWITCH":                 ["Schneider-XCMD2102", "Siemens-3SE5112"],
}

INVALID_CATEGORY_CODES = ["999001", "999002", "999003", "888100", "777200"]
INVALID_BASE_NAMES = ["COMPONENT", "SPARE PART", "ELEMENT", "DEVICE", "UNIT"]
FORBIDDEN_SYMBOLS = ["#", "*", ";", "'", "|", "!"]
STATUSES = ["NEW", "APPROVED", "IN REVIEW", "PENDING"]


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def make_row(i):
    code, cat_label, base_name = random.choice(CATEGORIES)
    designator = random.choice(DESIGNATORS[cat_label])
    mfr_part = random.choice(MFR_PARTS[cat_label])
    status = random.choice(STATUSES)

    err_category      = random.random() < 0.05
    err_base_name     = random.random() < 0.05
    err_symbol        = random.random() < 0.08
    err_lowercase     = random.random() < 0.07
    err_extra_space   = random.random() < 0.06
    err_long_label    = random.random() < 0.06
    err_no_base       = random.random() < 0.06
    err_no_designator = random.random() < 0.05
    err_long_part     = random.random() < 0.04

    actual_code      = random.choice(INVALID_CATEGORY_CODES) if err_category else code
    actual_base_name = random.choice(INVALID_BASE_NAMES)     if err_base_name else base_name

    fi = LABEL_FI[base_name]
    de = LABEL_DE[base_name]

    description_en = f"{base_name} {designator}"
    description_fi = f"{fi} {designator}"
    description_de = f"{de} {designator}"

    if err_long_label:
        description_en = f"{base_name} {designator} ISO-2024-REV3-APPENDIX"

    if err_no_base:
        description_en = f"{designator} REPLACEMENT PART"

    if err_lowercase:
        description_en = description_en[:8].lower() + description_en[8:]

    if err_no_designator:
        description_fi = fi

    if err_extra_space:
        description_de = description_de[:12] + "  " + description_de[12:]

    if err_symbol:
        sym = random.choice(FORBIDDEN_SYMBOLS)
        col_choice = random.randint(0, 2)
        if col_choice == 0:
            description_en = description_en[:10] + sym + description_en[10:]
        elif col_choice == 1:
            description_fi = description_fi[:8] + sym + description_fi[8:]
        else:
            description_de = description_de[:9] + sym + description_de[9:]

    if err_long_part:
        mfr_part = mfr_part + "-SPECIAL-ORDER-ITEM"

    return {
        "item_id":        f"I{i+1:05d}",
        "product_group":  actual_code,
        "basic_name":     actual_base_name,
        "specification":  designator,
        "description_en": description_en,
        "description_fi": description_fi,
        "description_de": description_de,
        "product_code":   mfr_part,
        "status":         status,
    }


# ---------------------------------------------------------------------------
# Reference sheets
# ---------------------------------------------------------------------------

def build_reference():
    cat_rows = [
        {"product_group_id": c, "description_en": lbl, "basic_name": bn}
        for c, lbl, bn in CATEGORIES
    ]
    return pd.DataFrame(cat_rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)

    items = pd.DataFrame([make_row(i) for i in range(250)])
    item_path = os.path.join(out_dir, "validation_data.xlsx")
    items.to_excel(item_path, index=False)
    print(f"Wrote {len(items)} rows to {item_path}")

    df_cat = build_reference()
    ref_path = os.path.join(out_dir, "reference_data.xlsx")
    df_cat.to_excel(ref_path, index=False)
    print(f"Wrote reference ({len(df_cat)} categories) to {ref_path}")
