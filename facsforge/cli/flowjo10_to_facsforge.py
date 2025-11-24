"""
FlowJo v10 → FACSForge converter

FlowJo v10 uses ZIP-based .wsp files containing:
    workspace.xml
    analysis.xml
    compensation.xml   (sometimes)
    display.xml        (sometimes)

Inside the XML, gates are represented differently than in v9:

    <Gate type="PolygonGate">
        <Points> ... </Points>
    </Gate>

    <Gate type="RectangleGate"
          xMin="..." xMax="..."
          yMin="..." yMax="..."
          xAxis="FSC-A" yAxis="SSC-A">
        ...
    </Gate>

    <Gate type="RangeGate" parameter="FSC-A" min="..." max="..." />

FlowJo v10 sometimes omits axis/channel info for polygon gates,
so we must infer or leave as empty lists.
"""

import zipfile
import xml.etree.ElementTree as ET
import yaml

# =====================================================================
# ZIP LOADING
# =====================================================================

def load_flowjo10_xml(wsp_path):
    """Load FlowJo v10 workspace.xml from inside a ZIP .wsp file."""
    try:
        with zipfile.ZipFile(wsp_path, "r") as z:
            for name in z.namelist():
                if name.lower().endswith(".xml") and "workspace" in name.lower():
                    return ET.fromstring(z.read(name))
            # fallback: any XML
            for name in z.namelist():
                if name.lower().endswith(".xml"):
                    return ET.fromstring(z.read(name))
    except zipfile.BadZipFile:
        raise RuntimeError("This is not a FlowJo v10 ZIP-based WSP (use v9 parser).")


# =====================================================================
# PANEL EXTRACTION
# =====================================================================

def extract_panel_v10(root):
    """
    FlowJo v10 stores parameters differently from v9.
    Typical structure:

    <Keyword name="P1N" value="FSC-A"/>
    <Keyword name="P1S" value="FSC-A short name"/>
    <Keyword name="P1D" value="FSC detector"/>

    Or under <Parameter> in some files.

    This parser provides a minimal panel mapping.
    """

    panel = {}

    # 1) Try FlowJo v10 Parameter nodes (some workspaces use them)
    for p in root.findall(".//Parameter"):
        name = p.get("name") or p.get("shortName") or p.get("longName")
        if not name:
            continue

        fluor = None
        det = p.find("Detector")
        if det is not None:
            fluor = det.text

        panel[name] = {
            "fluor": fluor,
            "role": None,
            "ignore": False,
        }

    # 2) Fallback: Keyword-based detector/channel mapping
    # Example: P1N = FSC-A  /  P1D = FITC
    keywords = {kw.get("name"): kw.get("value") for kw in root.findall(".//Keyword")}
    for key, val in keywords.items():
        if key.endswith("N") and val:
            channel = val
            detector = keywords.get(key[:-1] + "D", None)  # P1D
            panel[channel] = {
                "fluor": detector,
                "role": None,
                "ignore": False,
            }

    return panel



def parse_gate_v10(g_el):
    return parse_gatingml_gate(g_el)



# =====================================================================
# EXTRACT GATES → FACSForge STRUCTURE
# =====================================================================

def extract_gates_v10(root):
    """
    FlowJo v10 stores populations like:

        <Population name="CD3+" parent="Lymphocytes">
            <Gate type="PolygonGate"> ... </Gate>
        </Population>

    We map:
        population → celltypes entry
    """

    celltypes = {}

    for pop in root.findall(".//Population"):
        name = pop.get("name")
        parent = pop.get("parent")
        gate_el = pop.find("Gate")

        if gate_el is None:
            continue

        gate_def = parse_gate_v10(gate_el)
        if gate_def is None:
            continue

        celltypes[name] = {
            "parent": parent,
            "gate": gate_def,
            "positive": [],
            "negative": [],
        }

    return celltypes


# =====================================================================
# TOP-LEVEL CONVERTER
# =====================================================================

def convert_v10(wsp_path, experiment_name="FlowJoV10"):
    """
    Convert FlowJo v10 ZIP-based WSP → FACSForge dict.
    """

    root = load_flowjo10_xml(wsp_path)

    return {
        "metadata": {
            "experiment_name": experiment_name,
            "operator": None,
            "date": None,
            "notes": "",
        },
        "panel": extract_panel_v10(root),
        "celltypes": extract_gates_v10(root),
        "umap": {
            "enabled": False
        },
    }
