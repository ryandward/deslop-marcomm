"""CROWN management and research structure, rebuilt from source/original.jpg.

Changes from the source:
  - "Industrial Liasson Officer" -> "Industrial Liaison Officer" (spelling)
  - dropped the blue Steering Committee border, which isn't an NMSU color
  - BASIN-WE spans the full width, so the six thrust arrows land on it
    instead of on a bare line, and it's Aggie Crimson: in Desert Monsoon
    gray it took 25% of the visible color, over NMSU's 20% tertiary cap
  - thrust leads share one baseline along the bottom of their cards
  - Education and Outreach Committee and Science Advisory Board are empty in
    the source, and stay empty until someone sends us their members
"""

from __future__ import annotations

from pathlib import Path as FilePath

from nmsu.brand import AGGIE_CRIMSON, BLACK, DESERT_MONSOON, DESERT_SAND, ORGAN_MOUNTAIN, WHITE_SANDS, Paint, Style
from nmsu.export import publish
from nmsu.layout import Circle, Group, Item, Path, Rect, Text, arrow_down, cap_height, centered_stack, wrap

HERE = FilePath(__file__).resolve().parent

# ---------------------------------------------------------------- content ----

TITLE_TEXT = "CROWN Management and Research Structure"
SUBTITLE_TEXT = ("Colorado River Basin Consortium for Optimized Energy-Water Systems "
                 "from Nontraditional Sources (CROWN)")
EXECUTIVE = ("Executive Director", "P. Xu")
DIRECTORS = [("Industrial Liaison Officer", "P. Fiske"),
             ("Deputy Director", "D. Sedlak"),
             ("Operations Director", "T. Schaub")]
BOARDS: list[tuple[str, list[str]]] = [
    ("Industrial Advisory Board", [
        "Jacobs Engineering Group", "Captura Corporation", "Active Membranes",
        "Next TFX, Inc.", "Hydranautics", "EnergyX", "DuPont", "Tidal Metals",
        "Equatic Technology", "Imagine H2O",
        "National Research Platform / National Artificial Intelligence Research Resource (NRP/NAIRR) NGL"]),
    ("Stakeholder Advisory Board", [
        "Arizona Public Service (APS)", "MSSC", "City of Phoenix",
        "Colorado Produced Water Consortium (CoPWC)",
        "Central Valley Salinity Alternatives for Long-Term Sustainability (CV-SALTS)"]),
    ("Education and Outreach Committee", []),
    ("Science Advisory Board", []),
]
THRUSTS = [
    ("T1", ["Basin Resource Assessment and Opportunity Mapping"], "B. Scanlon"),
    ("T2", ["Safeguarding water-energy security in AI industries"], "T. Tong"),
    ("T3", ["Lowering costs and energy use for brackish water desalination and "
            "wastewater reuse through brine volume minimization"], "M. Elimelech"),
    ("T4", ["Scalable technologies for the treatment and reuse of produced water"], "C. Newtson"),
    ("T5", ["Revolutionizing brine management through valorization of bulk chemicals",
            "Securing domestic supply chain for critical mineral resources through brine mining"], "Z. Ren"),
    ("T6", ["Autonomous process control and optimization"], "T. Cath"),
]
PLATFORM_NAME = "Cross-Cutting Platform: BASIN-WE"
PLATFORM_LINES = ["Basin Analytics and Systems Intelligence Network for Water and Energy",
                  "AI-powered decision support, data integration, and systems intelligence"]

# ----------------------------------------------------------------- styles ----
# NMSU asks for two or three sizes and styles per piece: 20 / 9 / 7.5 pt in
# ExtraBold / Bold / Medium.

C = Paint(AGGIE_CRIMSON)
INK = Paint(BLACK)
WH = Paint(WHITE_SANDS)

TITLE = Style(800, 20, 24, C)
SUBTITLE = Style(500, 9, 11, Paint(DESERT_MONSOON))
SECTION = Style(800, 9, 11, C)
SECTION_REV = Style(800, 9, 11, WH)
ROLE = Style(700, 9, 11, C)
ROLE_REV = Style(700, 9, 11, WH)
NAME = Style(500, 9, 11, INK)
NAME_REV = Style(500, 9, 11, WH)
BOARD_TITLE = Style(700, 9, 11, C)
BOARD_ITEM = Style(500, 7.5, 9, INK)
BADGE = Style(800, 9, 11, WH)
THRUST_TITLE = Style(500, 7.5, 9, INK)
THRUST_LEAD = Style(700, 7.5, 9, C)
PLATFORM_HEAD = Style(700, 9, 11, WH)
PLATFORM_BODY = Style(500, 7.5, 9.5, WH)

