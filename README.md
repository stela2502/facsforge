# facsforge

**FlowJo-compatible FACS analysis as code**

`facsforge` is a command-line toolkit for reproducible flow cytometry analysis driven by configuration files instead of GUIs.  
It allows you to run FlowJo-style gating, plotting, and index overlay pipelines non-interactively and reproducibly.

The project is designed for HPC systems, containers, and automated workflows where GUI tools are unsuitable.

---

## Features

- FlowJo `.wsp` → YAML conversion
- Polygon gates and hierarchical gating
- Batch processing of FCS files
- CSV export of gated populations
- FlowJo-like plots (PNG)
- Index sorting overlay support
- Logicle (biexponential) scaling for fluorescence channels
- Linear scaling for FSC / SSC / Time
- Designed for HPC, Slurm, Apptainer/Singularity

---

## Philosophy

facsforge follows three core principles:

1. **Declare gating, don’t click it**
2. **Automate everything repeatable**
3. **Never hide biology in a GUI**

Your cytometry analysis becomes:

- versionable
- reviewable
- testable
- reproducible

---

## Installation

### From source (development)

```bash
git clone https://github.com/stela2502/facsforge.git
cd facsforge
pip install -e .
```

## Usage

`facsforge` provides a command-line interface for generating experiment configurations, importing FlowJo projects, and executing fully automated cytometry analyses.

All functionality is accessed through the `facsforge` CLI with subcommands.

---

### Generate a starter config from an FCS file

Create a YAML configuration scaffold directly from an input FCS file.  
This inspects the channel header and produces a template config you can edit.

```bash
facsforge flowjo9_to_facsforge --out my_config_file.yaml --wsp my_flowjo_project.wsp
```

This will convert the FlowJo project into a yaml structured config file.

---

### Run the analysis pipeline

Run the full gating and analysis workflow defined in a YAML config:

```bash
facsforge analyze-facs --outdir results/analysis --fcs sort_data.fcs --index-csv sort_data.csv --config my_config_file.yaml
```

Arguments:

- `sample.fcs` — input flow cytometry file  
- `index.csv` — index sorting metadata (optional but recommended)  
- `gates.yaml` — YAML configuration defining gates and metadata  
- `-o results/analysis` — output directory (default: `analysis_out`)  

Outputs include:

- `gated_*.csv` — gated populations
- `*.png` — scatter plots and fluorescence plots
- index overlay (if provided)

---

### Import a FlowJo workspace (main feature)

facsforge can directly convert FlowJo project files into executable YAML pipelines.

#### FlowJo v9 (XML-based)

```bash
facsforge flowjo9_to_facsforge --out my_config_file.yaml --wsp my_flowjo_project.wsp
```

#### FlowJo v10 (ZIP-based)

**This is currently not implemented**

```bash
facsforge flowjo10_to_facsforge project.wsp -o facsforge.yaml --name ExperimentName
```

The generated YAML:

- preserves gating structure
- imports compensation information (if present)
- adds metadata and experiment name
- validates itself before being written

You can immediately run the result:

```bash
facsforge analyze-facs --outdir results/analysis --fcs sort_data.fcs --index-csv sort_data.csv --config my_config_file.yaml
```

---

### Validation and merging behavior

- Existing YAML files are automatically merged when importing FlowJo projects.
- Missing metadata (date, compensation path) is filled automatically.
- YAML is validated against an internal schema before writing.
- Any schema error aborts conversion with a readable validation message.

---

### Debugging

All CLI commands print diagnostic information on failure.  
When importing FlowJo v9, the parsed YAML structure is printed prior to validation to allow inspection.

---

### Exit codes

- `0` — success
- `1` — input or schema error
- non-zero — unexpected failure

---

### Typical workflow

```bash
# Convert FlowJo project to YAML
facsforge flowjo10_to_facsforge --wsp project.wsp --out facsforge.yaml

# Run automated analysis
facsforge analyze-facs --fcs sample.fcs --index-csv index.csv --config facsforge.yaml --outpath results
```

Outputs:

```
results/analysis/
├── gated_Population1.csv
├── gated_Population2.csv
├── Population1_X_vs_Y.png
└── Population2_X_vs_Y.png
```

---

## Scaling behavior

facsforge mimics FlowJo defaults:

| Channel type | Scaling |
|---------------|---------|
| FSC / SSC | Linear |
| TIME | Linear |
| Fluorescence | Logicle |

The logicle transform uses FlowJo-style defaults and supports negative values from compensation.

---

## Index sorting overlay

Index CSV files are automatically overlaid if columns match gating channels.  
If a `Well` column is present, well IDs are rendered directly on the plot at the sorted event positions.

---

## Testing

To run the integration tests:

```bash
pytest -v
```

The test suite verifies:

- CLI behavior
- file generation
- gate population sizes
- output integrity

---

## Project structure

```
facsforge/
├── cli/
├── core/
├── tests/
├── setup.cfg
└── pyproject.toml
```

---

## Contributing

Contributions are welcome.

- gate types
- plotting improvements
- workspace converters
- documentation
- performance tuning

---

## License

MIT License  
See LICENSE file for details.

---

## Links

GitHub repository:  
https://github.com/stela2502/facsforge

