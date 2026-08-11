import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("zero_agent", ROOT / "scripts" / "zero_agent.py")
zero_agent = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(zero_agent)


class ZeroAgentTests(unittest.TestCase):
    def test_failure_classification(self):
        self.assertEqual(zero_agent.classify_failure("HTTP 429 quota exceeded", 1), "quota")
        self.assertEqual(zero_agent.classify_failure("authentication required", 1), "auth")
        self.assertEqual(zero_agent.classify_failure("requires a subscription, upgrade for access", 1), "subscription")
        self.assertEqual(zero_agent.classify_failure("account is not eligible", 1), "eligibility")
        self.assertEqual(zero_agent.classify_failure("invalid tool type: namespace", 1), "compatibility")
        self.assertEqual(zero_agent.classify_failure("C:/Users/u/.gemini/antigravity-cli/scratch/x.ts", 0), "workspace")
        self.assertEqual(zero_agent.classify_failure("boom", 1), "runtime")
        self.assertEqual(zero_agent.classify_failure("ok", 0), "success")

    def test_ansi_is_stripped_before_classification(self):
        dirty = "\x1b[31mHTTP 429 quota exceeded\x1b[0m\x1b]0;title\x07"
        clean = zero_agent.strip_terminal_controls(dirty)
        self.assertEqual(clean, "HTTP 429 quota exceeded")
        self.assertEqual(zero_agent.classify_failure(clean, 1), "quota")

    def test_successful_exact_reply_is_displayed_without_provider_noise(self):
        prompt = "Reply exactly: ZERO LOCAL WRITE PASS. Do not modify any files."
        output = "provider warning\nZERO LOCAL WRITE PASS. Do not modify any files.\n"
        self.assertEqual(
            zero_agent.display_output(output, prompt, 0),
            "ZERO LOCAL WRITE PASS.\n",
        )

    def test_exact_reply_is_not_fabricated_when_provider_omits_it(self):
        prompt = "Reply exactly: ZERO LOCAL WRITE PASS. Do not modify any files."
        output = "different response\n"
        self.assertEqual(zero_agent.display_output(output, prompt, 0), output)

    def test_windows_cmd_wrapper_resolution(self):
        with patch.object(
            zero_agent,
            "resolve_executable",
            side_effect=[r"C:\npm\codex.cmd", r"C:\Windows\System32\cmd.exe"],
        ):
            command = zero_agent.prepare_command(
                ["codex", "exec", "hello & goodbye"], platform_name="nt"
            )
        self.assertEqual(command["executable"], r"C:\Windows\System32\cmd.exe")
        self.assertIn('/d /q /v:off /s /c', command["args"])
        self.assertIn('"hello ^& goodbye"', command["args"])

    def test_windows_resolves_standard_ollama_install_outside_path(self):
        local_app_data = Path(r"C:\Users\dev\AppData\Local")
        expected = local_app_data / "Programs" / "Ollama" / "ollama.exe"
        with patch.object(zero_agent.shutil, "which", return_value=None), \
             patch.object(zero_agent.Path, "is_file", return_value=True), \
             patch.object(zero_agent.Path, "resolve", return_value=expected):
            resolved = zero_agent.resolve_executable(
                "ollama",
                platform_name="nt",
                environ={"LOCALAPPDATA": str(local_app_data)},
            )
        self.assertEqual(resolved, str(expected))

    def test_windows_replaces_unlaunchable_desktop_codex_binary(self):
        expected = Path(r"C:\Users\dev\AppData\Local\OpenAI\Codex\bin\version\codex.exe")
        with patch.object(
            zero_agent.shutil,
            "which",
            return_value=r"C:\Program Files\WindowsApps\OpenAI.Codex\codex.exe",
        ), patch.object(
            zero_agent,
            "windows_install_candidates",
            return_value=[expected],
        ), patch.object(
            zero_agent.Path,
            "is_file",
            return_value=True,
        ), patch.object(
            zero_agent.Path,
            "resolve",
            return_value=expected,
        ):
            resolved = zero_agent.resolve_executable("codex", platform_name="nt")
        self.assertEqual(resolved, str(expected))

    def test_render_command(self):
        profile = {"command": ["agent", "--model", "{model}", "{prompt}"]}
        self.assertEqual(
            zero_agent.render_command(profile, "fix tests", "local-model"),
            ["agent", "--model", "local-model", "fix tests"],
        )

    def test_hard_lock_configuration(self):
        config = json.loads((ROOT / "configs" / "router.json").read_text())
        self.assertTrue(config["absolute_zero"])
        self.assertFalse(config["allow_zero_incremental"])
        self.assertFalse(any(p["cost_class"] == "paid" and p.get("enabled", True) for p in config["profiles"]))

    def test_write_mode_excludes_unverified_cloud_editors(self):
        config = json.loads((ROOT / "configs" / "router.json").read_text())
        profiles = {p["id"]: p for p in config["profiles"]}
        self.assertNotIn("write", profiles["antigravity-headless"]["modes"])
        self.assertNotIn("write", profiles["minimax-m3-free"]["modes"])
        self.assertIn("write", profiles["codex-local"]["modes"])
        self.assertIn("--ignore-user-config", profiles["codex-local"]["command"])
        self.assertIn("--ephemeral", profiles["codex-local"]["command"])
        self.assertIn("Return only the final answer as plain text", profiles["codex-local"]["command"][-1])
        self.assertIn("{prompt}", profiles["codex-local"]["command"][-1])

    def test_profile_allowed_respects_mode_and_cost(self):
        zero_read = {"enabled": True, "modes": ["read"], "cost_class": "zero"}
        incremental_read = {"enabled": True, "modes": ["read"], "cost_class": "zero-incremental"}
        paid_read = {"enabled": True, "modes": ["read"], "cost_class": "paid"}
        self.assertTrue(zero_agent.profile_allowed(zero_read, "read", True, False))
        self.assertFalse(zero_agent.profile_allowed(zero_read, "write", True, False))
        self.assertFalse(zero_agent.profile_allowed(incremental_read, "read", True, False))
        self.assertTrue(zero_agent.profile_allowed(incremental_read, "read", True, True))
        self.assertFalse(zero_agent.profile_allowed(paid_read, "read", True, True))

    def test_sanitized_env_strips_paid_keys_and_forces_utf8(self):
        policy = json.loads((ROOT / "configs" / "zero-dollar-policy.json").read_text())
        previous = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "must-not-leak"
        try:
            env = zero_agent.sanitized_env({"env": {"LOCAL_ONLY": "1"}}, policy)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertEqual(env["LOCAL_ONLY"], "1")
            self.assertEqual(env["PYTHONIOENCODING"], "utf-8")
            self.assertEqual(env["PYTHONUTF8"], "1")
        finally:
            if previous is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous

    def test_run_task_uses_utf8_replacement_decoding(self):
        fake_proc = type("Proc", (), {"stdout": "ok\n", "returncode": 0})()
        with patch.object(zero_agent, "load_state", return_value={"profiles": {}}), \
             patch.object(zero_agent, "save_state"), \
             patch.object(zero_agent, "profile_available", return_value=True), \
             patch.object(zero_agent, "prepare_command", side_effect=lambda command: {"args": command}), \
             patch.object(zero_agent.subprocess, "run", return_value=fake_proc) as run:
            result = zero_agent.run_task("hello", mode="read")
            self.assertEqual(result, 0)
            kwargs = run.call_args.kwargs
            self.assertEqual(kwargs["encoding"], "utf-8")
            self.assertEqual(kwargs["errors"], "replace")
            self.assertIs(kwargs["stdin"], zero_agent.subprocess.DEVNULL)
            self.assertFalse(kwargs.get("shell", False))

    def test_spawn_failure_is_persisted(self):
        state = {"profiles": {}}
        saved = []
        with patch.object(zero_agent, "load_state", return_value=state), \
             patch.object(zero_agent, "save_state", side_effect=lambda value: saved.append(value.copy())), \
             patch.object(zero_agent, "profile_available", return_value=True), \
             patch.object(zero_agent, "prepare_command", side_effect=FileNotFoundError("codex")):
            result = zero_agent.run_task("hello", mode="write")
        self.assertEqual(result, 2)
        profile_state = state["profiles"]["codex-local"]
        self.assertEqual(profile_state["last_failure_class"], "unavailable")
        self.assertIsNone(profile_state["last_exit_code"])
        self.assertTrue(saved)


if __name__ == "__main__":
    unittest.main()
