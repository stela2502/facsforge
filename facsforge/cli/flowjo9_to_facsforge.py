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
    data = parse_gatingml_gate(g_el)
    return data


# ============================================================
# Population → celltypes extraction
# ============================================================

def extract_population_tree(root):
    """
    Extract FlowJo v9 population hierarchy using xml.etree (no getparent()).

    Returns:
        pop_parent:  { pop_name → parent population name or None }
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
    Insert parent relationships into celltypes using hierarchy from ExternalPopNode.
    """

    hierarchy = extract_gate_path_from_external_nodes(root)

    for pop_name, obj in celltypes.items():
        path = hierarchy.get(pop_name)

        # Store gate_path if available
        if path:
            obj["gate_path"] = path

            # Assign parent from path if possible
            if len(path) >= 2:
                obj["parent"] = path[-2]
            else:
                obj["parent"] = None

        else:
            obj["gate_path"] = [pop_name]
            obj["parent"] = None

def extract_gate_path_from_external_nodes(root):
    """
    Extract gating hierarchy from FlowJo ExternalPopNode entries.
    Returns: dict { population_name -> gate_path[] }
    """
    paths = {}

    for node in root.findall(".//ExternalPopNode"):
        pop = node.find(".//BD_CellView_Lens")
        if pop is None:
            continue

        name = pop.get("population")
        raw = pop.get("path")

        if not name or not raw:
            continue

        # Normalize and split
        path = [p.strip() for p in raw.split("/") if p.strip()]

        paths[name] = path

    return paths

# ============================================================
# Top-level conversion
# ============================================================

def convert_v9(wsp_path, experiment_name="FlowJoV9"):
    root = load_flowjo9_xml(wsp_path)

    print ("flowjo9_to_facsforge - working!")

    celltypes = extract_celltypes_v9(root)
    paths = extract_gate_path_from_external_nodes(root)
    
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
