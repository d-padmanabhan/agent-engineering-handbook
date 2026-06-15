# Static vs interactive architecture diagrams

| Aspect | Mermaid (Markdown) | React Flow (SPA) |
| --- | --- | --- |
| Where | `*.md`, ADRs, wiki | `*Diagram.tsx`, routed pages |
| Rule | `800-markdown.mdc` | `815-reactflow-diagrams.mdc` |
| Strength | Versioned text, easy review diff | Animation, logos, complex layout |
| Tradeoff | Less precision for icons | More code to maintain |

Pick one primary medium per deliverable; cross-link from docs to the SPA route when both exist.

## External AI diagram tools

Use these as accelerators, not as replacements for a maintainable source of truth.

| Tool | Best fit | Round-trip / ownership guidance |
| --- | --- | --- |
| Mermaid Chart AI | Engineering-maintained diagrams | Best fit when the desired source of truth is Mermaid. Can export PNG, SVG, or MMD. Keep Mermaid/MMD in the repo. |
| Eraser | Nicer engineering visuals | Can import Mermaid and export PNG/SVG/PDF. Mermaid round-tripping is weaker, so manually review any generated Mermaid before committing. |
| Lucidchart AI | Polished business-friendly diagrams | Supports Mermaid input, but generated diagrams are not ideal for code-based round-tripping. Use for stakeholder visuals. |
| Napkin AI | Presentation / infographic visuals | Exports PNG/SVG/PPT/PDF, but not Mermaid. Use for slides and narrative visuals, not canonical engineering diagrams. |

Rule of thumb: if future maintainers must edit it in Git, use Mermaid or React Flow. If the artifact is for a deck or executive narrative, exported visuals are acceptable as generated artifacts.
