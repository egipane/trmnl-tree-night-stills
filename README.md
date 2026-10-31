# TRMNL Tree Night — epaper stills

Oslo night matrix for the **Tree Night — Sleep** private plugin.

- 43 grayscale PNGs (600×450, 8-bit, Pillow mode `L`) under `epaper/`
- Naming: `m{MM}-{clear|overcast|rain|snow}-night.png`
- May–Sep: no snow (Oslo prune → overcast fallback in Liquid)
- Moon JPEGs under `moons/` (`00-new.jpg` … `07-waning-crescent.jpg`)
- Separate RGBA disks under `moons/alpha/` (not written by the hero converter)

jsDelivr bases (trailing slash). `@main` is what Liquid uses today; pin `@<sha>` when a board must keep a frozen still:

- Heroes: `https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@main/epaper/`
- Moons: `https://cdn.jsdelivr.net/gh/egipane/trmnl-tree-night-stills@main/moons/`

Convert and publish steps: [docs/PUBLISH.md](docs/PUBLISH.md).

```bash
python3 scripts/convert_still.py path/to/source.png --month 10 --weather clear
```

That writes `epaper/m10-clear-night.png`. `curl -I` the jsDelivr URL and require HTTP 200 before handing it to TRMNL Coder. This repo publishes stills only. It does not deploy a TRMNL plugin.
