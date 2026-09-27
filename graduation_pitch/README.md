# FarmTrust Graduation Materials

Graduation book and pitch deck sources for FarmTrust, plus the scripts that generate their figures and deliverables.

## Structure

| Path | Purpose | Tracked |
| --- | --- | --- |
| `book/` | Book sources: chapters, front matter, figures, and generation scripts. | yes |
| `presentation/` | Self-contained HTML pitch deck, its assets, narration scripts, and PDF export script. | yes |
| `outputs/` | Generated deliverables (DOCX, PDF, PPTX) and rendered previews. | no (gitignored) |

## Build The Graduation Book

```powershell
cd book
python generate_graduation_book.py
```

Deliverables land under `outputs/book/`; rendered QA previews under `outputs/previews/`. Both are gitignored, so a clean clone regenerates them rather than storing them.

## Regenerate Figures

```powershell
cd book
python generate_diagram_assets.py
```

Writes the thesis-styled diagrams (`fig01`–`fig15`, `satellite_to_decisions`) into `book/assets/`.

## Present The Pitch Deck

Open `presentation/farmtrust_deck.html` directly in a browser — no build step. To export a PDF:

```powershell
cd presentation
.\scripts\render_deck.ps1
```

See `presentation/README.md` for details.
