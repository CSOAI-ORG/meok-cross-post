"""
meok-cross-post — One-command distribution to MCP marketplaces.

The 6-platform nuclear launch sequence for a single MCP server:
  1. Smithery (smithery.ai)       — registry + hosted runtime
  2. MCP Registry (modelcontextprotocol) — official Anthropic registry
  3. Docker Hub                    — `docker push` to namespace
  4. Glama.ai                      — discovery + ratings
  5. MCPize.io                     — auto-deploy from GitHub
  6. PulseMCP.com                  — directory + newsletter

Each platform has a small Python adapter (one file each in adapters/).
The CLI is `meok-cross-post` (entry point: meok_cross_post.cli:main).

Scoring:
  Each adapter returns a 0-100 score for the README + repo + pyproject.
  Total = unweighted average, max 600 (6 platforms * 100).
  Goal: 500+/600 for "production-ready" listing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class PlatformScore:
    """Score for one marketplace listing."""
    platform: str
    score: int  # 0-100
    issues: list[str] = field(default_factory=list)
    ready: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "score": self.score,
            "issues": self.issues,
            "ready": self.ready,
            "metadata": self.metadata,
        }


def _check_readme(path: Path) -> tuple[int, list[str]]:
    """Score a README 0-40. +5 install snippet, +5 usage, +5 license, etc."""
    if not path.exists():
        return 0, ["README.md missing"]
    text = path.read_text(encoding="utf-8", errors="ignore")
    score = 0
    issues = []
    if len(text) < 500:
        issues.append("README too short (<500 chars)")
    else:
        score += 10
    if "## install" in text.lower() or "pip install" in text.lower():
        score += 10
    else:
        issues.append("Missing install instructions")
    if "## usage" in text.lower() or "```python" in text or "```bash" in text:
        score += 10
    else:
        issues.append("Missing usage example")
    if "license" in text.lower() or "mit" in text.lower():
        score += 5
    else:
        issues.append("No license mention")
    if len(text) > 3000:
        score += 5
    if "## features" in text.lower() or "## what" in text.lower():
        score += 5
    return min(score, 40), issues


def _check_pyproject(path: Path) -> tuple[int, list[str]]:
    """Score a pyproject.toml 0-30. +10 name, +10 version, +5 deps, +5 description."""
    if not path.exists():
        return 0, ["pyproject.toml missing"]
    text = path.read_text(encoding="utf-8")
    score = 0
    issues = []
    if "name" in text:
        score += 10
    else:
        issues.append("pyproject.toml missing [project] name")
    if "version" in text:
        score += 10
    else:
        issues.append("pyproject.toml missing version")
    if "description" in text:
        score += 5
    if "dependencies" in text or "requires-python" in text:
        score += 5
    return min(score, 30), issues


def _check_github(path: Path) -> tuple[int, list[str]]:
    """Score GitHub readiness 0-30. +10 LICENSE, +10 workflows, +5 CODEOWNERS, +5 dependabot."""
    score = 0
    issues = []
    if (path / "LICENSE").exists():
        score += 10
    else:
        issues.append("Missing LICENSE file")
    gh = path / ".github"
    if gh.exists():
        score += 5
        if (gh / "workflows").exists():
            score += 5
        if (gh / "dependabot.yml").exists():
            score += 5
        if (gh / "CODEOWNERS").exists():
            score += 5
    else:
        issues.append("Missing .github/ directory")
    return min(score, 30), issues


def score_repo(path: str | Path) -> dict[str, Any]:
    """Score a local repo against the 6 marketplaces.

    Args:
        path: path to the MCP server repo (must contain pyproject.toml + README.md)

    Returns:
        dict with total_score, max_score, per_platform breakdown, ready flag
    """
    p = Path(path).resolve()
    if not (p / "pyproject.toml").exists() and not (p / "package.json").exists():
        return {"error": "no_pyproject_or_package_json", "path": str(p)}

    readme_score, readme_issues = _check_readme(p / "README.md")
    if (p / "pyproject.toml").exists():
        pyproject_score, pyproject_issues = _check_pyproject(p / "pyproject.toml")
    else:
        # Node MCP server
        pyproject_score, pyproject_issues = 25, ["Node.js MCP — pyproject.toml not applicable"]
    gh_score, gh_issues = _check_github(p)

    # 6 platforms × 100. Each platform's score is its own 0-100 derived from
    # the same upstream signals (readme, pyproject, github readiness).
    platforms = [
        "smithery", "mcp_registry", "docker_hub",
        "glama", "mcpize", "pulse_mcp",
    ]

    platform_scores: list[dict[str, Any]] = []
    for plat in platforms:
        # Per-platform weighting. Smithery cares most about pyproject; Docker
        # cares most about GitHub workflows; Glama about README.
        if plat == "smithery":
            score = int(readme_score * 1.0 + pyproject_score * 1.2 + gh_score * 0.5)
            # cap 100
            score = min(score, 100)
            issues = list(readme_issues) + [f"smithery: {i}" for i in pyproject_issues]
        elif plat == "mcp_registry":
            score = int(readme_score * 0.8 + pyproject_score * 1.0 + gh_score * 0.7)
            score = min(score, 100)
            issues = [f"mcp_registry: {i}" for i in readme_issues]
        elif plat == "docker_hub":
            # docker_hub scores gh workflows + LICENSE heavy. Max signal:
            # readme=40, pyproject=30, gh=30 → 40*0.5 + 30*0.3 + 30*1.2 = 20+9+36 = 65
            # We need 80+ so require Dockerfile in addition.
            dockerfile = (p / "Dockerfile").exists()
            if dockerfile:
                score = min(int(readme_score * 0.5 + pyproject_score * 0.3 + gh_score * 1.2 + 20), 100)
            else:
                score = int(readme_score * 0.5 + pyproject_score * 0.3 + gh_score * 1.2)
            score = min(score, 100)
            issues = []
            if not dockerfile:
                issues.append("docker_hub: Dockerfile missing (needed for image build)")
        elif plat == "glama":
            score = int(readme_score * 1.2 + pyproject_score * 0.8 + gh_score * 0.5)
            score = min(score, 100)
            issues = list(readme_issues)
        elif plat == "mcpize":
            score = int(readme_score * 1.0 + pyproject_score * 0.8 + gh_score * 0.8)
            score = min(score, 100)
            issues = [f"mcpize: {i}" for i in readme_issues]
        elif plat == "pulse_mcp":
            score = int(readme_score * 0.9 + pyproject_score * 0.9 + gh_score * 0.6)
            score = min(score, 100)
            issues = [f"pulse_mcp: {i}" for i in readme_issues]
        else:
            score = 0
            issues = []

        platform_scores.append({
            "platform": plat,
            "score": score,
            "issues": issues,
            "ready": score >= 80,
        })

    total = sum(p["score"] for p in platform_scores)
    max_total = 600
    ready_count = sum(1 for p in platform_scores if p["ready"])

    return {
        "path": str(p),
        "readme_score": readme_score,
        "pyproject_score": pyproject_score,
        "github_score": gh_score,
        "platforms": platform_scores,
        "total_score": total,
        "max_score": max_total,
        "ready_count": ready_count,
        "ready_for_production": total >= 500 and ready_count >= 4,
    }


__all__ = ["score_repo", "PlatformScore"]
