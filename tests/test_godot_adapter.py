import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "capabilities" / "godot" / "adapter.py"
spec = importlib.util.spec_from_file_location("godot_adapter", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
GodotAdapter = module.GodotAdapter
GodotCapabilityError = module.GodotCapabilityError


class GodotAdapterTests(unittest.TestCase):
    def test_missing_executable_fails_closed(self):
        with patch("shutil.which", return_value=None):
            with self.assertRaises(GodotCapabilityError):
                GodotAdapter()

    def test_create_project_is_local_and_deterministic(self):
        adapter = GodotAdapter(executable="godot")
        with tempfile.TemporaryDirectory() as tmp:
            project_file = adapter.create_project(tmp, "Demo")
            content = project_file.read_text(encoding="utf-8")
            self.assertIn('config/name="Demo"', content)
            self.assertIn('run/main_scene="res://main.tscn"', content)
            self.assertIn('renderer/rendering_method="gl_compatibility"', content)

    @patch("subprocess.run")
    def test_health_calls_only_local_godot(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "4.x"
        run.return_value.stderr = ""
        adapter = GodotAdapter(executable="/usr/bin/godot")
        result = adapter.health()
        self.assertEqual(result.returncode, 0)
        command = run.call_args.args[0]
        self.assertEqual(command, ("/usr/bin/godot", "--version"))

    def test_manifest_preserves_absolute_zero(self):
        manifest_path = MODULE_PATH.parent / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["cost_class"], "zero")
        self.assertFalse(manifest["paid_fallback"])
        self.assertFalse(manifest["network_required"])
        self.assertTrue(manifest["guardrails"]["absolute_zero_compatible"])
        self.assertFalse(manifest["guardrails"]["authoritative_pricing"])
        self.assertFalse(manifest["guardrails"]["authoritative_engineering"])


if __name__ == "__main__":
    unittest.main()
