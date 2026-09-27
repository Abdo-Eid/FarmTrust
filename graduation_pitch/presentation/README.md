# FarmTrust Pitch Deck

Self-contained HTML pitch deck for FarmTrust. No build step and no runtime dependencies — open `farmtrust_deck.html` in a browser and present.

## Contents

| Path | Purpose |
| --- | --- |
| `farmtrust_deck.html` | The deck. All slides, styles, and navigation in one file. |
| `FarmTrust_pitch_content.md` | English narrative and slide copy (source of truth for wording). |
| `FarmTrust_pitch_script_AR.md` | Arabic narration script. |
| `FarmTrust_technical_part.md` | Technical annex content. |
| `system_design_brief/` | System design brief bridging the product and the analysis visuals. |
| `assets/` | Slide imagery (case study, satellite, pivot, delta visuals). |
| `scripts/render_deck.ps1` | Optional PDF export. |

## Present

Open `farmtrust_deck.html` directly, or serve the folder:

```powershell
python -m http.server 8000
```

## Export To PDF

```powershell
.\scripts\render_deck.ps1
```

Writes `output/pdf/farmtrust_deck.pdf` plus a size-optimized `farmtrust_deck_compact.pdf`. Requires Chrome or Edge, Node.js, Python, and poppler (`pdfinfo`, `pdftoppm`). Intermediate files land in `tmp/`.

Both `output/` and `tmp/` are gitignored — generated artifacts are not stored. The deck is edited as HTML; re-export after changing it.

## Note

The graduation book is the sibling directory `graduation_pitch/book/`. An earlier PPTXGenJS-based deck under `graduation_book_python/presentation/` was retired in favour of this HTML deck.
