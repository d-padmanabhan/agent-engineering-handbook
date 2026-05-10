# Refresh Command Template

Reusable template for a `/refresh-<kb-name>` slash command implementing the web-research KB refresh pattern. Copy, fill in the angle-bracket fields, and drop into `.cursor/commands/`.

```markdown
---
description: Refresh the <KB NAME> from web research. Reads <SOURCE FILE>, researches each item via cross-referenced web searches (HARD CAP: <CAP> web-tool calls per item, <=3 sources per claim), and writes a new <CANONICAL FILE>. The previous file is archived with a timestamp suffix so downstream commands keep working. POTENTIALLY LONG-RUNNING - up to <CAP> web-tool calls per item.
---

The user wants to refresh the <KB NAME> used by <DOWNSTREAM SKILL/COMMAND>.

This command is powered by the skill at `.cursor/skills/web-research-kb-refresh/SKILL.md` (or `~/.cursor/skills/...`) and the helper `<RELATIVE PATH TO YOUR KB HELPER>.py`.

> **Up-front warning the user must see:** this is a **potentially lengthy** operation. For each item the agent runs `WebSearch` / `WebFetch` calls under a **HARD CAP of <CAP> web-tool calls per item** (aim for 4-8 via multi-intent queries), cross-referencing at most 3 sources per claim, plus synthesis. A full refresh of <N> items takes roughly <T> minutes elapsed under the cap.

Operating rules:

1. **Source file.** If `$ARGUMENTS` contains a path, use it. Otherwise ask. Do not assume a default.

2. **Up-front warning.** Before doing anything expensive, tell the user this is long-running and ask to confirm. If the user has already asked for the refresh from within `<CALLER COMMAND>`, the warning was already issued there - do not re-warn; proceed.

3. **Scope prompt.** After confirming, ask the user which items to refresh via `AskQuestion`:

   - All items in scope - default
   - Only items not currently in the KB - typically the fastest, fills gaps
   - Only items currently in the KB - refreshes existing facts
   - Specific list - the user will provide comma-separated names

4. **Enumerate items.** Run `<HELPER --list-source SOURCE_PATH>` and parse the JSON.

5. **Dump the current KB.** Run `<HELPER --dump-current>`. Reuse analyst-judgment fields **as-is** for items already in the KB. Only the **research columns** below are regenerated.

6. **Research columns (rebuild from the web, cross-referenced):**

   - `<column1>`
   - `<column2>`
   - ...

   **Research protocol for each item (HARD BUDGET: <CAP> web-tool calls, `WebSearch` + `WebFetch` combined):**

   1. **Initial pass (<=3 calls):** Start with 2-3 multi-intent `WebSearch` queries. Compose so one search covers several research columns.
   2. **Deep reads (0-3 calls):** Use `WebFetch` only on the highest-signal hits.
   3. **Targeted gap-fills (0-3 calls):** Only if coverage is still thin on a specific column.
   4. **STOP rule: never exceed <CAP> web-tool calls per item.** If coverage is still insufficient at the cap, mark the deficient column(s) with `REVIEW - insufficient online coverage` and move on.
   5. For each research column, synthesize a concise (1-3 sentence) answer.
   6. **Cross-reference <=3 sources per claim.** A claim is sound when at least **two independent sources** agree, OR a vendor primary source is corroborated by one analyst/market source.
   7. Record **one `evidence` tuple per sourced claim** with source tag (`source` / `vendor-docs` / `analyst` / `market` / `case-study` / `judgement` / etc.) and a short note ending with the URL.
   8. If a column genuinely cannot be resourced from <=3 sources OR if the cap is hit before corroboration, mark with `REVIEW - <reason>` and add a `judgement` evidence tuple. Do not invent facts.

7. **Judgment columns (DO NOT regenerate):**

   - `<judgment_column1>` - copy from existing KB entry if present; for new items, set to `REVIEW - set after first <DOWNSTREAM RUN>`.
   - `<judgment_column2>` - same policy.

   These depend on portfolio + strategic intent in the source brief, not on vendor research.

8. **Assemble the entries JSON.** Build a JSON structure with one entry per item that should be in the KB after the refresh. Include items just researched AND items left untouched. The helper writes the full file from this list; anything missing is dropped. Write to a temp file (e.g., `/tmp/kb_entries.json`).

9. **Apply.** Run `<HELPER --apply /tmp/kb_entries.json>`. This atomically swaps the canonical file:

   1. Archives the existing canonical file with timestamp `<YYYYMMDD-HHMMSS>` (= `now - 1s`).
   2. Writes the new canonical file from the JSON.
   3. Imports/parses the new file to verify validity. If verification fails, the helper rolls back automatically.

10. **Summarize to the user:**

    - Source path.
    - Scope refreshed (count: in-scope items; new-to-KB vs existing).
    - **Archive path** of the prior file (rollback / diff).
    - **Per-item summary:** one bullet per refreshed item with the 2-3 most load-bearing sources.
    - **REVIEW placeholders** - any field left as `REVIEW - ...` with the reason.
    - **Next step:** suggest running `<DOWNSTREAM COMMAND>` so the user sees the new facts reflected.

11. **Failure modes:**

    - If web search returns no useful results for an item -> mark all research columns `REVIEW - insufficient online coverage` and surface prominently.
    - If a name in the source is a typo, normalize in the entry's `name` field but flag it on the source.
    - If a dependency is missing (`openpyxl`, `requests`, etc.), install it and retry.
    - If the helper script does not exist, tell the user the refresh is not installed and stop - do not write the KB by hand.

12. **Do NOT:**

    - Regenerate other KBs (e.g., advisory views, decision rationale) - those are separate concerns.
    - Delete or modify archived files. They are rollback anchors.
    - Edit downstream consumers. The canonical filename is stable; consumers are unaffected.
    - Touch judgment columns for items already in the KB unless the user explicitly requested an analyst-judgment refresh.
```

## Notes

- **`<CAP>` typical values** - 9 calls per item for fact-rich domains (vendor / market / pricing); 4-5 per item for narrow domains (single-vendor docs). Tune by measuring the marginal value of calls 8-9 over time.
- **`<T>` estimation** - roughly 60-90 seconds per item under the cap; for 13 items, plan for 13-20 minutes. Surface this as a range in the up-front warning.
- **Multi-intent query examples** - "vendor X 2026 overview competitors pricing" covers 4 columns; "vendor X security advisories 2025 2026" covers 2 columns. Push for queries that pull double duty.
- **Cap enforcement** - the agent must self-enforce. There is no kernel-level governor; the discipline is the cap stated in the warning + explicit count tracking per item.
- **Idempotency** - re-running the refresh on the same source should converge. If two consecutive runs produce widely different KBs, the protocol is not deterministic enough; tighten the prompts and the source-tag thresholds.
