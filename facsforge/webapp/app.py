"""
FACSForge Web Server
--------------------

This module provides the core Flask application that powers the
interactive annotation, gating inspection, panel editing, and
index-to-sequencing linking interface.

This is the ROOT of the web server. Other modules will be added later:
 - pages.py (multi-step workflow)
 - api.py (AJAX endpoints)
 - static/ (JS/CSS)
 - templates/ (HTML templates)

For now this file defines:
 - Flask app
 - load/save config logic
 - entrypoint function `run_server()`
"""

import os
import yaml
from flask import Flask, render_template, request, jsonify


# ------------------------------------------------------------
# Globals (simple for now – replaced later with a class)
# ------------------------------------------------------------

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

CONFIG_DATA = {}
CONFIG_PATH = None


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def load_config(path):
    """Load a FACSForge YAML config into memory."""
    global CONFIG_DATA, CONFIG_PATH
    CONFIG_PATH = os.path.abspath(path)

    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as f:
        CONFIG_DATA = yaml.safe_load(f) or {}

    # Add default structure if missing
    CONFIG_DATA.setdefault("panel", {})
    CONFIG_DATA.setdefault("celltypes", {})
    CONFIG_DATA.setdefault("umap", {"enabled": False})
    CONFIG_DATA.setdefault("metadata", {})

    return CONFIG_DATA


def save_config():
    """Save the in-memory CONFIG_DATA back to disk."""
    if CONFIG_PATH is None:
        return False

    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(CONFIG_DATA, f, sort_keys=False)

    return True


# ------------------------------------------------------------
# Web Routes
# ------------------------------------------------------------

@app.route("/")
def index():
    """
    Main entry point.

    Shows a landing page with:
     - overview of the loaded config
     - links to each workflow step (panels, gates, UMAP, seq linking, etc.)
    """
    return render_template("index.html", config=CONFIG_DATA)


@app.route("/api/panel", methods=["GET", "POST"])
def api_panel():
    """
    API to GET or UPDATE the panel section.
    """
    if request.method == "GET":
        return jsonify(CONFIG_DATA.get("panel", {}))

    if request.method == "POST":
        payload = request.json
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid panel format"}), 400

        CONFIG_DATA["panel"] = payload
        save_config()
        return jsonify({"status": "ok"})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    """
    GET: return entire config
    POST: replace config
    """
    if request.method == "GET":
        return jsonify(CONFIG_DATA)

    CONFIG_DATA.update(request.json)
    save_config()
    return jsonify({"status": "saved"})


# ------------------------------------------------------------
# GATES API
# ------------------------------------------------------------

@app.route("/api/gates", methods=["GET", "POST"])
def api_gates():
    """
    GET:
        Returns the entire gate + celltype structure from CONFIG_DATA["celltypes"].
        This includes:
            - parent
            - positive / negative marker annotations
            - gate geometry (polygon / rectangle / threshold)
    POST:
        Replaces CONFIG_DATA["celltypes"] with the provided gate structure.

        Expected format:
            {
              "GateName": {
                  "parent": "ParentGate" or null,
                  "positive": ["CD3", "CD4"],
                  "negative": ["CD19"],
                  "gate": {...}
              },
              ...
            }
    """

    # GET request → return entire structure
    if request.method == "GET":
        return jsonify(CONFIG_DATA.get("celltypes", {}))

    # POST request → update gates
    payload = request.json

    if not isinstance(payload, dict):
        return jsonify({"error": "Gate data must be a dictionary"}), 400

    # Basic validation: every entry must have required fields
    for gatename, info in payload.items():
        if not isinstance(info, dict):
            return jsonify({"error": f"Gate '{gatename}' must be a dict"}), 400

        if "gate" not in info:
            return jsonify({"error": f"Gate '{gatename}' is missing its 'gate' geometry"}), 400

        info.setdefault("parent", None)
        info.setdefault("positive", [])
        info.setdefault("negative", [])

        # Ensure list types
        if not isinstance(info["positive"], list):
            return jsonify({"error": f"Gate '{gatename}': 'positive' must be a list"}), 400
        if not isinstance(info["negative"], list):
            return jsonify({"error": f"Gate '{gatename}': 'negative' must be a list"}), 400

    # Everything looks OK → apply update
    CONFIG_DATA["celltypes"] = payload

    save_config()

    return jsonify({"status": "gates saved"})


@app.route("/api/save", methods=["POST"])
def api_save():
    """Explicit save request."""
    save_config()
    return jsonify({"status": "saved"})


# ------------------------------------------------------------
# Server Entrypoint
# ------------------------------------------------------------

def run_server(config_path, host="127.0.0.1", port=8080):
    """
    Start the FACSForge web server.
    Used by CLI:
        facsforge web <config.yaml>
    """
    print(f"🔧 Loading config: {config_path}")
    load_config(config_path)

    print(f"🌐 Starting FACSForge Web at http://{host}:{port}")
    print("Press Ctrl+C to stop.\n")

    app.run(host=host, port=port, debug=False)


# CLI will import run_server(), not Flask app directly
__all__ = ["run_server", "app"]

