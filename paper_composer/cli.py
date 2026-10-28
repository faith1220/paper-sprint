"""Command-line interface; all operations are local and use the standard library."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from . import core


def parser():
    command = argparse.ArgumentParser(prog="paper-sprint", description="Practical, source-grounded research protocol bookkeeping")
    command.add_argument("--version", action="version", version=__version__)
    commands = command.add_subparsers(dest="command", required=True)
    for name in ("init", "validate", "ablations", "freeze", "record", "select", "report", "demo"):
        sub = commands.add_parser(name)
        sub.add_argument("path", help="Project directory (init/demo require a new path)")
        if name in ("init", "demo"):
            sub.add_argument("--modules", type=int, choices=(2, 3), default=2)
        if name == "init":
            sub.add_argument("--name", default="untitled")
        if name == "validate":
            sub.add_argument("--ready", action="store_true", help="Require evidence-backed protocol fields and split manifests")
        if name == "record":
            sub.add_argument("--file", required=True, help="JSON result object; artifacts must already be inside the project")
        if name == "select":
            sub.add_argument("--arm", required=True)
            sub.add_argument("--reason", required=True)
        if name == "report":
            sub.add_argument("--output", help="Optional JSON report path")
    return command


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            result = core.init_project(args.path, args.name, args.modules)
        elif args.command == "demo":
            result = core.run_demo(args.path, args.modules)
        elif args.command == "validate":
            errors = core.validate_project(args.path, ready=args.ready)
            if errors:
                raise core.ProjectError("; ".join(errors))
            result = {"valid": True, "ready": args.ready, "ready_blockers": [] if args.ready else core.validate_project(args.path, ready=True)}
        elif args.command == "ablations":
            result = {"arms": core.ablation_matrix(args.path)}
        elif args.command == "freeze":
            result = core.freeze_project(args.path)
        elif args.command == "record":
            result = core.record_result(args.path, core.read_json(args.file))
        elif args.command == "select":
            result = core.select_candidate(args.path, args.arm, args.reason)
        else:
            result = core.build_report(args.path)
            if args.output:
                if Path(args.output).exists():
                    raise core.ProjectError("Refusing to overwrite an existing report destination; choose a new path")
                core.write_json(args.output, result)
        print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
        return 2 if result.get("status") == "INVALID" else 0
    except (core.ProjectError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
