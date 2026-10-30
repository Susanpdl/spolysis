# Athlete review

Native audit started 2026-10-30 on iPhone 17 Pro, iOS 26.5.
This is a reviewable development candidate, not a production release assertion.

## Evidence and priorities

| Severity | Issue and athlete impact | Reproduction and evidence | Implemented fix | Verification and limits |
| --- | --- | --- | --- | --- |
| P0 external | Production sign-in unavailable; real accounts and saved analyses blocked | Both configured Supabase hostnames fail local DNS resolution on 2026-10-30 | No production changes | Owner restoration required before real authentication and database validation |
| P1 | Completed analysis misleadingly says reconstruction is ongoing when result retrieval fails | Native processing history item becomes completed, result endpoint returns 503, spinner persists; `.gnhf/evidence/completion-before.png` | Distinguish completed-result loading and failure; retry saved result without upload; keep return-to-history action | Native completion-failure recovery passes in the consolidated suite; local fixture only |
| P1 | Video and 3D download failures leave text instructing a reload without an action | Native fixture returns 503 for actual pipeline media; baseline recovery tests fail because retry controls are absent | Visible media retry fetches fresh signed links and remounts failed video even if URL is unchanged; bounded motion download with cancellation; refresh errors remain retryable | Native media and refresh-failure recovery passes; actual signed-link expiry timing still untested |
| P2 validation | Native checks drop 150 ms long presses on welcome and history | Original smoke and signed-in checks fail before navigation or a result request; ordinary taps complete the full signed-in journey | Ordinary taps, hittability wait, and password-dialog handling in native checks | Signed-out smoke passes in consolidated regression |

## Journey covered

The native fixture journey completed history, playback of an existing R2 pipeline overlay, 3D playback/pause/rotation/reset, stroke and hand selection, library import, native upload, result sharing, account review, and sign-out.
Media was downloaded read-only from an existing pipeline result, not generated for this audit.
The imported overlay exercises the upload path but is not raw footage suitable for evaluating reconstruction quality.
The fixture returns predetermined analysis metadata and does not analyze imported footage.
All five consolidated native tests pass with zero failures in 115.025 seconds.
The welcome, account creation, history, capture setup, viewer, recovery states, and recovered video were visually inspected in 1206 x 2622 simulator screenshots.
Review the [completed-result recovery](screenshots/recovery-completed-result.png), [video recovery](screenshots/recovery-video.png), and [motion recovery](screenshots/recovery-motion.png) screens.
The screenshot subjects and authentication are isolated fixtures using actual existing pipeline media.

## Ranked remaining audit

1. Audit capture guidance, upload interruption and navigation, rejected and failed jobs, and confirmation retry without duplicate upload.
2. Audit session expiry/recovery, offline history, pagination failure, privacy expectations, and account boundaries.
3. Review coaching clarity, comparison interpretation, attribution, and the limits visible at the moment of review.
   The inspected volley result highlights the right elbow at estimated contact but recommends a right-knee change during preparation, so the relationship between the highlighted joint and coaching priority needs review.
4. Exercise Dynamic Type and smaller screens, loading/empty states, and accessible controls.
5. Consolidate the final native regression evidence after these cohesive phases.

Physical camera behavior, Android runtime, distribution signing, production database writes, external account access, and model accuracy remain separate unverified claims.
