# NMSU brand rules

Everything here comes from NMSU's brand toolkit at https://brand.nmsu.edu, read on 2026-10-14. Plain-text snapshots of the pages we cite are in `reference/brand-site/`. `nmsu/brand.py` encodes these rules and `nmsu/lint.py` enforces them, so when this file changes, those change with it. Rules we added ourselves are marked **house rule** so nobody mistakes them for NMSU policy.

## Color

| Color | Tier | HEX | RGB | CMYK | PMS | What NMSU says it's for |
|---|---|---|---|---|---|---|
| Aggie Crimson | core | `#8C0B42` | 140/11/66 | 10/97/37/43 * | 208 | The main identifier. Always present, always dominant |
| White Sands | core | `#FFFFFF` | 255/255/255 | 0/0/0/0 | - | Backgrounds that make crimson stand out |
| Organ Mountain | secondary | `#B6A5AD` | 182/165/173 | 25/30/20/5 | 5225 C | Backgrounds for info boxes and tables |
| Desert Sand | secondary | `#D7C9C4` | 215/201/196 | 10/15/15/5 | 7604 C | Backgrounds for info boxes and tables |
| Azure Sky | tertiary | `#009DB8` | 0/157/184 | 100/0/22/10 | 2229 C | Subheadings, drop caps, small infographics, URLs |
| Mesilla Valley Sunset | tertiary | `#F2824F` | 242/130/79 | 1/60/75/0 | 1575 C | Subheadings, drop caps, small infographics |
| Desert Monsoon | tertiary | `#6D6E71` | 109/110/113 | 0/0/0/70 | Cool Grey 10 | Elements that need a dark highlight |
| Sagebrush Mint | tertiary | `#6CC3BC` | 108/195/188 | 56/2/30/0 | 7472 C | Minor elements like arrows and shapes. **Never text** |
| Black | text | `#231F20` | 35/31/32 | 0/0/0/100 | - | Text, which NMSU allows alongside white |

\* NMSU says to work with the printer to confirm the CMYK breakdown for Aggie Crimson.

Use PMS for spot-color printing, CMYK for process printing, and RGB or HEX for screens. Swatch libraries generated from this table are in `brand/swatches/`: `NMSU_RGB.ase` and `NMSU_CMYK.ase` for Illustrator and InDesign, and `NMSU.gpl` for Inkscape and GIMP.

How the lint reads NMSU's color rules:

- **"Aggie Crimson ... should always be present and the dominant color."** Crimson has to appear, and no other chromatic color (Azure Sky, Mesilla Valley Sunset, Sagebrush Mint) may cover more of the visible page than crimson does. Desert Sand, Organ Mountain and Desert Monsoon are warm and cool grays, and NMSU itself prescribes the first two as large info-box backgrounds, so we don't count them as competing with crimson for dominance.
- **"Aggie Crimson, along with white, should always be the most prominent color used."** No single color may cover more of the page than crimson and white together. That rule catches the full-bleed colored backgrounds AI tools love.
- **Tertiary colors "should not take up more than 20 percent of the overall color palette."** The lint measures this on the rendered page, counting visible pixels only, weighting tints by their strength and leaving white out of the total. It measures the render rather than the layout because panels hidden under cards shouldn't count.
- **Combinations.** NMSU calls Aggie Crimson + White Sands + Desert Monsoon "traditionally NMSU", and Aggie Crimson + White Sands + Azure Sky "contemporary".
- **Accessibility.** Text has to meet WCAG 2.2 AA: 4.5:1, or 3:1 for large text (18 pt, or 14 pt bold). The lint samples both ends and the middle of every line against whatever is painted behind it. NMSU also says not to rely on color alone and to check that the design works in black and white, and a person has to judge both of those. publish writes a grayscale render for that look.

## Typefaces

- **Gotham** is NMSU's primary typeface, licensed from Hoefler&Co, and NMSU has only limited licenses. Headlines use Gotham Black, Medium and Book.
- **Montserrat** and **Open Sans** are NMSU's free substitutes for Gotham, and both are in `brand/fonts/` under the SIL Open Font License. We set everything in Montserrat, because it renders identically on every machine. The Illustrator script swaps in Gotham when `PREFER_GOTHAM = true`, using this map:

  | Montserrat | Gotham |
  |---|---|
  | Regular, Medium | Book |
  | SemiBold | Medium |
  | Bold | Bold |
  | ExtraBold, Black | Black |

- **Body copy.** NMSU suggests Open Sans for digital and Adobe Garamond for print. Adobe Garamond is commercial and isn't stored here.
- **"Use only two or three different font styles and sizes in a single printed piece,"** and never stretch or skew type. The lint caps a piece at three sizes and three weights.
- Rotis was retired in 2017 and survives only inside the logo. NMSU's Microsoft Office templates use Tahoma so files travel well.
- **House rules:** no type under 7 pt, and no line may fill more than 98% of its box, so a different Montserrat build (Adobe Fonts, an older Google zip) can't push it over the edge.

