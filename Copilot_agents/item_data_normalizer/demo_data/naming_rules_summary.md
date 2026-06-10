# Fastener Naming Rules — Summary

This file describes the naming conventions used by the Fastener Normalizer agent.
It is a simplified reference for the demo. The full internal rules document is not published.

---

## Name Structure

```
[Description (English)] [Standard] [Coating/Finish] [Material/Class] [Size]
```

Example: `Hexagon socket head cap screw ISO 4762 Zn 8.8 M8×80`

---

## Standard Priority

If both ISO and DIN standards are present, use ISO only in the output.

| Input standards         | Output standard |
|-------------------------|-----------------|
| DIN 912, ISO 4762       | ISO 4762        |
| DIN 603, ISO 8677       | ISO 8677        |
| DIN 916 (only)          | DIN 916         |
| INT-2019 (only)         | INT-2019        |

---

## Standard-to-Description Mapping (key entries)

| Standard               | Description (English)                         | Description (Finnish)          |
|------------------------|-----------------------------------------------|--------------------------------|
| ISO 4762               | Hexagon socket head cap screw                 | Kuusiokoloruuvi                |
| ISO 10642              | Hexagon socket countersunk head screw         | Kuusiokoloruuvi uppokanta      |
| ISO 4014 / ISO 4017    | Hexagon head screw                            | Kuusioruuvi                    |
| ISO 8677 / ISO 8678    | Cup square bolt                               | Lukkoruuvi                     |
| ISO 4029 / DIN 916     | Hexagon socket set screw                      | Kuusiokolopidätinruuvi         |
| ISO 4032               | Hexagon nut                                   | Kuusiomutteri                  |
| ISO 7042               | Self-locking nut                              | Jousimutteri                   |
| ISO 7089               | Plain washer                                  | Tasainen aluslevy              |

If no standard mapping is found, the existing descriptions are kept with case and spacing normalized.

---

## Size Normalization

| Input        | Output   | Rule                                    |
|--------------|----------|-----------------------------------------|
| `M8x80`      | `M8×80`  | Replace `x` with multiplication sign × |
| `M6 x 1,0 x 25` | `M6×25` | Comma → dot, collapse extra tokens   |
| `M12  8`     | `M12 8`  | Collapse multiple spaces               |

---

## Text Normalization

- All-caps names and descriptions are sentence-cased: `HEXAGON NUT` → `Hexagon nut`
- Leading, trailing, and consecutive spaces are removed
- Stray letters that are clearly noise are dropped

---

## Coating and Material Tokens

Coating and finish tokens must not be lost:

- `Zn` — zinc coating
- `A2-70`, `A4-70` — stainless steel grade
- `8.8`, `10.9`, `12.9` — strength class

These are preserved in Specification before the size token: `ISO 4762 Zn 8.8 M8×80`
