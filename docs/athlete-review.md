# Athlete review

Native audit started 2026-10-30 on iPhone 17 Pro, iOS 26.5.
This is a reviewable development candidate, not a production release assertion.

## Evidence and priorities

| Severity | Issue and athlete impact | Reproduction and evidence | Implemented fix | Verification and limits |
| --- | --- | --- | --- | --- |
| P0 validation | Production sign-in and database writes remain unverified | Earlier DNS failure was superseded by user-supplied Supabase GoTrue and Fly health HTTP 200 checks at 2026-10-30 21:58 America/New_York | No production changes | Connectivity alone does not validate authentication or persistence |
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

## Current GNHF backend verification

Run `objective-make-spoly-e894a3`, iteration 1, reproduced eight authentication-service failures being mislabeled as invalid credentials through protected HTTP requests and the real GoTrue SDK.
Service failures now return retryable HTTP 503 without authorizing requests or creating jobs; rejected credentials remain HTTP 401.
The same token succeeds after isolated upstream recovery.
See [Overnight handoff](overnight-handoff.md) for baseline evidence and validation limits.
No native UI or production authentication claim is made by these checks.

Iteration 2 reproduced completion overwriting a concurrent failure or rejection through the HTTP callback lifecycle.
Completion now guards its status write, returns HTTP 409 if the terminal callback wins, and preserves the athlete-visible terminal message and result-access gate.
All 36 Python tests pass, including both callback orderings and duplicate completion compatibility.
The isolated database adapter establishes handler behavior, not deployed database concurrency; the existing separate result write can leave an inaccessible row.
See [Overnight handoff](overnight-handoff.md) for baseline evidence and the deferred transactional option.

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

## Continuation confirmation recovery

Continuation run bfd94b iteration 1 reproduces Temporal connect/start outages and post-start metadata failure through protected HTTP confirmation requests.
Orchestration outages now return retryable 503 with saved-video reuse guidance; metadata failure after successful workflow acceptance no longer falsely reports that analysis failed to start.
All 49 Python tests pass, including recovery and processing callbacks without saved workflow metadata; Ruff passes.
These are isolated service-adapter tests, not native UI or production signed-in validation.

## Continuation result availability

Continuation run bfd94b iteration 2 reproduces completed-result HTTP 200 responses for missing, empty, and unavailable storage artifacts, and HTTP 500 for signing failure.
Result fetch now verifies nonempty stored artifacts before issuing private links and returns retryable HTTP 503 when media or signing is unavailable.
Ownership is checked before any storage access; the completed job remains completed so the athlete can retry loading its result.
All 57 Python tests and Ruff pass, including overlay and skeleton failure/recovery checks and unauthorized access without storage calls.
These are isolated HTTP/storage-adapter checks, not production R2 or native UI validation.

## Continuation upload lifetime

Continuation run bfd94b iteration 3 increases private upload URL validity from five minutes to one hour for the supported MP4 and MOV flows.
HTTP issuance tests use real local signing and preserve pending-job ownership and signed content-type binding.
All 59 Python tests and Ruff pass, including existing confirmation-time size and file-type rejection checks.
This validates the URL contract without production storage access; it does not establish cellular transfer reliability or in-flight expiry behavior.
Physical-device transfer interruption and app-termination recovery remain unverified.

## Continuation completion delivery

Continuation run bfd94b iteration 4 reproduces a saved result becoming failed after its completion status write returns HTTP 500.
The failure callback now leaves a job with a saved result unchanged, allowing a repeated completion callback to restore result access.
Workflow completion and rejection delivery errors no longer invoke the analysis-failure callback; processing and analysis errors still do.
All 64 Python tests and Ruff pass, including HTTP partial-completion recovery and isolated workflow branch checks.
These checks do not run a Temporal server or establish production database concurrency.
Exhausted delivery retries still require operational callback recovery; the job can remain processing until delivery succeeds.

## Continuation public API protection

Continuation run bfd94b iteration 5 disables public API documentation routes and limits new upload URL requests to 10 per minute per client address.
HTTP regression checks verify that excess requests create no jobs or signed links, while saved-video confirmation and job reads remain available.
All 68 Python tests and Ruff pass.
The limiter is process-local; production proxy addressing and enforcement across replicas remain unverified.
This is isolated API validation, not a production load test or native UI check.

## Continuation setup guidance

Continuation run bfd94b iteration 6 aligns README onboarding with the current welcome and empty-home button labels and includes migration 004 in rollout prerequisites.
The current-status guidance now reflects the previously recorded connectivity recovery without claiming production sign-in or database validation.
Verification is a source/document comparison and a clean diff check, not a new native journey or production service check.
The old welcome selectors in `SmokeTests.swift` remain a known local follow-up; historical native passes do not validate the current landing screen.

## Continuation native test compatibility

Continuation run bfd94b iteration 7 updates welcome, sign-out, session recovery, and empty-history selectors to the current approved copy without changing product screens or artwork.
The native build also exposed two shared navigation helpers scoped privately to the recovery class; they now live in a file-local XCTestCase extension so both test classes compile.
The generated test project passes simulator build-for-testing for arm64 and x86_64.
All 68 Python tests, Ruff, app TypeScript, ESLint, and diff checks pass.
CoreSimulator access fails in this sandbox with connection refused and Operation not permitted, so no native test execution or new screenshots are claimed.
A simulator run remains necessary to verify accessibility labels and navigation at runtime.

## Continuation workflow wait bounds

Continuation run bfd94b iteration 8 adds five-minute activity queue-wait limits and a two-hour execution limit for new analysis workflows.
All 72 Python tests and Ruff pass, including HTTP workflow-start options and isolated timeout-failure branches.
Analysis activity failure requests retrying the same clip; a result-delivery failure does not overwrite successful analysis with recapture guidance.
No real Temporal timeout or native UI behavior was exercised.
A completely absent worker cannot deliver any status callback, and workflow execution timeout alone does not change the athlete's database status.
Live worker and poller verification and stranded-job recovery remain captain responsibilities.

## Continuation history failure reasons

Continuation run bfd94b iteration 9 exposes saved rejection and service-failure reasons directly in history rows and their accessibility labels.
The reason occupies the card width below the summary and is not truncated; completed and active jobs do not display stale failure text.
A local render probe reproduced the missing reason before the change and passes afterward, including missing-reason compatibility.
The native selected-rejection test now asserts the history button's reason before navigating, and the simulator test target builds successfully.
All 72 Python tests, Ruff, TypeScript, ESLint, and changed-screen formatting pass.
CoreSimulator remains inaccessible in this sandbox, so these checks do not establish native layout, VoiceOver behavior, or a runtime UI-test pass.

## Continuation estimated-phase viewer entry

Continuation run bfd94b iteration 10 opens the motion viewer paused at the supplied estimated contact phase instead of always at frame zero.
Historical results without valid phase metadata still open at frame zero.
An isolated execution of the actual viewer load handler reproduces the old behavior and verifies the fix, boundary values, invalid metadata, and playback reset.
All 72 Python tests, Ruff, TypeScript, ESLint, and the viewer build pass.
CoreSimulator and browser access remain blocked, so native interaction and visual presentation are unverified.
The phase is a wrist-motion estimate, not detected ball contact; analyzed-window timing and automatic selection explanation remain follow-up work.
