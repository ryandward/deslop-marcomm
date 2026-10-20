# deslop-marcomm

People across NMSU keep sending Marketing and Communications (MarComm) graphics that free-tier AI tools made for them: org charts, flowcharts, flyers, proposal figures. Then they ask MarComm to make them look right. The content is usually what they need, but the design is whatever the tool felt like that day: off-brand colors, made-up fonts, misspelled words, boxes that don't line up, sometimes an invented NMSU logo. The department is overwhelmed with these requests. We keep this repo so Claude can do the rebuild: take the content, rebuild the design from scratch in NMSU's brand, and hand back an Illustrator file that a MarComm designer can finish.

## Who we're working with

The person in the session is usually someone in MarComm: a designer, a coordinator, or the head of marketing. MarComm owns the NMSU brand, so a few things follow from that:

- **Their reading of a brand rule beats ours.** `BRAND.md` and `nmsu/brand.py` are our reading of https://brand.nmsu.edu. When someone in MarComm says a rule means something else, we change `brand.py` and `BRAND.md` together, and record in `BRAND.md` who decided it and when.
- **Most of them are designers, not programmers.** We explain in plain words, show the preview image instead of code, and don't ask them to read Python. They'll finish the work in Illustrator, so that's the handoff we optimize for.
- **They have assets we don't.** That means the official logo files and unit setups from the Brand Portal, and probably Gotham licenses. When those matter to a job, ask for them.

## How we work here

We never edit the slop. We read it for its content, transcribe that content into a job's `build.py`, and rebuild the design from the toolkit's primitives. The source's layout, colors, fonts, icons, gradients, shadows and emoji are only hints about structure, and we keep nothing but the information architecture: who reports to whom, what belongs with what, and what flows into what.

Every design leaves this repo through `nmsu.export.publish()`, and that function is really the point of the repo:

1. It lints the layout.
2. It renders the PDF and PNGs.
3. It lints the render.
4. It proves the Illustrator script draws the same picture as the SVG.

Files only reach `out/` when every step passes. A `BrandViolation` is a red build: it means the design is off-brand, so we fix the design. We never loosen a rule in `nmsu/brand.py` just to get a job through. Rules only change when MarComm says they read differently, as described above.

The CROWN chart shows how this plays out. Its first version put the BASIN-WE platform in Desert Monsoon gray, and the chart looked fine. The render lint measured the gray at 25% of the visible color, though, and NMSU caps tertiary colors at 20%, so the platform moved to Aggie Crimson.

## Where things are

- `nmsu/brand.py`: the palette, typefaces and rule thresholds, and the only place a color or font may come from
- `nmsu/layout.py`: HarfBuzz text measurement plus the primitives `Rect`, `Circle`, `Path`, `Text`, `Image`, `PhotoSlot`, `Logo`, `QRCode`, `Group`, `arrow_down` and `centered_stack`
- `nmsu/photo.py`: turns a requester's photo into a working copy we can place, without touching the original
- `nmsu/lint.py`: the brand compiler
- `nmsu/export.py`: the SVG writer, the Illustrator script writer, renders, and `publish()`
- `nmsu/swatches.py`: writes `brand/swatches/` from the palette
- `brand/`: fonts, logos, swatch libraries
- `reference/brand-site/`: dated text snapshots of the brand.nmsu.edu pages the rules cite
- `tools/illustrator_mock.js`: a strict mock of Illustrator's scripting DOM
- `tests/`: each test feeds the lint a piece of typical slop and proves it gets refused, plus one on-brand control that runs the whole toolchain
- `jobs/<slug>/`: one folder per request, with `source/` (exactly what came in), `build.py` and `out/`
- `BRAND.md`: the rules in plain language, with sources
- `README.md`: the human guide for MarComm

## Taking a new job

1. Get a short job name and which unit sent the request. Make `jobs/<slug>/source/` and put exactly what came in there. Nothing in `source/` ever gets edited. Sources may be images, PDFs, slides or documents; read them however works. `.gitattributes` sends everything in `source/` to Git LFS except `.md` and `.txt` files, so write the brief down as `request.md`.
2. Transcribe the text into constants at the top of `build.py`. This is where AI slop does the most damage, so we go slowly:
   - Copy exactly what's there.
   - Fix only unambiguous misspellings of ordinary words, like "Liasson" to "Liaison". List every fix in the `build.py` docstring and in the report back.
   - Never correct names of people, organizations, programs, acronyms, numbers or dates. AI image tools garble these in plausible-looking ways, so when one looks wrong we flag it and ask rather than guess.
   - When text is unreadable, we ask. We don't fill it in from context.
   - Never add content the source doesn't have, whether that's a tagline, an icon that implies meaning, or an extra box.
3. Check the format before building. We build single-page graphics here (charts, diagrams, flowcharts, posters, flyers), and they come out as Illustrator material. Multi-page documents belong in InDesign, which this toolkit can't produce yet, and we say so rather than forcing it. Reports and slide decks should start from NMSU's official Word and PowerPoint templates (see `BRAND.md`).
4. Write `build.py`. Use `jobs/crown-structure/build.py` as the pattern for print diagrams, `jobs/aces-shaping-futures-poster/build.py` for print posters with photo slots and an FPO image, and `jobs/commencement-welcome-fall-2026/build.py` for screens, logos, photos and QR codes:
   - content constants first
   - then a type scale of at most three sizes and three weights
   - then `build()`, which returns layers bottom to top
   - then `publish()`, with `medium=Medium.SCREEN` for anything shown on a display, which switches units to pixels
