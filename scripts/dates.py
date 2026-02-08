#!/usr/bin/env python3
"""
Stdlib-only date resolver for agentic systems.

Resolves natural language date expressions to ISO dates using only Python builtins.
No third-party dependencies required.

Usage:
    python3 dates.py resolve "next wednesday"
    python3 dates.py resolve "in 3 days"
    python3 dates.py resolve "2 fridays from now"
    python3 dates.py weekday 2026-02-08
    python3 dates.py calendar 2 2026
    python3 dates.py relative 2026-03-15
"""

import argparse
import calendar
import json
import re
from datetime import datetime, timedelta

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    # Abbreviations
    "mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3,
    "thurs": 3, "fri": 4, "sat": 5, "sun": 6,
}

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}


def _next_weekday(weekday: int, ref: datetime, weeks_ahead: int = 0) -> datetime:
    """Get the next occurrence of a weekday from ref date, optionally N weeks ahead."""
    days_ahead = weekday - ref.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return ref + timedelta(days=days_ahead + (weeks_ahead * 7))


def _prev_weekday(weekday: int, ref: datetime, weeks_back: int = 0) -> datetime:
    """Get the most recent past occurrence of a weekday from ref date."""
    days_back = ref.weekday() - weekday
    if days_back <= 0:
        days_back += 7
    return ref - timedelta(days=days_back + (weeks_back * 7))


