# bng-address-lookup (Claude Code plugin)

Look up the closest UK postal addresses to a British National Grid (BNG) coordinate
— or any EPSG-specified CRS — using the Buchanan Gazetteer API. Supports single
coordinate lookups and batch CSV processing.

This repository is a Claude Code [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
hosting a single plugin (`bng-address-lookup`).

## Quickstart for new users

### Prerequisites

1. **Claude Code installed** and signed in — https://claude.com/claude-code
2. **Python 3** on your `PATH` (`python3 --version` should work). Standard on macOS;
   on other systems install via your package manager (`brew install python`,
   `apt install python3`, etc.).
3. **A Buchanan Gazetteer API token.** Either:
   - Ping the maintainer ([@javanicki](https://github.com/javanicki)) for the
     shared token — fastest, everyone uses one key, or
   - Request your own from Buchanan Services — slower but each user gets a
     separate, revocable credential.

   The token is **required** — the plugin ships no fallback.

### 1. Set the API token

Add this line to your `~/.zshrc` (or `~/.bashrc`):

```bash
export BNG_API_TOKEN=<paste-the-token-here>
```

Then run `source ~/.zshrc` or open a new terminal so the variable is picked up.

The plugin exits immediately with a helpful error if the variable is unset, so
do this first.

### 2. Install the plugin

In a Claude Code session, run these slash commands one at a time:

```text
/plugin marketplace add javanicki/bng-address-lookup
/plugin install bng-address-lookup@patryk-plugins
/reload-plugins
```

After install, the skill is available namespaced as
`/bng-address-lookup:bng-address-lookup`. Claude will also pick it up
automatically when you describe a BNG lookup task in natural language.

### 3. Try it

Ask Claude in plain English:

> "find addresses near coordx=534903.29, coordy=184167.36"

You should see Claude run the lookup script and report 5 nearby UK addresses,
saving a CSV under `/tmp/bng_outputs/`.

### Updating later

When the maintainer pushes improvements:

```text
/plugin marketplace update patryk-plugins
```

## Usage

### Single coordinate

> "Find addresses near coordx=534903.29, coordy=184167.36"

Claude will run the lookup and save a CSV of the nearest addresses to
`/tmp/bng_outputs/` (or `$CLAUDE_OUTPUT_DIR` if set).

### Batch from CSV

Provide a CSV with `coordX` and `coordY` columns (case-insensitive). Any other
columns are passed through to the output unchanged — useful for keeping site
IDs or names alongside the results. Optional per-row overrides: `epsg`, `limit`.

> "Run the BNG lookup on `~/Downloads/sites.csv`"

## Configuration

| Env var             | Purpose                                                      |
| :------------------ | :----------------------------------------------------------- |
| `BNG_API_TOKEN`     | **Required.** Your Buchanan Gazetteer API token. The script exits with an error if unset. |
| `CLAUDE_OUTPUT_DIR` | Override the directory results are written to (defaults to `/tmp/bng_outputs/`). |

## Requirements

- Python 3 (standard library only — no pip dependencies for the core script).
- A working Buchanan Gazetteer API token, supplied via the `BNG_API_TOKEN`
  environment variable. No token ships with the plugin.

## Troubleshooting

| Symptom | Likely cause / fix |
| :-- | :-- |
| First lookup fails with `BNG_API_TOKEN ... not set` | The env var isn't in the shell Claude Code is running from. Add it to `~/.zshrc` and restart the terminal (or `source` the file). |
| Buchanan API returns HTTP 401 / 403 | The token in `$BNG_API_TOKEN` is invalid or revoked. Get a fresh one from the maintainer or Buchanan Services. |
| `python: command not found` | The skill uses `python3`, not `python`. If this still fails, install Python 3 and ensure `python3` is on your `PATH`. |
| Plugin shows old behaviour after a push | Run `/plugin marketplace update patryk-plugins` then `/reload-plugins`. |

## Repo layout

```
.
├── .claude-plugin/
│   └── marketplace.json          ← marketplace catalog
├── plugins/
│   └── bng-address-lookup/
│       ├── .claude-plugin/
│       │   └── plugin.json       ← plugin manifest
│       └── skills/
│           └── bng-address-lookup/
│               ├── SKILL.md      ← skill instructions for Claude
│               └── scripts/
│                   └── lookup.py ← API client + CSV writer
└── README.md
```

## Local development

Test changes without publishing by running Claude Code with `--plugin-dir`:

```bash
claude --plugin-dir ./plugins/bng-address-lookup
```

Then in the session: `/reload-plugins` to pick up edits.
