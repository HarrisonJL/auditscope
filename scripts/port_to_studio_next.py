"""
Mechanically ports the locally-tested GenVM v0.2.11 contracts to Studio
Next's v0.3.0 conventions, and checks that the committed ports are exactly
what this produces - so a port can never drift from its tested source.
Only import / decorator / base-class / message spellings change (the same
five substitutions used for every contract in this account).

Usage (from the repo root):
    python3 scripts/port_to_studio_next.py          # check: committed ports == regenerated ports
    python3 scripts/port_to_studio_next.py --write  # regenerate the ports
"""

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = ["auditscope", "listing_gate"]

BRADBURY_HEADER = (
    "# v0.1.0\n"
    '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }\n'
)
STUDIO_NEXT_HEADER = (
    "# v0.3.0\n"
    '# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }\n'
)


def port(text: str) -> str:
    def sub(old: str, new: str, required: bool = True) -> None:
        nonlocal text
        n = text.count(old)
        assert n >= 1 or not required, f"expected pattern missing: {old!r}"
        text = text.replace(old, new)

    sub(BRADBURY_HEADER, STUDIO_NEXT_HEADER)
    sub("(real GenVM v0.2.11 requirement)", "(real GenVM requirement)")
    uses_storage = "TreeMap" in text or "DynArray" in text
    uses_dataclass = "@allow_storage" in text
    sub("from genlayer import *\n",
        "import genlayer as gl\n"
        "from genlayer.types import *\n"
        + ("from genlayer.storage import TreeMap, DynArray\n" if uses_storage else "")
        + ("from dataclasses import dataclass\n" if uses_dataclass else ""))
    sub("gl.message_raw['datetime']", "gl.message.datetime", required=False)
    sub("@allow_storage\n", "@gl.storage.allow\n@dataclass\n", required=False)
    sub("(gl.Contract):", "(gl.contract.Contract):")
    # Consumer contracts only: the cross-contract accessor was renamed.
    sub("gl.get_contract_at(", "gl.contract.get_at(", required=False)
    assert "allow_storage" not in text.replace("gl.storage.allow", "") and "message_raw" not in text
    assert "from genlayer import *" not in text
    return text


def main() -> int:
    write = "--write" in sys.argv
    bad = 0
    for name in CONTRACTS:
        src = REPO / "contracts" / f"{name}.py"
        dst = REPO / "contracts" / f"{name}_studio_next.py"
        generated = port(src.read_text())
        if write:
            dst.write_text(generated)
            print(f"wrote {dst.name}")
        else:
            same = dst.read_text() == generated
            bad += not same
            print(("IDENTICAL  " if same else "DIFFERENT  ") + dst.name)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
