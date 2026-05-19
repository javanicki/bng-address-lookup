# bng-address-lookup (Claude Code plugin)

Look up the closest UK postal addresses to a British National Grid (BNG) coordinate
— or any EPSG-specified CRS — using the Buchanan Gazetteer API. Supports single
coordinate lookups and batch CSV processing.

This repository is a Claude Code [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
hosting a single plugin (`bng-address-lookup`).

## Install

### 1. Get a Buchanan Gazetteer API token

This plugin does **not** ship with a token. You need one from Buchanan Services
to use the API. Once you have it, export it in your shell:

```bash
export BNG_API_TOKEN=your-token-here
```

Add the line to `~/.zshrc` (or `~/.bashrc`) so it persists across sessions.
The plugin will fail fast with a helpful error if the variable is unset.

### 2. Add the marketplace and install

In Claude Code:

```text
/plugin marketplace add <git-url-to-this-repo>
/plugin install bng-address-lookup@patryk-plugins
```

After installation, the skill is available namespaced as
`/bng-address-lookup:bng-address-lookup`, but Claude will also pick it up
automatically when you describe a BNG lookup task (e.g. "find addresses near
this grid ref", or by attaching a CSV of coordinates).

The first time you run a lookup, Claude will check whether `BNG_API_TOKEN` is
set; if not, it will ask you for the token and run the lookup with it inline.

To pick up changes after the maintainer pushes a new commit:

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

Set in your shell rc file, e.g.:

```bash
export BNG_API_TOKEN=your-token-here
```

## Requirements

- Python 3 (standard library only — no pip dependencies for the core script).
- A working Buchanan Gazetteer API token, supplied via the `BNG_API_TOKEN`
  environment variable. No token ships with the plugin.

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