## Logo

| File in `brand/logos/` | What it is | Use it on | NMSU's original |
|---|---|---|---|
| `nmsu-vertical-setup-crimson.svg` | Crimson mark over the tagline and "New Mexico State University" | White and light backgrounds | `logo-vertical-cimson.svg` |
| `nmsu-vertical-setup-white.svg` | The same setup with white type | Crimson and dark backgrounds | `logo-vertical-white.svg` |
| `nmsu-mark-white.svg` | The mark alone, a white state shape with crimson letters | Crimson and dark backgrounds | `logo-solo-white.svg` |

These are the copies NMSU serves for its own website from `https://source.nmsu.edu/assets/svg/logos/`. The official print files and unit setups live on the NMSU Brand Portal (https://eltnmsu.sharepoint.com/sites/Brand-Portal/, NMSU login). When someone gets those, they go in `brand/logos/portal/` and take priority for print. NMSU's terms are that downloading the marks means agreeing to follow its brand guidelines.

The toolkit places the two vertical setups with `Logo`. publish ships a copy of the file in `out/assets/` whose canvas is trimmed to the artwork, so Illustrator, the SVG and the checks all measure the same box. The artwork itself is untouched. For clear space, the S in "State" measures 25.3 of the crimson setup's 213.89 units of height, and 12.2 of the white setup's 88.4.

NMSU's logo files use crimson `#8C1844`, not the palette's `#8C0B42`. "Don't change the color of the NMSU logo," so we never recolor them to match.

The rules NMSU gives for the logo:

- Use the files as provided. Never redraw, recolor, outline, shadow, stretch, enclose in a shape, add text or graphics to, deconstruct, or combine with another brand's logo.
- In communications, the logo appears only in core colors. On a colored background it's black, white or Aggie Crimson, whichever is most visible.
- **Clear space** is at least the height of the "S" in "State", on every side, and it applies to setups too.
- **Minimum size:** the mark is at least 0.5 in high in print and 75 px on screen. Horizontal and vertical setups are at least 0.4375 in in print and 50 px on screen.
- The "NM State" lettering and its font never appear outside the mark.
- A college, department or program name goes in an official logo setup from Marketing and Communications. We never typeset a unit name next to the logo ourselves.
- On print, plan the logo from the start and don't hide it on a back cover. Any print piece that doesn't carry a setup still has to include the full name "New Mexico State University" somewhere.
- Co-branding with partner logos goes to Marketing and Communications for review. As a partner logo, the NMSU mark appears uncombined and unaltered.
- **Restricted marks we never use:** the seal (Board of Regents and Office of the President only), the Classic Aggie (restricted by a licensing agreement with Oklahoma State), the athletics marks (protected, with their own crimson), and the stationery mark (official letterhead, envelopes and business cards only).

How the lint holds logo placements to those rules:

- **Clear space.** Nothing may come within one S-height of the logo, except the background it sits on.
- **Minimum size.** The logo has to meet the minimum for the medium. A screen job (`Medium.SCREEN`) works in pixels, and a print job in points.
- **The right version.** The white version goes on dark backgrounds (relative luminance under 0.25) and the crimson one on light backgrounds. The logo's main color also has to reach 3:1 against what's behind it (**house rule**).
- **A solid background.** The logo never sits on a photo.

## Tagline

"BE BOLD. Shape the Future.®" is a registered trademark. It always carries the ®, sets "BE BOLD." in Gotham Black and "Shape the Future." in Gotham Medium, stays on one line, and never appears without the logo, in another font, with changed punctuation, or on a curve. Since we don't have Gotham, we only ever use the tagline as part of a provided logo setup file.

## Photography

NMSU's FAQ says not to use AI to create or modify photos or videos of campus locations, and to use genuine photography instead. Any AI-made campus imagery in a source gets dropped, and the requester gets told why.

Two **house rules** cover photos:

- A photo keeps its proportions; a stretched photo is refused.
- Text never sits on a photo, because contrast can't be guaranteed there.

## QR codes and screens

These are **house rules**:

- **Quiet zone.** QR codes carry the full four-module quiet zone the QR standard requires.
- **Error correction.** They use level Q (25%), for screens seen at an angle.
- **They have to scan.** Each one gets scanned off the render and has to open exactly its address.
- **Minimum text size.** Screen text is at least 16 px, and print text at least 7 pt.

## Templates and contacts

- Word report templates, PowerPoint templates, and Marq licenses (templates@nmsu.edu): https://brand.nmsu.edu/applying-brand/templates.html
- Marketing and Communications, for brand questions and logo setups: mktgserv@nmsu.edu, 575-646-3221. Co-branding: 575-646-7557.
- The NMSU Writing Style Guide (AP-based) covers copy such as articles and releases: https://brand.nmsu.edu/applying-brand/style-guide/

## Decisions by MarComm

MarComm owns the brand. When MarComm reads a rule differently from how this file does, the decision goes here, with who made it and when, and `nmsu/brand.py` changes to match in the same commit.

None yet.
