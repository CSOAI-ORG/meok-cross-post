"""Tests for meok-cross-post — score a sample MCP repo."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from meok_cross_post import score_repo


def make_fake_repo(tmpdir: Path, *, with_license=True, with_workflows=True, with_dependabot=True, with_codeowners=False, with_dockerfile=False, readme_size=4000):
    (tmpdir / "pyproject.toml").write_text("""
[project]
name = "fake-mcp"
version = "0.1.0"
description = "A test MCP server."
requires-python = ">=3.9"
dependencies = ["mcp>=1.0.0"]
""".strip())
    readme = "# fake-mcp\n\n" + "Lorem ipsum " * (readme_size // 12)
    readme += "\n\n## install\n\n```bash\npip install fake-mcp\n```\n\n## usage\n\n```python\nfrom fake_mcp import server\n```\n\nMIT license."
    (tmpdir / "README.md").write_text(readme)
    if with_license:
        (tmpdir / "LICENSE").write_text("MIT License\n\nCopyright (c) 2026 MEOK AI Labs")
    if with_workflows or with_dependabot or with_codeowners:
        (tmpdir / ".github").mkdir(exist_ok=True)
    if with_workflows:
        (tmpdir / ".github" / "workflows").mkdir(exist_ok=True)
        (tmpdir / ".github" / "workflows" / "ci.yml").write_text("name: ci\non: push")
    if with_dependabot:
        (tmpdir / ".github" / "dependabot.yml").write_text("version: 2\nupdates: []")
    if with_codeowners:
        (tmpdir / ".github" / "CODEOWNERS").write_text("* @meok")
    if with_dockerfile:
        (tmpdir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"-m\", \"server\"]")
    return tmpdir


def test_score_empty_repo_returns_error():
    with tempfile.TemporaryDirectory() as d:
        result = score_repo(d)
    assert "error" in result
    assert "no_pyproject_or_package_json" in result["error"]


def test_score_minimal_repo():
    with tempfile.TemporaryDirectory() as d:
        p = make_fake_repo(Path(d), with_license=False, with_workflows=False, with_dependabot=False)
        result = score_repo(p)
    assert result["total_score"] > 0
    assert result["readme_score"] >= 20  # got install + usage + license mention
    assert result["pyproject_score"] == 30  # got all 30
    assert result["github_score"] == 0  # no LICENSE, no GH
    print(f"  minimal repo: total={result['total_score']}, ready={result['ready_count']}/6")


def test_score_full_repo_high_score():
    with tempfile.TemporaryDirectory() as d:
        p = make_fake_repo(Path(d), with_codeowners=True, readme_size=5000)
        result = score_repo(p)
    # All 3 signals strong, expect most platforms to be ready
    assert result["total_score"] >= 400, f"Expected >=400, got {result['total_score']}"
    assert result["ready_count"] >= 3
    print(f"  full repo: total={result['total_score']}, ready={result['ready_count']}/6, prod_ready={result['ready_for_production']}")


def test_score_with_all_signal_perfect_score():
    """All signals at max + Dockerfile should hit 600/600."""
    with tempfile.TemporaryDirectory() as d:
        p = make_fake_repo(Path(d), with_codeowners=True, with_dockerfile=True, readme_size=10000)
        result = score_repo(p)
    # README: 40, pyproject: 30, GH: 30. With per-platform weighting this should be near-perfect.
    assert result["github_score"] == 30, f"github score: {result['github_score']}"
    assert result["readme_score"] >= 30, f"readme score: {result['readme_score']}"
    assert result["pyproject_score"] == 30
    # All 6 platforms should be ready
    assert result["ready_count"] == 6, f"ready count: {result['ready_count']}, {result['platforms']}"
    assert result["ready_for_production"] is True
    print(f"  perfect: total={result['total_score']}/600 (prod_ready={result['ready_for_production']})")


def test_score_per_platform_breakdown():
    with tempfile.TemporaryDirectory() as d:
        p = make_fake_repo(Path(d), with_codeowners=True)
        result = score_repo(p)
    platforms = {pl["platform"]: pl["score"] for pl in result["platforms"]}
    assert set(platforms.keys()) == {
        "smithery", "mcp_registry", "docker_hub", "glama", "mcpize", "pulse_mcp"
    }
    # All scores should be in 0-100
    for name, score in platforms.items():
        assert 0 <= score <= 100, f"{name}: {score}"
    print(f"  per-platform: {platforms}")


def test_docker_hub_lower_without_workflows():
    """Docker Hub should score lower when no GH workflows."""
    with tempfile.TemporaryDirectory() as d:
        p = make_fake_repo(Path(d), with_workflows=False)
        result = score_repo(p)
    platforms = {pl["platform"]: pl["score"] for pl in result["platforms"]}
    assert platforms["docker_hub"] < platforms["smithery"]
    print(f"  no workflows: docker_hub={platforms['docker_hub']} < smithery={platforms['smithery']}")


def test_score_real_c2pa_repo():
    """Score the real c2pa-watermark-mcp I just shipped."""
    real = Path("/Users/nicholas/clawd")  # could be elsewhere
    if not (real / "c2pa-watermark-mcp").exists():
        # try /tmp fallback
        real = Path("/tmp/c2pa-watermark-mcp")
    if not real.exists():
        print("  (skip: c2pa repo not on disk)")
        return
    result = score_repo(real)
    print(f"  c2pa-watermark-mcp: total={result['total_score']}/600, ready={result['ready_count']}/6")


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
        except AssertionError as e:
            print(f"✗ {t.__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed} test(s) FAILED")
        sys.exit(1)
    print(f"\n✅ All {len(tests)} tests passed")
