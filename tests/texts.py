"""Collects every English text the window can show, by reading the source."""

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "fog_launch"
TEXT_TABLES = {"QUALITY_LABELS", "labels"}
STATUS_TEXTS = {"STARTED", "NEXT"}


def english_texts() -> set[str]:
    texts: set[str] = set()
    for file in PACKAGE.glob("*.py"):
        if file.name == "i18n.py":
            continue
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", getattr(node.func, "attr", ""))
                first = node.args[0] if node.args else None
                if name in {"t", "FogError", "IniError", "__init__"} and isinstance(first, ast.Constant):
                    if isinstance(first.value, str):
                        texts.add(first.value)
            elif isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in STATUS_TEXTS:
                texts.add(node.value.value)
            elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                target = node.targets[0].id
                if target == "title" and isinstance(node.value, ast.Constant) and node.value.value:
                    texts.add(node.value.value)
                elif target in TEXT_TABLES and isinstance(node.value, ast.Dict):
                    texts.update(v.value for v in node.value.values if isinstance(v, ast.Constant))
    return texts


if __name__ == "__main__":
    for text in sorted(english_texts()):
        print(repr(text))
