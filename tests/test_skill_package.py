#!/usr/bin/env python3
"""Executable packaging tests for the agent-agnostic Ravenquill skill."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = ROOT / "install.sh"
INSTALL_PS1 = ROOT / "install.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
BASH = shutil.which("bash")
GIT = shutil.which("git")

REQUIRED = (
    "SKILL.md",
    "methodology/writing-harness.md",
    "methodology/taiwan-writing-glossary.md",
    "scripts/taiwan-style-check.py",
    "scripts/protected-material-check.py",
)
EXCLUDED = ("hooks", "integrations", "skill", "tighten")


def bash_path(path: Path, style: str) -> str:
    if style == "wsl":
        relative = path.resolve().as_posix().split(":", 1)[1].lstrip("/")
        return f"/mnt/{path.drive[0].lower()}/{relative}"
    if style == "git-bash":
        relative = path.resolve().as_posix().split(":", 1)[1].lstrip("/")
        return f"/{path.drive[0].lower()}/{relative}"
    return path.resolve().as_posix()


def detect_bash_style() -> str | None:
    if not BASH:
        return None
    styles = ("native",) if os.name != "nt" else ("wsl", "git-bash", "native")
    for style in styles:
        candidate = bash_path(INSTALL_SH, style)
        result = subprocess.run(
            [BASH, "-lc", f"test -f {shlex.quote(candidate)}"],
            capture_output=True,
        )
        if result.returncode == 0:
            return style
    return None


BASH_STYLE = detect_bash_style()


def assert_skill_contract(
    testcase: unittest.TestCase, destination: Path, *, installed: bool
) -> None:
    for relative in REQUIRED:
        testcase.assertTrue((destination / relative).is_file(), relative)
    if installed:
        for relative in EXCLUDED:
            testcase.assertFalse((destination / relative).exists(), relative)

    text = (destination / "SKILL.md").read_text(encoding="utf-8")
    testcase.assertTrue(text.startswith("---\n"))
    frontmatter = text.split("---", 2)[1]
    fields = dict(
        line.split(":", 1) for line in frontmatter.splitlines() if ":" in line
    )
    testcase.assertEqual(fields.get("name", "").strip(), "ravenquill")
    testcase.assertTrue(fields.get("description", "").strip().startswith("Use when"))


class SkillDiscoveryContract(unittest.TestCase):
    def test_repository_root_is_a_discoverable_skill(self):
        assert_skill_contract(self, ROOT, installed=False)


class GitMaterializationContract(unittest.TestCase):
    @unittest.skipUnless(GIT and BASH_STYLE, "git and an accessible bash are required")
    def test_shell_installer_stays_lf_and_runs_after_windows_style_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            checkout = base / "checkout"
            source.mkdir()

            for name in ("install.sh", "SKILL.md", ".gitattributes"):
                path = ROOT / name
                if path.exists():
                    shutil.copy2(path, source / name)
            for name in ("methodology", "scripts"):
                shutil.copytree(ROOT / name, source / name)

            commands = (
                [GIT, "init", str(source)],
                [GIT, "-C", str(source), "add", "."],
                [
                    GIT,
                    "-C",
                    str(source),
                    "-c",
                    "user.name=Package Test",
                    "-c",
                    "user.email=package-test@example.invalid",
                    "commit",
                    "-m",
                    "fixture",
                ],
                [
                    GIT,
                    "-c",
                    "core.autocrlf=true",
                    "clone",
                    "--no-hardlinks",
                    str(source),
                    str(checkout),
                ],
            )
            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            self.assertNotIn(b"\r\n", (checkout / "install.sh").read_bytes())
            skill_root = base / "installed"
            script = bash_path(checkout / "install.sh", BASH_STYLE)
            target = bash_path(skill_root, BASH_STYLE)
            result = subprocess.run(
                [BASH, "-lc", f"bash {shlex.quote(script)} {shlex.quote(target)}"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            assert_skill_contract(self, skill_root / "ravenquill", installed=True)


class InstallerContract(unittest.TestCase):
    def _sandbox_env(self, root: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(root / "sandbox-home")
        env["CLAUDE_SKILLS_DIR"] = str(root / "legacy-safety")
        return env

    def _assert_installer(self, command: list[str], skill_root: Path, env: dict[str, str]) -> None:
        first = subprocess.run(command, capture_output=True, text=True, env=env)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

        destination = skill_root / "ravenquill"
        assert_skill_contract(self, destination, installed=True)

        sentinel = destination / "keep-me.txt"
        sentinel.write_text("unrelated", encoding="utf-8")
        second = subprocess.run(command, capture_output=True, text=True, env=env)
        self.assertNotEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "unrelated")

    @unittest.skipUnless(BASH_STYLE, "bash cannot access this worktree")
    def test_shell_installs_to_custom_root_and_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_root = root / "custom-skills"
            script = bash_path(INSTALL_SH, BASH_STYLE)
            target = bash_path(skill_root, BASH_STYLE)
            command = [BASH, "-lc", f"bash {shlex.quote(script)} {shlex.quote(target)}"]
            self._assert_installer(command, skill_root, self._sandbox_env(root))

    @unittest.skipUnless(POWERSHELL, "PowerShell is not available")
    def test_powershell_installs_to_custom_root_and_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_root = root / "custom-skills"
            command = [
                POWERSHELL,
                "-NoProfile",
                "-File",
                str(INSTALL_PS1),
                "-SkillRoot",
                str(skill_root),
            ]
            self._assert_installer(command, skill_root, self._sandbox_env(root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
