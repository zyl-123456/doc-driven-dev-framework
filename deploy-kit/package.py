#!/usr/bin/env python3
"""Build ZIP, tar.gz and SHA-256 list after checking release-copy consistency."""
import argparse
import datetime
import hashlib
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="输出 ZIP 路径")
    parser.add_argument("--date", default=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat())
    args = parser.parse_args()
    try:
        date = datetime.date.fromisoformat(args.date).strftime("%Y%m%d")
    except ValueError:
        parser.error("--date 必须为 YYYY-MM-DD")
    result = subprocess.run([sys.executable, str(HERE / "sync-master.py"), "--check"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        print(result.stdout)
        print("FAIL 先同步发布副本，再打包")
        return 1
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    out = (args.out or ROOT / "dist" / ("doc-driven-kit-v%s-%s.zip" % (version, date))).resolve()
    if out.suffix != ".zip":
        parser.error("--out 必须以 .zip 结尾")
    if HERE == out or HERE in out.parents:
        parser.error("输出不能放进 deploy-kit，避免把产物再次打入自身")
    items = [p for p in sorted(HERE.rglob("*")) if p.is_file()
             and "__pycache__" not in p.parts and not any(part.startswith(".") for part in p.relative_to(HERE).parts)
             and not p.name.endswith((".pyc", ".bak", ".tmp")) and ".bak-" not in p.name]
    # Dotfiles in master are intentional release sources, including CI and Git settings.
    items += [p for p in sorted((HERE / "payload" / "master").rglob("*")) if p.is_file()
              and "__pycache__" not in p.parts and any(part.startswith(".") for part in p.relative_to(HERE).parts)]
    items = sorted(set(items))
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in items:
            archive.write(path, "deploy-kit/" + path.relative_to(HERE).as_posix())
    tar = out.with_suffix(".tar.gz")
    with tarfile.open(tar, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        for path in items:
            archive.add(path, "deploy-kit/" + path.relative_to(HERE).as_posix())
    sums = out.with_suffix(".sha256")
    sums.write_bytes("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
                             for p in (out, tar)).encode("utf-8"))
    print("PASS v%s，%d 个文件\n%s\n%s\n%s" % (version, len(items), out, tar, sums))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
