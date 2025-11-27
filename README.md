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

### Using Singularity / Apptainer module (HPC)

```bash
ml FlowUtils
```

---

## Usage

### Basic workflow

```bash
facsforge analyze-facs     -o results/analysis     experiment.fcs     index.csv     gates.yaml
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

### Convert FlowJo workspace

```bash
facsforge flowjo2own experiment.wsp > gates.yaml
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

Typical areas of development:

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

