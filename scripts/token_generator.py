#!/usr/bin/env python3
"""Generate platform-specific design tokens from CSV data."""

import argparse
import json
import sys

from core import get_by_app_type, load_csv


def _hex_to_argb(hex_color: str) -> str:
    """Convert #RRGGBB to 0xFFRRGGBB format for Dart."""
    h = hex_color.lstrip("#")
    return f"0xFF{h.upper()}"


def _tokens_by_category(tokens: list[dict], category: str) -> list[dict]:
    """Filter tokens by category."""
    return [t for t in tokens if t["Category"] == category]


def generate_flutter(colors: dict, tokens: list[dict]) -> dict:
    """Generate Dart code snippets for Flutter."""
    color_fields = []
    for role in ["Primary", "Secondary", "Accent", "Background", "Surface", "Error", "On_Primary", "On_Secondary"]:
        val = colors.get(role, "#000000")
        field_name = role.lower().replace("on_", "on")
        color_fields.append(f"  static const Color {field_name} = Color({_hex_to_argb(val)});")
    app_colors = "class AppColors {\n  AppColors._();\n\n" + "\n".join(color_fields) + "\n}"

    spacing_fields = []
    for t in _tokens_by_category(tokens, "spacing"):
        name = t["Token_Name"].replace("spacing_", "")
        # Dart identifiers can't start with a digit
        if name[0].isdigit():
            name = f"x{name}"
        spacing_fields.append(f"  static const double {name} = {t['Value']};")
    app_spacing = "class AppSpacing {\n  AppSpacing._();\n\n" + "\n".join(spacing_fields) + "\n}"

    radius_fields = []
    for t in _tokens_by_category(tokens, "radius"):
        name = t["Token_Name"].replace("radius_", "")
        radius_fields.append(f"  static const double {name} = {t['Value']};")
    app_radius = "class AppRadius {\n  AppRadius._();\n\n" + "\n".join(radius_fields) + "\n}"

    duration_fields = []
    for t in _tokens_by_category(tokens, "duration"):
        name = t["Token_Name"].replace("duration_", "")
        ms = t["Value"].replace("ms", "")
        duration_fields.append(f"  static const Duration {name} = Duration(milliseconds: {ms});")
    app_duration = "class AppDuration {\n  AppDuration._();\n\n" + "\n".join(duration_fields) + "\n}"

    primary = _hex_to_argb(colors.get("Primary", "#000000"))
    secondary = _hex_to_argb(colors.get("Secondary", "#000000"))
    background = _hex_to_argb(colors.get("Background", "#FFFFFF"))
    surface = _hex_to_argb(colors.get("Surface", "#FFFFFF"))
    error = _hex_to_argb(colors.get("Error", "#DC2626"))
    theme = f"""ThemeData appTheme() {{
  return ThemeData(
    colorScheme: const ColorScheme.light(
      primary: Color({primary}),
      secondary: Color({secondary}),
      surface: Color({surface}),
      error: Color({error}),
    ),
    scaffoldBackgroundColor: const Color({background}),
    useMaterial3: true,
  );
}}"""

    return {
        "platform": "flutter",
        "files": {
            "app_colors.dart": app_colors,
            "app_spacing.dart": app_spacing,
            "app_radius.dart": app_radius,
            "app_duration.dart": app_duration,
            "app_theme.dart": theme,
        },
    }


def generate_android(colors: dict, tokens: list[dict]) -> dict:
    """Generate Android XML resource snippets."""
    color_lines = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]
    for role in ["Primary", "Secondary", "Accent", "Background", "Surface", "Error", "On_Primary", "On_Secondary"]:
        val = colors.get(role, "#000000")
        name = f"color_{role.lower()}"
        color_lines.append(f'    <color name="{name}">{val}</color>')
    color_lines.append("</resources>")
    colors_xml = "\n".join(color_lines)

    dimen_lines = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]
    for t in _tokens_by_category(tokens, "spacing"):
        dimen_lines.append(f'    <dimen name="{t["Token_Name"]}">{t["Value"]}dp</dimen>')
    for t in _tokens_by_category(tokens, "radius"):
        dimen_lines.append(f'    <dimen name="{t["Token_Name"]}">{t["Value"]}dp</dimen>')
    dimen_lines.append("</resources>")
    dimens_xml = "\n".join(dimen_lines)

    primary = colors.get("Primary", "#000000")
    secondary = colors.get("Secondary", "#000000")
    background = colors.get("Background", "#FFFFFF")
    themes_xml = f"""<style name="Theme.App" parent="Theme.Material3.Light.NoActionBar">
    <item name="colorPrimary">{primary}</item>
    <item name="colorSecondary">{secondary}</item>
    <item name="android:colorBackground">{background}</item>
    <item name="colorError">#DC2626</item>
</style>"""

    return {
        "platform": "android",
        "files": {
            "colors.xml": colors_xml,
            "dimens.xml": dimens_xml,
            "themes.xml": themes_xml,
        },
    }


def generate_ios(colors: dict, tokens: list[dict]) -> dict:
    """Generate Swift code snippets for iOS."""
    color_lines = ["import UIKit", "", "extension UIColor {"]
    for role in ["Primary", "Secondary", "Accent", "Background", "Surface", "Error", "On_Primary", "On_Secondary"]:
        val = colors.get(role, "#000000").lstrip("#")
        name = role[0].lower() + role[1:] if not role.startswith("On_") else "on" + role[3:]
        r, g, b = int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16)
        color_lines.append(
            f"    static let app{name.capitalize()} = UIColor("
            f"red: {r}/255, green: {g}/255, blue: {b}/255, alpha: 1)"
        )
    color_lines.append("}")
    color_swift = "\n".join(color_lines)

    spacing_lines = ["import UIKit", "", "enum AppSpacing {"]
    for t in _tokens_by_category(tokens, "spacing"):
        name = t["Token_Name"].replace("spacing_", "")
        spacing_lines.append(f"    static let {name}: CGFloat = {t['Value']}")
    spacing_lines.append("}")
    spacing_swift = "\n".join(spacing_lines)

    radius_lines = ["import UIKit", "", "enum AppRadius {"]
    for t in _tokens_by_category(tokens, "radius"):
        name = t["Token_Name"].replace("radius_", "")
        radius_lines.append(f"    static let {name}: CGFloat = {t['Value']}")
    radius_lines.append("}")
    radius_swift = "\n".join(radius_lines)

    return {
        "platform": "ios",
        "files": {
            "Color+App.swift": color_swift,
            "Spacing.swift": spacing_swift,
            "BorderRadius.swift": radius_swift,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate platform-specific design tokens")
    parser.add_argument("--platform", required=True, choices=["flutter", "android", "ios"])
    parser.add_argument("--app-type", required=True, help="App type from mobile-app-types.csv")
    args = parser.parse_args()

    colors = get_by_app_type(args.app_type, "colors")
    if not colors:
        print(json.dumps({"error": f"No color data found for app type '{args.app_type}'"}))
        sys.exit(1)

    tokens = load_csv("platform-tokens.csv")

    generators = {
        "flutter": generate_flutter,
        "android": generate_android,
        "ios": generate_ios,
    }
    result = generators[args.platform](colors, tokens)
    result["app_type"] = args.app_type
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
