import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("framework_verify", ROOT / "verify.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class StructureChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ddd-v5-")
        self.root = Path(self.temp.name)
        self.docs = self.root / "开发驱动文档"
        self.docs.mkdir()
        for name in verify.DOC_NAMES:
            text = re.sub(r"\{\{[^{}]*\}\}", "已明确", (ROOT / name).read_text(encoding="utf-8"))
            (self.docs / name).write_text(text, encoding="utf-8")
        text = re.sub(r"\{\{[^{}]*\}\}", "无", (ROOT / "START_HERE.md").read_text(encoding="utf-8"))
        (self.root / "START_HERE.md").write_text(text, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def report(self, **kwargs):
        return verify.run(self.root, **kwargs)

    def failures(self, **kwargs):
        return [r for r in self.report(**kwargs)["results"] if r["level"] == "FAIL"]

    def append(self, index, text):
        path = self.docs / verify.DOC_NAMES[index]
        path.write_text(path.read_text(encoding="utf-8") + "\n" + text, encoding="utf-8")

    def test_project_auto_detection_and_optional_no_git(self):
        self.assertEqual("project", self.report()["mode"])
        self.assertEqual([], self.failures())

    def test_template_mode_allows_unfilled_but_project_fails(self):
        self.append(1, "{{待裁决}}")
        self.assertTrue(self.failures())
        self.assertEqual([], self.failures(mode="template"))

    def test_simple_change_without_technical_ids_is_valid(self):
        for index in (1, 2, 3):
            (self.docs / verify.DOC_NAMES[index]).write_text("# 当前内容\n不需要独立拆解。", encoding="utf-8")
        self.assertEqual([], self.failures())

    def test_missing_file_reports_failure_without_traceback(self):
        (self.docs / verify.DOC_NAMES[2]).unlink()
        self.assertTrue(self.failures())

    def test_dangling_reference_across_requirement_design_evidence(self):
        for index in (1, 3, 4):
            with self.subTest(index=index):
                self.append(index, "关联 REQ-missing-999")
                self.assertTrue(any("悬空编号" in r["name"] for r in self.failures()))
                path = self.docs / verify.DOC_NAMES[index]
                path.write_text(path.read_text(encoding="utf-8").replace("关联 REQ-missing-999", ""), encoding="utf-8")

    def test_duplicate_definition_fails_but_plain_test_reference_does_not(self):
        self.append(3, "| REQ-001 | 人工验收 | 通过 |")
        self.assertEqual([], self.failures())
        self.append(3, "### REQ-001 错误的重复定义")
        self.assertTrue(any("重复定义" in r["name"] for r in self.failures()))

    def test_identifier_tables_and_namespaced_ids(self):
        self.append(4, "| 编号 | 内容 |\n|---|---|\n| ASM-ui-1000 | 待验证 |\n")
        self.append(2, "推进前提引用 ASM-ui-1000")
        self.assertEqual([], self.failures())

    def test_examples_comments_and_substrings_are_not_references(self):
        self.append(4, "<!-- Q-999 -->\n```text\nASM-999\n```\nREQ-001")
        self.assertEqual([], self.failures())

    def test_local_links_fail_when_target_missing_and_allow_encoded_spaces(self):
        path = self.root / "带 空格.md"
        path.write_text("证据", encoding="utf-8")
        self.append(1, "[证据](../%E5%B8%A6%20%E7%A9%BA%E6%A0%BC.md#任意锚点)")
        self.assertEqual([], self.failures())
        self.append(1, "[缺失](../missing.md)")
        self.assertTrue(any("本地链接" in r["name"] for r in self.failures()))

    def test_size_warning_is_not_failure_and_can_be_disabled(self):
        self.append(4, "长内容" * 6000)
        report = self.report(max_doc_bytes=100)
        self.assertTrue(any(r["level"] == "WARN" for r in report["results"]))
        self.assertFalse(any(r["level"] == "FAIL" for r in report["results"]))
        self.assertFalse(any(r["level"] == "WARN" for r in self.report(max_doc_bytes=0)["results"]))

    def test_acceptance_count_excludes_pitfalls_and_other_sections(self):
        text = "## 可复用经验\n| 2026-10-10 | 坑 |\n## 验证记录\n| 2026-10-10 | 检查 |\n## 其他\n| 2026-10-10 | 债 |"
        self.assertEqual(1, verify.acceptance_rows(text))

    def test_release_requires_committed_input(self):
        self.assertTrue(any("发布输入" in r["name"] for r in self.failures(mode="template", release=True)))

    def test_ambiguous_document_roots_fail(self):
        shutil.copy2(self.docs / verify.DOC_NAMES[0], self.root / verify.DOC_NAMES[0])
        self.assertTrue(any("位置唯一" in r["name"] for r in self.failures()))


if __name__ == "__main__":
    unittest.main()
