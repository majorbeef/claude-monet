"""Every relative link in the plugin's Markdown resolves, and every role a skill names exists."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = [p for d in ("skills", "agents") for p in (ROOT / d).rglob("*.md")] + [ROOT / "README.md"]
ROLES = {p.stem for p in (ROOT / "agents").glob("*.md")}
SKILLS = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}


class ContentTest(unittest.TestCase):
    def test_relative_links_resolve(self):
        broken = []
        for doc in DOCS:
            text = re.sub(r"```.*?```", "", doc.read_text(), flags=re.S)
            for target in re.findall(r"\]\(([^)\s]+)\)", text):
                if re.match(r"^(https?:|mailto:|#)", target):
                    continue
                if not (doc.parent / target.split("#")[0]).exists():
                    broken.append(f"{doc.relative_to(ROOT)} -> {target}")
        self.assertEqual(broken, [])

    def test_named_roles_and_commands_exist(self):
        missing = []
        for doc in DOCS:
            text = doc.read_text()
            for role in re.findall(r"monet:([a-z][a-z-]+)", text):
                if role not in ROLES and role not in SKILLS:
                    missing.append(f"{doc.relative_to(ROOT)}: monet:{role}")
            for role in re.findall(r"`([a-z]+(?:-[a-z]+){1,5})`", text):
                looks_like_role = role.endswith(("-engineer", "-architect", "-specialist", "-skeptic", "-prosecutor",
                                                 "-member", "-writer", "-outsider", "-archaeologist", "-user",
                                                 "-product", "-manager", "-lead", "-ahead", "-staff"))
                if looks_like_role and role not in ROLES:
                    missing.append(f"{doc.relative_to(ROOT)}: {role}")
        self.assertEqual(sorted(set(missing)), [])

    def test_skill_names_match_directories(self):
        for skill in SKILLS:
            front = (ROOT / "skills" / skill / "SKILL.md").read_text().split("---")[1]
            self.assertIn(f"name: {skill}\n", front)


if __name__ == "__main__":
    unittest.main()
