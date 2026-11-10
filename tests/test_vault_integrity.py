"""Unit test verifying the integrity, links, and Python code blocks across the Knowledge Vault."""

import ast
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VAULT_DIR = ROOT / "vault"
SKILLS_DIR = ROOT / "skills"


class VaultIntegrityTests(unittest.TestCase):
    def test_vault_directory_exists_and_contains_atomic_docs(self):
        self.assertTrue(VAULT_DIR.is_dir(), "vault/ directory must exist")
        readme = VAULT_DIR / "README.md"
        self.assertTrue(readme.is_file(), "vault/README.md must exist")

        all_md_files = list(VAULT_DIR.rglob("*.md"))
        # Must have at least 15 granular atomic markdown documents
        self.assertGreaterEqual(len(all_md_files), 18, f"Expected >= 18 vault documents, found {len(all_md_files)}")

    def test_all_links_in_vault_readme_resolve(self):
        readme = (VAULT_DIR / "README.md").read_text(encoding="utf-8")
        # Match markdown links: [text](relative/path.md)
        links = re.findall(r"\[[^\]]+\]\(([^)#]+?)(?:#[^)]*)?\)", readme)
        for link in links:
            if link.startswith("http"):
                continue
            target_path = (VAULT_DIR / link).resolve()
            self.assertTrue(
                target_path.is_file(),
                f"Link '{link}' in vault/README.md does not resolve to a file (looked at {target_path})",
            )

    def test_skill_links_to_vault_resolve(self):
        skill_files = list(SKILLS_DIR.rglob("*.md"))
        for sf in skill_files:
            content = sf.read_text(encoding="utf-8")
            links = re.findall(r"\[[^\]]+\]\(([^)#]+?)(?:#[^)]*)?\)", content)
            for link in links:
                if "vault" in link:
                    target = (sf.parent / link).resolve()
                    self.assertTrue(
                        target.exists(),
                        f"Skill link '{link}' in {sf} does not resolve to {target}",
                    )

    def test_python_code_blocks_in_vault_are_syntactically_valid(self):
        all_md_files = list(VAULT_DIR.rglob("*.md"))
        code_block_pattern = re.compile(r"```python\s*(.*?)\s*```", re.DOTALL)

        valid_blocks = 0
        for md_file in all_md_files:
            text = md_file.read_text(encoding="utf-8")
            blocks = code_block_pattern.findall(text)
            for idx, code in enumerate(blocks):
                # Ignore placeholder ellipses in pseudo-code
                clean_code = re.sub(r"^\s*\.\.\.\s*$", "pass", code, flags=re.MULTILINE)
                try:
                    ast.parse(clean_code)
                    valid_blocks += 1
                except SyntaxError as e:
                    self.fail(f"Syntax error in Python code block #{idx+1} in {md_file.name}: {e}")

        self.assertGreater(valid_blocks, 10, "Expected at least 10 valid Python snippets in the vault")

    def test_every_vault_document_is_indexed_in_readme(self):
        readme = (VAULT_DIR / "README.md").read_text(encoding="utf-8")
        for md_file in VAULT_DIR.rglob("*.md"):
            if md_file.name == "README.md":
                continue
            rel = md_file.relative_to(VAULT_DIR).as_posix()
            self.assertIn(rel, readme, f"Vault document '{rel}' must be indexed in vault/README.md")

    def test_specialist_skills_do_not_repeat_master_boilerplate(self):
        for name in ("create-2d-assets", "create-3d-assets", "create-vfx", "create-sfx"):
            text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("## Scaffolding & Generation", text, f"{name} repeats scaffolding boilerplate from AGENTS.md")
            self.assertNotIn("## Verification Loop (Required)", text, f"{name} repeats verification boilerplate from create-game-assets")


if __name__ == "__main__":
    unittest.main()