5. Run `.venv/bin/python jobs/<slug>/build.py`, read every finding, and fix the design.
6. Look at `out/<stem>.png` and `out/<stem>_grayscale.png` with the Read tool before reporting anything. The lint can't judge alignment or balance, or whether the hierarchy still reads in grayscale.
7. Report back in a few plain sentences:
   - what changed from the source, and why
   - which content we corrected, and which we're flagging
   - which file to open in Illustrator
8. When asked, draft a short note MarComm can send to the requester. It should say what changed, why the brand needed it, and anything we need them to confirm. It shouldn't lecture them about AI tools.

## What publish writes

- `<stem>_build.jsx` is what a designer should get. In Illustrator they run File > Scripts > Other Script..., then Save As `.ai`. The script builds a native document with:
  - NMSU global swatches
  - named layers
  - each box grouped with its text
  - centered live text
  - Gotham instead of Montserrat, if `PREFER_GOTHAM = true` is set at the top of the file on a machine that has it
- `<stem>.svg` opens directly in Illustrator and looks exact, but each line comes in as its own text object.
- `<stem>.pdf` embeds the fonts under their real Montserrat names, ready to drop into a proposal, Word or LaTeX.
- `<stem>.png` and `<stem>_grayscale.png` are previews. For a screen job, `<stem>.png` is the finished file at exactly the artboard's pixel size.
- `assets/` holds the photos and logos the `.jsx` links to. It has to stay next to the `.jsx`.

Documents are RGB with global swatches. For offset print, a designer would switch to `brand/swatches/NMSU_CMYK.ase` and confirm the crimson with the printer, as NMSU asks.

## Things we don't do, and say why

These come from NMSU's brand rules, and `BRAND.md` has the citations. When a request asks for one of them, we decline that part and explain.

- **Redrawing, recoloring or modifying the NMSU logo.** That includes "fixing" the logo's `#8C1844` to match the palette. Logos come only from `brand/logos/`, or from Brand Portal files in `brand/logos/portal/`, used as provided.
- **Typesetting a college or department name next to the logo.** That's an official logo setup, and it comes from MarComm's own setup files.
- **Adding the seal, the Classic Aggie, athletics marks, or the stationery mark.** We only use these when the MarComm person in the session confirms the use is authorized.
- **The tagline in anything but Gotham, or without the logo.** We only use it inside a provided setup file.
- **AI-generated or AI-modified photos of campus.** NMSU's FAQ says no. Requesters need genuine photography.

`Logo` places the two vertical setups in `brand/logos/` exactly as provided. The lint holds every placement to NMSU's clear space (the height of the S in "State"), minimum size, and the right version for its background. The standalone mark (`nmsu-mark-white.svg`) isn't wired up yet, because its file carries Illustrator's private data, so it still goes in by hand. Standalone pieces like flyers, posters and one-pagers need the logo and the full name "New Mexico State University". A figure that goes inside a larger NMSU document doesn't need its own logo.

## Keeping requesters' material private

Jobs often hold unpublished material: grant proposals, internal org charts, people's names. Before pushing to a remote, we check whether it's public. If it is, we don't push a job until the MarComm person confirms that job's content can be public.

## What verification covers and what it doesn't

- **Illustrator never runs here.** `tools/illustrator_mock.js` holds the `.jsx` to our model of Illustrator's scripting API, and `publish()` requires the mock's redraw to match the SVG under both artboard coordinate conventions. If someone reports that a `.jsx` fails in real Illustrator, the mock was wrong. We get the exact error message, fix the mock to match what Illustrator actually did, watch publish go red, and then fix the emitter.
- **Renders only see the repo's fonts.** `export.font_env()` gives Inkscape a private fontconfig that only knows `brand/fonts/`, so the lint and the renderer measure the same font files whatever is installed system-wide.
- **Tests and types.** Run `.venv/bin/pytest` and `.venv/bin/mypy` (strict). Every job's script is named `build.py`, so mypy can't take them in one run; `tests/test_types.py` type-checks each job separately. `typings/` holds exact stubs for the slices of uharfbuzz and fontTools we call. When the toolkit needs more of those libraries, we extend the stubs; we don't add `Any`, `type: ignore` or `ignore_missing_imports`.
- **Photos and QR codes.** Text never sits on a photo, because its contrast can't be checked there. A photo can't be stretched, and it has to be sharp enough for the medium: 300 ppi at its printed size, or no upscaling on a screen. When the only file we have is too small, we place it with `fpo=True`, so publish lists it and Illustrator names it "FPO" until a designer swaps in the real file. When a request has room for photos we don't have, we draw `PhotoSlot`s, which the lint treats like the photos they'll become. Every QR code is scanned straight off the render and has to open exactly the address it was built with.
- **Every rule needs a test.** Each test in `tests/test_rules.py` should fail when its rule is loosened. When we add a rule, we add the piece of slop that proves it bites.

## Growing the toolkit

When a job needs something the toolkit doesn't have yet, we add it to `nmsu/` once rather than drawing it inline in the job. That covers things like a new shape, a table, or left-aligned text. Two jobs drawing the same thing two different ways is exactly how drift starts. A new primitive needs four things:

- an SVG emitter
- an Illustrator emitter
- a matching entry in `tools/illustrator_mock.js`
- lint coverage

Known gaps right now:

- placing the standalone NMSU mark (the two vertical setups work)
- left-aligned text, since every `Text` is centered
- multi-page and InDesign output
- native CMYK documents
- any use of Open Sans, which the toolkit stores but doesn't set anything in

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                         # all passing means the whole toolchain works
.venv/bin/python -m nmsu.swatches        # after any palette change
```

`publish()` also needs `inkscape`, `node` and ImageMagick's `magick` on `PATH`, and the repo needs Git LFS. On a Mac that's `brew install python node imagemagick git-lfs`, `brew install --cask inkscape`, then `git lfs install`. So far the repo has only been run on Linux, so on a new machine the first `pytest` run is the real check.
