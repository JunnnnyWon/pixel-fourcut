from __future__ import annotations

from collections import deque
from functools import lru_cache
from pathlib import Path

from PIL import Image

from backend.config import FRAMES_FOLDER

CANVAS_SIZE = (1200, 1800)
TOP_SLOT = (130, 350, 940, 600)
BOTTOM_SLOT = (130, 1000, 940, 600)
DEFAULT_LAYOUT = {
    "original": {"scale": 1.0, "offset_x": 0, "offset_y": 0},
    "ai": {"scale": 1.0, "offset_x": 0, "offset_y": 0},
}


def list_frames() -> list[dict]:
    frames_dir = Path(FRAMES_FOLDER)
    if not frames_dir.exists():
        return []

    items = []
    for path in sorted(frames_dir.glob("frame-*.png")):
        frame_id = path.stem
        items.append(
            {
                "frame_id": frame_id,
                "filename": path.name,
                "label": frame_id.replace("frame-", "").replace("-", " ").title(),
                "path": str(path),
                "url": f"/api/frames/{frame_id}",
                "slots": get_frame_slots(path),
            }
        )
    return items


def get_frame_path(frame_id: str) -> Path | None:
    for item in list_frames():
        if item["frame_id"] == frame_id:
            return Path(item["path"])
    return None


def compose_print(
    original_path: Path,
    ai_path: Path,
    frame_path: Path,
    output_path: Path,
    layout: dict | None = None,
) -> Path:
    canvas = Image.new("RGBA", CANVAS_SIZE, (255, 255, 255, 255))
    original = Image.open(original_path).convert("RGBA")
    ai_result = Image.open(ai_path).convert("RGBA")
    frame = Image.open(frame_path).convert("RGBA")
    resolved_layout = normalize_layout(layout)
    slots = get_frame_slots(frame_path)

    if frame.size != CANVAS_SIZE:
        frame = frame.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)

    _paste_cover(canvas, original, slot_tuple(slots["original"]), resolved_layout["original"])
    _paste_cover(canvas, ai_result, slot_tuple(slots["ai"]), resolved_layout["ai"])
    composed = Image.alpha_composite(canvas, frame)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save(output_path)
    return output_path


def _paste_cover(
    canvas: Image.Image,
    image: Image.Image,
    slot: tuple[int, int, int, int],
    slot_layout: dict,
) -> None:
    x, y, width, height = slot
    scale = max(0.2, min(3.0, float(slot_layout.get("scale", 1.0))))
    offset_x = int(slot_layout.get("offset_x", 0))
    offset_y = int(slot_layout.get("offset_y", 0))
    base_width, base_height = _cover_size(image.size, width, height)

    resized = image.resize(
        (
            max(1, int(round(base_width * scale))),
            max(1, int(round(base_height * scale))),
        ),
        Image.Resampling.LANCZOS,
    )

    slot_canvas = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    paste_x = int(round((width - resized.width) / 2 + offset_x))
    paste_y = int(round((height - resized.height) / 2 + offset_y))
    slot_canvas.alpha_composite(resized, (paste_x, paste_y))
    canvas.alpha_composite(slot_canvas, (x, y))


def _cover_size(source_size: tuple[int, int], target_width: int, target_height: int) -> tuple[int, int]:
    source_width, source_height = source_size
    scale = max(target_width / source_width, target_height / source_height)
    return (
        max(1, int(round(source_width * scale))),
        max(1, int(round(source_height * scale))),
    )


def normalize_layout(layout: dict | None) -> dict:
    merged = {
        "original": dict(DEFAULT_LAYOUT["original"]),
        "ai": dict(DEFAULT_LAYOUT["ai"]),
    }
    if not layout:
        return merged

    for key in ("original", "ai"):
        values = layout.get(key) or {}
        merged[key]["scale"] = float(values.get("scale", merged[key]["scale"]))
        merged[key]["offset_x"] = int(values.get("offset_x", merged[key]["offset_x"]))
        merged[key]["offset_y"] = int(values.get("offset_y", merged[key]["offset_y"]))
    return merged


def slot_tuple(slot: dict) -> tuple[int, int, int, int]:
    return (int(slot["x"]), int(slot["y"]), int(slot["width"]), int(slot["height"]))


def get_frame_slots(frame_path: Path) -> dict:
    frame_path = Path(frame_path)
    if not frame_path.exists():
        return _default_slots()
    return _get_frame_slots_cached(str(frame_path), frame_path.stat().st_mtime_ns)


@lru_cache(maxsize=64)
def _get_frame_slots_cached(frame_path_str: str, mtime_ns: int) -> dict:
    del mtime_ns
    frame_path = Path(frame_path_str)
    image = Image.open(frame_path).convert("RGBA")
    alpha = image.getchannel("A")
    width, height = image.size
    pixels = alpha.load()
    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, tuple[int, int, int, int]]] = []

    for y in range(height):
        for x in range(width):
            if pixels[x, y] != 0 or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            min_x = max_x = x
            min_y = max_y = y
            touches_edge = x in {0, width - 1} or y in {0, height - 1}
            count = 0

            while queue:
                current_x, current_y = queue.popleft()
                count += 1
                min_x = min(min_x, current_x)
                max_x = max(max_x, current_x)
                min_y = min(min_y, current_y)
                max_y = max(max_y, current_y)

                for next_x, next_y in (
                    (current_x + 1, current_y),
                    (current_x - 1, current_y),
                    (current_x, current_y + 1),
                    (current_x, current_y - 1),
                ):
                    if 0 <= next_x < width and 0 <= next_y < height and pixels[next_x, next_y] == 0 and (next_x, next_y) not in seen:
                        seen.add((next_x, next_y))
                        queue.append((next_x, next_y))
                        if next_x in {0, width - 1} or next_y in {0, height - 1}:
                            touches_edge = True

            if not touches_edge:
                components.append((count, (min_x, min_y, max_x, max_y)))

    top_two = sorted(components, key=lambda item: item[0], reverse=True)[:2]
    if len(top_two) < 2:
        return _default_slots()

    top_two = sorted(top_two, key=lambda item: item[1][1])
    original = bbox_to_slot(top_two[0][1])
    ai = bbox_to_slot(top_two[1][1])
    return {"original": original, "ai": ai}


def bbox_to_slot(bbox: tuple[int, int, int, int]) -> dict:
    min_x, min_y, max_x, max_y = bbox
    return {
        "x": int(min_x),
        "y": int(min_y),
        "width": int(max_x - min_x + 1),
        "height": int(max_y - min_y + 1),
    }


def _default_slots() -> dict:
    return {
        "original": {"x": TOP_SLOT[0], "y": TOP_SLOT[1], "width": TOP_SLOT[2], "height": TOP_SLOT[3]},
        "ai": {"x": BOTTOM_SLOT[0], "y": BOTTOM_SLOT[1], "width": BOTTOM_SLOT[2], "height": BOTTOM_SLOT[3]},
    }
