---
name: pdf-export
description: Add client-side PDF export to a web app using jspdf + html2canvas-pro. Use when the user asks to download, save, or export the current page, a report, a slide deck, a chart, or any DOM element as a PDF. Covers single-element snapshots and multi-page documents with TOC bookmarks. No server, no Puppeteer at runtime - all browser-side.
---

# Add client-side PDF export

Wire a "Download PDF" feature into a React/TypeScript web app. The output is generated entirely in the browser - the user clicks a button, the SPA rasterizes the relevant DOM nodes, and `jspdf` assembles the PDF and triggers a download.

## When to trigger this skill

- "Add a download PDF button..."
- "Let users export this report / slide / dashboard / chart as a PDF"
- "Save the current page as PDF"
- "Print this to a file"
- "We need PDF export"
- Any time a developer asks for browser-native PDF generation (no server, no Puppeteer)

Do **not** use this skill if the user wants:

- Server-rendered PDFs (use Puppeteer / Playwright on a server)
- Vector PDFs from data structures (use `pdfkit` or `pdfmake`)
- "Print this page" with `window.print()` (that's a one-liner; just suggest it)

## Step 1: Clarify the scope

Before writing code, ask the user 2 short questions if any of these are unclear:

1. **Single element or multi-page?**
   - One DOM element (a report, a card, a chart) -> Pattern A
   - A sequence of slides / pages / sections -> Pattern B
2. **Page size?** Default to letter or A4 portrait for reports; 16:9 landscape (1920x1080) for slide decks. Confirm if unsure.

For multi-page docs, also ask: **do they want a clickable TOC** (outline bookmarks)? Default yes for >3 pages.

## Step 2: Detect framework and package manager

```bash
# In project root:
cat package.json | head -20      # look for react/next/vite/vue
test -f bun.lock && echo bun || test -f pnpm-lock.yaml && echo pnpm || test -f yarn.lock && echo yarn || echo npm
grep -E '"tailwindcss":' package.json   # check Tailwind major version
```

**Critical**: if Tailwind 4 is in use, you MUST use `html2canvas-pro` (not vanilla `html2canvas`). Tailwind 4 emits `oklch()` colors that vanilla html2canvas cannot parse and the export will throw at runtime. Tailwind 3 works with either, but prefer `-pro` anyway - it's a maintained fork.

## Step 3: Install

Pick the matching command:

```bash
bun add jspdf html2canvas-pro
# OR
pnpm add jspdf html2canvas-pro
# OR
npm install jspdf html2canvas-pro
# OR
yarn add jspdf html2canvas-pro
```

No type packages needed - both libraries ship their own.

## Pattern A: Single-element snapshot

For a single report / page / dashboard. Target by `ref` or a known DOM selector.

`src/lib/exportToPdf.ts`:

```ts
import html2canvas from "html2canvas-pro";
import jsPDF from "jspdf";

type ExportOptions = {
  filename?: string;
  /** Page size as [width, height] in PDF points (1 pt = 1/72 inch). */
  format?: [number, number] | "a4" | "letter";
  orientation?: "portrait" | "landscape";
  /** Background to fill in transparent areas. */
  backgroundColor?: string;
};

/**
 * Snapshot one DOM node into a single-page PDF. Use for reports / dashboards
 * / cards. For multi-page exports, see exportDeckToPdf.
 */
export async function exportElementToPdf(
  node: HTMLElement,
  options: ExportOptions = {},
): Promise<void> {
  const { filename = "export.pdf", format = "a4", orientation = "portrait", backgroundColor = "#ffffff" } = options;

  // Wait one extra frame so any in-flight layout (lazy fonts, recently mounted
  // children) settles before the canvas snapshot freezes everything.
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

  const canvas = await html2canvas(node, {
    backgroundColor,
    scale: 2,            // 2x for retina-quality output
    useCORS: true,
    logging: false,
  });

  const pdf = new jsPDF({ orientation, unit: "pt", format, compress: true });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();

  // Fit the captured image into the page while preserving aspect ratio.
  const imgAspect = canvas.width / canvas.height;
  const pageAspect = pageWidth / pageHeight;
  const drawWidth = imgAspect > pageAspect ? pageWidth : pageHeight * imgAspect;
  const drawHeight = imgAspect > pageAspect ? pageWidth / imgAspect : pageHeight;
  const dx = (pageWidth - drawWidth) / 2;
  const dy = (pageHeight - drawHeight) / 2;

  pdf.addImage(canvas.toDataURL("image/jpeg", 0.92), "JPEG", dx, dy, drawWidth, drawHeight, undefined, "FAST");
  pdf.save(filename);
}
```

Wire to a button:

```tsx
import { useRef } from "react";
import { exportElementToPdf } from "./lib/exportToPdf";

export function Report() {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <>
      <button onClick={() => ref.current && void exportElementToPdf(ref.current, { filename: "report.pdf" })}>
        Download PDF
      </button>
      <div ref={ref}>{/* report content */}</div>
    </>
  );
}
```

## Pattern B: Multi-page document with TOC bookmarks

For slide decks, multi-section reports, anything with >1 page. Each page is rendered off-screen at fixed dimensions so the output is pixel-deterministic regardless of viewport.

`src/lib/exportDeckToPdf.ts`:

```ts
import html2canvas from "html2canvas-pro";
import jsPDF from "jspdf";

type PageInput = {
  /** Returns the DOM node to rasterize for this page. */
  render: () => Promise<HTMLElement>;
  /** Shown as a clickable bookmark in the PDF viewer's outline pane. */
  title: string;
};

type ExportOptions = {
  filename?: string;
  width?: number;
  height?: number;
  backgroundColor?: string;
  onProgress?: (current: number, total: number) => void;
};

export async function exportDeckToPdf(
  pages: PageInput[],
  options: ExportOptions = {},
): Promise<void> {
  const { filename = "deck.pdf", width = 1920, height = 1080, backgroundColor = "#0b1220", onProgress } = options;

  const pdf = new jsPDF({ orientation: "landscape", unit: "px", format: [width, height], compress: true });

  // jsPDF's outline API isn't typed - cast it once.
  const outline = (pdf as unknown as {
    outline: { add: (parent: unknown, title: string, options: { pageNumber: number }) => void };
  }).outline;

  for (let i = 0; i < pages.length; i++) {
    onProgress?.(i, pages.length);
    const page = pages[i]!;
    const node = await page.render();

    const canvas = await html2canvas(node, {
      backgroundColor,
      width, height, windowWidth: width, windowHeight: height,
      scale: 1,
      useCORS: true,
      logging: false,
    });

    const data = canvas.toDataURL("image/jpeg", 0.92);
    if (i > 0) pdf.addPage([width, height], "landscape");
    pdf.addImage(data, "JPEG", 0, 0, width, height, undefined, "FAST");
    outline?.add(null, `${i + 1}. ${page.title}`, { pageNumber: i + 1 });
  }
  onProgress?.(pages.length, pages.length);
  pdf.save(filename);
}
```

When pages are React components (not pre-mounted DOM), use this off-screen render hook:

```tsx
import { useCallback, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { ComponentType } from "react";
import { exportDeckToPdf } from "./exportDeckToPdf";

type Page = { title: string; Component: ComponentType };

export function useDeckExport(pages: Page[], width = 1920, height = 1080) {
  const [exporting, setExporting] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);

  const exportPdf = useCallback(async () => {
    if (exporting) return;
    setExporting(true);
    setProgress({ current: 0, total: pages.length });

    // Off-screen host - sized to the canvas, positioned far off the viewport.
    const host = document.createElement("div");
    Object.assign(host.style, {
      position: "fixed", left: "-100000px", top: "0",
      width: `${width}px`, height: `${height}px`, background: "#0b1220",
    });
    document.body.appendChild(host);
    document.body.classList.add("export-mode"); // hide chrome + freeze animations
    const root: Root = createRoot(host);

    const renderAt = (i: number): Promise<HTMLElement> =>
      new Promise((resolve) => {
        const Page = pages[i]!.Component;
        root.render(<Page />);
        // Two RAF ticks so layout + fonts are stable before we screenshot.
        requestAnimationFrame(() => requestAnimationFrame(() => resolve(host)));
      });

    try {
      await exportDeckToPdf(
        pages.map((p, i) => ({ title: p.title, render: () => renderAt(i) })),
        { filename: "deck.pdf", width, height, onProgress: (c, t) => setProgress({ current: c, total: t }) },
      );
    } finally {
      root.unmount();
      host.remove();
      document.body.classList.remove("export-mode");
      setExporting(false);
      setProgress(null);
    }
  }, [exporting, pages, width, height]);

  return { exporting, progress, exportPdf };
}
```

Add CSS to freeze animations and hide interactive chrome during rasterization:

```css
/* Hide toolbars / sidebars / floating buttons so they don't appear in the PDF. */
.export-mode .pdf-hide { display: none !important; }

/* Pause SMIL animations and CSS transitions during snapshot. */
.export-mode * {
  animation-play-state: paused !important;
  transition: none !important;
}

/* If you also want to respect prefers-reduced-motion for the same elements: */
@media (prefers-reduced-motion: reduce) {
  .pdf-hide animateMotion, .pdf-hide animate { display: none; }
}
```

Mark any deck chrome (nav buttons, side panels) with `className="pdf-hide"` so it disappears during export.

## Common gotchas (resolve before claiming done)

1. **Tailwind 4 + vanilla html2canvas = runtime error.** Use `html2canvas-pro` whenever the project has `tailwindcss@^4`. Vanilla `html2canvas` cannot parse `oklch()` colors.
2. **Cross-origin images** (S3 avatars, CDN logos) need `useCORS: true` AND the image server must send `Access-Control-Allow-Origin`. Otherwise the canvas gets tainted and `toDataURL` throws. If you can't fix the server, set `allowTaint: true` and accept that you can't read back the canvas - which kills PDF export. Better: proxy the image through your own origin.
3. **Web fonts not loaded** -> rasterized text falls back to system fonts. Await `document.fonts.ready` before the snapshot if the page uses custom fonts.
4. **SVG `<animateMotion>` mid-flight** -> the snapshot catches the dot mid-path. The `.export-mode` class above pauses CSS animations, but SMIL (`animate`, `animateMotion`) needs the CSS selector above OR setting `display: none` on the animate elements during export.
5. **Layout shifts after mount** -> the 2-frame `requestAnimationFrame` trick gives React time to commit and the browser time to lay out. If the page has async content (data fetches, lazy components), `await` that before exporting.
6. **Bundle size** -> `jspdf` + `html2canvas-pro` are ~400 KB total. Behind a dynamic `import()` if you care about initial load:

   ```ts
   const exportPdf = async () => {
     const { exportElementToPdf } = await import("./lib/exportToPdf");
     await exportElementToPdf(node);
   };
   ```

7. **iOS Safari** -> sometimes blocks `pdf.save()` if it's not in a synchronous click handler. Trigger the export from `onClick` directly, not from a setTimeout/Promise chain.

## Step 4: Verify

After wiring it up, run these checks:

1. **Dev sanity**: open the page, click the button, confirm a PDF downloads with the expected content.
2. **Visual fidelity**: open the PDF and compare against the screen. Look for missing fonts, cropped content, color shifts, or missing logos.
3. **TOC (multi-page)**: open the PDF in Preview / Acrobat; the sidebar should show clickable bookmarks for each page.
4. **CORS images**: if the page contains any external images, verify they appear in the PDF (not blank rectangles).
5. **Bundle**: run `bun run build` (or `vite build` / `next build`) and check the chunk size delta. Suggest dynamic import if it's > 200 KB.

## Don't introduce these anti-patterns

- Don't add a `print:` Tailwind CSS path - that's for `window.print()`, not for jspdf rasterization.
- Don't snapshot a child element when you actually want the full page - `html2canvas` doesn't follow `position: fixed` siblings outside the target.
- Don't wrap `pdf.save()` in `setTimeout` - it breaks iOS Safari's user-gesture requirement.
- Don't pre-mount the off-screen host inside React tree state - use a vanilla DOM node + a temp `createRoot` so it doesn't leak into devtools / React strict-mode double renders.
