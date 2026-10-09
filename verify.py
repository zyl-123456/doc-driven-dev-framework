#!/usr/bin/env python3
"""Document structure checker, v5.0.1. No product or security certification."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

VERSION = "5.0.1"
MODE = "auto"  # Legacy template/project overrides remain supported.
DOC_NAMES = ["00-驱动开发规则.md", "01-人类需求描述.md", "02-需求技术拆解.md",
             "03-技术实现方案.md", "04-实现过程记录.md"]
ID_PATTERN = r"(?<![\w-])(?:REQ|TECH|D|M|ASM|Q|C|A|SEC|TD)-(?:[A-Za-z][A-Za-z0-9]*-)*\d+(?![\w-])"
IDENTIFIER = re.compile(ID_PATTERN)
PLACEHOLDER = re.compile(r"\{\{[^{}]*\}\}")


def visible(text):
    """Ignore examples in fenced code, HTML comments and template placeholders."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines, fence = [], None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return PLACEHOLDER.sub("", "\n".join(lines))


def definitions(text):
    """Definitions use heading/bullet starts or an explicitly labelled ID table."""
    found, id_table = [], False
    for line in text.splitlines():
        match = re.match(r"^\s*(?:#{1,6}\s+|[-*]\s+)(?:\*\*)?(" + ID_PATTERN + r")", line)
        if match:
            found.append(match.group(1))
        if line.lstrip().startswith("|"):
            first = line.strip().strip("|").split("|")[0].strip().strip("*`")
            if first in ("编号", "ID", "标识"):
                id_table = True
            elif re.fullmatch(r"[-: ]+", first):
                pass
            elif id_table and IDENTIFIER.fullmatch(first):
                found.append(first)
            elif not IDENTIFIER.fullmatch(first):
                id_table = False
        elif line.strip():
            id_table = False
    return found


def section(text, title):
    lines, body, level = text.splitlines(), [], None
    for line in lines:
        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if level is None:
            if heading and heading.group(2).strip() == title:
                level = len(heading.group(1))
        elif heading and len(heading.group(1)) <= level:
            break
        else:
            body.append(line)
    return "\n".join(body)


