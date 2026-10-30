# Athlete review

Native audit started 2026-10-30 on iPhone 17 Pro, iOS 26.5.
This is a reviewable development candidate, not a production release assertion.

## Evidence and priorities

| Severity | Issue and athlete impact | Reproduction and evidence | Implemented fix | Verification and limits |
| --- | --- | --- | --- | --- |
| P0 external | Production sign-in unavailable; real accounts and saved analyses blocked | Both configured Supabase hostnames fail local DNS resolution on 2026-10-30 | No production changes | Owner restoration required before real authentication and database validation |
| P1 | Completed analysis misleadingly says reconstruction is ongoing when result retrieval fails | Native processing history item becomes completed, result endpoint returns 503, spinner persists; `.gnhf/evidence/completion-before.png` | Distinguish completed-result loading and failure; retry saved result without upload; keep return-to-history action | Native completion-failure recovery passes in the consolidated suite; local fixture only |
| P1 | Video and 3D download failures leave text instructing a reload without an action | Native fixture returns 503 for actual pipeline media; baseline recovery tests fail because retry controls are absent | Visible media retry fetches fresh signed links and remounts failed video even if URL is unchanged; bounded motion download with cancellation; refresh errors remain retryable | Native media and refresh-failure recovery passes; actual signed-link expiry timing still untested |
| P1 | Selecting another unfinished analysis keeps showing the previous job, including hiding a rejection | Open a processing row, return to analyses, open a rejected row; the native screen still reconstructs the first job; `.gnhf/evidence/phase2-wrong-job-before.png` | Navigation identifies progress screens by job or clip and result screens by job; completion navigation runs only for the focused progress screen | Native regression covers switching to a rejected job and returning to capture |
| P1 | A successfully uploaded video cannot start from history after confirmation is interrupted | Reopen a pending job; only a queued spinner and history button appear; native baseline fails the resume assertion | Pending history offers retry through the existing ownership-checked confirmation endpoint; server verifies the uploaded object before starting | Native regression checks confirmation without a video upload; fixture evidence does not validate production R2 verification |
| P1 | History repeats failed page requests indefinitely and leaves older analyses inaccessible | Seed 22 jobs, interrupt page 2, scroll to the bottom; native baseline repeatedly requests page 2 with a spinner and no recovery action; `.gnhf/evidence/phase3-before` | Automatic pagination stops after the normal query retry budget; a specific error and retry action preserve loaded rows | Native pagination failure/recovery passes; exactly three failed attempts and one explicit successful retry; isolated service outage, not device airplane mode |
| P2 | Confirmation failure is presented as a failed upload, encouraging unnecessary re-selection | Native imported clip uploads successfully, fixture confirmation returns 503, UI says Upload interrupted; `.gnhf/evidence/phase2-confirm-before.png` | Distinct confirmation failure title, explicit reuse explanation, and Start analysis again action; progress content scrolls when space is limited | Native regression checks one video transfer and two confirmation attempts |
| P2 | History background polls activate the native pull-to-refresh control and can interfere with row interaction | Native pending-job tap at the five-second poll made no detail request and left history visible; `/tmp/spolysis-overnight-phase2-verified.xcresult`; the list used every refetch as native refreshing | Only an athlete's pull-to-refresh gesture now activates the native refresh control; automatic status polling continues | Repeated affected native flows validate selection and the import journey; polling correlation does not establish every simulator tap failure's cause |
| P2 | Cached analysis statuses look current after history updates fail | Drop history responses while a processing job polls; native screen still shows ANALYZING with no warning despite repeated 503s; `.gnhf/evidence/phase3-refresh-before` | Explain that loaded statuses may be stale and offer explicit update retry; unknown initial totals no longer claim zero analyses | Native poll-failure/recovery and initial-failure/empty-state checks pass; no persistent offline cache is introduced |
| P2 validation | Native checks drop 150 ms long presses on welcome and history | Original smoke and signed-in checks fail before navigation or a result request; ordinary taps complete the full signed-in journey | Ordinary taps, hittability wait, and password-dialog handling in native checks | Signed-out smoke passes in consolidated regression |

## Journey covered

