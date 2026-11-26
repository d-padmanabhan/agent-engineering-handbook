# Rich Content: Panels and Status Lozenges

Panels are the colored callout blocks; status lozenges are the small colored inline labels. Both exist in Jira rich-text fields and Confluence pages.

Public sources:

- [ADF panel node](https://developer.atlassian.com/cloud/jira/platform/apis/document/nodes/panel/)
- [ADF status node](https://developer.atlassian.com/cloud/jira/platform/apis/document/nodes/status/)
- [WCAG 2.2: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)

When authoring through the Atlassian MCP server, use the markup from the content format guide for the specific tool. Do not invent macro or HTML shapes.

## Panels

ADF supports these panel types:

| Panel | Use for |
| --- | --- |
| `info` | Context or background the reader should know |
| `note` | An important caveat, prerequisite, or constraint |
| `warning` | Risk of data loss, security exposure, outage, or an irreversible step |
| `success` | A verified outcome, approval, or completed state |
| `error` | A known failure, blocker, or unsupported path |

Rules:

- Use a panel only when the content needs more attention than surrounding text. Never use panels for decoration or layout.
- Start the panel with an explicit text label, such as "Warning:" or "Prerequisite:", so meaning does not depend on color or icon.
- Keep one idea per panel and keep it short. Panels hold paragraphs, lists, and headings, not whole procedures.
- Use at most one or two panels per section. A page full of panels has no emphasis left.
- Choose the panel type by meaning. Do not pick a type for its color.

ADF example for REST API callers:

```json
{
  "type": "panel",
  "attrs": { "panelType": "warning" },
  "content": [
    {
      "type": "paragraph",
      "content": [
        {
          "type": "text",
          "text": "Warning: rotating this key invalidates existing sessions."
        }
      ]
    }
  ]
}
```

## Status Lozenges

Status lozenges are inline labels that represent the state of work.

- Use short text, one to three words, that carries the full meaning on its own, such as `IN REVIEW` or `BLOCKED`.
- Keep a consistent vocabulary and color mapping within a page or space. A common mapping:

  | Color | Meaning |
  | --- | --- |
  | `neutral` | Not started or unknown |
  | `blue` | In progress |
  | `yellow` | At risk or awaiting review |
  | `green` | Done or approved |
  | `red` | Blocked or failed |
  | `purple` | Space-defined category |

- Use named colors rather than custom hex values so themes and accessibility modes render them consistently.
- Never rely on color alone. The lozenge text must state the status.
- Do not use static lozenges to mirror authoritative state that lives elsewhere, such as a Jira issue status. Link to the live source instead.

ADF example:

```json
{
  "type": "status",
  "attrs": { "text": "IN REVIEW", "color": "yellow" }
}
```

## Other Elements

- Use expands for long supporting detail that most readers can skip.
- Use tables for comparisons and structured reference data, not for layout.
- Use mentions only to notify a specific person who must act, and list them in the preview because they send notifications.
