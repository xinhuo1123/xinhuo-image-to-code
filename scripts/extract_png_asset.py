#!/usr/bin/env python3
"""Extract a PNG asset from a source image using an exact bounding box.

The output canvas is always exactly bbox width x bbox height. This script never
auto-trims transparent pixels.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract an exact-bbox PNG asset.")
    parser.add_argument("source", help="Source screenshot/design image")
    parser.add_argument("output", help="Output PNG path")
    parser.add_argument("--x", type=int, required=True, help="Source bbox x")
    parser.add_argument("--y", type=int, required=True, help="Source bbox y")
    parser.add_argument("--width", type=int, required=True, help="Source bbox width")
    parser.add_argument("--height", type=int, required=True, help="Source bbox height")
    parser.add_argument(
        "--remove-bg",
        choices=["none", "corners", "floodfill"],
        default="none",
        help="Remove solid background while preserving canvas size.",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=14,
        help="RGB tolerance for background removal.",
    )
    parser.add_argument(
        "--bg",
        help="Explicit background color as hex, for example #f7f7f7. Defaults to corner sampling.",
    )
    parser.add_argument("--manifest", help="Optional JSON file to append/update asset metadata.")
    parser.add_argument("--id", help="Layer id for manifest output.")
    return parser.parse_args()


def parse_hex_color(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"Invalid hex color: {value}")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))


def color_distance_ok(pixel: tuple[int, int, int, int], bg: tuple[int, int, int], tolerance: int) -> bool:
    return all(abs(int(pixel[i]) - int(bg[i])) <= tolerance for i in range(3))


def corner_background(image) -> tuple[int, int, int]:
    pixels = image.load()
    points = [
        pixels[0, 0],
        pixels[image.width - 1, 0],
        pixels[0, image.height - 1],
        pixels[image.width - 1, image.height - 1],
    ]
    rgb = [p[:3] for p in points]
    return tuple(sorted(channel)[len(channel) // 2] for channel in zip(*rgb))


def remove_bg_corners(image, bg: tuple[int, int, int], tolerance: int):
    out = image.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            pixel = pixels[x, y]
            if color_distance_ok(pixel, bg, tolerance):
                pixels[x, y] = (pixel[0], pixel[1], pixel[2], 0)
    return out


def remove_bg_floodfill(image, bg: tuple[int, int, int], tolerance: int):
    out = image.copy()
    pixels = out.load()
    seen = set()
    queue = deque(
        [
            (0, 0),
            (out.width - 1, 0),
            (0, out.height - 1),
            (out.width - 1, out.height - 1),
        ]
    )
    while queue:
        x, y = queue.popleft()
        if (x, y) in seen or x < 0 or y < 0 or x >= out.width or y >= out.height:
            continue
        seen.add((x, y))
        pixel = pixels[x, y]
        if not color_distance_ok(pixel, bg, tolerance):
            continue
        pixels[x, y] = (pixel[0], pixel[1], pixel[2], 0)
        queue.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return out


def update_manifest(path: Path, item: dict) -> None:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Manifest must be a JSON list.")
    else:
        data = []
    data = [entry for entry in data if entry.get("id") != item["id"]]
    data.append(item)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("Missing dependency: install Pillow.", file=sys.stderr)
        return 2

    source = Image.open(args.source).convert("RGBA")
    if args.x < 0 or args.y < 0 or args.width <= 0 or args.height <= 0:
        print("Invalid bbox.", file=sys.stderr)
        return 2
    if args.x + args.width > source.width or args.y + args.height > source.height:
        print("Bbox exceeds source image bounds.", file=sys.stderr)
        return 2

    asset = source.crop((args.x, args.y, args.x + args.width, args.y + args.height))
    bg = parse_hex_color(args.bg) if args.bg else corner_background(asset)

    if args.remove_bg == "corners":
        asset = remove_bg_corners(asset, bg, args.tolerance)
    elif args.remove_bg == "floodfill":
        asset = remove_bg_floodfill(asset, bg, args.tolerance)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    asset.save(output)

    if asset.size != (args.width, args.height):
        print("Internal error: output size changed.", file=sys.stderr)
        return 1

    if args.manifest:
        layer_id = args.id or output.stem
        update_manifest(
            Path(args.manifest),
            {
                "id": layer_id,
                "type": "bitmap",
                "source_bbox": {
                    "x": args.x,
                    "y": args.y,
                    "width": args.width,
                    "height": args.height,
                },
                "asset": str(output),
                "transparent_required": args.remove_bg != "none",
            },
        )

    print(f"wrote {output} size={asset.width}x{asset.height} remove_bg={args.remove_bg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
