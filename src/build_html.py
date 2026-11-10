"""Builds root index.html from modular components in src/components/."""

import re
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent
COMPONENTS_DIR = SRC_DIR / "components"
TEMPLATE_PATH = SRC_DIR / "index.template.html"
OUTPUT_PATH = ROOT_DIR / "index.html"


def build_html() -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    def replace_slot(match: re.Match) -> str:
        indent = match.group(1)
        component_name = match.group(2)
        comp_path = COMPONENTS_DIR / f"{component_name}.html"
        if not comp_path.exists():
            raise FileNotFoundError(f"Component not found: {comp_path}")
        content = comp_path.read_text(encoding="utf-8").strip("\n")
        if indent:
            lines = content.splitlines()
            return "\n".join(f"{indent}{line}" if line else "" for line in lines)
        return content

    pattern = re.compile(r"^([ \t]*)\{\{([a-zA-Z0-9_-]+)\}\}", re.MULTILINE)
    built = pattern.sub(replace_slot, template)
    return built


def main() -> None:
    html = build_html()
    OUTPUT_PATH.write_text(html + "\n", encoding="utf-8")
    print(f"Successfully generated {OUTPUT_PATH} ({len(html.splitlines())} lines)")


if __name__ == "__main__":
    main()
