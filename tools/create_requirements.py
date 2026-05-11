import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
req_in = ROOT / "requirements.in"
freeze = ROOT / "current_freeze.txt"
backend_reqs = ROOT / "backend" / "requirements.txt"
out_req = ROOT / "requirements.txt"
out_req_dev = ROOT / "requirements-dev.txt"


def parse_freeze(path):
    mapping = {}
    if not path.exists():
        return mapping
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"([^=<>!~\[\]]+)(.*)", line)
        if m:
            name = m.group(1).lower()
            mapping[name] = line
    return mapping


def parse_req_in(path):
    items = []
    if not path.exists():
        return items
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # pipreqs may output comments or extras; keep simple name
        items.append(line)
    return items


def main():
    freeze_map = parse_freeze(freeze)
    reqs = parse_req_in(req_in)

    pinned = []
    for r in reqs:
        name = re.split("[=<>!~\\[]", r)[0].lower()
        if name in freeze_map:
            pinned.append(freeze_map[name])
        else:
            pinned.append(r)

    # Combine with backend testing deps (keep separate as dev)
    dev_lines = []
    if backend_reqs.exists():
        for line in backend_reqs.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            dev_lines.append(s)

    # Add common dev tools
    tools = [
        "pytest",
        "pytest-django",
        "pytest-cov",
        "flake8",
        "mypy",
        "pipreqs",
        "pip-tools",
    ]
    for t in tools:
        n = t.lower()
        if n in freeze_map:
            dev_lines.append(freeze_map[n])
        else:
            dev_lines.append(t)

    # Write outputs
    out_req.write_text("\n".join(sorted(set(pinned))) + "\n")
    out_req_dev.write_text("\n".join(sorted(set(dev_lines))) + "\n")
    print(f"Wrote {out_req} and {out_req_dev}")


if __name__ == "__main__":
    main()
