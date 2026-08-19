<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0013. Curated policy display copy and a webapp visual design pass

- Status: Accepted
- Author: Ritesh Ambastha

## Context

The upload form (ADR-0011) offered exactly two choices - `demo_fast` and
`demo_with_audio` - as raw internal policy names with no further
explanation. A first-time visitor has no way to know that one runs
fully offline while the other downloads Whisper model weights on first
use, or what detectors each actually enables. This was reported
directly: the internal names read as arbitrary to someone who didn't
help build the pipeline. Separately, the webapp's original CSS was
functional but minimal - plain system-default form controls, no visual
hierarchy, and a plain-text "running"/"done" status column that gave no
at-a-glance read of a job's state.

## Decision

**Policy display metadata.** `redactguard_webapp.policy_catalog` gains a
`PolicyDisplay` dataclass (title, tagline, badge text/kind, detail
bullets) and a `display_for(PolicyChoice) -> PolicyDisplay` lookup. This
stays a webapp-local concern - keyed by policy name in a module-level
dict - rather than a field on `redactguard_core`'s `PolicyProfile`
pydantic model, because it's presentation copy for one consumer (this
webapp's upload form), not a property of the policy itself; a real
compliance profile like `gdpr_v1.yaml` has no use for it. Any policy not
in the curated dict (e.g. one a self-hoster drops into
`redactguard_webapp/policies/`) still renders, via a generated fallback
built from the profile's own `name`/`description`.

The upload form renders each policy as a card - a native radio input
plus a heading, colored badge ("Works offline" / "Downloads a model on
first use"), tagline, and bullet list - rather than a `<select>`, so the
distinguishing information is visible without an extra click.
`routes/pages.py` gained a small `render_upload_form()` helper so the
four call sites that render this template (the initial GET, and three
different validation-error paths in the POST handler) all build the
same `policy_display` mapping instead of duplicating it.

**Visual design.** `base.html`'s `<style>` block was rewritten around
CSS custom properties (`--color-*` design tokens) with a
`@media (prefers-color-scheme: dark)` override block, consistent with
the page's existing `color-scheme: light dark` declaration - so dark
mode is a data problem (swap the token values), not a second set of
rules to maintain. Status values (`queued`/`running`/`done`/`failed`)
render as colored pill badges instead of plain text. The policy-card
selection highlight uses the CSS `:has()` relational pseudo-class
(`.policy-card:has(input:checked)`) rather than JavaScript, since every
target browser for a self-hosted tool a developer runs locally supports
it.

## A bug caught by the redesign, before it shipped

Turning the status column into an `inline-flex` pill meant the class
could no longer sit directly on a `<td>` - `dashboard.html` originally
applied `class="status-{{ job.status }}"` to the table cell itself,
which would have broken that row's cell layout the moment the new CSS
landed. Caught during visual verification (a Playwright screenshot of
the dashboard looked subtly wrong) and fixed by moving the status class
onto a nested `<span>` instead, leaving the `<td>` a plain table cell.

## A bug caught in *verification*, not the product

While driving the upload flow end-to-end with Playwright (login →
upload a real file → watch it run to completion), the script
consistently ended up back on `/login` with its session cookie cleared,
and the server's access log never showed a `POST /upload` - only a
`POST /logout` each time. The cause was the verification script, not
the product: it selected the submit button with the generic
`button[type=submit]`, which also matches the header nav's own
"Log out" button - and that button appears earlier in the DOM (the
header renders before the page's `{% block content %}`), so a
non-strict `.click()` on that selector submitted the logout form
instead of the upload form. Rewriting the script to scope the selector
to the upload form (`form[action='/upload'] button[type=submit]`)
resolved it immediately; the webapp's routes and templates needed no
change here. Recorded because it's exactly the kind of false alarm that
looks like a server regression until the DOM is checked - and because a
future contributor debugging "upload seems to log the user out" should
find this instead of re-diagnosing it from scratch.

## Consequences

A first-time visitor can now tell, from the upload form alone, which
policy runs entirely offline and which one needs a one-time model
download - without reading the README or the YAML files. The page looks
considerably more finished, and the design-token approach means a
future accent-color or dark-mode tweak is a handful of variable edits,
not a re-audit of every rule.

Curated policy copy in `_DISPLAY_INFO` is one more place that can drift
from the actual YAML if a bundled policy's behavior changes without a
matching copy update - there's no automated check tying "audio disabled"
in the YAML to "Works offline" in the badge. Low risk today with only
two bundled policies, but worth a lint/test if the catalog grows.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