def acceptance_rows(text):
    body = section(text, "验证记录") or section(text, "已完成的验收结论（结论绑定输入版本）")
    return len(re.findall(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|", body, re.M))


def git_state(root):
    def call(args):
        result = subprocess.run(["git", "-C", str(root)] + args, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=15)
        return result.returncode, result.stdout.strip()
    try:
        rc, commit = call(["rev-parse", "HEAD"])
        if rc:
            return {"commit": None, "dirty": None, "status": "无可用提交"}
        rc, status = call(["status", "--porcelain"])
        if rc:
            return {"commit": commit, "dirty": None, "status": "状态读取失败"}
        dirty = len(status.splitlines())
        return {"commit": commit, "dirty": dirty,
                "status": "工作区变更（结论包含未提交输入）" if dirty else "已提交输入"}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None, "status": "Git 不可用"}


def run(root, mode="auto", release=False, max_doc_bytes=16000):
    root = Path(root).resolve()
    results = []

    def record(level, name, detail=""):
        results.append({"level": level, "name": name, "detail": detail})

    if mode == "auto":
        mode = "template" if (root / "VERSION").is_file() and (root / "deploy-kit").is_dir() else "project"
    candidates = [root / d for d in ("开发驱动文档", ".", "docs/开发驱动文档", "文档/开发驱动文档")]
    matches = [p for p in candidates if (p / DOC_NAMES[0]).is_file()]
    if not matches:
        record("FAIL", "定位五文档", "找不到 00；未继续检查")
        return {"checker": VERSION, "mode": mode, "input": git_state(root), "results": results}
    doc = matches[0]
    record("FAIL" if len(matches) > 1 else "PASS", "文档位置唯一", str(doc.relative_to(root)))
    texts = {}
    for path in [doc / n for n in DOC_NAMES] + [root / "START_HERE.md"]:
        try:
            text = path.read_text(encoding="utf-8")
            ok = bool(text.strip())
            record("PASS" if ok else "FAIL", "文件非空: " + path.name)
            if ok:
                texts[path] = text
        except (OSError, UnicodeError) as exc:
            record("FAIL", "读取: " + path.name, str(exc))
    if len(texts) != 6:
        return {"checker": VERSION, "mode": mode, "input": git_state(root), "results": results}
    for path, text in texts.items():
        if mode == "project" and PLACEHOLDER.search(re.sub(r"<!--.*?-->", "", text, flags=re.S)):
            record("FAIL", "待填内容: " + path.name, "填写或删除不适用项；示例代码中的占位符也需处理")
        if max_doc_bytes > 0 and len(text.encode("utf-8")) > max_doc_bytes:
            record("WARN", "规模提示: " + path.name, "检查重复和检索成本；不阻断交付，也不是 token 测量")
        for match in re.finditer(r"\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[\"'][^)]*)?\)", visible(text)):
            target = match.group(1) or match.group(2)
            if target.startswith("#") or urlsplit(target).scheme:
                continue
            target_path = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if target_path and not (path.parent / target_path).exists():
                record("FAIL", "本地链接: " + path.name, target)
    declarations, references = {}, set()
    for path in list(texts)[:5][1:]:  # Rules contain examples, not product ID declarations.
        clean = visible(texts[path])
        references.update(IDENTIFIER.findall(clean))
        for ident in definitions(clean):
            if ident in declarations:
                record("FAIL", "重复定义: " + ident, path.name + " / " + declarations[ident])
            else:
                declarations[ident] = path.name
    for ident in sorted(references - declarations.keys()):
        record("FAIL", "悬空编号: " + ident, "定义一次或移除无效引用；无需补齐四段链")
    record("INFO", "编号检查范围", "检查显式定义与引用，不证明需求语义或测试覆盖")
    snapshot = texts[root / "START_HERE.md"]
    for key in ("正在做", "卡在哪", "下一步"):
        match = re.search(r"^\s*-\s*\*\*" + key + r"\*\*[：:]\s*(.*)$", snapshot, re.M)
        ok = match is not None and bool(match.group(1).strip())
        record("PASS" if ok else "FAIL", "快照字段存在且非空: " + key)
    record("INFO", "快照检查范围", "只检查已填写，不证明新鲜度；需对照当前输入")
    record("INFO", "验证记录行数", str(acceptance_rows(texts[doc / DOC_NAMES[4]])))
    state = git_state(root)
    if release:
        if mode != "template":
            record("FAIL", "发布检查适用范围", "--release 仅用于框架母版发布；产品发布用项目自己的检查")
        record("PASS" if state["commit"] and state["dirty"] == 0 else "FAIL", "发布输入已提交且工作区干净")
        try:
            version = (root / "VERSION").read_text(encoding="utf-8").strip()
            note = root / "releases" / ("v" + version + ".md")
            change = (root / "CHANGELOG.md").read_text(encoding="utf-8")
            ok = version == VERSION and ("## " + version) in change and note.is_file()
            record("PASS" if ok else "FAIL", "版本与发布说明对应", version)
            script = root / "deploy-kit" / "sync-master.py"
            proc = subprocess.run([sys.executable, str(script), "--check"], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=30)
            record("PASS" if proc.returncode == 0 else "FAIL", "发布副本一致", proc.stdout.strip())
        except (OSError, subprocess.SubprocessError) as exc:
            record("FAIL", "发布元数据或副本检查", str(exc))
    return {"checker": VERSION, "mode": mode, "input": state, "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--mode", choices=("auto", "template", "project"), default=MODE)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--max-doc-bytes", type=int, default=16000, help="规模提示阈值；0 关闭。字节不等于 token")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run(args.root, args.mode, args.release, args.max_doc_bytes)
    failures = sum(r["level"] == "FAIL" for r in report["results"])
    report["ok"] = failures == 0
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("文档结构检查 " + VERSION + " / " + report["mode"])
        print("输入: " + json.dumps(report["input"], ensure_ascii=False))
        for r in report["results"]:
            print("[{level}] {name} {detail}".format(**r))
        print("验收结果: 文档结构%s，失败 %d 项" % ("通过" if not failures else "失败", failures))
        print("范围限制: 不证明功能正确、安全合规、快照新鲜或开发效率提升。")
    return 1 if failures else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
