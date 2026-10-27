# Publish Tree Night stills

This repo is the public image host for Tree Night night art. A Cursor cloud agent converts a source image, commits the still, and jsDelivr serves it over HTTPS. Plugin 521135 already loads `@main`. Publishing a still is a commit on this repo. It is not a TRMNL plugin deploy.

## Layout

| Path | What it is |
| --- | --- |
| `epaper/m{MM}-{weather}-night.png` | Hero still. 600×450, 8-bit grayscale, Pillow mode `L`. `MM` is `01`–`12`. Weather is `clear`, `overcast`, `rain`, or `snow`. |
| `moons/00-new.jpg` … `moons/07-waning-crescent.jpg` | Moon disks. 1024×1024 RGB JPEG. |
| `moons/alpha/` | Separate 1024×1024 RGBA PNGs. `scripts/convert_still.py` will not write here. |
| `scripts/fixtures/PROOF-hero-pipeline.png` | Pipeline proof only. Not a Liquid pathname. |

May–Sep (`05`–`09`) have no snow file. Liquid falls back to overcast. The converter rejects those names unless `--allow-summer-snow` is passed, and those files still should not be committed under `epaper/`.

Counted on `main`: 43 hero PNGs and 8 moon JPEGs. Sampled `epaper/m10-clear-night.png` and `epaper/m07-clear-night.png` are 600×450 8-bit grayscale.

## Convert the next hero

From the repo root, with the source image already on disk (a workspace file or a download from a public HTTPS URL):

```bash
python3 -m pip install -r scripts/requirements.txt
python3 scripts/convert_still.py path/to/source.png --month 10 --weather clear
```

Stdout on success:

```text
wrote /…/epaper/m10-clear-night.png 600x450 L
```

That path is the stable name. Commit `epaper/m10-clear-night.png`. Pass `--force` only when the new art should replace the matrix cell that is already there.

Preview the destination without writing:

```bash
python3 scripts/convert_still.py path/to/source.png --month 10 --weather clear --dry-run
```

## Arguments

| Argument | Required | Meaning |
| --- | --- | --- |
| `source` | yes | Input image path, relative to the current working directory. |
| `--kind hero` | default | Output a 600×450 mode-`L` PNG. |
| `--month` | hero, unless `--output` | Month `1`–`12`. The file uses `m01` … `m12`. |
| `--weather` | hero, unless `--output` | `clear`, `overcast`, `rain`, or `snow`. |
| `--out-dir` | no | Directory for the stable name. Default is this repo's `epaper/` (heroes) or `moons/` (moons), next to the script, independent of the shell's cwd. |
| `--output` | no | Exact output path. Use this for proofs and scratch files. Overrides the stable filename. |
| `--fit` | no | `cover` (default, center-crop to fill), `contain` (letterbox on black), or `stretch`. A source that is already the target size is copied without resampling. |
| `--posterize-16` | no | Heroes only. Quantize to 16 gray levels after the `L` convert. Off by default: the published matrix is 8-bit `L`, and the TRMNL X panel reduces that to 4-bit (16 gray) on device. |
| `--force` | no | Overwrite an existing destination. |
| `--dry-run` | no | Convert in memory and print the path. |
| `--allow-summer-snow` | no | Permit `snow` for months `05`–`09`. |
| `--kind moon` | no | Output a 1024×1024 RGB JPEG. |
| `--phase` | moon, unless `--output` | One of `00-new`, `01-waxing-crescent`, `02-first-quarter`, `03-waxing-gibbous`, `04-full`, `05-waning-gibbous`, `06-last-quarter`, `07-waning-crescent`. |

Alpha on the source is flattened onto black before the fit. EXIF orientation is applied.

Other hero examples:

```bash
python3 scripts/convert_still.py path/to/source.png --month 1 --weather snow --fit contain
python3 scripts/convert_still.py path/to/source.png --month 12 --weather overcast --posterize-16
python3 scripts/convert_still.py path/to/source.png --output scripts/fixtures/PROOF-hero-pipeline.png
```

Optional moon JPEG (does not touch `moons/alpha/`):

```bash
python3 scripts/convert_still.py path/to/source.jpg --kind moon --phase 04-full
```

`--help` prints the same contract.

## jsDelivr bases

Trailing slash, public HTTPS:

- Heroes: `https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@main/epaper/`
- Moons: `https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@main/moons/`

Full hero URL (verified HTTP 200 against `@main` while this runbook was added):

`https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@main/epaper/m10-clear-night.png`

`@main` is what Liquid uses today. It follows the default branch, and jsDelivr caches it (`x-jsd-version: main`). A later commit can change the bytes behind that URL.

Pin a full 40-character commit SHA when a board must keep the still that was smoked. The pin does not move when `main` moves:

`https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@<sha>/epaper/m10-clear-night.png`

Example pin of the matrix as it stood before this runbook (HTTP 200, `content-type: image/png`, `x-jsd-version-type: commit`). That commit contains `epaper/m10-clear-night.png`:

`https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@320dd2348bfb592efcee86d69a152a7866d92f95/epaper/m10-clear-night.png`

Use `@main` when the URL should match plugin 521135. Use `@<sha>` when this board should ignore later stills. A branch name other than `main` is a valid jsDelivr ref, and it is not what the plugin loads.

## Smoke test

Run this after the still is on the ref you are about to hand out. `curl -I` must show HTTP 200 before that URL goes to TRMNL Coder.

```bash
curl -sI -o /dev/null -w "%{http_code}\n" \
  "https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@main/epaper/m10-clear-night.png"

curl -I \
  "https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@main/epaper/m10-clear-night.png"
```

Require status `200` and `content-type: image/png` for a hero (`image/jpeg` for a moon JPEG). A new `@main` file can 404 until jsDelivr sees the commit. Retry the same URL. Do not switch the plugin to a non-200 URL.

Confirm the geometry locally before the push:

```bash
python3 -c "from PIL import Image; im=Image.open('epaper/m10-clear-night.png'); print(im.size, im.mode)"
```

Expect `(600, 450) L`.

## Cloud agent checklist

1. Branch off `main`. Do not force-push `main`.
2. Put the source image in the workspace as a file. Download it from public HTTPS if that is how the bot delivered it.
3. `python3 -m pip install -r scripts/requirements.txt`
4. `python3 scripts/convert_still.py <source> --month <MM> --weather <wx>`
5. Read the stdout line and confirm `600x450 L` and `epaper/m{MM}-{wx}-night.png`.
6. Leave May–Sep snow out of `epaper/`. Leave `moons/alpha/` untouched unless the task is an intentional replacement of those RGBA files, which this converter does not produce.
7. Commit the still. Open a pull request into `main`.
8. After it is on the ref you will cite, `curl -I` that exact URL and require HTTP 200.
9. Hand TRMNL Coder the public HTTPS URL only.

## TRMNL handoff

- Public HTTPS URLs only.
- Do not put image bytes in TRMNL webhook JSON.
- Do not Deploy a live plugin from this repo.
- Do not add or edit plugin markup here. This repo publishes stills.

## Proof fixture

`scripts/fixtures/PROOF-hero-pipeline.png` was produced by:

```bash
python3 scripts/convert_still.py epaper/m10-clear-night.png \
  --output scripts/fixtures/PROOF-hero-pipeline.png
```

The source was already 600×450 mode `L`, so the script copies those pixels without resampling. The fixture is pixel-identical to `epaper/m10-clear-night.png` and is pipeline evidence only. Liquid paths stay under `epaper/` and `moons/`. The existing hero and moon libraries are not rewritten by this proof.
