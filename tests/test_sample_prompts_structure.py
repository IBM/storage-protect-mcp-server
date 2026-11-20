"""
test_sample_prompts_structure.py
=================================
Structural conformance tests for the sample prompt catalogs.

Validates that every prompt in docs/example/sample-prompts.md and
tests/negative_sample_prompts.md follows the prompt-engineering structure
(role, context, task, constraints, output format), stays within the
100-character line limit, references only registered MCP tools, and that every
negative prompt maps to an existing automated test.

docs/example/sample-prompts.md is written in natural English. A standard prompt
is an opening paragraph (the role, then the context and MCP server) followed by
three introduced blocks::

    You are a <role> responsible for ...
    <environment and MCP server>. <situation that triggered the request>.

    Do the following:
    1. <numbered actions naming the exact MCP tools>

    The following constraints apply:
    - <scope limits and execution safety rules>

    Generate the output with the following format:
    <shape of the expected answer>

The two "Context-Optimised ... Blueprint" prompts are long-form and place the
constraints block after the output block; they are only required to contain all
three introduced blocks.

tests/negative_sample_prompts.md still uses the labelled form (Role:, Context:,
Task:, Constraints:, Output Format:).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
POSITIVE_DOC = REPO_ROOT / "docs" / "example" / "sample-prompts.md"
NEGATIVE_DOC = REPO_ROOT / "tests" / "negative_sample_prompts.md"
NEGATIVE_TESTS = REPO_ROOT / "tests" / "test_sample_prompts_negative.py"

MAX_LINE = 100
SECTIONS = ["Role:", "Context:", "Task:", "Constraints:", "Output Format:"]

# Natural-English block introducers used by docs/example/sample-prompts.md.
TASK_MARK = "Do the following:"
CONSTRAINTS_MARK = "The following constraints apply:"
OUTPUT_MARK = "Generate the output with the following format:"
POSITIVE_MARKS = [TASK_MARK, CONSTRAINTS_MARK, OUTPUT_MARK]
BLUEPRINT_MARK = "Follow these query success rules:"

# Prompts per persona section in sample-prompts.md (blueprint prompts included
# in the section that contains them).
EXPECTED_POSITIVE_COUNTS = {
    "R-01": 17,
    "R-02": 13,
    "R-03": 14,
    "R-04": 8,
    "R-05": 13,
    "R-06": 13,
    "R-07": 11,
    "BLUEPRINT": 1,
    "R-08": 38,
}
EXPECTED_NEGATIVE_COUNTS = {
    "R-01": 3, "R-02": 2, "R-03": 2, "R-04": 2,
    "R-05": 2, "R-06": 2, "R-07": 2, "R-08": 3,
}

_TOOL_RE = re.compile(
    r"\b((?:query|define|update|set|delete|run|restore|register)_[a-z0-9_]+)\b"
)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _positive_prompts() -> list[tuple[str, str]]:
    """Return (persona_key, prompt_text) for every ```text block in the doc."""
    text = POSITIVE_DOC.read_text(encoding="utf-8")
    prompts: list[tuple[str, str]] = []
    for section in re.split(r"(?m)^## ", text)[1:]:
        title = section.split("\n", 1)[0]
        m = re.match(r"(R-0\d) ·", title)
        if m:
            key = m.group(1)
        elif title.startswith("Context-Optimised Investigation Blueprint"):
            key = "BLUEPRINT"
        else:
            continue
        for block in re.findall(r"```text\n(.*?)\n```", section, re.S):
            prompts.append((key, block))
    return prompts


def _negative_prompts() -> list[tuple[str, str, str]]:
    """Return (np_id, prompt_text, test_mapping) for each negative catalog entry."""
    text = NEGATIVE_DOC.read_text(encoding="utf-8")
    entries: list[tuple[str, str, str]] = []
    for entry in re.split(r"(?m)^### ", text)[1:]:
        np_id = entry.split(":", 1)[0]
        block = re.search(r"```text\n(.*?)\n\s*```", entry, re.S)
        mapping = re.search(r"\*\*Test Mapping\*\*: `([^`]+)`", entry)
        assert block and mapping, f"{np_id}: missing prompt block or test mapping"
        prompt = "\n".join(line[2:] if line.startswith("  ") else line
                           for line in block.group(1).split("\n"))
        entries.append((np_id, prompt, mapping.group(1)))
    return entries


def _registered_tools() -> set[str]:
    """Names of all registered MCP tools (BaseCommand subclasses)."""
    import sp_mcp_server.commands  # noqa: F401  (imports every command module)
    from sp_mcp_server.commands.base import BaseCommand

    def walk(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from walk(sub)

    names: set[str] = set()
    for cls in walk(BaseCommand):
        try:
            names.add(cls.name.fget(cls.__new__(cls)))  # type: ignore[union-attr]
        except Exception:
            continue  # abstract intermediates
    return names


def _opening(prompt: str) -> str:
    """Opening paragraph (role + context) of a natural-English prompt, one line."""
    return " ".join(prompt.split(TASK_MARK, 1)[0].split())


POSITIVE = _positive_prompts()
NEGATIVE = _negative_prompts()


# ---------------------------------------------------------------------------
# sample-prompts.md
# ---------------------------------------------------------------------------

class TestPositivePromptCatalog:
    """docs/example/sample-prompts.md conformance."""

    def test_prompt_counts_per_persona(self):
        counts: dict[str, int] = {}
        for key, _ in POSITIVE:
            counts[key] = counts.get(key, 0) + 1
        assert counts == EXPECTED_POSITIVE_COUNTS

    @pytest.mark.parametrize("idx", range(len(POSITIVE)))
    def test_prompt_has_all_blocks(self, idx: int):
        key, prompt = POSITIVE[idx]
        lines = prompt.split("\n")
        positions = []
        for mark in POSITIVE_MARKS:
            assert mark in lines, f"[{key} #{idx}] missing '{mark}'"
            positions.append(lines.index(mark))
        if BLUEPRINT_MARK not in lines:
            assert positions == sorted(positions), (
                f"[{key} #{idx}] blocks out of order: {positions}"
            )
        opening = _opening(prompt)
        assert opening.startswith("You are a"), f"[{key} #{idx}] must open with the role"

    def test_no_legacy_section_labels(self):
        """The natural-English rewrite must not leave labelled sections behind."""
        legacy = {"Role:", "Context:", "Task:", "Constraints:", "Output Format:",
                  "Query Success Rules:", "Required Execution Sequence:"}
        for key, prompt in POSITIVE:
            found = legacy & set(prompt.split("\n"))
            assert not found, f"[{key}] legacy labels remain: {sorted(found)}"

    @pytest.mark.parametrize("idx", range(len(POSITIVE)))
    def test_prompt_lines_within_limit(self, idx: int):
        key, prompt = POSITIVE[idx]
        too_long = [l for l in prompt.split("\n") if len(l) > MAX_LINE]
        assert not too_long, f"[{key} #{idx}] lines exceed {MAX_LINE} chars: {too_long}"

    def test_role_matches_persona(self):
        expected = {
            "R-01": "Data Protection Operator",
            "R-02": "Data Protection Administrator",
            "R-03": "Infrastructure Solution Architect",
            "R-04": "Workload and Application Owner",
            "R-05": "Security and Compliance Officer",
            "R-06": "Resilience Operations Manager",
            "R-07": "IBM Storage Protect Service Engineer",
            "R-08": "Data Protection Administrator",
        }
        for key, prompt in POSITIVE:
            if key in expected and BLUEPRINT_MARK not in prompt:
                role = _opening(prompt)
                assert expected[key] in role, f"[{key}] unexpected role: {role}"

    def test_context_names_mcp_server(self):
        for key, prompt in POSITIVE:
            if BLUEPRINT_MARK in prompt:
                continue
            assert "sp-mcp-" in _opening(prompt), f"[{key}] context lacks MCP server id"

    def test_referenced_tools_are_registered(self):
        registered = _registered_tools() | {"run_servermon"}
        unknown: set[str] = set()
        for _, prompt in POSITIVE:
            unknown |= {t for t in _TOOL_RE.findall(prompt) if t not in registered}
        assert not unknown, f"Prompts reference unregistered tools: {sorted(unknown)}"

    def test_every_prompt_tool_has_positive_test(self):
        """Each registered tool named in a prompt is exercised in the positive suite."""
        from sp_mcp_server.commands.base import BaseCommand

        def walk(cls):
            for sub in cls.__subclasses__():
                yield sub
                yield from walk(sub)

        by_name = {}
        for cls in walk(BaseCommand):
            try:
                by_name[cls.name.fget(cls.__new__(cls))] = cls.__name__  # type: ignore[union-attr]
            except Exception:
                continue
        positive_src = (REPO_ROOT / "tests" / "test_sample_prompts_positive.py").read_text(
            encoding="utf-8")
        referenced = set()
        for _, prompt in POSITIVE:
            referenced |= set(_TOOL_RE.findall(prompt))
        untested = sorted(
            t for t in referenced
            if t in by_name and by_name[t] not in positive_src
        )
        assert not untested, f"Prompt tools without a positive test: {untested}"

    def test_constraints_define_execution_safety(self):
        """Every standard prompt states whether it is read-only, advisory, or gated."""
        for key, prompt in POSITIVE:
            if BLUEPRINT_MARK in prompt:
                continue  # long-form blueprints keep their own rule sets
            constraints = prompt.split(CONSTRAINTS_MARK, 1)[1].split(OUTPUT_MARK, 1)[0]
            assert (
                "Read-only" in constraints
                or "Advisory" in constraints
                or "confirmation" in constraints
                or "approve" in constraints
            ), f"[{key}] Constraints define no execution safety rule"


# ---------------------------------------------------------------------------
# negative_sample_prompts.md
# ---------------------------------------------------------------------------

class TestNegativePromptCatalog:
    """tests/negative_sample_prompts.md conformance."""

    def test_prompt_counts_per_persona(self):
        counts: dict[str, int] = {}
        for np_id, _, _ in NEGATIVE:
            persona = "R-" + np_id[4:6]
            counts[persona] = counts.get(persona, 0) + 1
        assert counts == EXPECTED_NEGATIVE_COUNTS

    @pytest.mark.parametrize("np_id,prompt,_mapping", NEGATIVE, ids=[n[0] for n in NEGATIVE])
    def test_prompt_structure_and_width(self, np_id: str, prompt: str, _mapping: str):
        lines = prompt.split("\n")
        positions = [lines.index(s) for s in SECTIONS if s in lines]
        assert len(positions) == len(SECTIONS), f"{np_id}: missing sections"
        assert positions == sorted(positions), f"{np_id}: sections out of order"
        assert all(len(l) + 2 <= MAX_LINE for l in lines), f"{np_id}: line exceeds {MAX_LINE}"

    @pytest.mark.parametrize("np_id,_prompt,mapping", NEGATIVE, ids=[n[0] for n in NEGATIVE])
    def test_mapping_resolves_to_test(self, np_id: str, _prompt: str, mapping: str):
        path, cls, func = mapping.split("::")
        assert (REPO_ROOT / path) == NEGATIVE_TESTS
        source = NEGATIVE_TESTS.read_text(encoding="utf-8")
        assert re.search(rf"(?m)^class {cls}\b", source), f"{np_id}: class {cls} not found"
        assert re.search(rf"(?m)^\s+def {func}\(", source), f"{np_id}: {func} not found"
