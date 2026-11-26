# Jira Issues

Public sources:

- [Jira Cloud issues REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/)
- [Atlassian Document Format](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
- [Jira search after write](https://developer.atlassian.com/cloud/jira/platform/search-and-reconcile/)
- [Atlassian Rovo MCP Server](https://developer.atlassian.com/cloud/rovo-mcp/guides/getting-started/)

## Discover Before Creating

- Resolve the project key and confirm the issue type is valid for that project. Use the project issue-type metadata rather than guessing names.
- Identify required fields and allowed values before drafting. When a create is rejected with allowed values or a repair hint, correct the payload once. Do not loop through guesses.
- Search for an existing issue that already covers the request before creating a new one. Prefer linking or updating over duplicating.

## Drafting Issue Content

- Write a specific summary that states the outcome, not the activity.
- Structure descriptions with the documentation standards skill: context, problem, intended outcome, acceptance criteria, and links.
- Rich-text fields such as `description` are stored as Atlassian Document Format. The MCP tools accept Markdown or HTML and convert it. Use HTML when the body needs panels, status lozenges, or tables. Read the content format guide for the specific tool before authoring HTML.
- Single-line text fields accept plain strings, not rich content.
- Inline media needs an existing issue: create the issue first, then embed media with an edit.
- Mentions notify the mentioned users. Include them only when intended, and list them in the preview.

## Editing Safely

- Read the issue immediately before editing. Draft the change against that state, and re-read if drafting took long enough for others to edit.
- The MCP `editJiraIssue` tool and the REST `fields` object replace values. For labels, components, fix versions, and other multi-value fields, send the complete intended list built from the current values, or existing values are lost.
- When calling the REST API directly, prefer the `update` object with `add` and `remove` operations for multi-value fields. It changes only the named values and avoids losing a concurrent edit.
- Jira field edits have no version precondition. Compare the issue's `updated` timestamp with the value you drafted against. If it changed, re-draft on the latest state and re-preview material changes.
- Change only the fields the user asked to change. Do not rewrite a whole description to adjust one section.
- When a description contains inline media, panels, expands, status lozenges, or mentions, read and write it as HTML. A Markdown write drops content Markdown cannot represent.
- Combine several field changes to one issue into one edit to stay within per-issue write limits.

## Side Effects Are Separate Mutations

Each of the following changes state beyond the issue body. Include it only when the user requested it, and list it in the preview:

- status transitions;
- assignee, reporter, or watcher changes;
- comments;
- issue links and remote links;
- sprint moves and board ranking;
- hierarchy changes such as converting a task to a subtask; and
- deletion, which always requires explicit confirmation.

Make each idempotent by checking state first:

- transition: skip when the issue is already in the target status;
- link: skip when the same link already exists; and
- comment: check for an existing matching comment before repeating a write with an unknown outcome.

## Search After Write

Jira JQL search is eventually consistent. A just-created or edited issue may not appear in search results for seconds to minutes. When you hold the issue IDs, pass them in `reconcileIssues` for consistent results. Read the issue directly by key to verify a write instead of relying on search.

## Rich Content in Jira

Use panels and status lozenges as described in [rich content](rich-content.md). Do not encode the authoritative workflow status in a static description lozenge; the issue's status field is the source of truth.
