/**
 * build_cover_letter.js — Renders the visually-designed "Professional" cover letter
 * (navy photo sidebar + letter body) via docx-js.
 *
 * This is the rendering layer only. All content (letter paragraphs, recipient,
 * salutation, sidebar copy, photo) is passed in as a JSON file — nothing here is
 * per-job or hardcoded. It is invoked by scripts/build_cover_letter_professional.py,
 * which supplies that JSON (the letter drafted in /tailor-resume step 6 plus the
 * Professional resume's sidebar content, with identity fields pulled
 * from reference/core-resume.docx and reference/background-notes.md).
 *
 * Requires the `docx` npm package: run `npm install` once in the project root.
 *
 * Usage: node scripts/build_cover_letter.js <content.json> <output.docx>
 *
 * content.json shape:
 *   {
 *     "name": "Your Name", "credentials": "Degrees/credentials" (optional),
 *     "contact": ["line", ...], "education": [{"degree":"...","school":"..."}],
 *     "certifications": ["...", ...] (optional), "core_expertise": ["...", ...],
 *     "photo": "absolute path to a pre-cropped JPEG", "photo_aspect": width/height,
 *     "date": "Month D, YYYY", "recipient": ["...", ...] (optional),
 *     "salutation": "Dear Hiring Manager,", "paragraphs": ["...", ...],
 *     "closing": "Sincerely,", "closing_name": "Your Name"
 *   }
 * "**bold**" markup inside paragraph/sidebar strings renders as a bold run, matching
 * the convention used by scripts/build_professional.py.
 */
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, BorderStyle, AlignmentType, ImageRun, Header,
  VerticalAlign, HorizontalPositionRelativeFrom, VerticalPositionRelativeFrom,
  TextWrappingType,
} = require("docx");
const fs = require("fs");
const zlib = require("zlib");

const NAVY = "1B2A49";
const ACCENT = "C9A24B";
const SIDEBAR_TEXT = "FFFFFF";
const SIDEBAR_MUTED = "C9D3E6";
const MAIN_TEXT = "222222";
const MAIN_MUTED = "555555";

// Twips (1/1440in) for layout; EMU (1/914400in) for the floating background bands —
// same units python-docx uses, since OOXML's wp:posOffset is EMU either way.
const EMU_PER_IN = 914400;
const PAGE_W_IN = 8.5;
const PAGE_H_IN = 11;
const SIDEBAR_W_IN = 2.75; // matches build_professional.py's navy sidebar width
const ACCENT_W_IN = 0.05;

const PAGE_W = Math.round(PAGE_W_IN * 1440);
const PAGE_H = Math.round(PAGE_H_IN * 1440);
const SIDEBAR_W = Math.round(SIDEBAR_W_IN * 1440);
const MAIN_W = PAGE_W - SIDEBAR_W;

// ---------- solid-color PNG (no image deps needed — same idea as
// build_professional.py's _solid_png, built here with zlib since docx-js runs in Node) ----------

function crc32(buf) {
  let crc = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    crc ^= buf[i];
    for (let k = 0; k < 8; k++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function pngChunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const typeData = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(typeData), 0);
  return Buffer.concat([len, typeData, crc]);
}
function solidPng(hex, w = 4, h = 4) {
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const raw = Buffer.alloc(h * (1 + w * 3));
  for (let y = 0; y < h; y++) {
    const row = y * (1 + w * 3);
    for (let x = 0; x < w; x++) {
      raw[row + 1 + x * 3] = r; raw[row + 1 + x * 3 + 1] = g; raw[row + 1 + x * 3 + 2] = b;
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // color type: RGB
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  return Buffer.concat([
    signature,
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", zlib.deflateSync(raw)),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

function band(hex, xIn, widthIn) {
  return new Paragraph({
    children: [new ImageRun({
      data: solidPng(hex),
      type: "png",
      transformation: { width: Math.round(widthIn * 96), height: Math.round(PAGE_H_IN * 96) },
      floating: {
        horizontalPosition: { relative: HorizontalPositionRelativeFrom.PAGE, offset: Math.round(xIn * EMU_PER_IN) },
        verticalPosition: { relative: VerticalPositionRelativeFrom.PAGE, offset: 0 },
        behindDocument: true,
        lockAnchor: true,
        wrap: { type: TextWrappingType.NONE },
      },
    })],
  });
}

function richRuns(text, { size, color, boldColor, bold = false }) {
  if (bold) return [new TextRun({ text, bold: true, color, size, font: "Calibri" })];
  return text
    .split(/\*\*/)
    .filter((part) => part.length)
    .map((part, i) => new TextRun({
      text: part, bold: i % 2 === 1, color: (i % 2 === 1 && boldColor) ? boldColor : color, size, font: "Calibri",
    }));
}

function sidebarHeading(text) {
  return new Paragraph({
    spacing: { before: 220, after: 100 },
    children: [new TextRun({ text: text.toUpperCase(), bold: true, color: ACCENT, size: 17, font: "Calibri" })],
    border: { bottom: { color: ACCENT, size: 4, style: BorderStyle.SINGLE, space: 4 } },
  });
}
function sidebarLine(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 45 },
    bullet: opts.bullet ? { level: 0 } : undefined,
    children: richRuns(text, { size: opts.size || 17, color: opts.color || SIDEBAR_TEXT, boldColor: opts.color || SIDEBAR_TEXT, bold: opts.bold }),
  });
}
function letterPara(text) {
  return new Paragraph({
    spacing: { after: 180, line: 264 },
    children: richRuns(text, { size: 19, color: MAIN_TEXT, boldColor: NAVY }),
  });
}

function buildSidebar(c) {
  const children = [];
  if (c.photo && fs.existsSync(c.photo)) {
    const aspect = c.photo_aspect || 5 / 6;
    const width = 132;
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 160 },
      children: [new ImageRun({
        data: fs.readFileSync(c.photo), type: "jpg",
        transformation: { width, height: Math.round(width / aspect) },
      })],
    }));
  }
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 20 },
    children: [new TextRun({ text: c.name.toUpperCase(), bold: true, color: SIDEBAR_TEXT, size: 23, font: "Calibri" })],
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 180 },
    children: [new TextRun({ text: c.credentials || "", bold: true, color: ACCENT, size: 15, font: "Calibri" })],
  }));

  children.push(sidebarHeading("Contact"));
  for (const line of c.contact) children.push(sidebarLine(line));

  children.push(sidebarHeading("Core Expertise"));
  for (const item of c.core_expertise) children.push(sidebarLine(item, { bullet: true }));

  children.push(sidebarHeading("Education"));
  for (const e of c.education) {
    children.push(sidebarLine(e.degree, { bold: true, after: 0 }));
    children.push(sidebarLine(e.school, { color: SIDEBAR_MUTED, size: 16, after: 90 }));
  }

  if (c.certifications && c.certifications.length) {
    children.push(sidebarHeading("Certifications"));
    for (const item of c.certifications) children.push(sidebarLine(item, { bullet: true }));
  }

  return children;
}

