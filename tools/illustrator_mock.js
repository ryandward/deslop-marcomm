// Runs a generated Illustrator build script against a strict mock of the
// Illustrator DOM, then redraws what it built as SVG so nmsu.export can diff
// it against the real SVG. Strict means reading or writing a property the
// mock doesn't model throws, so a misspelled API name fails here instead of
// in front of someone in Illustrator.
//
// The mock encodes our understanding of Illustrator's scripting API. When a
// real Illustrator run disagrees with it, fix the mock to match Illustrator
// first, then fix the emitter until publish passes again.
//
// usage: node illustrator_mock.js build.jsx out.svg [cc|legacy]
//   cc      artboardRect [0, 0, W, -H]  (Illustrator CS6 and later)
//   legacy  artboardRect [0, H, W, 0]   (older documents and versions)
const fs = require("fs");
const vm = require("vm");
const [jsxPath, outPath, mode = "cc"] = process.argv.slice(2);

function strict(obj, label) {
  return new Proxy(obj, {
    get(t, k) {
      if (typeof k === "symbol" || k in t) return t[k];
      throw new Error(`${label}: no property '${String(k)}'`);
    },
    set(t, k, v) {
      if (!(k in t)) throw new Error(`${label}: cannot set unknown '${String(k)}'`);
      t[k] = v;
      return true;
    },
  });
}

const Enum = (name, keys) => strict(Object.fromEntries(keys.map((k) => [k, `${name}.${k}`])), name);
const ctx = {
  DocumentColorSpace: Enum("DocumentColorSpace", ["RGB", "CMYK"]),
  CoordinateSystem: Enum("CoordinateSystem", ["DOCUMENTCOORDINATESYSTEM", "ARTBOARDCOORDINATESYSTEM"]),
  ColorModel: Enum("ColorModel", ["PROCESS", "SPOT", "REGISTRATION"]),
  Justification: Enum("Justification", ["LEFT", "CENTER", "RIGHT"]),
  StrokeJoin: Enum("StrokeJoin", ["ROUNDENDJOIN", "MITERENDJOIN", "BEVELENDJOIN"]),
  RGBColor: function () { return strict({ red: 0, green: 0, blue: 0, typename: "RGBColor" }, "RGBColor"); },
  SpotColor: function () { return strict({ spot: null, tint: 100, typename: "SpotColor" }, "SpotColor"); },
  alert: (m) => console.log("ALERT:", m),
};

let DOC = null;
const WEIGHT = { "Montserrat-Regular": 400, "Montserrat-Medium": 500, "Montserrat-SemiBold": 600,
  "Montserrat-Bold": 700, "Montserrat-ExtraBold": 800, "Montserrat-Black": 900 };
const fontsInstalled = Object.keys(WEIGHT);

function pathItem(points, closed) {
  return strict({ kind: "path", r: 0, box: null, name: "", pts: points, closed, filled: true, fillColor: null,
    stroked: false, strokeColor: null, strokeWidth: 1, strokeJoin: null,
    setEntirePath(p) { this.pts = p; } }, "PathItem");
}

function container(label) {
  const items = [];
  const c = { name: "", items, locked: false };
  c.groupItems = strict({ add() { const g = strict({ kind: "group", ...container("GroupItem") }, "GroupItem"); items.push(g); return g; } }, "GroupItems");
  const rect = (top, left, w, h, r) => {
    const p = pathItem([[left, top], [left + w, top], [left + w, top - h], [left, top - h]], true);
    p.kind = "rect"; p.r = r || 0; items.push(p); return p;
  };
  c.pathItems = strict({
    add() { const p = pathItem([], false); items.push(p); return p; },
    rectangle: (t, l, w, h) => rect(t, l, w, h, 0),
    roundedRectangle: (t, l, w, h, hr, vr) => { if (hr !== vr) throw new Error("radii"); return rect(t, l, w, h, hr); },
    ellipse(top, left, w, h) { const p = pathItem([], true); p.kind = "ellipse"; p.box = [left, top, w, h]; items.push(p); return p; },
  }, "PathItems");
  c.textFrames = strict({
    pointText(anchor) {
      const ca = strict({ textFont: null, size: 12, autoLeading: true, leading: 14.4, fillColor: null }, "CharacterAttributes");
      const pa = strict({ justification: "Justification.LEFT" }, "ParagraphAttributes");
      const t = { kind: "text", name: "", anchor: anchor.slice(), contents: "", paraLeads: {},
        textRange: strict({ characterAttributes: ca, paragraphAttributes: pa }, "TextRange"),
        translate(dx, dy) { this.anchor[0] += dx; this.anchor[1] += dy; } };
      // Illustrator keeps a point-text anchor fixed and justifies around it.
      Object.defineProperty(t, "geometricBounds", { get() {
        const half = pa.justification === "Justification.CENTER" ? 0 : 50;
        return [t.anchor[0] - 50 + half, t.anchor[1] + 10, t.anchor[0] + 50 + half, t.anchor[1] - 10];
      } });
      Object.defineProperty(t, "paragraphs", { get() {
        const n = t.contents.split("\r").length;
        return new Proxy([], { get(_, k) {
          const i = Number(k);
          if (!Number.isInteger(i) || i < 0 || i >= n) throw new Error(`paragraphs[${String(k)}] out of range (n=${n})`);
          return strict({ characterAttributes: strict({ set leading(v) { t.paraLeads[i] = v; }, get leading() { return t.paraLeads[i]; } }, "ParaCharAttrs") }, "Paragraph");
        } });
      } });
      const st = strict(t, "TextFrame");
      items.push(st);
      return st;
    },
  }, "TextFrames");
  return c;
}

