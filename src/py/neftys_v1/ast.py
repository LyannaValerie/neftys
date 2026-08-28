from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .lexer import Token

@dataclass
class Node:
    kind: str
    fields: dict[str, Any] = field(default_factory=dict)
    token: Token | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


def render_tree(root: Node) -> str:
    lines: list[str] = []

    def scalar(value: Any) -> str:
        if isinstance(value, str):
            return repr(value)
        return repr(value)

    def walk(node: Node, prefix: str = "", connector: str = "") -> None:
        extra = ""
        if node.attrs:
            pairs = ", ".join(f"{k}={v}" for k, v in node.attrs.items())
            extra = f" [{pairs}]"
        lines.append(prefix + connector + node.kind + extra)
        child_prefix = prefix + ("    " if connector == "└── " else "│   " if connector else "")

        items: list[tuple[str, Any]] = list(node.fields.items())
        for idx, (name, value) in enumerate(items):
            last = idx == len(items) - 1
            conn = "└── " if last else "├── "
            next_prefix = child_prefix
            if isinstance(value, Node):
                lines.append(next_prefix + conn + f"{name}:")
                walk(value, next_prefix + ("    " if last else "│   "), "└── ")
            elif isinstance(value, list):
                lines.append(next_prefix + conn + f"{name}:")
                list_prefix = next_prefix + ("    " if last else "│   ")
                if not value:
                    lines.append(list_prefix + "└── []")
                else:
                    for j, item in enumerate(value):
                        lconn = "└── " if j == len(value) - 1 else "├── "
                        if isinstance(item, Node):
                            walk(item, list_prefix, lconn)
                        else:
                            lines.append(list_prefix + lconn + scalar(item))
            else:
                lines.append(next_prefix + conn + f"{name}: {scalar(value)}")

    walk(root)
    return "\n".join(lines)


