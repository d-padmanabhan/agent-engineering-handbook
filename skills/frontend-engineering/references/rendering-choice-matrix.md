# Rendering Choice Matrix

When to pick SSG / SSR / SPA / ISR / hybrid. The wrong choice locks you into months of unnecessary cost or complexity. Get this right upfront and the rest of the architecture falls into place.

## The matrix

| Use case | First choice | Why |
|---|---|---|
| Marketing site, blog, docs | **SSG** | Cheapest hosting (CDN-only); SEO native; fast TTFB |
| E-commerce listing pages | **ISR** or **SSG + ISR** | Mostly static; inventory occasionally changes |
| E-commerce product pages | **ISR** or **SSR** | Per-product page; freshness matters; SEO matters |
| Personalized dashboard (authed) | **SSR** (selective hydration) or **SPA** | Per-user; SEO does not matter; framework choice drives this |
| Internal tool (no SEO need) | **SPA** | Simplest; CDN-able; rich client-side interactivity |
| Real-time collaborative app (Figma, Linear) | **SPA** + websockets | SSR adds no value; client-side is the architecture |
| Documentation portal (versioned) | **SSG** (Hugo / Docusaurus / VitePress / Astro Starlight) | Static + per-version builds |
| Forum / community with new posts | **SSR** or **ISR** with on-demand revalidate | Freshness + SEO |
| Long-form content with personalization (news with paywall) | **SSR** | Per-user paywall logic; SEO for crawlers |
| Dashboard with charts (internal) | **SPA** | No SEO; chart libraries are client-only anyway |
| Webhook receiver UI | **SPA** | Pure interactivity; no public-facing pages |

---

## Worked example 1: B2B marketing site

**Scenario:** SaaS marketing site, 50 pages, content updated 1-2x/week, SEO is the top metric.

**Choice: SSG with Astro, Hugo, or Eleventy.**

- Build once, deploy to CDN. Hosting cost: pennies.
- SEO: every page is a real HTML file. Perfect Lighthouse SEO score out of the box.
- TTFB: < 100ms anywhere (edge-cached).
- Build time: 10-30s for 50 pages.

**Wrong choice for this:** Next.js SPA. You would pay for a server, hurt SEO, slow TTFB, and add bundle cost - all to render essentially static content.

**Acceptable alternative:** Next.js or Nuxt in pure SSG mode. Equivalent outcome with a heavier toolchain - pick if the team already knows it.

---

## Worked example 2: authenticated internal dashboard

**Scenario:** Internal analytics tool, 200 active users, no public access, behind SSO.

**Choice: SPA (React or Vue or Svelte).**

- No SEO need (gated behind auth).
- Server-side rendering adds no benefit (no crawler benefit; no FCP benefit on auth-locked pages).
- Hosting: serve static files from a CDN; auth happens at the API tier.
- State: TanStack Query for server state; minimal global client state (only auth user, theme).

**Wrong choice for this:** Next.js with SSR. You would add server cost and complexity for zero benefit. The auth wall negates SSR's value.

**Edge case:** if the dashboard needs to be embedded in a customer-facing page later, the rendering choice changes. Worth a footnote in the ADR.

---

## Worked example 3: two-sided marketplace (mixed audience)

**Scenario:** Marketplace with both anonymous browse (SEO matters) and authed flows (SEO does not).

**Choice: Hybrid - SSG/ISR for browse (`/listings/*`), SPA-ish (SSR shell + client interactivity) for authed (`/account/*`).**

- Next.js or Nuxt or SvelteKit can do this per-route.
- Browse pages: SSG at build; ISR on listing edit; cached at CDN.
- Authed pages: SSR for the shell (auth check, layout) + client-side fetch for data via TanStack Query.

**Discipline required:** per-route rendering choice documented; do not accidentally SSR the dashboard or accidentally SPA the listings page. PR template should ask "what is the rendering mode for this route?".

---

## Worked example 4: real-time collaborative editor

**Scenario:** Linear / Figma / Notion clone. Heavy client-side state, websockets, optimistic UI.

**Choice: SPA + WebSocket (or WebRTC for peer-to-peer).**

- SSR provides nothing for an interaction-dominated workspace.
- Client owns the state; server is the sync engine.
- Optionally a tiny SSR or SSG shell for the public landing / marketing routes, but the app itself is SPA.

**Wrong choice for this:** Next.js with RSC. Server components do not help when 95% of the app is bidirectional client-server sync.

---

## Decision questions

Five questions, answered honestly, pick the rendering model for you:

1. **Does SEO matter for this route?**
   No -> SPA is on the table. Yes -> need HTML in the response (SSG or SSR).

2. **Is the content per-user?**
   Yes -> SSR (or SPA if no SEO). No -> SSG is on the table.

3. **How often does content change?**
   Rare (weekly) -> SSG. Frequent (hourly) -> ISR. Per-request -> SSR.

4. **Does the team know the meta-framework?**
   No -> use what you know; meta-frameworks are 6-12 months of learning cost.

5. **What is the hosting budget?**
   Tight -> SSG (CDN-only). Reasonable -> SSR is fine.

Answer those five honestly; the choice usually picks itself.

---

## Hybrid considerations

Most non-trivial apps in 2026 end up hybrid. The discipline:

- **Document per-route rendering** in `README.md` or per-route comments
- **CI lints** that prevent accidental rendering-mode changes (e.g., Next.js `getServerSideProps` added to a route documented as SSG)
- **Bundle budgets per rendering mode** - SSG routes can have looser budgets than SPA routes
- **Auth flow boundaries** clearly drawn - SSR for auth check + shell, SPA for the authed app interior

The hybrid trap: every route becomes its own architecture decision. Without documentation discipline, six months later nobody remembers why this route is SSR and that one is SSG.

---

## When to revisit

- Real users complain about a perf metric that the current rendering mode cannot fix
- SEO requirements change (authed app needs a public landing; marketing site adds a member portal)
- Team composition changes (new framework expertise; loss of existing expertise)
- Hosting cost rises beyond what the rendering mode justifies

Otherwise: rendering choice is a 3-5 year decision. Make it deliberately and stop relitigating.
