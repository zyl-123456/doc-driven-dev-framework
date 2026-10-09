import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync = load("kit_sync", ROOT / "deploy-kit" / "sync-master.py")
installer = load("kit_installer", ROOT / "deploy-kit" / "install.py")
guard = load("kit_guard", ROOT / "hooks" / "doc-driven-guard.py")


class DeploymentChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ddd-deploy-")
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def call(self, script, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, str(ROOT / "deploy-kit" / script)] + list(args),
                              capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)

    def test_session_entry_and_no_per_message_injection(self):
        start = guard.response({"cwd": str(ROOT), "hook_event_name": "SessionStart"})
        self.assertLessEqual(len(start["hookSpecificOutput"]["additionalContext"]), 600)
        self.assertEqual({"continue": True}, guard.response({"cwd": str(ROOT), "hook_event_name": "UserPromptSubmit"}))
        self.assertEqual({"continue": True}, guard.response({"cwd": str(self.base), "hook_event_name": "SessionStart"}))

    def test_malformed_hook_input_never_blocks(self):
        for raw in ("garbage", "[]", "null", '{"cwd": [], "hook_event_name":"SessionStart"}'):
            proc = subprocess.run([sys.executable, str(ROOT / "hooks" / "doc-driven-guard.py")],
                                  input=raw, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(0, proc.returncode)
            self.assertEqual({"continue": True}, json.loads(proc.stdout))

    def test_hook_upgrade_preserves_unrelated_config(self):
        config = {"theme": "dark", "hooks": {"UserPromptSubmit": [{"hooks": [
            {"command": "old/doc-driven-guard.py"}, {"command": "my-own-hook"}]}]}}
        updated = installer.update_hooks(config, '"new/python" "new/doc-driven-guard.py"')
        self.assertEqual("dark", updated["theme"])
        self.assertEqual([{ "command": "my-own-hook"}], updated["hooks"]["UserPromptSubmit"][0]["hooks"])
        self.assertIn("new/python", updated["hooks"]["SessionStart"][0]["hooks"][0]["command"])
        self.assertEqual(updated, installer.update_hooks(json.loads(json.dumps(updated)), '"new/python" "new/doc-driven-guard.py"'))

    def test_copy_changes_back_up_once_and_preserve_original(self):
        path = self.base / "settings.json"
        path.write_bytes(b"old")
        self.assertTrue(installer.write_bytes(path, b"new"))
        backup = list(self.base.glob("*.bak-*"))
        self.assertEqual(1, len(backup))
        self.assertEqual(b"old", backup[0].read_bytes())
        self.assertFalse(installer.write_bytes(path, b"new"))
        self.assertEqual(1, len(list(self.base.glob("*.bak-*"))))

    def test_install_dry_run_does_not_write_home(self):
        home = self.base / "empty home"
        result = self.call("install.py", "--home", str(home), "--dry-run")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse(home.exists())

    def test_install_twice_preserves_memory_and_updates_old_paths(self):
        home = self.base / "user home"
        wb = home / ".workbuddy"
        wb.mkdir(parents=True)
        (wb / "MEMORY.md").write_bytes("人类自己的记忆".encode())
        cfg = {"custom": 1, "hooks": {"UserPromptSubmit": [{"hooks": [{"command": "old/doc-driven-guard.py"}]}]}}
        (wb / "settings.json").write_text(json.dumps(cfg), encoding="utf-8")
        for _ in range(2):
            result = self.call("install.py", "--home", str(home))
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            if _ == 0:
                backups = len(list(home.rglob("*.bak-*")))
        self.assertEqual(backups, len(list(home.rglob("*.bak-*"))))
        self.assertEqual("人类自己的记忆".encode(), (wb / "MEMORY.md").read_bytes())
        installed = json.loads((wb / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(1, installed["custom"])
        self.assertNotIn("UserPromptSubmit", installed["hooks"])

    def test_bad_existing_configuration_is_not_overwritten(self):
        wb = self.base / ".workbuddy"
        wb.mkdir()
        (wb / "settings.json").write_bytes(b"invalid-json")
        result = self.call("install.py", "--home", str(self.base))
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(b"invalid-json", (wb / "settings.json").read_bytes())
        self.assertFalse((wb / "skills").exists())

    def test_manifest_detects_corruption_before_installation(self):
        payload = self.base / "payload"
        payload.mkdir()
        (payload / "file").write_bytes(b"modified")
        manifest = {"version": "5.0.0", "files": {"file": hashlib.sha256(b"original").hexdigest()}}
        (payload / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertFalse(installer.payload_valid(payload)[0])

    def test_imported_sync_handles_legacy_stdout_encoding(self):
        script = ROOT / "deploy-kit/sync-master.py"
        code = ("import importlib.util,sys; "
                "s=importlib.util.spec_from_file_location('kit_sync',sys.argv[1]); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "sys.exit(m.sync(check=True))")
        env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, "-c", code, str(script)],
                                capture_output=True, env=env)
        self.assertEqual(0, result.returncode, result.stderr.decode("ascii", errors="replace"))
        self.assertIn(b"PASS", result.stdout)

    def test_sync_check_fails_on_drift_and_unknown_copies(self):
        master = self.base / "master"
        master.mkdir()
        for name in sync.MASTER:
            shutil.copy2(ROOT / name, master / name)
        for folder in ("skills", "hooks"):
            shutil.copytree(ROOT / folder, master / folder)
        self.assertEqual(0, sync.sync(master))
        self.assertEqual(0, sync.sync(master, True))
        (master / "README.md").write_text("changed", encoding="utf-8")
        self.assertEqual(1, sync.sync(master, True))
        self.assertEqual(0, sync.sync(master))
        (master / "deploy-kit/payload/master/unknown.md").write_text("extra", encoding="utf-8")
        self.assertEqual(1, sync.sync(master, True))

    def test_new_master_is_self_contained_in_path_with_spaces(self):
        target = self.base / "new master"
        result = self.call("init-master-workspace.py", "--target", str(target))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        proc = subprocess.run([sys.executable, str(target / "deploy-kit/sync-master.py"), "--check"],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertTrue((target / "tests/test_verify.py").is_file())
        self.assertTrue((target / "releases/v5.0.0.md").is_file())

    def test_master_dry_run_and_internal_target_rejection(self):
        target = self.base / "not-created"
        self.assertEqual(0, self.call("init-master-workspace.py", "--target", str(target), "--dry-run").returncode)
        self.assertFalse(target.exists())
        self.assertNotEqual(0, self.call("init-master-workspace.py", "--target", str(ROOT / "deploy-kit/payload")).returncode)

    def test_package_contents_hashes_and_self_contained_release(self):
        archive = self.base / "release.zip"
        result = self.call("package.py", "--out", str(archive), "--date", "2026-10-10")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        tar = archive.with_suffix(".tar.gz")
        with zipfile.ZipFile(archive) as z, tarfile.open(tar) as t:
            zip_files = {n: z.read(n) for n in z.namelist()}
            tar_files = {m.name: t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
            self.assertEqual(zip_files, tar_files)
            self.assertIn("deploy-kit/payload/master/.github/workflows/check.yml", zip_files)
            self.assertNotIn("deploy-kit/payload/master/.workbuddy/memory/MEMORY.md", zip_files)
        for line in archive.with_suffix(".sha256").read_text().splitlines():
            expected, name = line.split("  ", 1)
            self.assertEqual(expected, hashlib.sha256((self.base / name).read_bytes()).hexdigest())
        self.assertNotEqual(0, self.call("package.py", "--out", str(ROOT / "deploy-kit/self.zip")).returncode)


if __name__ == "__main__":
    unittest.main()
