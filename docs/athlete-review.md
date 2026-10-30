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
| P1 | A missing or invalid saved video is treated as upload success, so retry never transfers the needed video | Native pending-history and imported-video baselines show start-only retry after confirmation returns 400; `.gnhf/evidence/phase4-before` and `.gnhf/evidence/phase4-transfer-before` | A typed HTTP error distinguishes validation failure; local retry transfers the chosen clip again, while history explains the need to choose the original video again | All 14 consolidated native tests and both strengthened playback checks pass; no persistent transfer queue is added |
| P2 | A storage outage is reported as a bad athlete video | Confirmation caught all storage exceptions as HTTP 400, including connectivity and permission failures | Only absent or invalid objects return 400; service failures return retryable 503 and preserve the start-only recovery path | HTTP integration tests cover missing objects, unsupported metadata, connectivity, service failure, permission failure, and recovery; 24 Python tests pass |
| P2 | Automatic session removal and sign-out service failure retain the prior session's in-memory analysis queries | Corrected native baselines re-enter the same account during a history outage without restarting JavaScript; the old row and total remain visible; `.gnhf/evidence/phase5-baseline` | Clear queries at the shared removed-or-changed-session boundary before publishing identity changes; preserve same-athlete token refreshes | Both new session checks pass in the 15-of-16 consolidated run; the failed pagination check then passes twice; no cross-account disclosure is established |
| P2 | Sign-out service error says the athlete is still signed in after local credentials are removed | Native auth logout returns 503; welcome appears with Could not sign out | Explain local sign-out and unconfirmed remote revocation separately; disable duplicate submissions | Native sign-out outage and re-entry check passes; does not claim other sessions were revoked |
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

## Iteration 4 validation

This phase distinguishes a transfer failure, an unusable saved video, and an analysis-start service outage.
The pending-history native baseline reproduces a start-only retry action even after the saved video is reported missing or invalid.
The initial import baseline did not leave history after its tab tap and is not evidence of the upload defect.
The corrected import baseline follows the established result-to-capture path and reproduces an upload-success claim that contradicts the server's validation failure.
Native bundles are `/tmp/spolysis-overnight-phase4-before.xcresult` and `/tmp/spolysis-overnight-phase4-transfer-before.xcresult`.
Local retry now clears the unusable-upload assumption and transfers the selected clip again.
History-only jobs explain why the original video must be selected again, and pending jobs no longer display a reconstruction spinner before analysis starts.
Storage outages preserve the existing video and offer start-only retry; only missing or invalid objects require a new transfer.
The API change preserves the existing 400 response text and ownership checks, adds a retryable 503 for storage failures, and requires normal deployment before production behavior changes.
The 24 Python tests pass, including nine new HTTP integration cases for storage classification and recovery.
TypeScript and ESLint pass.
The final consolidated native pass completes all 14 tests with zero failures in 287.153 seconds.
It includes the 12 recovery tests, the signed-in import/viewer/share/sign-out journey, and authentication screens.
The first consolidated attempt passed 11 of 14: a dropped history tap made no detail request, its simulated confirmation outage leaked into the signed-in journey, and the missing sign-out then blocked the authentication smoke.
Signed-in setup now resets fixture state independently; history entry taps the visible row center without automatic interaction retries.
The failed tap trace was already centered, so the root cause of intermittent native input failure remains unestablished.
The consolidated pass did not repeat that failure.
Two affected transfer checks then gained explicit native video-ready assertions and both passed again in 67.183 seconds.
Their original result-title screenshots were captured during transition and did not establish loaded playback.
Final failure states and loaded playback were visually inspected at 1206 x 2622.
Review [missing video from history](screenshots/missing-upload-recovery.png), [invalid saved video](screenshots/upload-validation-recovery.png), and [transfer failure](screenshots/upload-transfer-recovery.png).
Exact commands and result bundles are in [Overnight handoff](overnight-handoff.md).
These checks use isolated HTTP failures and do not validate device airplane mode, app termination during transfer, or production R2/database writes.

## Iteration 5 validation

This phase covers the shared session lifecycle rather than only the successful profile sign-out handler.
Corrected native baselines reproduce retained in-memory history after both automatic expiry with rejected refresh and a sign-out HTTP 503.
The first short-session attempt used a still-valid access token; the installed auth SDK deliberately preserved it after proactive refresh rejection.
The corrected fixture uses a one-second access token and verifies an actual automatic refresh request before session removal.
Both baselines sign back in within the same JavaScript runtime while history is unavailable, making stale cache reuse observable.
User-specific query keys already separate different account IDs; this audit does not establish a cross-account data leak.
The fix clears queries before publishing a removed or changed identity and retains them for same-athlete token refreshes.
A service error now reports local sign-out truthfully and explains that remote session revocation is unconfirmed.
The consolidated native run passes 15 of 16 tests in 371.588 seconds, including both new session checks and the full signed-in journey.
The pagination check fails on an unrelated dropped result-entry tap before reaching pagination; the fixture receives no detail request.
It now starts directly in history and passes twice with zero failures in 44.866 seconds, retaining bounded request-count assertions and avoiding automatic tap retries.
Product source is unchanged after the consolidated run.
There is no uninterrupted 16-test pass on the final test source in this phase, and the general intermittent native input cause remains unestablished.
Four session screenshots were inspected at 1206 x 2622; the immediate revoked-session welcome screenshot captures navigation transition rather than stable layout.
Review the stable [sign-out service warning](screenshots/session-signout-service-warning.png) and [new-session history outage](screenshots/session-reentry-history-unavailable.png).
TypeScript, ESLint, viewer build, Ruff, fixture formatting, and changed TypeScript formatting pass.
No API/pipeline implementation or auth-library dependency changed.
These checks use isolated auth responses, not production session revocation or device airplane mode.
No secure-erasure or account-deletion claim is made.

## Ranked remaining audit

1. Continue capture guidance, actual network interruption, app termination during a transfer, and failed-job recovery.
   HTTP transfer-failure and missing-upload recovery are implemented in iteration 4.
   Rejected-job navigation, pending-job restart, and confirmation retry are implemented in iteration 2.
2. Audit device-offline sessions, privacy expectations, account deletion/retention, and cross-account behavior.
   Expired-session re-entry and sign-out service-error cleanup are implemented in iteration 5; history service-failure and pagination recovery are implemented in iteration 3.
   Airplane-mode behavior remains a separate claim.
3. Review coaching clarity, comparison interpretation, attribution, and the limits visible at the moment of review.
   The inspected volley result highlights the right elbow at estimated contact but recommends a right-knee change during preparation, so the relationship between the highlighted joint and coaching priority needs review.
4. Exercise Dynamic Type and smaller screens, loading/empty states, and accessible controls.
5. Consolidate the final native regression evidence after these cohesive phases.

Physical camera behavior, Android runtime, distribution signing, production database writes, external account access, and model accuracy remain separate unverified claims.