def _add_months(dt: datetime, months: int) -> datetime:
    """Add N months to a date, clamping day to valid range."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def resolve(expression: str, ref: datetime | None = None) -> dict:
    """
    Resolve a natural language date expression to a structured result.

    Returns a dict with: date (ISO), day_of_week, expression, and description.
    """
    ref = ref or datetime.now()
    today = ref.replace(hour=0, minute=0, second=0, microsecond=0)
    expr = expression.lower().strip()

    # Strip time-of-day suffixes so "tomorrow morning" resolves as "tomorrow"
    time_suffixes = r"\s+(?:at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|in\s+the\s+(?:morning|afternoon|evening)|morning|afternoon|evening|night)$"
    has_time_suffix = bool(re.search(time_suffixes, expr))
    if has_time_suffix:
        expr = re.sub(time_suffixes, "", expr).strip()

    parsed = None
    desc = ""

    # --- Fixed words ---
    if expr in ("today", "now"):
        parsed = today
        desc = "today"
    elif expr == "tomorrow":
        parsed = today + timedelta(days=1)
        desc = "tomorrow"
    elif expr == "yesterday":
        parsed = today - timedelta(days=1)
        desc = "yesterday"

    # --- "day after tomorrow", "day before yesterday" ---
    elif expr == "day after tomorrow":
        parsed = today + timedelta(days=2)
        desc = "day after tomorrow"
    elif expr == "day before yesterday":
        parsed = today - timedelta(days=2)
        desc = "day before yesterday"

    # --- End/start of week/month/year ---
    elif expr in ("end of week", "end of this week", "this weekend"):
        # End of week = coming Sunday (or today if already Sunday)
        days_to_sunday = 6 - today.weekday()
        if days_to_sunday == 0 and expr != "this weekend":
            days_to_sunday = 0
        parsed = today + timedelta(days=days_to_sunday)
        desc = "end of this week (Sunday)"
    elif expr in ("start of next week", "beginning of next week", "next week"):
        days_to_monday = 7 - today.weekday()
        parsed = today + timedelta(days=days_to_monday)
        desc = "start of next week (Monday)"
    elif expr in ("end of month", "end of this month", "eom"):
        last_day = calendar.monthrange(today.year, today.month)[1]
        parsed = today.replace(day=last_day)
        desc = "end of this month"
    elif expr in ("start of next month", "beginning of next month"):
        parsed = _add_months(today.replace(day=1), 1)
        desc = "start of next month"
    elif expr in ("end of year", "end of this year", "eoy"):
        parsed = today.replace(month=12, day=31)
        desc = "end of this year"
    elif expr in ("start of next year", "beginning of next year"):
        parsed = today.replace(year=today.year + 1, month=1, day=1)
        desc = "start of next year"

    # --- "next/this/last <weekday>" ---
    if parsed is None:
        m = re.match(r"(next|this|last|previous)\s+(\w+)", expr)
        if m:
            modifier, day_name = m.group(1), m.group(2)
            if day_name in WEEKDAYS:
                wd = WEEKDAYS[day_name]
                if modifier in ("next", "this"):
                    parsed = _next_weekday(wd, today)
                    desc = f"next {day_name}"
                elif modifier in ("last", "previous"):
                    parsed = _prev_weekday(wd, today)
                    desc = f"last {day_name}"
            elif day_name == "week":
                if modifier == "next":
                    parsed = today + timedelta(days=7 - today.weekday())
                    desc = "start of next week"
                elif modifier in ("last", "previous"):
                    parsed = today - timedelta(days=today.weekday() + 7)
                    desc = "start of last week"
            elif day_name == "month":
                if modifier == "next":
                    parsed = _add_months(today.replace(day=1), 1)
                    desc = "start of next month"
                elif modifier in ("last", "previous"):
                    parsed = _add_months(today.replace(day=1), -1)
                    desc = "start of last month"

    # --- "N <weekday>s from now" ---
    if parsed is None:
        m = re.match(r"(\d+)\s+(\w+?)s?\s+from\s+(?:now|today)", expr)
        if m:
            count = int(m.group(1))
            unit = m.group(2)
            if unit in WEEKDAYS:
                parsed = _next_weekday(WEEKDAYS[unit], today, weeks_ahead=count - 1)
                desc = f"{count} {unit}(s) from now"
            elif unit in ("day",):
                parsed = today + timedelta(days=count)
                desc = f"{count} day(s) from now"
            elif unit in ("week",):
                parsed = today + timedelta(weeks=count)
                desc = f"{count} week(s) from now"
            elif unit in ("month",):
                parsed = _add_months(today, count)
                desc = f"{count} month(s) from now"
            elif unit in ("year",):
                parsed = today.replace(year=today.year + count)
                desc = f"{count} year(s) from now"

    # --- "in N business days / workdays" (must come before generic "in N units") ---
    if parsed is None:
        m = re.match(r"in\s+(\d+)\s+(?:business\s+days?|workdays?|work\s+days?)", expr)
        if m:
            count = int(m.group(1))
            d = today
            added = 0
            while added < count:
                d += timedelta(days=1)
                if d.weekday() < 5:
                    added += 1
            parsed = d
            desc = f"in {count} business day(s)"

    # --- "in N days/weeks/months/years" ---
    if parsed is None:
        m = re.match(r"in\s+(\d+)\s+(\w+?)s?$", expr)
        if m:
            count = int(m.group(1))
            unit = m.group(2)
            if unit == "day":
                parsed = today + timedelta(days=count)
                desc = f"in {count} day(s)"
            elif unit == "week":
                parsed = today + timedelta(weeks=count)
                desc = f"in {count} week(s)"
            elif unit == "month":
                parsed = _add_months(today, count)
                desc = f"in {count} month(s)"
            elif unit == "year":
                parsed = today.replace(year=today.year + count)
                desc = f"in {count} year(s)"

    # --- "N days/weeks/months ago" ---
    if parsed is None:
        m = re.match(r"(\d+)\s+(\w+?)s?\s+ago", expr)
        if m:
            count = int(m.group(1))
            unit = m.group(2)
            if unit == "day":
                parsed = today - timedelta(days=count)
                desc = f"{count} day(s) ago"
            elif unit == "week":
                parsed = today - timedelta(weeks=count)
                desc = f"{count} week(s) ago"
            elif unit == "month":
                parsed = _add_months(today, -count)
                desc = f"{count} month(s) ago"
            elif unit == "year":
                parsed = today.replace(year=today.year - count)
                desc = f"{count} year(s) ago"

    # --- "a week from now", "a month from now" ---
    if parsed is None:
        m = re.match(r"an?\s+(\w+)\s+from\s+(?:now|today)", expr)
        if m:
            unit = m.group(1)
            if unit == "week":
                parsed = today + timedelta(weeks=1)
                desc = "a week from now"
            elif unit == "month":
                parsed = _add_months(today, 1)
                desc = "a month from now"
            elif unit == "year":
                parsed = today.replace(year=today.year + 1)
                desc = "a year from now"

    # --- "next weekday" / "next business day" ---
    if parsed is None:
        if expr in ("next weekday", "next business day", "next workday"):
            d = today + timedelta(days=1)
            while d.weekday() >= 5:
                d += timedelta(days=1)
            parsed = d
            desc = "next business day"

    # --- Bare weekday name = next occurrence ---
    if parsed is None:
        if expr in WEEKDAYS:
            parsed = _next_weekday(WEEKDAYS[expr], today)
            desc = f"next {expr}"

    # --- "<month> <day>" or "<day> <month>" e.g. "march 15" or "15 march" ---
    if parsed is None:
        m = re.match(r"(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?$", expr)
        if m and m.group(1) in MONTH_NAMES:
            month = MONTH_NAMES[m.group(1)]
            day = int(m.group(2))
            year = int(m.group(3)) if m.group(3) else today.year
            try:
                candidate = datetime(year, month, day)
                # If no year specified and date is past, use next year
                if not m.group(3) and candidate.date() < today.date():
                    candidate = datetime(year + 1, month, day)
                parsed = candidate
                desc = f"{m.group(1).title()} {day}, {candidate.year}"
            except ValueError:
                pass

    if parsed is None:
        m = re.match(r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(\w+)(?:\s*,?\s*(\d{4}))?$", expr)
        if m and m.group(2) in MONTH_NAMES:
            day = int(m.group(1))
            month = MONTH_NAMES[m.group(2)]
            year = int(m.group(3)) if m.group(3) else today.year
            try:
                candidate = datetime(year, month, day)
                if not m.group(3) and candidate.date() < today.date():
                    candidate = datetime(year + 1, month, day)
                parsed = candidate
                desc = f"{m.group(2).title()} {day}, {candidate.year}"
            except ValueError:
                pass

    # --- ISO date string passthrough: "2026-03-15" ---
    if parsed is None:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", expr)
        if m:
            try:
                parsed = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                desc = "ISO date"
            except ValueError:
                pass

    # --- Build result ---
    if parsed is None:
        return {"error": f"Could not parse: '{expression}'"}

    result_date = parsed.date() if isinstance(parsed, datetime) else parsed
    result = {
        "date": result_date.isoformat(),
        "day_of_week": result_date.strftime("%A"),
        "expression": expression,
        "description": desc,
        "days_from_today": (result_date - today.date()).days,
    }

    # Warn if the expression contained time info that was stripped or ignored
    if has_time_suffix:
        result["warning"] = "Time component detected but ignored (date-only resolver)"
    else:
        time_keywords = ["at ", " am", " pm", "noon", "midnight", "o'clock"]
        if any(kw in expression.lower() for kw in time_keywords):
            result["warning"] = "Time component detected but ignored (date-only resolver)"

    return result



def get_weekday(date_str: str) -> dict:
    """Get the day of week for a date string."""
    try:
        dt = datetime.fromisoformat(date_str)
        return {
            "date": dt.date().isoformat(),
            "day_of_week": dt.strftime("%A"),
            "day_number": dt.weekday(),
            "is_weekend": dt.weekday() >= 5,
            "is_weekday": dt.weekday() < 5,
        }
    except ValueError:
        return {"error": f"Invalid date format: '{date_str}', expected YYYY-MM-DD"}


def show_calendar(month: int | None = None, year: int | None = None) -> str:
    """Show a formatted calendar for a month."""
    now = datetime.now()
    month = month or now.month
    year = year or now.year
    cal = calendar.TextCalendar(firstweekday=calendar.SUNDAY)
    return cal.formatmonth(year, month)


def relative_description(date_str: str) -> dict:
    """Describe a date relative to today."""
    try:
        dt = datetime.fromisoformat(date_str).date()
    except ValueError:
        return {"error": f"Invalid date format: '{date_str}', expected YYYY-MM-DD"}

    today = datetime.now().date()
    delta = (dt - today).days

    if delta == 0:
        human = "today"
    elif delta == 1:
        human = "tomorrow"
    elif delta == -1:
        human = "yesterday"
    elif delta > 0:
        weeks, days = divmod(delta, 7)
        parts = []
        if weeks:
            parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        human = f"in {' and '.join(parts)}"
    else:
        abs_delta = abs(delta)
        weeks, days = divmod(abs_delta, 7)
        parts = []
        if weeks:
            parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        human = f"{' and '.join(parts)} ago"

    # Count business days
    bdays = 0
    d = min(today, dt)
    end = max(today, dt)
    while d < end:
        if d.weekday() < 5:
            bdays += 1
        d += timedelta(days=1)

    return {
        "date": dt.isoformat(),
        "day_of_week": dt.strftime("%A"),
        "days_from_today": delta,
        "business_days": bdays if delta >= 0 else -bdays,
        "human_readable": human,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Resolve natural language dates (stdlib only)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # resolve
    p_resolve = sub.add_parser("resolve", help="Resolve a date expression")
    p_resolve.add_argument("expression", help="e.g. 'next wednesday', 'in 3 days'")

    # weekday
    p_wd = sub.add_parser("weekday", help="Day of week for a date")
    p_wd.add_argument("date", help="YYYY-MM-DD")

    # calendar
    p_cal = sub.add_parser("calendar", help="Show month calendar")
    p_cal.add_argument("month", type=int, nargs="?", help="Month (1-12)")
    p_cal.add_argument("year", type=int, nargs="?", help="Year (e.g. 2026)")

    # relative
    p_rel = sub.add_parser("relative", help="Describe date relative to today")
    p_rel.add_argument("date", help="YYYY-MM-DD")

    args = parser.parse_args()

    if args.command == "resolve":
        result = resolve(args.expression)
        print(json.dumps(result, indent=2))
    elif args.command == "weekday":
        result = get_weekday(args.date)
        print(json.dumps(result, indent=2))
    elif args.command == "calendar":
        print(show_calendar(args.month, args.year))
    elif args.command == "relative":
        result = relative_description(args.date)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
