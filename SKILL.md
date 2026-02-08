---
name: date-resolver
description: >
  Resolve relative and natural language date expressions to concrete ISO dates. Use this skill
  whenever you need to compute a relative date like "next Wednesday", "3 fridays from now",
  "in 2 business days", or "end of month". Also use it for calendar lookups, day-of-week
  checks, and computing how far away a target date is (including business days). This skill
  handles the date *math* — the error-prone computation part. It does NOT handle knowing
  today's date (that should already be in your context via a hook or system prompt). Trigger
  on any date arithmetic: "when is", "how many days until", "what day of the week is",
  scheduling math, deadline computation, or any expression that needs resolving to a concrete
  date. Even if you think you can do the math yourself, use the script — off-by-one errors
  in date arithmetic are common and undermine trust.
---

# Date Resolver

A zero-dependency date computation tool for agentic systems. Uses only Python stdlib — no
virtual environments, no pip installs, no network access. Just `python3`.

## Why This Exists

Date math is one of the most common sources of subtle errors in agentic workflows. "Next
Wednesday" means different things depending on what day it is. "In 3 business days" requires
knowing weekends. "End of month" depends on which month. Rather than doing this arithmetic
in your head (where off-by-one errors are easy), run the script and get a definitive answer.

This skill is the computation layer only. It assumes you already know today's date (from
your system prompt, a SessionStart hook, or similar). If you don't have today's date in
context, run `date +%Y-%m-%d` once to establish it, then use this skill for everything else.

## Quick Reference

The script lives at `scripts/dates.py` relative to this skill's directory. All commands
output structured JSON (except `calendar` which outputs formatted text).

### Resolve a natural language date

```bash
python3 <skill-path>/scripts/dates.py resolve "<expression>"
```

Returns: date (ISO), day_of_week, days_from_today, description.

**Supported expressions:**

| Pattern | Examples |
|---------|----------|
| Fixed words | `today`, `tomorrow`, `yesterday` |
| Compound | `day after tomorrow`, `day before yesterday` |
| Next/last weekday | `next wednesday`, `last friday`, `this monday` |
| Bare weekday | `friday` (= next occurrence) |
| N weekdays from now | `3 fridays from now`, `2 sundays from now` |
| In N units | `in 3 days`, `in 2 weeks`, `in 1 month`, `in 4 years` |
| N units ago | `5 days ago`, `2 months ago`, `1 year ago` |
| A unit from now | `a week from now`, `a month from now` |
| Business days | `next business day`, `in 3 business days`, `in 5 workdays` |
| Period boundaries | `end of month`, `start of next month`, `end of year`, `eom`, `eoy` |
| Week boundaries | `end of week`, `start of next week`, `next week` |
| Named dates | `march 15`, `15th of march`, `december 25 2026` |
| ISO passthrough | `2026-03-15` |

### Get day of week for a specific date

```bash
python3 <skill-path>/scripts/dates.py weekday 2026-03-15
```

Returns: date, day_of_week, day_number, is_weekend, is_weekday.

### Show a month calendar

```bash
python3 <skill-path>/scripts/dates.py calendar [month] [year]
```

Defaults to current month/year if omitted. Sunday-first layout.

### Describe a date relative to today

```bash
python3 <skill-path>/scripts/dates.py relative 2026-03-15
```

Returns: date, day_of_week, days_from_today, business_days, human_readable.

## When to Use Each Command

| Situation | Command |
|-----------|---------|
| "When is next Friday?" | `resolve "next friday"` |
| "What day of the week is March 15?" | `weekday 2026-03-15` |
| "How far away is the deadline?" | `relative 2026-04-01` |
| "Show me this month" | `calendar` |
| User mentions a relative date in conversation | `resolve` to ground it, then use the ISO date |

## Usage Pattern in Workflows

When a user or upstream system gives you a relative date like "by next Thursday", the
recommended pattern is:

1. Run `resolve "next thursday"` to get the concrete ISO date
2. Use the ISO date in all downstream operations
3. When reporting back to the user, include both: "next Thursday (February 12, 2026)"

This grounds the relative expression early and prevents drift if the workflow spans
multiple days.

## Important Notes

- The script uses system local time. If timezone precision matters, account for that
  separately.
- Ambiguous expressions prefer future dates. "Friday" means *next* Friday. Named months
  without a year pick the next occurrence. This is intentional for agentic use cases where
  you're usually planning ahead.
- Weekday abbreviations work: `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`.
- Returns structured JSON so you can extract exactly the field you need.
- If a time component is detected (e.g. "next Tuesday at 3pm"), the date is resolved
  but a warning is included in the output. This is a date-only resolver.
- Zero dependencies. Runs anywhere Python 3.10+ is available.

## What This Doesn't Handle

These patterns are outside scope — if you encounter them, break the expression down
into parts the script can handle, or do the final step yourself:

- **Compound expressions**: "2 weeks and 3 days from now" — resolve each part separately
- **Nth weekday of month**: "first Monday of March" — use `calendar` to look it up visually
- **Time of day**: "3pm tomorrow" — the date resolves but time is ignored (with a warning)
- **Timezones**: all dates use system local time
- **Recurring patterns**: "every other Friday" — resolve one instance at a time
