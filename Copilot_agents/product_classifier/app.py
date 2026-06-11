"""Product Classifier — Streamlit simulation of the Copilot Studio agent."""

import json
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Product Classifier",
    page_icon="🔍",
    layout="centered",
)

# ─────────────────────────────────────────────────────────────────────────────
# Pre-built examples — real responses from the agent
# ─────────────────────────────────────────────────────────────────────────────

EXAMPLES = {
    "ADN25-25IPA": {
        "group_code": "20000",
        "group_name": "Pneumatic Cylinders",
        "description_en": "Compact pneumatic cylinder",
        "description_fi": "Kompakti paineilmasylinteri",
        "specification": "ADN-25-25-I-P-A",
        "short_reason": (
            "The Festo part ADN-25-25-I-P-A is described in manufacturer sources as a compact "
            "pneumatic cylinder according to ISO 21287."
        ),
        "confidence": 0.96,
        "evidence": [
            {
                "title": "Compact cylinder ADN-25-25-I-P-A - Festo",
                "url": "https://ftp.festo.com/Public/PNEUMATIC/SOFTWARE_SERVICE/Datasheet/EN_US/536263.pdf",
            },
            {
                "title": "Compact cylinder ADN-25-25-I-P-A | Festo USA",
                "url": "https://www.festo.com/us/en/a/536263/",
            },
        ],
        "clarifying_question": None,
    },
    "089UDC306BAECA": {
        "group_code": "30000",
        "group_name": "Motors",
        "description_en": "AC servo motor",
        "description_fi": "AC-servomoottori",
        "specification": "089UDC306BAECA",
        "short_reason": (
            "Manufacturer references identify 089UDC306BAECA as a Control Techniques (Nidec) "
            "Unimotor HD series AC servo motor."
        ),
        "confidence": 0.93,
        "evidence": [
            {
                "title": "089UDC306BAECA - AC servo motors - Applied Automation",
                "url": "https://shop.appliedindustrialautomation.com/products/089UDC306BAECA",
            },
            {
                "title": "Nidec Drives | Unimotor hd Downloads",
                "url": "https://moen.nidec.com/en/drives/Downloads/User-Guides-and-Software/unimotorhd",
            },
        ],
        "clarifying_question": None,
    },
    "AFKOVL-80-25": {
        "group_code": "42000",
        "group_name": "Hydraulic Filters",
        "description_en": "Hydraulic filter element",
        "description_fi": "Hydrauliikkasuodatinelementti",
        "specification": "AFKOVL-80-25",
        "short_reason": (
            "The AFKOVL code designates hydraulic filter elements, confirmed by multiple "
            "distributor sources including Airfil and Oxfil."
        ),
        "confidence": 0.95,
        "evidence": [
            {
                "title": "Airfil AFKOVL8025 Hydraulic Filter – Oxfil.com",
                "url": "https://oxfil.com/en/eu/product/hydraulic-filter/airfil-afkovl8025",
            },
            {
                "title": "Filter finder - Airfil Oy",
                "url": "https://en.airfil.fi/tuotteet/hae/SFlEQUM=",
            },
        ],
        "clarifying_question": None,
    },
    "100 92 SH": {
        "group_code": "50000",
        "group_name": "Couplings",
        "description_en": "Flexible coupling element",
        "description_fi": "Joustava kytkinelementti",
        "specification": "ROTEX 100 92 Shore A",
        "short_reason": (
            "Web evidence shows '100 92 SH' corresponds to a KTR ROTEX coupling spider with "
            "92 Shore A hardness, used as an elastomer element in flexible jaw couplings."
        ),
        "confidence": 0.96,
        "evidence": [
            {
                "title": "ROTEX 100 Spider 92 Shore A T-PUR® orange - Awelastic",
                "url": "https://awelastic.com/product/rotex-100-spider-92-shore-a-t-pur-orange/",
            },
        ],
        "clarifying_question": None,
    },
    "1015": {
        "group_code": "60000",
        "group_name": "Bearings",
        "description_en": "Plain bearing bushing",
        "description_fi": "Liukulaakeriholkki",
        "specification": "1015 DU (PTFE-lined sleeve)",
        "short_reason": (
            "Web evidence shows '1015DU' refers to a GGB DU™ cylindrical plain bushing with "
            "PTFE lining, but '1015' also appears as a thrust ball bearing code — ambiguous."
        ),
        "confidence": 0.70,
        "evidence": [
            {
                "title": "1015DU Datasheet - GGB DU™ Cylindrical Bushes | GlobalSpec",
                "url": "https://datasheets.globalspec.com/ds/enpro-industries/1015du/cf9b85be-a352-46cc-a5f4-d44cce6cbe3e",
            },
            {
                "title": "1015 | Single Direction Thrust Ball Bearings | SKDIN",
                "url": "https://www.skdin.com/products/bearings/ball-bearings/thrust-ball-bearings/single-direction-thrust-ball-bearings/productid-1015",
            },
        ],
        "clarifying_question": "Is this part a plain bearing bushing (e.g., DU type sleeve) or a thrust ball bearing?",
        "followup_response": {
            "group_code": "60000",
            "group_name": "Bearings",
            "description_en": "Needle roller bearing",
            "description_fi": "Neulalaakeri",
            "specification": "1015",
            "short_reason": (
                "User indicated the part is a needle bearing, which falls under rolling bearings "
                "(needle types included). This aligns with internal grouping for roller bearings."
            ),
            "confidence": 0.85,
            "evidence": [
                {
                    "title": "1015 | Aerospace-Bearing",
                    "url": "https://aerospace-bearing.com/en/catalog/unmounted-antifriction-bearings/3110-00-156-1901/1015",
                },
            ],
            "clarifying_question": None,
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Material groups from Excel
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data
def load_material_groups() -> dict[str, str]:
    path = Path(__file__).parent / "demo_data" / "material_groups_demo.xlsx"
    df = pd.read_excel(path, dtype=str)
    # Positional access so a column header rename in the Excel doesn't break the app
    return dict(zip(df.iloc[:, 0], df.iloc[:, 1]))


def _groups_as_text(groups: dict) -> str:
    return "\n".join(f"{code}: {name}" for code, name in groups.items())


# ─────────────────────────────────────────────────────────────────────────────
# Matching
# ─────────────────────────────────────────────────────────────────────────────


def find_example(ticket: str) -> dict | None:
    """Case-insensitive, whitespace-insensitive lookup against EXAMPLES."""
    key = ticket.strip().upper().replace(" ", "")
    for ex_key, ex_val in EXAMPLES.items():
        if key == ex_key.strip().upper().replace(" ", ""):
            return ex_val
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Live classification: Tavily web search + Claude Haiku
# ─────────────────────────────────────────────────────────────────────────────


def _get_secret(name: str) -> str:
    # st.secrets raises FileNotFoundError when no secrets.toml exists locally;
    # fall back to environment variables so the app still runs in that case
    try:
        return st.secrets.get(name) or ""
    except Exception:
        return os.environ.get(name, "")


def classify_live(ticket: str, groups: dict) -> tuple[dict | None, str | None]:
    """Tavily search → Claude Haiku → structured JSON classification."""
    # Lazy imports so a missing package shows a clear error rather than crashing at startup
    try:
        from tavily import TavilyClient
        import anthropic
    except ImportError:
        return None, "Required packages not installed: tavily-python, anthropic."

    tavily_key = _get_secret("TAVILY_API_KEY")
    anthropic_key = _get_secret("ANTHROPIC_API_KEY")

    if not tavily_key or not anthropic_key:
        return None, (
            "API keys not configured. Add TAVILY_API_KEY and ANTHROPIC_API_KEY to "
            "Streamlit secrets (Settings → Secrets on Streamlit Cloud)."
        )

    # Web search
    try:
        tavily = TavilyClient(api_key=tavily_key)
        results = tavily.search(
            query=f"{ticket} industrial part type specifications datasheet",
            max_results=5,
            search_depth="basic",  # "advanced" gives richer results but costs more API credits
        )
        snippets = "\n\n".join(
            f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content'][:500]}"
            for r in results.get("results", [])
        )
    except Exception as exc:
        return None, f"Search failed: {exc}"

    # Classification
    groups_str = _groups_as_text(groups)
    system = f"""You are an industrial product classifier for item master data.

Reference catalogue (group_code: group_name):
{groups_str}

Rules:
- Return ONLY valid JSON — no markdown fences, no text outside the JSON object
- group_code must be one of the codes in the reference catalogue above
- confidence: 0.00–1.00
- If confidence < 0.70, include a specific clarifying_question; otherwise null
- evidence URLs must come from the search results provided

Field definitions:
- description_en: Generic product type label in English. 2–5 words only. NO brand names, NO model numbers, NO specifications. Examples: "Gear motor", "Pneumatic cylinder", "Hydraulic filter element", "Plain bearing bushing"
- description_fi: Same in Finnish. Examples: "Hammasmoottori", "Paineilmasylinteri", "Hydrauliikkasuodatinelementti"
- specification: The exact model or type code that identifies this specific product — use the ticket value if confirmed by web sources. Do NOT describe the product here, only the identifying code. Examples: "R37DRN100LS4", "AFKOVL-80-25"
- short_reason: 1–2 concise sentences. State what the product is and the key identification signal from the search results."""

    user = f"""Ticket: {ticket}

Web search results:
{snippets}

Return JSON with exactly this structure:
{{
  "group_code": "...",
  "group_name": "...",
  "description_en": "...",
  "description_fi": "...",
  "specification": "...",
  "short_reason": "...",
  "confidence": 0.00,
  "evidence": [{{"title": "...", "url": "..."}}],
  "clarifying_question": null
}}"""

    try:
        client = anthropic.Anthropic(api_key=anthropic_key)
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown fences if the model includes them despite instructions
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw.strip())
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"Could not parse model response as JSON: {exc}"
    except Exception as exc:
        return None, f"Classification failed: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Result rendering
# ─────────────────────────────────────────────────────────────────────────────


def _confidence_color(value: float) -> str:
    if value >= 0.90:
        return "#2e7d32"  # green
    if value >= 0.70:
        return "#f57c00"  # amber
    return "#c62828"      # red


def render_result(result: dict, label: str = "") -> None:
    if label:
        st.caption(label)

    code = result.get("group_code", "")
    name = result.get("group_name", "")
    confidence = float(result.get("confidence", 0))
    color = _confidence_color(confidence)

    st.markdown("**Product group**")
    st.markdown(
        f'<span style="background:{color};color:white;padding:7px 14px;'
        f'border-radius:5px;font-size:1.05rem;font-weight:600;">'
        f"{code} — {name}</span>",
        unsafe_allow_html=True,
    )
    st.write("")  # spacing after badge
    # Custom HTML bar instead of st.progress() — Streamlit's built-in bar color
    # can't be reliably overridden via CSS across different Streamlit versions
    st.markdown(
        f'<div style="margin-bottom:12px;">'
        f'<div style="background:#e0e0e0;border-radius:4px;height:8px;">'
        f'<div style="background:{color};width:{confidence*100:.0f}%;height:100%;border-radius:4px;"></div>'
        f'</div>'
        f'<span style="font-size:0.85rem;color:#555;">Confidence: {confidence:.0%}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Description (EN)**  \n{result.get('description_en', '')}")
        st.markdown(f"**Description (FI)**  \n{result.get('description_fi', '')}")
    with col2:
        st.markdown(f"**Specification**  \n`{result.get('specification', '')}`")
        st.markdown(f"**Reason**  \n{result.get('short_reason', '')}")

    evidence = [e for e in result.get("evidence", []) if e.get("url")]
    if evidence:
        st.markdown("**Web search results**")
        for e in evidence:
            st.markdown(f"- [{e['title']}]({e['url']})")


# ─────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────────────────────

for _k, _v in {
    "current_ticket": "",
    "current_result": None,
    "show_followup": False,
    "run_now": False,
    "pending_ticket": "",
    "selectbox_version": 0,
    "input_version": 0,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
# Layout
# ─────────────────────────────────────────────────────────────────────────────

st.title("Product Classifier")
st.markdown(
    "A Microsoft Copilot Studio agent for industrial item master data. "
    "It takes a vague item creation ticket — a part number, a model code, or a rough description — "
    "runs a web search to identify the real product, and maps it to the correct internal product group. "
    "The output includes harmonized descriptions, specification, confidence score, and source links."
)
st.markdown(
    "_This page is a simplified simulation of the agent, not the agent itself. "
    "The real agent runs inside Microsoft Copilot Studio with Bing web search._"
)

st.divider()

with st.expander("How this works"):
    st.markdown(
        """
### Pre-built examples

The dropdown below contains five real item descriptions from the agent test run,
with the actual agent responses stored in this app. Select a description, press **Classify**,
and the response appears instantly — no web search is made.

The examples cover different product types and difficulty levels:
- `ADN25-25IPA` — Festo part number, unambiguous, high confidence
- `089UDC306BAECA` — servo motor code, high confidence
- `AFKOVL-80-25` — hydraulic filter element, high confidence
- `100 92 SH` — ambiguous input resolved to coupling spider, high confidence
- `1015` — low confidence: the agent raises a clarifying question and updates its
  answer based on the user's response

### Your own input

You can also type any industrial part number or model code and press **Classify**.
The app will run a live web search and classify the result using the same output
format as the real agent. Results depend on what public sources are available for
the part.

The demo catalogue contains 15 product groups. For the best results, try part numbers
from the product families listed in the reference catalogue below.
"""
    )

st.divider()

groups = load_material_groups()

# ── Pre-built examples ────────────────────────────────────────────────────────

st.subheader("Pre-built examples")
st.caption(
    "These are real item descriptions from the agent test run. "
    "Select one and press **Classify**."
)

_placeholder = "— select a pre-built item description —"
example_options = [_placeholder] + list(EXAMPLES.keys())
selected_example = st.selectbox(
    "Pre-built item description",
    options=example_options,
    index=0,
    label_visibility="collapsed",
    # Version in key forces a full reset when incremented after classification
    key=f"example_select_{st.session_state.selectbox_version}",
)

# ── Own input ─────────────────────────────────────────────────────────────────

st.subheader("Or type your own input")

custom_ticket = st.text_input(
    "Item creation ticket description",
    placeholder="Type a part number or model code",
    key=f"ticket_input_{st.session_state.input_version}",
)

# Reference catalogue — shown here so users can see which product families work best
with st.expander("Reference catalogue — 15 product groups in this demo"):
    st.caption(
        "For best results with live classification, use part numbers from these product families. "
        "A production deployment would use the full internal catalogue."
    )
    df = pd.DataFrame(list(groups.items()), columns=["Group Code", "Group Name"])
    st.dataframe(df, hide_index=True, use_container_width=True)

if st.button("Classify", type="primary"):
    custom = custom_ticket.strip()
    sel = selected_example if selected_example != _placeholder else ""
    effective = custom or sel
    if effective:
        st.session_state.pending_ticket = effective
        st.session_state.run_now = True
        st.session_state.show_followup = False
    else:
        st.warning("Select a pre-built example or type an item description.")

# ── Classification ────────────────────────────────────────────────────────────

if st.session_state.run_now:
    st.session_state.run_now = False
    current = st.session_state.pending_ticket.strip()
    if current:
        example = find_example(current)
        if example:
            st.session_state.current_result = example
        elif len(current) < 4:
            # Too short for a reliable web search — return without calling the API
            st.session_state.current_result = {
                "group_code": "—",
                "group_name": "Insufficient data",
                "description_en": "Input too short to classify",
                "description_fi": "Syöte liian lyhyt luokitteluun",
                "specification": current,
                "short_reason": (
                    "At least 4 characters are needed for a reliable product identification. "
                    "Please provide a part number, model code, or description."
                ),
                "confidence": 0.0,
                "evidence": [],
                "clarifying_question": None,
            }
        else:
            with st.spinner("Searching the web and classifying..."):
                result, err = classify_live(current, groups)
            st.session_state.current_result = result if result else {"_error": err}
        st.session_state.current_ticket = current
        # Increment version keys — forces both widgets to re-render empty on next run
        st.session_state.input_version += 1
        st.session_state.selectbox_version += 1
        st.rerun()

# ── Result display ────────────────────────────────────────────────────────────

result = st.session_state.current_result
if result:
    st.divider()

    with st.container(border=True):
        if "_error" in result:
            st.error(result["_error"])
        else:
            is_example = find_example(st.session_state.current_ticket) is not None
            source_label = (
                "📋 Pre-built demo response (real agent run)"
                if is_example
                else "🤖 Live classification (Tavily + Claude)"
            )
            # Show the classified ticket before the result
            st.markdown(
                f"**Ticket:** `{st.session_state.current_ticket}`"
            )
            st.write("")
            render_result(result, label=source_label)

            # Clarifying question flow
            cq = result.get("clarifying_question")
            if cq and not st.session_state.show_followup:
                st.warning(f"❓ **Clarifying question:** {cq}")
                with st.form("followup_form"):
                    followup = st.text_input(
                        "Your answer", placeholder='e.g. "needle bearing"'
                    )
                    if st.form_submit_button("Continue") and followup.strip():
                        st.session_state.show_followup = True
                        # The only pre-built follow-up response is for "needle bearing";
                        # any other answer gets a note explaining the demo limitation
                        if "needle" not in followup.lower() and result.get("followup_response"):
                            st.session_state.current_result["_followup_note"] = (
                                "In the real agent, your clarification triggers a new web search. "
                                "This demo has a pre-built response for 'needle bearing' — try that."
                            )

            if st.session_state.show_followup:
                if result.get("followup_response"):
                    st.divider()
                    render_result(
                        result["followup_response"],
                        label="📋 Updated classification after clarification",
                    )
                elif result.get("_followup_note"):
                    st.info(result["_followup_note"])
