# Spolysis session handoff

Last updated: 2026-10-30.
This is a portable summary of project decisions and work from the current conversation, not an export of private assistant memory.
Treat the working tree and current user instructions as authoritative when this snapshot becomes stale.

## Start here

Read `AGENTS.md` and `CLAUDE.md` before editing.
Use `README.md` for setup and checks and `docs/IMPLEMENTATION_STATUS.md` for recorded validation and release blockers.
The workspace is `/Users/spoudel/Desktop/spolysis`.
The GitHub remote is `https://github.com/Susanpdl/spolysis.git`, and the current branch is `main`.
Inspect `git status` before working and preserve uncommitted changes.

## User preferences and decisions

The user likes a green brand palette and the whimsical, pastel, watercolor and ink illustration direction inspired by Fly.io's landing page.
Use original Spolysis artwork and characters, not Fly.io assets.
`DESIGN.md` and `characters.md` are design references; adapt their ideas to this tennis app rather than copying unrelated product concepts.
The user explicitly loved the new storybook landing illustration and approved the landing page redesign.
The subsequent app-wide redesign was rejected and reverted in full.
Do not reintroduce that redesign or infer approval to spread the landing artwork across every screen.
Make targeted changes when the user identifies a specific UI issue.

The user prefers practical execution and minimal repeated permission questions.
Do not interpret historical broad permissions as a new overnight objective or unlimited authorization for unrelated actions.
Follow the explicit limits and overnight requirements in `AGENTS.md`.
The user prefers meaningful end-to-end verification over frequent unit-test runs after every small edit.
Never claim visual or production validation based solely on static checks or fixture-backed scenes.

## Accepted product direction

Tennis is the implemented sport.
Table tennis, soccer, and basketball have placeholders and a sport catalog so more sports can be added later.
Do not build or claim working analysis backends for those placeholders.

The motion viewer should use a recognizable human dummy, a tennis racket attached to the hand, and an environment that makes orientation clear.
The user wants a front-facing default view and "Show your swing" unchecked initially.
Playback speed controls and simple coaching cues linked to the 3D movement are desired.
The user prefers understandable action bullets over exact angle deviations as the main explanation.
The tennis ball and ball-flight path were removed at the user's request.
The gold racket-grip trajectory remains.
Viewer scene source is `app/viewer/viewer.js`; HTML packaging is in `app/scripts/build-viewer.mjs`.
Rebuild with `npm --prefix app run build:viewer`; do not manually edit generated viewer output.

## Approved landing page

`app/src/screens/WelcomeScreen.tsx` contains the editorial landing layout with cream and sage styling, a serif headline, signup action, and three explanatory steps.
`app/src/components/LandingPreview.tsx` displays the bundled illustration using React Native Image.
The artwork is `app/assets/illustrations/tennis-storybook.png`.
It depicts an apricot cloud sprite playing tennis on a floating garden court with an owl coach, pastel clouds, and watercolor texture.
The old SVG mannequin illustration was replaced, not retained as the landing image.
The image uses a 3:2 aspect ratio and contain resizing to preserve the composition.
The illustration is decorative marketing art, not an actual analysis screenshot.

## Git checkpoint

Commit `e256ce0` contains the earlier app experience, sports placeholders, viewer changes, and green theme.
Commit `af76c00` contains the accepted landing page redesign and storybook illustration.
Both were pushed to `origin/main`.
The rejected app-wide redesign was never committed and was reverted to `af76c00`.

## Latest padding fix

The latest user issue was padding inside the home empty-state section titled "Your first session starts here".
The onboarding guide previously added another padded, bordered card inside that section, squeezing its content.
`app/src/components/GettingStarted.tsx` now accepts `embedded?: boolean`.
Embedded mode removes its own padding, border, corner radius, and redundant heading, and stretches across the parent content width.
Number badges do not shrink.
`app/src/screens/HomeScreen.tsx` uses `<GettingStarted embedded />` in that empty state.
Standalone uses of GettingStarted retain their existing card presentation.
The user authorized committing and pushing this fix together with the handoff notes.
Consult Git history for the resulting commit and push status.

## Verification and limitations

The latest padding change passed app TypeScript checking, ESLint, and `git diff --check`.
Commands were `npm --prefix app run typecheck` and `npm --prefix app run lint`.
Simulator access through computer-use tooling was denied in this session.
The latest landing page and padding fix have not been visually verified in the simulator.
Do not treat prior screenshots in `docs/screenshots` as evidence of the current UI.
An earlier viewer orientation check used a browser render with synthetic motion, not a production end-to-end analysis.
The user previously reported reactivating Supabase; current service health has not been verified by this handoff.

## Suggested next action

If continuing the padding task, visually inspect the home empty state on a narrow phone and with larger text when simulator access is available.
Confirm the guide fits within the outer card, numbers remain readable, and the CTA does not overflow.
Keep the accepted landing page and artwork intact.
The padding fix and handoff notes were authorized for commit and push on 2026-10-30.
