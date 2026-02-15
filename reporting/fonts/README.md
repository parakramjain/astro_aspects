# Fonts for PDF generation

The PDF renderer requires embedded fonts that support Hindi (Devanagari) and Latin text.

**Do not commit the font binaries** (`.ttf`) to the repository unless you have explicit permission to do so.
This folder is intentionally kept in git via `.gitkeep`.

## Required files

Copy these four `.ttf` files into this folder:

- `NotoSansDevanagari-Regular.ttf`
- `NotoSansDevanagari-Bold.ttf`
- `NotoSans-Regular.ttf`
- `NotoSans-Bold.ttf`

## Where to download

You can obtain these fonts from official Noto/Google sources:

1) **Google Fonts (easy):**
   - Noto Sans Devanagari: https://fonts.google.com/noto/specimen/Noto+Sans+Devanagari
   - Noto Sans: https://fonts.google.com/noto/specimen/Noto+Sans

   On each page, click **Download family**, unzip, then copy the matching `.ttf` files.

2) **Noto Fonts on GitHub (official source):**
   - https://github.com/notofonts

   Navigate to the Noto Sans Devanagari and Noto Sans projects and download the `.ttf` assets.

## Installation steps (Windows)

1) Download the font family zip(s) (see links above).
2) Unzip.
3) Find the exact `.ttf` filenames listed in **Required files**.
4) Copy them into:
   - `reporting/fonts/`
5) Re-run PDF generation.

## Verify

From the repo root:

```powershell
Get-ChildItem .\reporting\fonts\*.ttf
```

Then:

```powershell
C:/Users/parak/Documents/Parakram/astro_project/astro_aspects/venv/Scripts/python.exe -m reporting.cli --input "output\Riya__1993-02-20__1W__2026-01-16.json" --report-type WEEKLY --language HI --out out
```

## Alternative: configure absolute paths

If you prefer not to copy files into the repo, set these fields in `ReportConfig`:

- `noto_sans_devanagari_regular_path`
- `noto_sans_devanagari_bold_path`
- `noto_sans_regular_path`
- `noto_sans_bold_path`
