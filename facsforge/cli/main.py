import argparse
import yaml
import sys
from facsforge.core.validate_schema import validate_config
from facsforge.core.merge import merge_configs, load_existing_yaml
from datetime import date

print(">>> facsforge.cli.main loaded")


def main():
    parser = argparse.ArgumentParser(
        prog="facsforge",
        description="FACSForge: Flow Cytometry analysis and YAML-driven gating."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------
    # generate-config
    # ------------------------------------------------------------
    gen = subparsers.add_parser(
        "generate-config",
        help="Generate a complete YAML config from an FCS file."
    )
    gen.add_argument("--fcs", required=True, help="Path to input FCS file")
    gen.add_argument("--out", required=True, help="Output YAML config file")

    # ------------------------------------------------------------
    # analyze-facs (single file)
    # ------------------------------------------------------------
    analyze = subparsers.add_parser(
        "analyze-facs",
        help="Run the gating + analysis pipeline on a single FCS file."
    )
    analyze.add_argument("--fcs", required=True, help="Path to FCS file")
    analyze.add_argument("--index-csv", required=True, help="Index sorted cells CSV")
    analyze.add_argument("--config", required=True, help="YAML experiment config")
    analyze.add_argument("--outdir", required=True, help="Output directory")

    # ------------------------------------------------------------
    # flowjo9 → yaml
    # ------------------------------------------------------------
    flowjo9 = subparsers.add_parser(
        "flowjo9_to_facsforge",
        help="Convert FlowJo v9 XML-based WSP to FACSForge YAML."
    )
    flowjo9.add_argument("--wsp", required=True)
    flowjo9.add_argument("--out", default="facsforge.yaml")
    flowjo9.add_argument("--name", default="FlowJoV9")

    # ------------------------------------------------------------
    # flowjo10 → yaml
    # ------------------------------------------------------------
    flowjo10 = subparsers.add_parser(
        "flowjo10_to_facsforge",
        help="Convert FlowJo v10 ZIP-based WSP to FACSForge YAML."
    )
    flowjo10.add_argument("--wsp", required=True)
    flowjo10.add_argument("--out", default="facsforge.yaml")
    flowjo10.add_argument("--name", default="FlowJoV10")

    # ------------------------------------------------------------
    # Parse args
    # ------------------------------------------------------------
    args = parser.parse_args()

    # ------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------
    if args.command == "generate-config":
        from facsforge.cli.generate_config import cmd_generate_config
        return cmd_generate_config(args.fcs, args.out)

    elif args.command == "analyze-facs":
        from facsforge.cli.analyze_facs import cmd_analyze_facs
        return cmd_analyze_facs(
            args.fcs,
            args.config,
            args.index_csv,
            args.outdir
        )

    elif args.command == "flowjo9_to_facsforge":
        from facsforge.cli.flowjo9_to_facsforge import convert_v9
        data = convert_v9(args.wsp, args.name)

        existing = load_existing_yaml(args.out)
        merged = merge_configs(existing, data)

        if not data.get("metadata", {}).get("date"):
            today = date.today().strftime("%Y-%m-%d")
            data.setdefault("metadata", {})["date"] = today

        if data.get("compensation", {}).get("path") is None:
            data.setdefault("compensation", {})["path"] = ""

        validate_config(data)

        with open(args.out, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        return 0

    elif args.command == "flowjo10_to_facsforge":
        from facsforge.cli.flowjo10_to_facsforge import convert_v10
        data = convert_v10(args.wsp, args.name)

        if not data.get("metadata", {}).get("date"):
            today = date.today().strftime("%Y-%m-%d")
            data.setdefault("metadata", {})["date"] = today

        if data.get("compensation", {}).get("path") is None:
            data.setdefault("compensation", {})["path"] = ""

        validate_config(data)

        with open(args.out, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    print(">>> CLI ENTRYPOINT HIT", sys.argv)
    main()
