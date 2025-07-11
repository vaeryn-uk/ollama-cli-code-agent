#!/usr/bin/env python
"""Update README with a section for each config var."""
from pathlib import Path
import importlib.util
import sys

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
spec = importlib.util.spec_from_file_location(
    "ocla.config", SRC_DIR / "ocla" / "config.py"
)
config = importlib.util.module_from_spec(spec)
if spec.loader:
    spec.loader.exec_module(config)

START_MARKER = "<!-- CONFIG_TABLE_START -->"
END_MARKER = "<!-- CONFIG_TABLE_END -->"


def generate_table() -> str:
    rows = []
    for name, var in sorted(config.CONFIG_VARS.items()):
        env = var.env or "N/A"
        prop = var.config_file_property or "N/A"
        default = var.default or "N/A"
        cli = " ".join(var.cli) if var.cli else "N/A"
        desc = var.description
        if var.allowed_values:
            allowed = "\n".join(
                f"  - `{k}`: {v}" if v else f"  - `{k}`"
                for k, v in var.allowed_values.items()
            )
        else:
            allowed = ""

        rows.append(
            "\n".join(
                [
                    f"### {name}\n",
                    f"{desc}\n",
                    f"- **CLI:** `{cli}`",
                    f"- **Environment variable:** `{env}`",
                    f"- **Config file:** `{prop}`",
                    f"- **Default value:** `{default}`",
                    f"- **Allowed values:**\n{allowed}" if allowed else "",
                    "",
                ]
            )
        )
    return "\n".join(rows)


def update_readme(path: Path) -> None:
    content = path.read_text().splitlines()
    table = generate_table()
    output = []
    inside = False
    replaced = False
    for line in content:
        if line.strip() == START_MARKER:
            inside = True
            replaced = True
            output.append(START_MARKER)
            output.append(table)
            continue
        if line.strip() == END_MARKER:
            inside = False
            output.append(END_MARKER)
            continue
        if not inside:
            output.append(line)
    if not replaced:
        output.append("")
        output.append("## Configuration")
        output.append(START_MARKER)
        output.append(table)
        output.append(END_MARKER)
    path.write_text("\n".join(output) + "\n")


def main() -> None:
    update_readme(Path("README.md"))
    print("README updated")


if __name__ == "__main__":
    main()
