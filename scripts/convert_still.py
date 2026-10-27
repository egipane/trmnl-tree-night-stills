#!/usr/bin/env python3
"""Convert a source image into a Tree Night still.

Heroes (default) are the publish path. From the repo root:

    python3 scripts/convert_still.py path/to/source.png --month 10 --weather clear

That writes epaper/m10-clear-night.png as a 600×450 grayscale PNG
(Pillow mode L, 8-bit). May–Sep snow is rejected (months 05–09).

Optional moon JPEGs match the existing moons/ library (1024×1024 RGB):

    python3 scripts/convert_still.py path/to/source.jpg --kind moon --phase 04-full

This script does not write moons/alpha/ (those files are RGBA disks).
Pass --force to overwrite a file that already exists.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps, PngImagePlugin

REPO_ROOT = Path(__file__).resolve().parent.parent
HERO_SIZE = (600, 450)
MOON_SIZE = (1024, 1024)
WEATHERS = ("clear", "overcast", "rain", "snow")
SUMMER_MONTHS = (5, 6, 7, 8, 9)
MOON_PHASES = (
    "00-new",
    "01-waxing-crescent",
    "02-first-quarter",
    "03-waxing-gibbous",
    "04-full",
    "05-waning-gibbous",
    "06-last-quarter",
    "07-waning-crescent",
)
RESAMPLE = Image.Resampling.LANCZOS


def die(message: str, code: int = 1) -> None:
    print(f"convert_still: {message}", file=sys.stderr)
    raise SystemExit(code)


def flatten(im: Image.Image) -> Image.Image:
    """Drop alpha onto black so night art stays full-bleed."""
    has_alpha = "A" in im.getbands() or (
        im.mode == "P" and "transparency" in im.info
    )
    if has_alpha:
        rgba = im.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    if im.mode == "L":
        return im
    return im.convert("RGB")


def load_source(path: Path) -> Image.Image:
    if not path.is_file():
        die(f"source not found: {path}")
    try:
        with Image.open(path) as im:
            im.load()
            transposed = ImageOps.exif_transpose(im)
            return flatten(transposed).copy()
    except Image.DecompressionBombError:
        die(f"source image is too large: {path}")
    except Exception as exc:
        die(f"could not read {path}: {exc}")


def fit_image(im: Image.Image, size: tuple[int, int], fit: str) -> Image.Image:
    target_w, target_h = size
    if im.size == size:
        return im
    source_w, source_h = im.size
    if source_w < 1 or source_h < 1:
        die("source image has a zero dimension")

    if fit == "stretch":
        return im.resize(size, RESAMPLE)

    if fit == "cover":
        scale = max(target_w / source_w, target_h / source_h)
        resized_w = max(target_w, round(source_w * scale))
        resized_h = max(target_h, round(source_h * scale))
        resized = im.resize((resized_w, resized_h), RESAMPLE)
        left = max(0, (resized_w - target_w) // 2)
        top = max(0, (resized_h - target_h) // 2)
        left = min(left, resized_w - target_w)
        top = min(top, resized_h - target_h)
        return resized.crop((left, top, left + target_w, top + target_h))

    if fit == "contain":
        scale = min(target_w / source_w, target_h / source_h)
        resized_w = max(1, min(target_w, round(source_w * scale)))
        resized_h = max(1, min(target_h, round(source_h * scale)))
        resized = im.resize((resized_w, resized_h), RESAMPLE)
        pad = 0 if im.mode == "L" else (0, 0, 0)
        canvas = Image.new(im.mode, size, pad)
        left = (target_w - resized_w) // 2
        top = (target_h - resized_h) // 2
        canvas.paste(resized, (left, top))
        return canvas

    die(f"unknown fit: {fit}")


def posterize_16(im: Image.Image) -> Image.Image:
    """Map 8-bit gray onto 16 display levels (0, 17, …, 255)."""
    lut = []
    for value in range(256):
        level = int(round(value * 15 / 255.0))
        lut.append(int(round(level * 255 / 15.0)))
    return im.point(lut)


def hero_filename(month: int, weather: str) -> str:
    return f"m{month:02d}-{weather}-night.png"


def destination_for(args: argparse.Namespace) -> Path:
    if args.output is not None:
        return args.output
    if args.kind == "hero":
        out_dir = args.out_dir if args.out_dir is not None else REPO_ROOT / "epaper"
        return out_dir / hero_filename(args.month, args.weather)
    out_dir = args.out_dir if args.out_dir is not None else REPO_ROOT / "moons"
    return out_dir / f"{args.phase}.jpg"


def require_suffix(dest: Path, kind: str) -> None:
    suffix = dest.suffix.lower()
    if kind == "hero" and suffix != ".png":
        die(f"hero output must end in .png: {dest}", code=2)
    if kind == "moon" and suffix not in (".jpg", ".jpeg"):
        die(f"moon output must end in .jpg: {dest}", code=2)


def refuse_alpha(dest: Path) -> None:
    alpha = (REPO_ROOT / "moons" / "alpha").resolve()
    resolved = dest.resolve()
    if resolved == alpha or alpha in resolved.parents:
        die("refusing to write under moons/alpha/ (RGBA disks are a separate set)")


def is_proof(dest: Path) -> bool:
    return "fixtures" in dest.parts or dest.name.startswith("PROOF")


def convert(source: Image.Image, args: argparse.Namespace) -> Image.Image:
    if args.kind == "hero":
        fitted = fit_image(source, HERO_SIZE, args.fit)
        gray = fitted if fitted.mode == "L" else fitted.convert("L")
        if args.posterize_16:
            gray = posterize_16(gray)
        return gray
    fitted = fit_image(source, MOON_SIZE, args.fit)
    if fitted.mode != "RGB":
        fitted = fitted.convert("RGB")
    return fitted


def verify(path: Path, kind: str) -> str:
    with Image.open(path) as check:
        check.load()
        if kind == "hero":
            if check.size != HERO_SIZE or check.mode != "L":
                path.unlink(missing_ok=True)
                die(
                    f"verification failed for {path}: "
                    f"got {check.size[0]}x{check.size[1]} {check.mode}, "
                    "expected 600x450 L"
                )
            return f"{check.size[0]}x{check.size[1]} {check.mode}"
        if check.size != MOON_SIZE or check.mode != "RGB":
            path.unlink(missing_ok=True)
            die(
                f"verification failed for {path}: "
                f"got {check.size[0]}x{check.size[1]} {check.mode}, "
                "expected 1024x1024 RGB"
            )
        return f"{check.size[0]}x{check.size[1]} {check.mode}"


def write_image(image: Image.Image, dest: Path, kind: str) -> None:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        die(f"could not create output directory {dest.parent}: {exc}")
    if kind == "hero":
        pnginfo = None
        if is_proof(dest):
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text(
                "Description",
                "Pipeline proof only. Not a TRMNL Liquid still.",
            )
        image.save(dest, format="PNG", optimize=True, pnginfo=pnginfo)
        return
    image.save(dest, format="JPEG", quality=90, optimize=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a source image into a Tree Night e-paper hero "
            "(600×450 grayscale PNG) or an optional moon JPEG."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 scripts/convert_still.py source.png --month 10 --weather clear\n"
            "  python3 scripts/convert_still.py source.png --month 1 --weather snow --fit contain\n"
            "  python3 scripts/convert_still.py source.jpg --kind moon --phase 04-full\n"
            "  python3 scripts/convert_still.py source.png --output scripts/fixtures/PROOF-hero-pipeline.png\n"
        ),
    )
    parser.add_argument("source", type=Path, help="source image path")
    parser.add_argument(
        "--kind",
        choices=("hero", "moon"),
        default="hero",
        help="hero writes a 600×450 L PNG (default); moon writes a 1024×1024 RGB JPEG",
    )
    parser.add_argument("--month", type=int, help="hero month 1–12 (zero-padded in the filename)")
    parser.add_argument(
        "--weather",
        choices=WEATHERS,
        help="hero weather: clear, overcast, rain, or snow",
    )
    parser.add_argument(
        "--phase",
        choices=MOON_PHASES,
        help="moon filename stem, for example 04-full",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="output directory (default: epaper/ for heroes, moons/ for moons)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="exact output path; overrides --month/--weather/--phase/--out-dir for the filename",
    )
    parser.add_argument(
        "--fit",
        choices=("cover", "contain", "stretch"),
        default="cover",
        help="cover center-crops (default), contain letterboxes on black, stretch resizes exactly",
    )
    parser.add_argument(
        "--posterize-16",
        action="store_true",
        help="heroes only: quantize gray to 16 levels after the L convert (off by default)",
    )
    parser.add_argument(
        "--allow-summer-snow",
        action="store_true",
        help="allow a snow hero in May–Sep (Liquid does not request those files)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the destination if it already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="convert in memory and print the destination without writing",
    )
    return parser


def validate(args: argparse.Namespace) -> None:
    if args.kind == "hero":
        needs_name = args.output is None
        if needs_name and (args.month is None or args.weather is None):
            die("heroes need --month and --weather, or pass --output", code=2)
        if args.month is not None and not 1 <= args.month <= 12:
            die("--month must be 1–12", code=2)
        if (
            args.weather == "snow"
            and args.month in SUMMER_MONTHS
            and not args.allow_summer_snow
        ):
            die(
                f"May–Sep have no snow still (month {args.month:02d}). "
                "Liquid falls back to overcast. Pass --allow-summer-snow to override.",
                code=2,
            )
        if args.phase is not None:
            die("--phase is only used with --kind moon", code=2)
        return

    if args.posterize_16:
        die("--posterize-16 applies to heroes only", code=2)
    if args.output is None and args.phase is None:
        die("moons need --phase, or pass --output", code=2)
    if args.month is not None or args.weather is not None:
        die("--month and --weather are only used with --kind hero", code=2)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate(args)
    dest = destination_for(args)
    require_suffix(dest, args.kind)
    refuse_alpha(dest)
    source = load_source(args.source)
    image = convert(source, args)
    summary = (
        f"{image.size[0]}x{image.size[1]} {image.mode}"
    )
    if args.dry_run:
        note = ""
        if dest.exists():
            note = "; destination exists, --force required to overwrite"
        print(f"dry-run: would write {dest} ({summary}){note}")
        return 0
    if dest.exists() and not args.force:
        die(f"destination exists (pass --force to overwrite): {dest}")
    write_image(image, dest, args.kind)
    verified = verify(dest, args.kind)
    print(f"wrote {dest} {verified}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
