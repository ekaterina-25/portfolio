# Product Classifier — Example Tickets

Each example shows a realistic item creation ticket as it arrives from a requester,
followed by the agent's JSON response.

---

## Ticket 1 — Pneumatic cylinder

**Input (ticket description):**
```
ADN25-25IPA
```

**Agent response:**
```json
{
  "group_code": "20000",
  "group_name": "Pneumatic Cylinders",
  "description_en": "Compact pneumatic cylinder",
  "description_fi": "Kompakti paineilmasylinteri",
  "specification": "ADN-25-25-I-P-A",
  "short_reason": "The Festo part ADN-25-25-I-P-A (similar to ADN25-25IPA) is described in manufacturer sources as a compact pneumatic cylinder according to ISO 21287, making it fit under pneumatic cylinders.",
  "confidence": 0.96,
  "evidence": [
    {
      "title": "Compact cylinder ADN-25-25-I-P-A - Festo",
      "url": "https://ftp.festo.com/Public/PNEUMATIC/SOFTWARE_SERVICE/Datasheet/EN_US/536263.pdf"
    },
    {
      "title": "Compact cylinder ADN-25-25-I-P-A | Festo USA",
      "url": "https://www.festo.com/us/en/a/536263/"
    }
  ],
  "clarifying_question": null
}


```

---

## Ticket 2 — Servo motor

**Input (ticket description):**
```
089UDC306BAECA
```

**Agent response:**
```json
{
  "group_code": "30000",
  "group_name": "Motors",
  "description_en": "AC servo motor",
  "description_fi": "AC-servomoottori",
  "specification": "089UDC306BAECA",
  "short_reason": "Manufacturer references identify 089UDC306BAECA as a Control Techniques (Nidec) Unimotor HD series AC servo motor.",
  "confidence": 0.93,
  "evidence": [
    {
      "title": "089UDC306BAECA - AC servo motors (Control Techniques) - Applied Automation",
      "url": "https://shop.appliedindustrialautomation.com/products/089UDC306BAECA"
    },
    {
      "title": "Nidec Drives | Unimotor hd Downloads",
      "url": "https://moen.nidec.com/en/drives/Downloads/User-Guides-and-Software/unimotorhd"
    }
  ],
  "clarifying_question": null
}
```

---

## Ticket 3 — Hydraulic filter element 

**Input (ticket description):**
```
AFKOVL-80-25
```

**Agent response:**
```json
{
  "group_code": "42000",
  "group_name": "Hydraulic Filters",
  "description_en": "Hydraulic filter element",
  "description_fi": "Hydrauliikkasuodatin­elementti",
  "specification": "AFKOVL-80-25",
  "short_reason": "The AFKOVL code designates hydraulic filter elements used in hydraulic systems, and similar references like AFKOVL-80-25 ABS confirm it belongs to the hydraulic filter family.",
  "confidence": 0.95,
  "evidence": [
    {
      "title": "Airfil AFKOVL8025 Hydraulic Filter – Oxfil.com",
      "url": "https://oxfil.com/en/eu/product/hydraulic-filter/airfil-afkovl8025"
    },
    {
      "title": "Filter finder - Airfil Oy",
      "url": "https://en.airfil.fi/tuotteet/hae/SFlEQUM="
    }
  ],
  "clarifying_question": null
}
```

---

## Ticket 4 — Coupling (ambiguous input)

**Input (ticket description):**
```
100 92 SH
```

**Agent response:**
```json
{
  "group_code": "50000",
  "group_name": "Couplings",
  "description_en": "Flexible coupling element",
  "description_fi": "Joustava kytkinelementti",
  "specification": "ROTEX 100 92 Shore A",
  "short_reason": "Web evidence shows that '100 92 SH' corresponds to a KTR ROTEX coupling spider with 92 Shore A hardness, used as an elastomer element in flexible jaw couplings.",
  "confidence": 0.96,
  "evidence": [
    {
      "title": "ROTEX 100 Spider 92 Shore A T-PUR® orange - Awelastic",
      "url": "https://awelastic.com/product/rotex-100-spider-92-shore-a-t-pur-orange/"
    },
    {
      "title": "Example item list – Flexible insert ROTEX 28 92 Shore A",
      "url": ""
    }
  ],
  "clarifying_question": null
}
```

---

## Ticket 5 — Ambiguous token, question raised

**Input (ticket description):**
```
1015
```

**Agent response:**
```json
{
  "group_code": "60000",
  "group_name": "Bearings",
  "description_en": "Plain bearing bushing",
  "description_fi": "Liukulaakeriholkkı",
  "specification": "1015 DU (PTFE-lined sleeve)",
  "short_reason": "Web evidence shows that '1015DU' refers to a GGB DU™ cylindrical plain bushing with PTFE lining, used as a sleeve bearing for low friction applications.",
  "confidence": 0.7,
  "evidence": [
    {
      "title": "1015DU Datasheet - GGB - DU™ Cylindrical Bushes - Inch Size | GlobalSpec",
      "url": "https://datasheets.globalspec.com/ds/enpro-industries/1015du/cf9b85be-a352-46cc-a5f4-d44cce6cbe3e"
    },
    {
      "title": "1015 | Single Direction Thrust Ball Bearings | SKDIN",
      "url": "https://www.skdin.com/products/bearings/ball-bearings/thrust-ball-bearings/single-direction-thrust-ball-bearings/productid-1015"
    }
  ],
  "clarifying_question": "Is this part a plain bearing bushing (e.g., DU type sleeve) or a thrust ball bearing?"
}
```
```
I gues it's a needle bearing
```
**Agent response:**
Thank you for clarifying! Based on that, the classification changes accordingly. Here is the corrected mapping:

```json
{
  "group_code": "60000",
  "group_name": "Bearings",
  "description_en": "Needle roller bearing",
  "description_fi": "Neulalaakeri",
  "specification": "1015",
  "short_reason": "User indicated the part is a needle bearing, which falls under rolling bearings (needle types included). This aligns with internal grouping for roller bearings.",
  "confidence": 0.85,
  "evidence": [
    {
      "title": "1015 | Aerospace-Bearing",
      "url": "https://aerospace-bearing.com/en/catalog/unmounted-antifriction-bearings/3110-00-156-1901/1015"
    }
  ],
  "clarifying_question": null
}
```
