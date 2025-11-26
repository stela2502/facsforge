import xml.etree.ElementTree as ET

# Namespaces for Gating-ML v2.0
NS_G = "{http://www.isac-net.org/std/Gating-ML/v2.0/gating}"
NS_D = "{http://www.isac-net.org/std/Gating-ML/v2.0/datatypes}"


# =====================================================================
# Helpers
# =====================================================================

def _get_value(coord_el):
    """Extract numeric value from <coordinate ns1:value="...">."""
    return float(
        coord_el.get(f"{NS_D}value") or
        coord_el.get("value")
    )


def _get_dim_name(dim_el):
    """
    Extract dimension channel name:
    <ns0:dimension>
        <ns1:fcs-dimension ns1:name="FSC-A"/>
    </ns0:dimension>
    """
    fcs_dim = dim_el.find(f"{NS_D}fcs-dimension")
    if fcs_dim is None:
        return None

    return (
        fcs_dim.get(f"{NS_D}name") or
        fcs_dim.get("name")
    )


# =====================================================================
# PolygonGate
# =====================================================================

def parse_polygon_gate(poly_el):
    """
    Parse a PolygonGate from Gating-ML v2.0:

    <ns0:PolygonGate>
        <ns0:dimension>...</ns0:dimension>
        <ns0:vertex>
            <ns0:coordinate ns1:value="123"/>
            <ns0:coordinate ns1:value="456"/>
        </ns0:vertex>
        ...
    </ns0:PolygonGate>
    """

    # -------- channels --------
    channels = []
    for dim in poly_el.findall(f"{NS_G}dimension"):
        name = _get_dim_name(dim)
        if name:
            channels.append(name)

    # -------- vertices --------
    vertices = []
    for v in poly_el.findall(f"{NS_G}vertex"):
        coords = v.findall(f"{NS_G}coordinate")
        if len(coords) != 2:
            continue
        x = _get_value(coords[0])
        y = _get_value(coords[1])
        vertices.append([x, y])

    return {
        "type": "polygon",
        "channels": channels,
        "vertices": vertices,
    }


# =====================================================================
# RectangleGate
# =====================================================================

def parse_rectangle_gate(rect_el):
    dims = rect_el.findall(f"{NS_G}dimension")
    if len(dims) != 2:
        print("WARNING: RectangleGate has !=2 dimensions")
        return None

    # Channel names
    ch_x = _get_dim_name(dims[0])
    ch_y = _get_dim_name(dims[1])

    # Bounds
    x_min = float(dims[0].get(f"{NS_G}min") or dims[0].get("min"))
    x_max = float(dims[0].get(f"{NS_G}max") or dims[0].get("max"))
    y_min = float(dims[1].get(f"{NS_G}min") or dims[1].get("min"))
    y_max = float(dims[1].get(f"{NS_G}max") or dims[1].get("max"))

    # Represent as polygon
    return {
        "type": "polygon",
        "channels": [ch_x, ch_y],
        "vertices": [
            [x_min, y_min],
            [x_max, y_min],
            [x_max, y_max],
            [x_min, y_max],
        ]
    }



# =====================================================================
# Top-Level Gate Parser
# =====================================================================

def parse_gatingml_gate(gate_el):
    """
    Dispatch to the correct Gating-ML 2.0 parser.

    <Gate>
        <ns0:PolygonGate>...</ns0:PolygonGate>
    </Gate>
    """

    # Polygon ---------------------------------------
    poly = gate_el.find(f"{NS_G}PolygonGate")
    if poly is not None:
        return parse_polygon_gate(poly)

    # Rectangle -------------------------------------
    rect = gate_el.find(f"{NS_G}RectangleGate")
    if rect is not None:
        return parse_rectangle_gate(rect)

    # Unsupported gate types (RangeGate, BooleanGate, etc.)
    print("WARNING: Unsupported Gating-ML 2.0 gate:\n",
          ET.tostring(gate_el, encoding="unicode"))
    return None