The native fixture journey completed history, playback of an existing R2 pipeline overlay, 3D playback/pause/rotation/reset, stroke and hand selection, library import, native upload, result sharing, account review, and sign-out.
Media was downloaded read-only from an existing pipeline result, not generated for this audit.
The imported overlay exercises the upload path but is not raw footage suitable for evaluating reconstruction quality.
The fixture returns predetermined analysis metadata and does not analyze imported footage.
Phase 1 passed all five consolidated native tests with zero failures in 115.025 seconds.
The welcome, account creation, history, capture setup, viewer, recovery states, and recovered video were visually inspected in 1206 x 2622 simulator screenshots.
Review the [completed-result recovery](screenshots/recovery-completed-result.png), [video recovery](screenshots/recovery-video.png), and [motion recovery](screenshots/recovery-motion.png) screens.
The screenshot subjects and authentication are isolated fixtures using actual existing pipeline media.

## Iteration 2 validation

Native baselines separately reproduced wrong-job progress, a pending job without a start action, and misleading confirmation failure.
The initial switching test was obstructed by a delayed system password-save prompt; the signed-in rerun reproduced the actual defect.
The test now waits for that prompt after sign-in before opening history.
Recovery setup also resets fixture jobs and counters before every test, since assertion aborts can bypass Swift defer cleanup.
A later dropped history tap coincided with background polling; the refresh-control change removes that automatic animation.
The consolidated run passed seven of eight tests before the final history-refresh fix.
After that fix, pending-job recovery, distinct-job selection, and the full signed-in journey each passed twice: six executions with zero failures in 165.658 seconds.
The other five test methods passed in the preceding consolidated run.
Exact commands, failed-run evidence, and claim boundaries are recorded in [Overnight handoff](overnight-handoff.md).
The [pending-upload action](screenshots/pending-upload-recovery.png), [selected rejection](screenshots/rejected-analysis-selected.png), and [confirmation failure](screenshots/upload-confirmation-recovery.png) were inspected at 1206 x 2622.
The pending-job recovery uses an existing endpoint and does not add a queue, alter job ownership, or re-upload footage.
No physical-device transfer interruption or app-termination recovery is claimed.

## Iteration 3 validation

This phase addresses trustworthy history during service failures.
The pagination baseline repeatedly requested page 2 after the normal retry budget was exhausted, with no failure explanation or retry action.
The first refresh test used a swipe that did not issue a request and is not evidence of a failed refresh.
The corrected baseline uses processing-job polling and confirms multiple failed history responses while the cached row remains unchanged without warning.
Native baselines are `/tmp/spolysis-overnight-phase3-before.xcresult` and `/tmp/spolysis-overnight-phase3-refresh-before.xcresult`.
The implementation preserves loaded rows, distinguishes stale status from incomplete pagination, and provides separate retry controls.
Initial history failure shows an unavailable total; only a successful empty response shows zero and the first-analysis guide.
The final consolidated native suite passes all 11 tests with zero failures in 210.171 seconds.
It covers history failure/empty/recovery states, completed-result and media recovery, selected-job identity, pending-job restart, confirmation retry, the signed-in import/viewer/share/sign-out journey, and authentication screens.
Pagination asserts exactly three failed attempts, followed by one successful explicit retry that exposes the final row.
All six new history screenshots were inspected at 1206 x 2622, including the recovered states.
Review [initial history failure](screenshots/history-initial-recovery.png), [incomplete history recovery](screenshots/history-pagination-recovery.png), and [stale status warning](screenshots/history-stale-status.png).
TypeScript, ESLint, viewer build, Python lint, fixture formatting, and HomeScreen formatting pass.
The Python regression suite was not repeated because API and pipeline implementation are unchanged.
These are isolated HTTP 503 service failures, not device airplane mode or production account validation.

## Ranked remaining audit

1. Continue capture guidance, transfer interruption, app termination during a transfer, failed jobs, and missing-upload recovery.
   Rejected-job navigation, pending-job restart, and confirmation retry are implemented in iteration 2.
2. Audit session expiry/recovery, device offline across screens, privacy expectations, and account boundaries.
   History service-failure and pagination recovery are implemented in iteration 3; airplane-mode behavior remains a separate claim.
3. Review coaching clarity, comparison interpretation, attribution, and the limits visible at the moment of review.
   The inspected volley result highlights the right elbow at estimated contact but recommends a right-knee change during preparation, so the relationship between the highlighted joint and coaching priority needs review.
4. Exercise Dynamic Type and smaller screens, loading/empty states, and accessible controls.
5. Consolidate the final native regression evidence after these cohesive phases.

Physical camera behavior, Android runtime, distribution signing, production database writes, external account access, and model accuracy remain separate unverified claims.