ctx.app = strict({
  coordinateSystem: "CoordinateSystem.ARTBOARDCOORDINATESYSTEM",
  documents: strict({ add(cs, w, h) {
    const layers = [];
    const mkLayer = () => { const l = strict({ kind: "layer", ...container("Layer") }, "Layer"); return l; };
    layers.push(mkLayer());
    layers.add = () => { const l = mkLayer(); layers.push(l); return l; };
    const spots = [];
    DOC = strict({
      cs, w, h, layers, selection: [],
      artboards: [strict({ artboardRect: mode === "cc" ? [0, 0, w, -h] : [0, h, w, 0] }, "Artboard")],
      swatchGroups: strict({ add() { return strict({ name: "", spots: [], addSpot(s) { this.spots.push(s); } }, "SwatchGroup"); } }, "SwatchGroups"),
      spots: strict({ add() { const s = strict({ name: "", colorType: null, color: null }, "Spot"); spots.push(s); return s; } }, "Spots"),
    }, "Document");
    return DOC;
  } }, "Documents"),
  textFonts: strict({ getByName(n) { if (!fontsInstalled.includes(n)) throw new Error("no font " + n); return { name: n }; } }, "TextFonts"),
  redraw() {},
}, "Application");

const src = fs.readFileSync(jsxPath, "utf8");
vm.runInNewContext(src, ctx, { filename: jsxPath });

// ---- re-draw what was built, in top-down SVG coordinates ----
const ab = DOC.artboards[0].artboardRect;
const X = (x) => (x - ab[0]).toFixed(2), Y = (y) => (ab[1] - y).toFixed(2);
const hex = (c) => {
  if (!c) return "none";
  const s = c.spot, t = c.tint / 100, rgb = [s.color.red, s.color.green, s.color.blue];
  if (s.colorType !== "ColorModel.PROCESS") throw new Error("swatch not global process: " + s.name);
  return "#" + rgb.map((v) => Math.round(255 - t * (255 - v)).toString(16).padStart(2, "0").toUpperCase()).join("");
};
const paint = (p) => `fill="${p.filled ? hex(p.fillColor) : "none"}"` +
  (p.stroked ? ` stroke="${hex(p.strokeColor)}" stroke-width="${p.strokeWidth}" stroke-linejoin="round"` : "");
const out = [];
let counts = { rect: 0, path: 0, ellipse: 0, text: 0, group: 0 };
function emit(it) {
  counts[it.kind === "layer" ? "group" : it.kind]++;
  if (it.kind === "group" || it.kind === "layer") { out.push(`<g data-name="${it.name}">`); it.items.forEach(emit); out.push("</g>"); return; }
  if (it.kind === "rect") {
    const [l, t] = it.pts[0], [r, b] = it.pts[2];
    out.push(`<rect x="${X(l)}" y="${Y(t)}" width="${(r - l).toFixed(2)}" height="${(t - b).toFixed(2)}" rx="${it.r}" ${paint(it)}/>`);
  } else if (it.kind === "ellipse") {
    const [l, t, w, h] = it.box;
    out.push(`<ellipse cx="${X(l + w / 2)}" cy="${Y(t - h / 2)}" rx="${w / 2}" ry="${h / 2}" ${paint(it)}/>`);
  } else if (it.kind === "path") {
    out.push(`<path d="M${it.pts.map(([x, y]) => `${X(x)},${Y(y)}`).join(" L")}${it.closed ? " Z" : ""}" ${paint(it)}/>`);
  } else if (it.kind === "text") {
    const ca = it.textRange.characterAttributes;
    if (it.textRange.paragraphAttributes.justification !== "Justification.CENTER") throw new Error("not centered: " + it.name);
    if (ca.autoLeading) throw new Error("auto leading left on: " + it.name);
    let y = it.anchor[1];
    it.contents.split("\r").forEach((line, i) => {
      if (i) y -= it.paraLeads[i] ?? ca.leading;
      out.push(`<text x="${X(it.anchor[0])}" y="${Y(y)}" text-anchor="middle" font-family="Montserrat" font-weight="${WEIGHT[ca.textFont.name]}" font-size="${ca.size}" fill="${hex(ca.fillColor)}">${line.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</text>`);
    });
  }
}
DOC.layers.forEach(emit);
fs.writeFileSync(outPath, `<svg xmlns="http://www.w3.org/2000/svg" width="${DOC.w / 72}in" height="${DOC.h / 72}in" viewBox="0 0 ${DOC.w} ${DOC.h}">\n${out.join("\n")}\n</svg>\n`);
console.log(`mode=${mode} layers=${DOC.layers.map((l) => l.name + (l.locked ? "(locked)" : "")).join(", ")}`);
console.log("built:", JSON.stringify(counts), "coordinateSystem restored:", ctx.app.coordinateSystem);
