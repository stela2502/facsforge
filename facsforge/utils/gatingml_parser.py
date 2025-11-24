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
    """
    Parse a RectangleGate from Gating-ML v2.0:

    <ns0:RectangleGate>
        <ns0:dimension>...</ns0:dimension>
        <ns0:interval ns1:low="..." ns1:high="..."/>
    </ns0:RectangleGate>

    This is a 2-D rectangular gate defined by two dimensions and one interval PER dimension.
    """

    dims = rect_el.findall(f"{NS_G}dimension")
    if len(dims) != 2:
        print("WARNING: RectangleGate has !=2 dimensions")
        return None

    # -------- channel names --------
    channels = []
    for d in dims:
        name = _get_dim_name(d)
        if name:
            channels.append(name)

    # -------- intervals --------
    intervals = rect_el.findall(f"{NS_G}interval")
    if len(intervals) != 2:
        print("WARNING: RectangleGate has invalid interval count")
        return None

    # extract low/high with ns1:low and ns1:high
    def _get_low_high(iv):
        low = float(iv.get(f"{NS_D}low") or iv.get("low"))
        high = float(iv.get(f"{NS_D}high") or iv.get("high"))
        return low, high

    x_low, x_high = _get_low_high(intervals[0])
    y_low, y_high = _get_low_high(intervals[1])

    # Represent rectangle as two corners
    return {
        "type": "rectangle",
        "channels": channels,
        "vertices": [
            [x_low, y_low],
            [x_high, y_high],
        ],
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
