"""Static-content assertions for the reference-driven UI design skill
(spec 014, contracts/skill-contract.md). The skill is a methodology
document, so these check that its required rules and sections are present
and that it stays page-independent — not the quality of any redesign."""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / ".claude/skills/frontend-design"
SKILL_PATH = SKILL_DIR / "SKILL.md"
TEMPLATE_PATH = REPO_ROOT / "src/web/templates/index.html"
DATA_MODEL_PATH = REPO_ROOT / "specs/014-reference-driven-ui/data-model.md"

WORKFLOW_HEADINGS = [
    "Gather inputs",
    "Inspect references",
    "Understand the existing UI",
    "Design interpretation",
    "Implement",
    "Verify visually",
    "Refine",
    "Report",
]


def _skill() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """Body of the `##` section whose heading contains *heading*."""
    match = re.search(
        rf"^##[^\n]*{re.escape(heading)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    assert match, f"no '## ... {heading}' section"
    return match.group(1)


def test_skill_has_frontmatter_with_name_and_description():
    text = _skill()
    assert text.startswith("---\n")
    frontmatter = yaml.safe_load(text.split("---\n", 2)[1])
    assert frontmatter["name"] == "frontend-design"
    assert "design/references" in frontmatter["description"]


def test_skill_workflow_headings_are_in_order():
    text = _skill()
    positions = []
    for heading in WORKFLOW_HEADINGS:
        match = re.search(rf"^## \d+\. {re.escape(heading)}", text, re.MULTILINE)
        assert match, f"missing numbered heading '## N. {heading}'"
        positions.append(match.start())
    assert positions == sorted(positions)


def test_skill_states_precedence_over_generic_plugin_skill():
    assert "frontend-design:frontend-design" in _skill()


# --- User Story 1: inspect references, interpret before implementing ---


def test_skill_links_analysis_and_interpretation_files_that_exist():
    text = _skill()
    for name in ("reference-analysis.md", "design-interpretation.md"):
        assert name in text
        assert (SKILL_DIR / name).is_file()


def test_skill_forbids_copying_reference_assets():
    text = _skill().lower()
    for word in ("logos", "trademarks", "illustrations", "copy", "scrap"):
        assert word in text, f"do-not-copy rule missing '{word}'"


def test_gather_inputs_names_reference_location_and_shared_folder():
    section = _section(_skill(), "Gather inputs")
    assert "design/references/" in section
    assert "shared/" in section


def test_reference_analysis_covers_every_dimension():
    text = (SKILL_DIR / "reference-analysis.md").read_text(encoding="utf-8").lower()
    for dimension in (
        "layout",
        "hierarchy",
        "typography",
        "spacing",
        "alignment",
        "density",
        "color",
        "border",
        "radius",
        "shadow",
        "button",
        "input",
        "card",
        "navigation",
        "feedback",
        "responsive",
    ):
        assert dimension in text, f"reference analysis missing '{dimension}'"


def test_interpretation_template_has_every_data_model_section():
    data_model = DATA_MODEL_PATH.read_text(encoding="utf-8")
    block = data_model.split("## Design Interpretation", 1)[1].split("\n## ", 1)[0]
    sections = re.findall(r"^\| ([A-Z][^|]+?) \|", block, re.MULTILINE)
    sections = [s for s in sections if s != "Section"]
    assert "Not carried over" in sections
    template = (SKILL_DIR / "design-interpretation.md").read_text(encoding="utf-8")
    for section in sections:
        assert section in template, f"interpretation template missing '{section}'"


# --- User Story 2: implement without changing behavior ---


def test_skill_contains_learning_ui_rules():
    text = _skill().lower()
    for phrase in (
        "visual focus",
        "dashboard",
        "primary action",
        "correct",
        "incorrect",
        "loading",
        "sentence practice",
        "progress",
        "mobile",
    ):
        assert phrase in text, f"learning UI rule missing '{phrase}'"


def test_skill_contains_accessibility_floor():
    text = _skill().lower()
    for phrase in ("semantic", "keyboard", "focus", "contrast", "label", "44"):
        assert phrase in text, f"accessibility floor missing '{phrase}'"


def test_skill_requires_stopping_before_behavior_changes():
    text = _skill().lower()
    assert "stop and ask" in text
    assert "learning behavior" in text


def test_skill_runs_test_suite_and_adds_no_dependencies():
    text = _skill()
    assert "pytest" in text
    for line in text.lower().splitlines():
        assert not ("add" in line and "pyproject" in line and "never" not in line), line


# --- User Story 3: verify visually and refine ---


def test_skill_links_visual_verification_recipe():
    assert "visual-verification.md" in _skill()
    assert (SKILL_DIR / "visual-verification.md").is_file()


def test_visual_verification_recipe_contents():
    text = (SKILL_DIR / "visual-verification.md").read_text(encoding="utf-8")
    for needle in (
        "design/fixtures/vocabulary",
        "--port 8421",
        "127.0.0.1",
        "1280",
        "390",
        "npx",
        "playwright",
        "skipped",
        "design/verification/",
        '"collection"',
    ):
        assert needle in text, f"verification recipe missing '{needle}'"
    lowered = text.lower()
    for category in (
        "spacing",
        "sizing",
        "alignment",
        "typography",
        "density",
        "hierarchy",
        "consistency",
    ):
        assert category in lowered, f"comparison checklist missing '{category}'"


def test_refine_is_bounded_and_skipped_verification_is_reported():
    text = _skill()
    assert "3" in _section(text, "Refine")
    assert "skipped" in _section(text, "Verify visually").lower()


def test_report_lists_required_items():
    section = _section(_skill(), "Report").lower()
    for item in ("references", "interpretation", "files changed", "screenshot", "deviation"):
        assert item in section, f"report section missing '{item}'"


# --- User Story 4: page-independent and reusable ---


def test_skill_files_reference_no_element_ids_from_the_real_page():
    page_ids = re.findall(r'id="([^"]+)"', TEMPLATE_PATH.read_text(encoding="utf-8"))
    assert page_ids
    for path in sorted(SKILL_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for element_id in page_ids:
            assert f"#{element_id}" not in text, f"{path.name} names page element #{element_id}"
