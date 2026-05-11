from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
freeze_file = ROOT / "current_freeze.txt"
backend_reqs = ROOT / "backend" / "requirements.txt"
out_req = ROOT / "requirements.txt"
out_req_dev = ROOT / "requirements-dev.txt"


def parse_freeze(path):
    mapping = {}
    if not path.exists():
        return mapping
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name = re.split("[=<>!~]", line)[0].lower()
        mapping[name] = line
    return mapping


def main():
    freeze = parse_freeze(freeze_file)
    out_lines = []
    if backend_reqs.exists():
        for line in backend_reqs.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            name = re.split("[=<>!~]", s)[0].lower()
            if name in freeze:
                out_lines.append(freeze[name])
            else:
                out_lines.append(s)

    # write main requirements
    out_req.write_text("\n".join(sorted(set(out_lines))) + "\n")

    # make a dev file from testing deps + common tools
    dev_tools = [
        "pytest",
        "pytest-django",
        "pytest-cov",
        "coverage",
        "flake8",
        "mypy",
        "pipreqs",
        "pip-tools",
    ]
    dev_lines = []
    for t in dev_tools:
        n = t.lower()
        if n in freeze:
            dev_lines.append(freeze[n])
        else:
            dev_lines.append(t)
    out_req_dev.write_text("\n".join(sorted(set(dev_lines))) + "\n")
    print(f"Wrote {out_req} and {out_req_dev}")


if __name__ == "__main__":
    main()
