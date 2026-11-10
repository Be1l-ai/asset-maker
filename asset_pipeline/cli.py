"""CLI commands to scaffold new procedural asset directories from templates."""

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"


def list_templates() -> list[str]:
    """Return available template names."""
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir())


def init_asset(template_name: str, target_dir: Path | str, asset_name: str | None = None) -> Path:
    """Scaffold a new asset folder from a template."""
    src = TEMPLATES_DIR / template_name
    if not src.is_dir():
        available = ", ".join(list_templates())
        raise ValueError(f"Template '{template_name}' not found. Available: {available}")

    dst = Path(target_dir).resolve()
    if dst.exists() and any(dst.iterdir()):
        raise FileExistsError(f"Target directory '{dst}' already exists and is not empty.")

    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)

    name = asset_name or dst.name
    # Update ASSET_NAME inside generate.py if present
    gen_file = dst / "generate.py"
    if gen_file.is_file():
        code = gen_file.read_text()
        code = code.replace('ASSET_NAME = "asset"', f'ASSET_NAME = "{name}"')
        code = code.replace('ASSET_NAME = "icon"', f'ASSET_NAME = "{name}"')
        code = code.replace('ASSET_NAME = "model"', f'ASSET_NAME = "{name}"')
        code = code.replace('ASSET_NAME = "flipbook"', f'ASSET_NAME = "{name}"')
        code = code.replace('ASSET_NAME = "sound"', f'ASSET_NAME = "{name}"')
        code = code.replace('ASSET_NAME = "tile"', f'ASSET_NAME = "{name}"')
        gen_file.write_text(code)

    return dst


def main():
    parser = argparse.ArgumentParser(description="AssetMaking Scaffolding Tool")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="List available asset templates")

    new_parser = subparsers.add_parser("new", help="Scaffold a new asset from a template")
    new_parser.add_argument("template", choices=list_templates() or ["2d_icon", "2d_tile", "3d_prop", "vfx_flipbook", "sfx_sound"],
                            help="Template kind")
    new_parser.add_argument("destination", type=Path, help="Target folder (e.g. assets/sword)")
    new_parser.add_argument("--name", type=str, default=None, help="Asset identifier name")

    audit_parser = subparsers.add_parser("audit", help="Audit asset recipe(s): unused imports, vault_refs, stale hashes")
    audit_parser.add_argument("assets", type=Path, nargs="+", help="Asset folder(s)")

    cmp_parser = subparsers.add_parser("compare", help="Print metrics for two asset files side by side")
    cmp_parser.add_argument("a", type=Path)
    cmp_parser.add_argument("b", type=Path)

    args = parser.parse_args()

    if args.command == "list":
        for t in list_templates():
            print(f"- {t}")
    elif args.command == "new":
        target = init_asset(args.template, args.destination, args.name)
        print(f"✓ Created new asset in {target}")
        print(f"  Next step: cd {target} && python generate.py")
    elif args.command == "audit":
        from .audit import audit_recipe
        failed = False
        for folder in args.assets:
            report = audit_recipe(folder)
            print(report.format())
            failed |= not report.ok
        sys.exit(1 if failed else 0)
    elif args.command == "compare":
        from .audit import compare_assets
        print(compare_assets(args.a, args.b))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
