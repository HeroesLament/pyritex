import ast
from pathlib import Path

# Where things live
ROOT = Path(__file__).resolve().parent.parent
PYRITE_INIT = ROOT / "pyritex" / "__init__.py"

CONST_FILES = [
    ROOT / "pyritex" / "netlink" / "consts.py",
    ROOT / "pyritex" / "netlink" / "rtnl" / "consts.py",
]

STRUCT_EXPORTS = [
    "NetlinkSocket",
    "RouteMessage",
    "NetlinkHeader",
    "RtMsg",
]

CONST_FUNCTIONS = [
    "NLMSG_ALIGN",
    "NLMSG_LENGTH",
    "NLMSG_SPACE",
]

LOG_FUNCTIONS = [
    "set_pyritex_log_level",
]

EXTRA_EXPORTS = CONST_FUNCTIONS + LOG_FUNCTIONS

def extract_uppercase_names(path):
    with open(path, "r") as f:
        tree = ast.parse(f.read(), filename=str(path))
    names = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    names.append(target.id)
    return names

def generate_init():
    struct_imports = []
    const_imports = []

    # Structs
    for struct in STRUCT_EXPORTS:
        if struct == "NetlinkSocket":
            struct_imports.append(f"from pyritex.netlink.socket import {struct}")
        else:
            struct_imports.append(f"from pyritex.netlink.message import {struct}")

    # Constants
    for const_file in CONST_FILES:
        consts = extract_uppercase_names(const_file)
        relative = const_file.relative_to(ROOT).with_suffix("")
        mod_path = ".".join(relative.parts)
        for const in consts:
            const_imports.append(f"from {mod_path} import {const}")

    # Extra functions
    for func in CONST_FUNCTIONS:
        const_imports.append(f"from pyritex.netlink.consts import {func}")
    for func in LOG_FUNCTIONS:
        const_imports.append(f"from pyritex.log import {func}")

    all_exports = (
        STRUCT_EXPORTS
        + sum([extract_uppercase_names(f) for f in CONST_FILES], [])
        + EXTRA_EXPORTS
    )

    contents = f"""# This file is auto-generated by tools/build_api.py
# Do not edit manually.

# Structs
{chr(10).join(struct_imports)}

# Constants and Helpers
{chr(10).join(const_imports)}

__all__ = [
{chr(10).join(f'    "{name}",' for name in all_exports)}
]
"""

    PYRITE_INIT.write_text(contents.strip() + "\n")
    print(f"Wrote {PYRITE_INIT}")

if __name__ == "__main__":
    generate_init()
