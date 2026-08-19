<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0015. A real marketing landing page at "/", not a redirect straight to /login

- Status: Accepted
- Author: Ritesh Ambastha

## Context

`redactguard-webapp`'s `"/"` route (ADR-0011) has always just redirected
- to `/dashboard` if you're signed in, to `/login` otherwise. That's a
reasonable default for an app shell, but it means the very first thing
an unauthenticated visitor sees is a bare login form with zero context:
no explanation of what RedactGuard does, why it might matter to them,
or any reason to prefer signing up here over closing the tab. For a
project meant to be evaluated as a portfolio piece - and for the
product pitch itself, which is specifically about *not* trusting a
third party with your PII - that first impression matters.

## Decision

`"/"` now renders a real single-page marketing site
(`templates/landing.html`) for anonymous visitors; signed-in visitors
still redirect straight to `/dashboard`, unchanged. The page is a
standalone template rather than extending `base.html` - a marketing
hero section with a full-bleed gradient background and wide feature
grids doesn't fit the app shell's centered 860px container, and
`base.html`'s header nav (Dashboard / New job / Log out) has nothing to
show an anonymous visitor anyway.

The page's CSS custom properties (colors, radii, shadow) are pulled
from a new shared partial, `_design_tokens.html`, included by both
`base.html` and `landing.html`, rather than copy-pasted - the app shell
and the marketing page must always agree on the same indigo/light-dark
palette, and a shared include is the only way that's guaranteed rather
than merely intended.

Content and structure, in order: a hero with the core pitch and both
CTAs; a callout addressing security/compliance/engineering readers
specifically (the ask that prompted this page named that audience
directly - see the "who this is for" list); a four-item feature grid
tied to the project's own ADRs (self-hosted, ensemble detection,
verify-then-retry, policy-as-code) rather than generic marketing
claims; a four-step "how it works" strip; a second CTA banner; and a
contact section.

**Contact us** links to GitHub Issues/Discussions on the real repo
rather than a contact form. There's no email-sending backend in this
project, and building one solely to receive a "contact us" submission
would be infrastructure built for its own sake on a self-hosted OSS
tool where "open an issue" is both more idiomatic and more honest than
a form that quietly emails someone behind the scenes.

**Both signup and signin are deliberately repeated three times** (nav,
hero, closing CTA banner) as actual buttons (`.btn-primary`/
`.btn-outline`), not just text links - the explicit ask was to have
them "highlighted," and a visitor scrolling through a single-page site
shouldn't have to scroll back to the top to act on it.

## A responsive bug caught by an actual mobile screenshot

The first version's header nav button read "Get started free" next to
"Sign in" - fine on desktop, but at a 390px mobile viewport (verified
with a real Playwright screenshot, not just a browser resize in
imagination) the button's text wrapped onto three lines and blew out
the header's height. Fixed by shortening the header nav's CTA
specifically to "Sign up" (the hero and closing banner keep the fuller
"Get started free" - they have the room), adding `white-space: nowrap`
to every button so text can never wrap again, and a `max-width: 420px`
media query tightening header padding/gaps for narrow phones. Verified
again down to a 320px viewport (the narrowest realistic phone width)
after the fix.

## Consequences

An anonymous visitor arriving at the deployed webapp - or a portfolio
reviewer clicking the demo link - now gets a real explanation of what
the product is and who it's for before being asked to create an
account, with sign-up/sign-in reachable from anywhere on the page.
Both routes' behavior is pinned down in `test_landing_page.py` and the
updated `test_auth_routes.py` (the old "`/` always redirects to
`/login`" tests would have silently kept passing for the wrong reason
otherwise - they're rewritten to check the landing page renders, and to
check `/dashboard`'s redirect instead for the "still logged out"
assertions that used to lean on `/`'s old behavior).

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
