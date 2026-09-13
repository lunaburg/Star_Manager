"""Prepare a square PNG texture for SB3Utility.

The Workbench UI provides the interactive version of this workflow. This CLI
is useful when a known crop must be repeated or automated.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps


MIN_RESOLUTION = 64
MAX_RESOLUTION = 4096


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop an image to 1:1, resize it, and export an SB3Utility-ready PNG."
    )
    parser.add_argument("source", type=Path, help="Source PNG, JPG, or WebP image")
    parser.add_argument("output", type=Path, help="Destination .png path")
    parser.add_argument(
        "--crop",
        nargs=3,
        type=int,
        metavar=("X", "Y", "SIZE"),
        help="Square crop in source pixels; defaults to the largest centered square",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=1024,
        help=f"Square output size in pixels ({MIN_RESOLUTION}-{MAX_RESOLUTION}, default: 1024)",
    )
    parser.add_argument(
        "--keep-color",
        action="store_true",
        help="Keep the original color instead of producing a white neutral texture",
    )
    parser.add_argument(
        "--strength",
        type=float,
        default=1.25,
        help="Pure-texture detail strength (0.5-2.5, default: 1.25)",
    )
    return parser.parse_args()


def resolve_crop(image: Image.Image, crop: list[int] | None) -> tuple[int, int, int, int]:
    if crop is None:
        size = min(image.width, image.height)
        left = (image.width - size) // 2
        top = (image.height - size) // 2
        return left, top, left + size, top + size

    left, top, size = crop
    if size <= 0 or left < 0 or top < 0:
        raise ValueError("crop coordinates must be non-negative and SIZE must be positive")
    if left + size > image.width or top + size > image.height:
        raise ValueError(
            f"crop {left},{top},{size} exceeds source dimensions {image.width}x{image.height}"
        )
    return left, top, left + size, top + size


def make_pure_texture(image: Image.Image, strength: float) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    blur_radius = max(3.0, image.width * 0.018)
    local_tone = grayscale.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    scale = 1.0 / (strength * 1.75)
    neutral = ImageChops.subtract(grayscale, local_tone, scale=scale, offset=248)
    return neutral.convert("RGBA")


def process_texture(
    source_path: Path,
    output_path: Path,
    crop: list[int] | None,
    resolution: int,
    keep_color: bool,
    strength: float,
) -> tuple[int, int, int, int]:
    if not MIN_RESOLUTION <= resolution <= MAX_RESOLUTION:
        raise ValueError(f"resolution must be between {MIN_RESOLUTION} and {MAX_RESOLUTION}")
    if not 0.5 <= strength <= 2.5:
        raise ValueError("strength must be between 0.5 and 2.5")
    if output_path.suffix.lower() != ".png":
        raise ValueError("output path must end with .png")

    with Image.open(source_path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        crop_box = resolve_crop(image, crop)
        resized = image.crop(crop_box).resize(
            (resolution, resolution),
            Image.Resampling.LANCZOS,
        )
        output = resized if keep_color else make_pure_texture(resized, strength)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output.save(output_path, format="PNG", optimize=True)
        return crop_box


def main() -> int:
    args = parse_args()
    try:
        crop_box = process_texture(
            source_path=args.source.resolve(),
            output_path=args.output.resolve(),
            crop=args.crop,
            resolution=args.resolution,
            keep_color=args.keep_color,
            strength=args.strength,
        )
    except (OSError, ValueError) as error:
        raise SystemExit(f"Texture processing failed: {error}") from error

    mode = "original color" if args.keep_color else "pure white texture"
    print(
        f"Saved {args.resolution}x{args.resolution} {mode} PNG to {args.output.resolve()} "
        f"from crop {crop_box[0]},{crop_box[1]},{crop_box[2] - crop_box[0]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
