#!/usr/bin/env python3
"""Generate a complete design system recommendation for a mobile app."""

import argparse
import json
import sys

from core import get_by_app_type, load_csv, search

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

PLATFORM_SM_KEYS = {
    "flutter": ("Recommended_SM_Flutter", "Alternative_SM_Flutter"),
    "android": ("Recommended_SM_Android", None),
    "ios": ("Recommended_SM_iOS", None),
}


def _resolve_app_type(raw: str) -> str:
    """Extract core app type keyword from a descriptive input like 'fintech app'."""
    valid_types = [
        "fintech", "social", "e-commerce", "health", "education",
        "enterprise", "entertainment", "news", "productivity", "travel",
    ]
    raw_lower = raw.lower()
    for t in valid_types:
        if t in raw_lower:
            return t
    return raw.strip()


def _find_app_type(app_type: str) -> tuple[dict | None, str | None]:
    """Find app type data; return (row, note). Note is set if fuzzy matched."""
    row = get_by_app_type(app_type, "app_type")
    if row:
        return row, None

    result = search(app_type, "app_type", max_results=1)
    matches = result.get("results", [])
    if matches:
        matched = matches[0]
        note = f"Exact match for '{app_type}' not found. Using closest match: **{matched['App_Type']}**"
        return matched, note

    return None, f"No match found for '{app_type}'"


def generate_report(app_type_raw: str, platform: str) -> str:
    """Generate a markdown design system report."""
    app_type = _resolve_app_type(app_type_raw)
    app_data, match_note = _find_app_type(app_type)

    lines = []

    if not app_data:
        return f"Error: {match_note}"

    resolved_type = app_data["App_Type"]

    lines.append(f"## Design System: {resolved_type.title()}")
    lines.append("")
    if match_note:
        lines.append(f"> {match_note}")
        lines.append("")

    # State Management
    lines.append("### Recommended State Management")
    lines.append("")
    primary_key, alt_key = PLATFORM_SM_KEYS.get(platform, ("Recommended_SM_Flutter", "Alternative_SM_Flutter"))
    primary_sm = app_data.get(primary_key, "N/A")
    lines.append(f"- **Primary:** {primary_sm} — recommended for {resolved_type} apps due to {app_data.get('Complexity', 'medium')} complexity")
    if alt_key:
        alt_sm = app_data.get(alt_key, "N/A")
        lines.append(f"- **Alternative:** {alt_sm} — use when team has existing expertise or for simpler feature modules")
    lines.append("")

    # Colors
    colors = get_by_app_type(resolved_type, "colors")
    if colors:
        lines.append("### Color Palette")
        lines.append("")
        lines.append("| Role | Value | Usage |")
        lines.append("|------|-------|-------|")
        color_roles = {
            "Primary": "Main brand color, app bars, primary buttons",
            "Secondary": "Secondary actions, accents on dark surfaces",
            "Accent": "CTAs, highlights, success indicators",
            "Background": "Page background",
            "Surface": "Cards, sheets, dialogs",
            "Error": "Error states, destructive actions",
            "On_Primary": "Text/icons on primary color",
            "On_Secondary": "Text/icons on secondary color",
        }
        for role, usage in color_roles.items():
            val = colors.get(role, "N/A")
            lines.append(f"| {role} | `{val}` | {usage} |")
        if colors.get("Notes"):
            lines.append(f"\n*{colors['Notes']}*")
        lines.append("")

    # Typography
    typo = get_by_app_type(resolved_type, "typography")
    if typo:
        lines.append("### Typography")
        lines.append("")
        font_key = {"flutter": "Flutter_Font", "android": "Android_Font", "ios": "iOS_Font"}.get(platform, "Flutter_Font")
        lines.append(f"- **Font:** {typo.get(font_key, 'N/A')} ({typo.get('Mood', '')})")
        lines.append(f"- **H1:** {typo.get('H1_Size', 'N/A')} | **H2:** {typo.get('H2_Size', 'N/A')} | **Body:** {typo.get('Body_Size', 'N/A')} | **Caption:** {typo.get('Caption_Size', 'N/A')}")
        if typo.get("Google_Fonts_URL"):
            lines.append(f"- **Google Fonts:** {typo['Google_Fonts_URL']}")
        lines.append("")

    # UX Guidelines
    ux_rows = load_csv("mobile-ux-guidelines.csv")
    relevant = [r for r in ux_rows if r["Platform"] in ("all", platform)]
    relevant.sort(key=lambda r: SEVERITY_ORDER.get(r.get("Severity", "low"), 3))
    top_ux = relevant[:5]
    if top_ux:
        lines.append("### Key UX Guidelines")
        lines.append("")
        for i, g in enumerate(top_ux, 1):
            lines.append(f"{i}. **[{g['Severity'].upper()}]** {g['Category']}: {g['Do']}")
            lines.append(f"   - Avoid: {g['Dont']}")
        lines.append("")

    # Architecture
    reasoning = get_by_app_type(resolved_type, "reasoning")
    if reasoning:
        lines.append("### Architecture Pattern")
        lines.append("")
        lines.append(f"- **Architecture:** {reasoning.get('Architecture', 'N/A')}")
        lines.append(f"- **Folder Structure:** `{reasoning.get('Folder_Structure', 'N/A')}`")
        lines.append(f"- **Key Patterns:** {reasoning.get('Key_Patterns', 'N/A')}")
        lines.append(f"- **Test Priority:** {reasoning.get('Test_Priority', 'N/A')}")
        lines.append("")

        # Anti-patterns
        anti = reasoning.get("Anti_Patterns", "")
        if anti:
            lines.append("### Anti-patterns to Avoid")
            lines.append("")
            for item in anti.split(", "):
                lines.append(f"- {item}")
            lines.append("")

    # Pre-flight Checklist
    lines.append("### Pre-flight Checklist")
    lines.append("")
    lines.append(f"- [ ] State management ({primary_sm}) is set up with proper DI")
    lines.append(f"- [ ] Color tokens applied from design system (not hardcoded hex values)")
    lines.append(f"- [ ] Typography scale configured with {typo.get(font_key, 'system font') if typo else 'system font'}")
    lines.append(f"- [ ] All touch targets meet 48dp minimum")
    lines.append(f"- [ ] Error handling follows domain layer pattern with sealed Result types")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate mobile design system recommendation")
    parser.add_argument("--app-type", required=True, help="App type (e.g. 'fintech', 'fintech app')")
    parser.add_argument("--platform", required=True, choices=["flutter", "android", "ios"])
    args = parser.parse_args()

    report = generate_report(args.app_type, args.platform)
    print(report)


if __name__ == "__main__":
    main()
