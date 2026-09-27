"""Generate thesis-ready diagram assets for the FarmTrust graduation book."""

from __future__ import annotations

import math
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

INK = "#1f312f"
MUTED = "#5f6f6c"
GRID = "#c8d1cd"
TEAL = "#0f766e"
BLUE = "#426b94"
WHITE = "#ffffff"


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


TITLE = font(36, bold=True)
BODY = font(24)
NOTE = font(24)
SMALL = font(21)
DATA_TITLE = font(30, bold=True)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrapped_lines(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if text_size(draw, candidate, fnt)[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    subtitle: str | None = None,
    *,
    title_font: ImageFont.ImageFont = TITLE,
    subtitle_font: ImageFont.ImageFont = BODY,
) -> None:
    x1, y1, x2, y2 = box
    max_width = x2 - x1 - 42
    lines: list[tuple[str, ImageFont.ImageFont, str, int]] = []
    for line in wrapped_lines(draw, title, title_font, max_width):
        lines.append((line, title_font, INK, 10))
    if subtitle:
        for line in wrapped_lines(draw, subtitle, subtitle_font, max_width):
            lines.append((line, subtitle_font, MUTED, 5))
    total_height = sum(int(getattr(fnt, "size", 24) * 1.05) + gap for _, fnt, _, gap in lines) - (lines[-1][3] if lines else 0)
    y = y1 + ((y2 - y1) - total_height) / 2
    for line, fnt, color, gap in lines:
        w, h = text_size(draw, line, fnt)
        draw.text((x1 + ((x2 - x1) - w) / 2, y), line, fill=color, font=fnt)
        y += int(getattr(fnt, "size", 24) * 1.05) + gap


def box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    subtitle: str | None,
    *,
    outline: str = TEAL,
    width: int = 4,
    title_font: ImageFont.ImageFont = TITLE,
    subtitle_font: ImageFont.ImageFont = BODY,
) -> None:
    draw.rounded_rectangle(xy, radius=22, fill=WHITE, outline=outline, width=width)
    centered_text(draw, xy, title, subtitle, title_font=title_font, subtitle_font=subtitle_font)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    color: str = TEAL,
    width: int = 5,
) -> None:
    draw.line([start, end], fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 18
    left = (
        end[0] - size * math.cos(angle - math.pi / 6),
        end[1] - size * math.sin(angle - math.pi / 6),
    )
    right = (
        end[0] - size * math.cos(angle + math.pi / 6),
        end[1] - size * math.sin(angle + math.pi / 6),
    )
    draw.polygon([end, left, right], fill=color)


def routed_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    *,
    color: str = BLUE,
    width: int = 4,
) -> None:
    draw.line(points, fill=color, width=width, joint="curve")
    start = points[-2]
    end = points[-1]
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 17
    left = (
        end[0] - size * math.cos(angle - math.pi / 6),
        end[1] - size * math.sin(angle - math.pi / 6),
    )
    right = (
        end[0] - size * math.cos(angle + math.pi / 6),
        end[1] - size * math.sin(angle + math.pi / 6),
    )
    draw.polygon([end, left, right], fill=color)


def label(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, *, fnt: ImageFont.ImageFont = NOTE) -> None:
    draw.text((x, y), text, fill=MUTED, font=fnt)


def canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), WHITE)
    return image, ImageDraw.Draw(image)


def save(image: Image.Image, name: str) -> None:
    image.save(ASSETS_DIR / name, optimize=True)


def satellite_to_decisions() -> None:
    image, draw = canvas(1600, 500)
    boxes = [
        ((55, 105, 305, 295), "Land boundary", "Reviewer defines the parcel", TEAL),
        ((375, 105, 625, 295), "Satellite history", "Repeated Sentinel-2 observations", GRID),
        ((695, 105, 945, 295), "Activity evidence", "Cycles, gaps, indicators", GRID),
        ((1015, 105, 1265, 295), "Assessment report", "Status, confidence, watch items", TEAL),
        ((1335, 105, 1585, 295), "Human review", "Decision support, not approval", GRID),
    ]
    for xy, title, subtitle, color in boxes:
        box(draw, xy, title, subtitle, outline=color)
    for left, right in zip(boxes, boxes[1:]):
        arrow(draw, (left[0][2] + 12, 200), (right[0][0] - 14, 200), color=TEAL, width=5)
    draw.line((55, 365, 1585, 365), fill=GRID, width=2)
    label(draw, "The report preserves the chain from observed data to cautious interpretation.", 70, 402)
    save(image, "satellite_to_decisions.png")