function buildLetterBody(c) {
  const children = [];
  children.push(new Paragraph({
    spacing: { after: 260 },
    children: [new TextRun({ text: c.date, color: MAIN_MUTED, size: 18, font: "Calibri" })],
  }));
  if (c.recipient && c.recipient.length) {
    for (const line of c.recipient) {
      children.push(new Paragraph({
        spacing: { after: 40 },
        children: [new TextRun({ text: line, color: MAIN_TEXT, size: 19, font: "Calibri" })],
      }));
    }
    children.push(new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "", size: 19 })] }));
  }
  children.push(new Paragraph({
    spacing: { after: 220 },
    children: [new TextRun({ text: c.salutation, bold: true, color: NAVY, size: 20, font: "Calibri" })],
  }));
  for (const p of c.paragraphs) children.push(letterPara(p));
  children.push(new Paragraph({
    spacing: { before: 160 },
    children: [new TextRun({ text: c.closing, color: MAIN_TEXT, size: 19, font: "Calibri" })],
  }));
  children.push(new Paragraph({
    spacing: { before: 220 },
    children: [new TextRun({ text: c.closing_name, bold: true, color: NAVY, size: 19, font: "Calibri" })],
  }));
  return children;
}

function build(c) {
  return new Document({
    sections: [{
      properties: {
        page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: 0, bottom: 0, left: 0, right: 0 } },
      },
      // The navy sidebar + gold edge are full-page-height images anchored in the header
      // (behind text, positioned relative to the page) — the same technique
      // build_professional.py uses for the Professional resume — so the band always
      // reaches the bottom of the page regardless of how much sidebar/letter text there is.
      headers: {
        default: new Header({ children: [band(NAVY, 0, SIDEBAR_W_IN), band(ACCENT, SIDEBAR_W_IN, ACCENT_W_IN)] }),
      },
      children: [
        new Table({
          width: { size: PAGE_W, type: WidthType.DXA },
          columnWidths: [SIDEBAR_W, MAIN_W],
          borders: {
            top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
            left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
            insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE },
          },
          rows: [
            new TableRow({
              children: [
                new TableCell({
                  width: { size: SIDEBAR_W, type: WidthType.DXA },
                  verticalAlign: VerticalAlign.TOP,
                  margins: { top: 400, bottom: 300, left: 260, right: 260 },
                  children: buildSidebar(c),
                }),
                new TableCell({
                  width: { size: MAIN_W, type: WidthType.DXA },
                  verticalAlign: VerticalAlign.TOP,
                  margins: { top: 500, bottom: 300, left: 420, right: 420 },
                  children: buildLetterBody(c),
                }),
              ],
            }),
          ],
        }),
      ],
    }],
  });
}

async function main() {
  const [, , contentPath, outPath] = process.argv;
  if (!contentPath || !outPath) {
    console.error("Usage: node scripts/build_cover_letter.js <content.json> <output.docx>");
    process.exit(1);
  }
  const content = JSON.parse(fs.readFileSync(contentPath, "utf-8"));
  const doc = build(content);
  const buf = await Packer.toBuffer(doc);
  fs.writeFileSync(outPath, buf);
  console.log(`written ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