LINE_W = 1.75          # flow connectors
BRACKET_W = 1.25       # the bracket that groups the three directors
HAIRLINE = 0.75
BOX_R = 6

# ----------------------------------------------------------------- layout ----

W = 792                # 11 in
M = 28
CX = W / 2
CONTENT_W = W - 2 * M


def build() -> tuple[list[Group], float]:
    header = Group("Header", [
        Text("Title", [TITLE_TEXT], CX, 52, TITLE, CONTENT_W),
        Text("Subtitle", [SUBTITLE_TEXT], CX, 69, SUBTITLE, CONTENT_W),
    ], layer=True)
    connectors: list[Item] = []

    # Leadership: the executive director over three directors.
    box_w, box_h = 158, 36
    exec_box = Rect("box", CX - box_w / 2, 86, box_w, box_h, BOX_R, fill=C)
    leadership: list[Item] = [Group(EXECUTIVE[0], [exec_box, *centered_stack(
        EXECUTIVE[0], exec_box, [(EXECUTIVE[0], ROLE_REV), (EXECUTIVE[1], NAME_REV)])])]

    exec_bottom = exec_box.y + box_h
    bus_y = exec_bottom + 10
    dir_y = exec_bottom + 26
    dir_cx = [CX - 186, CX, CX + 186]
    connectors.append(Path("Exec trunk", [(CX, exec_bottom), (CX, bus_y)], stroke=C, sw=LINE_W))
    connectors.append(Path("Exec bus", [(dir_cx[0], bus_y), (dir_cx[2], bus_y)], stroke=C, sw=LINE_W))
    for (role, person), x in zip(DIRECTORS, dir_cx):
        connectors.append(arrow_down(f"To {role}", x, bus_y, dir_y, C, LINE_W))
        box = Rect("box", x - box_w / 2, dir_y, box_w, box_h, BOX_R, fill=Paint(DESERT_SAND))
        leadership.append(Group(role, [box, *centered_stack(role, box, [(role, ROLE), (person, NAME)])]))

    # A bracket gathers the directors; one trunk carries them into the committee.
    dir_bottom = dir_y + box_h
    panel_y = dir_bottom + 26
    connectors.append(Path("Director bracket", [(dir_cx[0], dir_bottom), (dir_cx[0], dir_bottom + 9),
                                                (dir_cx[2], dir_bottom + 9), (dir_cx[2], dir_bottom)],
                           stroke=Paint(ORGAN_MOUNTAIN), sw=BRACKET_W))
    connectors.append(arrow_down("To Steering Committee", CX, dir_bottom, panel_y, C, LINE_W))

    # Steering Committee: a light panel holding four board cards.
    pad, gap = 12, 12
    card_w = (CONTENT_W - 2 * pad - 3 * gap) / 4
    card_y = panel_y + 27
    head_h = 30                                  # room for a two-line board title
    rule_y = card_y + head_h + 6
    item_y0 = rule_y + 14
    built_cards: list[tuple[str, float, list[Item]]] = []
    list_bottoms: list[float] = []
    for i, (title, members) in enumerate(BOARDS):
        x = M + pad + i * (card_w + gap)
        cx = x + card_w / 2
        inner = card_w - 18
        t_lines = wrap(title, BOARD_TITLE, inner)
        t_span = cap_height(BOARD_TITLE) + (len(t_lines) - 1) * BOARD_TITLE.leading
        t_first = card_y + 6 + (head_h - t_span) / 2 + cap_height(BOARD_TITLE)
        parts: list[Item] = [Text(f"{title} title", t_lines, cx, t_first, BOARD_TITLE, inner),
                             Path("rule", [(x + 14, rule_y), (x + card_w - 14, rule_y)],
                                  stroke=Paint(ORGAN_MOUNTAIN), sw=HAIRLINE)]
        if members:
            lines: list[str] = []
            gaps: list[float] = []
            for member in members:
                wrapped = wrap(member, BOARD_ITEM, inner)
                gaps += [2.25 if lines else 0.0] + [0.0] * (len(wrapped) - 1)
                lines += wrapped
            members_text = Text(f"{title} members", lines, cx, item_y0, BOARD_ITEM, inner, gaps)
            parts.append(members_text)
            list_bottoms.append(members_text.last_baseline)
        built_cards.append((title, x, parts))
    card_h = max(list_bottoms) + 12 - card_y
    panel_h = card_y + card_h + pad - panel_y
    steering: list[Item] = [
        Rect("Steering Committee panel", M, panel_y, CONTENT_W, panel_h, 10,
             fill=Paint(DESERT_SAND, 35), stroke=Paint(ORGAN_MOUNTAIN), sw=HAIRLINE),
        Text("Steering Committee label", ["Steering Committee"], CX, panel_y + 18, SECTION, CONTENT_W),
    ]
    for title, x, parts in built_cards:
        steering.append(Group(title, [Rect("card", x, card_y, card_w, card_h, BOX_R, fill=WH,
                                           stroke=Paint(ORGAN_MOUNTAIN), sw=HAIRLINE), *parts]))

    # Research Thrusts: a crimson bar over six numbered cards.
    panel_bottom = panel_y + panel_h
    bar_y, bar_h = panel_bottom + 18, 21
    connectors.append(arrow_down("To Research Thrusts", CX, panel_bottom, bar_y, C, LINE_W))
    thrusts: list[Item] = [Group("Research Thrusts bar", [
        Rect("bar", M, bar_y, CONTENT_W, bar_h, 0, fill=C),
        Text("Research Thrusts label", ["Research Thrusts"], CX,
             bar_y + bar_h / 2 + cap_height(SECTION_REV) / 2, SECTION_REV, CONTENT_W),
    ])]
    t_gap = 12
    t_w = (CONTENT_W - 5 * t_gap) / 6
    badge_r = 11.5
    t_y = bar_y + bar_h + 7 + badge_r
    title_y0 = t_y + badge_r + 7 + cap_height(THRUST_TITLE)
    titles: list[tuple[str, float, float, float, Text, str]] = []
    for i, (tag, paras, lead) in enumerate(THRUSTS):
        x = M + i * (t_w + t_gap)
        inner = t_w - 12
        lines, gaps = [], []
        for para in paras:
            wrapped = wrap(para, THRUST_TITLE, inner)
            gaps += [5.0 if lines else 0.0] + [0.0] * (len(wrapped) - 1)
            lines += wrapped
        title_text = Text(f"{tag} title", lines, x + t_w / 2, title_y0, THRUST_TITLE, inner, gaps)
        titles.append((tag, x, x + t_w / 2, inner, title_text, lead))
    # Leads share one baseline across the row, under the longest title.
    lead_y = max(t[4].last_baseline for t in titles) + 18
    t_h = lead_y + 10 - t_y
    for tag, x, cx, inner, title_text, lead in titles:
        thrusts.append(Group(tag, [
            Rect("card", x, t_y, t_w, t_h, BOX_R, fill=Paint(DESERT_SAND, 60)),
            title_text,
            Text(f"{tag} lead", [lead], cx, lead_y, THRUST_LEAD, inner),
            Circle("badge", cx, t_y, badge_r, fill=C, stroke=WH, sw=2),
            Text(f"{tag} badge", [tag], cx, t_y + cap_height(BADGE) / 2, BADGE, 2 * badge_r),
        ]))

    # BASIN-WE runs underneath all six thrusts.
    t_bottom = t_y + t_h
    plat_y = t_bottom + 16
    for tag, x, cx, *_ in titles:
        connectors.append(arrow_down(f"{tag} to platform", cx, t_bottom, plat_y, C, LINE_W))
    plat_box = Rect("box", M, plat_y, CONTENT_W, 50, BOX_R, fill=C)
    platform: list[Item] = [Group("Cross-Cutting Platform", [plat_box, *centered_stack(
        "Platform", plat_box, [(PLATFORM_NAME, PLATFORM_HEAD), ("\n".join(PLATFORM_LINES), PLATFORM_BODY)])])]

    height = round(plat_y + plat_box.h + M + 4)
    # Bottom of the stack first: connectors sit under the boxes they join.
    return [
        Group("Connectors", connectors, layer=True),
        Group("Steering Committee", steering, layer=True),
        Group("Research Thrusts", thrusts, layer=True),
        Group("Cross-Cutting Platform", platform, layer=True),
        Group("Leadership", leadership, layer=True),
        header,
    ], height


if __name__ == "__main__":
    layers, height = build()
    publish(layers, width=W, height=height, out_dir=HERE / "out", stem="CROWN_structure_NMSU", title=TITLE_TEXT)
