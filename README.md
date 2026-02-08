# date-resolver

A zero-dependency date computation skill for AI agents. Resolves natural language date expressions to concrete ISO dates using only Python stdlib. No pip installs, no virtual environments, no network access.

## The Problem

Date math is one of the most reliable sources of subtle agent errors. "Next Wednesday" depends on what day it is. "In 3 business days" requires knowing weekends. "End of month" depends on which month. Agents get this wrong constantly — off-by-one errors, wrong week boundaries, hallucinated calendars.

This skill gives the agent a script to call instead of doing the math in its head.

## What It Handles

| Pattern | Examples |
|---------|----------|
| Fixed words | `today`, `tomorrow`, `yesterday` |
| Compound | `day after tomorrow`, `day before yesterday` |
| Next/last weekday | `next wednesday`, `last friday`, `this monday` |
| Bare weekday | `friday` (= next occurrence) |
| N weekdays from now | `3 fridays from now`, `2 sundays from now` |
| In N units | `in 3 days`, `in 2 weeks`, `in 1 month` |
| N units ago | `5 days ago`, `2 months ago` |
| Business days | `next business day`, `in 3 business days`, `in 5 workdays` |
| Period boundaries | `end of month`, `start of next month`, `end of year`, `eom`, `eoy` |
| Week boundaries | `end of week`, `start of next week` |
| Named dates | `march 15`, `15th of march`, `december 25 2026` |
| ISO passthrough | `2026-03-15` |

All output is structured JSON (except `calendar` which is formatted text).

## Quick Start

```bash
# Resolve a relative date
python3 scripts/dates.py resolve "next wednesday"
# {"date": "2026-02-11", "day_of_week": "Wednesday", "days_from_today": 3, ...}

# Get day of week for a specific date
python3 scripts/dates.py weekday 2026-03-15
# {"date": "2026-03-15", "day_of_week": "Sunday", "is_weekend": true, ...}

# Show a month calendar
python3 scripts/dates.py calendar 2 2026

# Describe a date relative to today
python3 scripts/dates.py relative 2026-04-01
# {"date": "2026-04-01", "days_from_today": 52, "business_days": 38, "human_readable": "in 7 weeks and 3 days"}
```

## Installation as an Agent Skill

Copy the skill directory into your agent's skills folder:

```bash
# Cursor
cp -r . ~/.cursor/skills/date-resolver/

# Claude Code
cp -r . ~/.claude/skills/date-resolver/

# Codex
cp -r . ~/.codex/skills/date-resolver/

# Any agent that supports skills
cp -r . <agent-skills-dir>/date-resolver/
```

The `SKILL.md` file contains the full skill definition with trigger patterns, usage instructions, and edge case documentation. Agents that support skill files will pick it up automatically.

## Usage Pattern in Workflows

When a user or upstream system gives you a relative date like "by next Thursday":

1. Run `resolve "next thursday"` to get the concrete ISO date
2. Use the ISO date in all downstream operations
3. When reporting back, include both: "next Thursday (February 12, 2026)"

This grounds the relative expression early and prevents drift if the workflow spans multiple days.

## Requirements

- Python 3.10+
- Zero third-party dependencies (stdlib only)

## Pairs Well With

- [date-grounding](https://github.com/ai-mcp-garage/date-grounding) — Session hook that injects today's date into agent context at start. Use date-grounding so the agent knows what day it is, then use date-resolver for all the arithmetic.

## License

MIT
