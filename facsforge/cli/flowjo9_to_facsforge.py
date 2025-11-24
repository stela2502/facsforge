import xml.etree.ElementTree as ET
from facsforge.utils import parse_gatingml_gate

# ============================================================
# XML Loader
# ============================================================

def load_flowjo9_xml(path):
    with open(path, "rb") as f:
        xml_bytes = f.read()
    try:
        return ET.fromstring(xml_bytes)
    except Exception as e:
        raise RuntimeError(f"Failed to parse FlowJo v9 XML: {e}")

# ============================================================
# Panel extraction
# ============================================================

def extract_panel_v9(root):
    """
    Generate panel structure matching FACSForge schema:
    
    panel = {
        "FSC-A": { "fluor": None, "role": None, "ignore": false },
        "SSC-A": { "fluor": "FITC", "role": null, "ignore": false },
        ...
    }
    """

    panel = {}

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

    return panel

def parse_gate_v9(g_el):
    return parse_gatingml_gate(g_el)


# ============================================================
# Population → celltypes extraction
# ============================================================

def extract_population_tree(root):
    """
    Extract FlowJo v9 population hierarchy using xml.etree (no getparent()).

    Returns:
        pop_parent:  { pop_name → parent_pop_name or None }
        pop_gateid: { pop_name → gate_id or None }
    """

    pop_parent = {}
    pop_gateid = {}

    # Walk tree manually to track parents
    def recurse(el, parent_pop_name=None):
        # Only handle <Population> nodes
        if el.tag == "Population":
            name = el.get("name")
            pop_parent[name] = parent_pop_name

            gate_el = el.find("gate")
            if gate_el is not None:
                pop_gateid[name] = gate_el.get("ref")
            else:
                pop_gateid[name] = None

            parent_pop_name = name  # this becomes new parent for children

        # Recurse into children
        for child in el:
            recurse(child, parent_pop_name)

    recurse(root)
    return pop_parent, pop_gateid

def extract_celltypes_v9(root):
    celltypes = {}

    for pop in root.findall(".//Population"):
        name = pop.get("name")
        parent = pop.get("parent")
        gate_el = pop.find("Gate")

        if gate_el is None:
            continue

        gate_def = parse_gate_v9(gate_el)
        if gate_def is None:
            continue

        celltypes[name] = {
            "parent": parent,
            "gate": gate_def,
            "positive": [],
            "negative": [],
        }

    return celltypes


def extract_gate_parents(root):
    """
    Extracts gate_id → parent_id mapping from FlowJo v9 XML.
    Returns:
        parents: dict { gate_id: parent_gate_id or None }
    """
    ns = {"g": "http://www.isac-net.org/std/Gating-ML/v2.0/gating"}

    parents = {}

    for gate_el in root.findall(".//g:Gate", ns):
        gid = gate_el.get("{http://www.isac-net.org/std/Gating-ML/v2.0/gating}id")
        pid = gate_el.get("{http://www.isac-net.org/std/Gating-ML/v2.0/gating}parent_id")
        parents[gid] = pid  # may be None
    return parents

def extract_gate_names(root):
    """
    Returns mapping gate_id → gate_name.
    """
    ns = {"g": "http://www.isac-net.org/std/Gating-ML/v2.0/gating"}
    names = {}

    for gate_el in root.findall(".//g:Gate", ns):
        gid = gate_el.get("{http://www.isac-net.org/std/Gating-ML/v2.0/gating}id")
        name_el = gate_el.find("./name")
        if name_el is not None:
            names[gid] = name_el.text.strip()
    return names


def build_yaml_hierarchy(celltypes, root):
    """
    Adds 'parent' field to each celltype in YAML.
    celltypes: dict { name → {...} }
    parents: dict { gate_id → parent_gate_id }
    names: dict { gate_id → gate_name }
    """
    # Build reverse lookup: name → id

    pop_parent, pop_gateid = extract_population_tree(root)

    # ---- 2. Get Gating-ML ID → name mapping
    gate_names = extract_gate_names(root)

    # ---- 3. Get Gating-ML ID → parent ID mapping
    gate_parents = extract_gate_parents(root)

    # ---- 4. Build reverse map: name → GatingML ID
    name_to_gid = {v: k for k, v in gate_names.items()}

    # ---- 5. Assign YAML parent for each celltype
    for cname in celltypes.keys():

        # Find gate ID for this population
        gid = name_to_gid.get(cname)
        if gid is None:
            celltypes[cname]["parent"] = None
            continue

        # Try population parent mapping first (most accurate)
        for pop_name, pgid in pop_gateid.items():
            if pgid == gid:
                parent_pop = pop_parent.get(pop_name)
                if parent_pop in celltypes:
                    celltypes[cname]["parent"] = parent_pop
                else:
                    celltypes[cname]["parent"] = None
                break
        else:
            # Fallback: gatingML parent_id
            parent_gid = gate_parents.get(gid)
            if parent_gid:
                parent_name = gate_names.get(parent_gid)
                if parent_name in celltypes:
                    celltypes[cname]["parent"] = parent_name
                else:
                    celltypes[cname]["parent"] = None
            else:
                celltypes[cname]["parent"] = None


# ============================================================
# Top-level conversion
# ============================================================

def convert_v9(wsp_path, experiment_name="FlowJoV9"):
    root = load_flowjo9_xml(wsp_path)

    celltypes = extract_celltypes_v9(root)
    
    build_yaml_hierarchy(celltypes, root )
    panel = extract_panel_v9(root)

    return {
        "metadata": {
            "experiment_name": experiment_name,
            "operator": "",
            "date": "",
            "notes": "",
        },
        "panel": panel,
        "ignore_markers": [],
        "compensation": {
            "source": "none",
            "path": None
        },
        "celltypes": celltypes,
        "celltypes_of_interest": [],
        "umap": {
            "enabled": False
        }
    }