def system_architecture() -> None:
    image, draw = canvas(1700, 700)
    label(draw, "Evidence creation stays separate from evidence explanation.", 70, 46)
    boxes = [
        ((70, 145, 335, 295), "Portal", "Land input, summary, report", TEAL),
        ((470, 145, 735, 295), "Backend service", "Jobs, data shaping, report access", TEAL),
        ((870, 145, 1135, 295), "Analysis worker", "Satellite pipeline and assessment", BLUE),
        ((1270, 145, 1535, 295), "Report surfaces", "Lender report and assistant", TEAL),
    ]
    for xy, title, subtitle, color in boxes:
        box(draw, xy, title, subtitle, outline=color)
    for left, right in zip(boxes, boxes[1:]):
        arrow(draw, (left[0][2] + 16, 220), (right[0][0] - 16, 220), color=TEAL if right[3] == TEAL else BLUE)
    artifact = (480, 430, 1220, 570)
    box(
        draw,
        artifact,
        "Stored evidence artifacts",
        "Source imagery, quality metrics, cycles, assessment, grounded report",
        outline=BLUE,
    )
    arrow(draw, (1000, 305), (905, 430), color=BLUE, width=4)
    arrow(draw, (1375, 305), (1110, 430), color=BLUE, width=4)
    save(image, "fig01_system_architecture.png")


def data_flow() -> None:
    image, draw = canvas(1600, 650)
    label(draw, "A conservative sequence from polygon to grounded report.", 60, 35)
    row1 = [
        ((70, 120, 330, 260), "Polygon", None, TEAL),
        ((450, 120, 710, 260), "Sentinel-2", None, TEAL),
        ((830, 120, 1090, 260), "Indices", None, BLUE),
        ((1210, 120, 1470, 260), "Smoothing", None, BLUE),
    ]
    row2 = [
        ((70, 380, 330, 520), "Activity cycles", None, BLUE),
        ((450, 380, 710, 520), "Assessment", None, TEAL),
        ((830, 380, 1090, 520), "Grounded report", None, TEAL),
        ((1210, 380, 1470, 520), "Assistant", None, TEAL),
    ]
    for items in (row1, row2):
        for xy, title, subtitle, color in items:
            box(draw, xy, title, subtitle, outline=color, title_font=DATA_TITLE)
        for left, right in zip(items, items[1:]):
            arrow(draw, (left[0][2] + 14, (left[0][1] + left[0][3]) // 2), (right[0][0] - 14, (right[0][1] + right[0][3]) // 2), color=TEAL)
    routed_arrow(draw, [(1340, 260), (1340, 315), (200, 315), (200, 380)], color=BLUE)
    draw.line((70, 575, 1470, 575), fill=GRID, width=2)
    label(draw, "Confidence and limitations travel with the evidence instead of being added at the end.", 85, 600, fnt=SMALL)
    save(image, "fig02_data_flow.png")


def evidence_read() -> None:
    image, draw = canvas(1550, 480)
    boxes = [
        ((70, 120, 390, 275), "Observed", "What the satellite and time series show", TEAL),
        ((485, 120, 805, 275), "Interpreted", "What the pattern cautiously means", BLUE),
        ((900, 120, 1220, 275), "Confidence", "How reliable the assessment is", BLUE),
        ((1315, 120, 1535, 275), "Watch", "What deserves human review", TEAL),
    ]
    for xy, title, subtitle, color in boxes:
        box(draw, xy, title, subtitle, outline=color)
    for left, right in zip(boxes, boxes[1:]):
        arrow(draw, (left[0][2] + 14, 198), (right[0][0] - 14, 198), color=BLUE if right[3] == BLUE else TEAL)
    draw.line((70, 350, 1535, 350), fill=GRID, width=2)
    label(
        draw,
        "Boundaries remain visible: no loan decision, yield estimate, pest diagnosis, crop proof, or legal survey.",
        85,
        385,
        fnt=SMALL,
    )
    save(image, "fig03_evidence_read.png")


def assistant_grounding() -> None:
    image, draw = canvas(1600, 720)
    left_top = (80, 130, 405, 285)
    left_bottom = (80, 430, 405, 585)
    center = (625, 275, 975, 445)
    right_top = (1195, 130, 1520, 285)
    right_bottom = (1195, 430, 1520, 585)
    box(draw, left_top, "Grounded report", "Evidence, confidence, boundaries", outline=TEAL)
    box(draw, left_bottom, "Curated field knowledge", "General agronomy context only", outline=GRID)
    box(draw, center, "Bounded prompt", "Answer from evidence; label unknowns", outline=BLUE)
    box(draw, right_top, "Narration", "Plain-language report readout", outline=TEAL)
    box(draw, right_bottom, "Q&A", "Questions over report evidence", outline=TEAL)
    arrow(draw, (405, 205), (625, 345), color=TEAL)
    arrow(draw, (405, 505), (625, 385), color=BLUE)
    arrow(draw, (975, 345), (1195, 205), color=TEAL)
    arrow(draw, (975, 385), (1195, 505), color=TEAL)
    draw.line((80, 645, 1520, 645), fill=GRID, width=2)
    label(draw, "Fallback: a rule-based summary remains available when the model is not configured.", 300, 670, fnt=SMALL)
    save(image, "fig04_assistant_grounding.png")


def main() -> None:
    ASSETS_DIR.mkdir(exist_ok=True)
    satellite_to_decisions()
    system_architecture()
    data_flow()
    evidence_read()
    assistant_grounding()


if __name__ == "__main__":
    main()
