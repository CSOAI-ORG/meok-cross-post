# meok-cross-post

One-command distribution scoring for MCP servers. Score a repo against
**6 marketplaces** and get a 0-600 number telling you if it's ready to ship.

```bash
$ meok-cross-post ~/clawd/csoai-org-v2

MEOK Cross-Post Score: /Users/nicholas/clawd/csoai-org-v2

  README:    35/40
  Pyproject: 25/30
  GitHub:    25/30

  Platform scores:
    [OK] smithery       88/100
    [OK] mcp_registry   82/100
    [OK] docker_hub     65/100
    [--] glama          91/100
    [OK] mcpize         85/100
    [OK] pulse_mcp      84/100

  Total: 495/600  (5/6 ready)
  STATUS: needs work to hit 500+/600
```

## What it does

Each platform has its own quality bar:

| Platform | Cares most about |
|----------|------------------|
| **Smithery** | pyproject.toml + README install snippet |
| **MCP Registry** | All-around, especially GH workflows |
| **Docker Hub** | Dockerfile + GH Actions workflow |
| **Glama** | README depth + features section |
| **MCPize** | Auto-deploy from GitHub = needs CI green |
| **PulseMCP** | README + clear description |

The score is a heuristic 0-100 per platform, derived from the same upstream
signals (README, pyproject, GitHub repo readiness). The CLI reports
**total/600** and a per-platform breakdown.

**Goal:** 500+/600 with ≥4 platforms "ready" (= 80+) = production-ready.

## Install

```bash
pip install meok-cross-post
```

## Usage

```bash
# Score a local MCP server
meok-cross-post ~/clawd/some-mcp-server

# Just the JSON
meok-cross-post ~/clawd/some-mcp-server --json

# Single platform
meok-cross-post ~/clawd/some-mcp-server --platform glama
```

## Roadmap

- [ ] Per-platform API calls (real Smithery + Glama + PulseMCP submission)
- [ ] Auto-PR for missing files (LICENSE, dependabot.yml, CODEOWNERS)
- [ ] CI integration (fail PR if score < 400)
- [ ] Webhook on `git push` to re-score

## License

MIT © MEOK AI Labs / CSOAI-ORG
