# Confluence Content

Public sources:

- [Confluence Cloud page REST API](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/)
- [Confluence Cloud rate limiting](https://developer.atlassian.com/cloud/confluence/rate-limiting/)
- [Atlassian Rovo MCP Server](https://developer.atlassian.com/cloud/rovo-mcp/guides/getting-started/)

## Before Authoring

- Resolve the destination space and parent by ID or URL. Do not create a page under a parent inferred from a title alone.
- Load the space instructions once per task, following the MCP tool's decision rule, and apply them.
- Read the content format guide once per task before authoring HTML. Confluence HTML is not standard HTML; the guide lists the supported markup and the page components available to the current user.
- Search the space for an existing page that already covers the topic. Prefer updating or linking over creating a near-duplicate.

## Choosing the Content Type

Follow the MCP tool's content-type guidance. Use a classic page when the user asks for one, the space requires it, or the workflow needs unpublished drafts. Use a blog post only for dated announcements. Honor an explicit request for private content, and confirm visibility in the preview.

## Creating a Page

- Preview the space, parent, title, content type, width, visibility, and body.
- Create once. A page create is not idempotent. After an unknown outcome, list the parent's children through the pages API and compare exact title, author, and creation time before any repeat. Do not assume titles are unique within a space.
- Record the returned content ID and URL in the operation ledger.

## Updating a Page

- Fetch the current content in the intended body format. For classic pages, fetch the full draft as the tool directs. Re-read rich content as HTML so panels, macros, media, and embeds survive the edit.
- Pass the snapshot or version token from the latest read. When the update is rejected as stale, re-read, reapply the intended change to the new body, and re-preview if the change is material. Never resend the old payload with a new token.
- Prefer granular node edits over whole-body replacement for targeted changes. Replacing the body discards concurrent edits and increases the blast radius.
- Use `dryRun` with granular edits to preview the resulting content before persisting. For whole-body replacement, `dryRun` only echoes the input, so review the full body in the preview instead.
- A version message that carries the operation ID makes later reconciliation reliable, but it is visible in page history. Show it in the preview, and omit it when the user or space conventions object.
- Mark small corrections as minor edits only when they do not change meaning.
- Use the token returned by a successful update for the next update instead of re-reading.
- Respect user intent for draft versus publish. Saving a draft is not publishing.

## Visibility and Sensitive Content

- Do not move content from a restricted page or issue into a page with broader visibility without explicit confirmation.
- Changing restrictions or ownership, or publishing a private page, always requires explicit confirmation.
- Never include credentials, tokens, private keys, or personal data that the page audience is not authorized to see.

## Rich Content in Confluence

Use panels, status lozenges, expands, and tables as described in [rich content](rich-content.md). To show live Jira status in a page, prefer a Jira issue link or macro that renders current status over a static lozenge that drifts.
