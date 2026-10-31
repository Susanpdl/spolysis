# Overnight handoff

## Current phase

Run `objective-make-spoly-e894a3`, iteration 1, hardens protected API requests during authentication-service outages.
Work stays in the isolated GNHF worktree; no commits, pushes, deployment, production mutations, or additional agents.
GNHF owns its run `notes.md`; this worker does not edit it.
Earlier phases below describe the previous run and retain their original evidence.

### Authentication outage classification

The HTTP baseline exercised history and upload creation through the real GoTrue SDK with isolated upstream responses.
All eight outage cases returned misleading HTTP 401 before the fix: 500, 502, 503, 504, 429, connection failure, timeout, and malformed successful response.
Baseline log: `/tmp/spolysis-e894a3-auth-before.log` (eight failures and two passing credential-rejection checks).
Protected endpoints now fail closed with HTTP 503 and a retry message when session verification is unavailable.
Upstream 401 and 403 still reject credentials with HTTP 401.
Regression checks verify that outages create no jobs or workflows and that the same token can read history and create an owned job after recovery.
This validates local HTTP and SDK behavior, not production authentication, database writes, or native session behavior.
Validation: `.venv-test/bin/python -m pytest -q` passes all 34 tests in 37.32 seconds.
Ruff over `api pipeline tests`, changed Python-file formatting, `pip check`, and `git diff --check` pass.
Two existing dependency deprecation warnings remain for Starlette's httpx adapter and Supabase's gotrue package.
A separate Python 3.11 `.venv-test` was installed in this worktree; no mutable dependencies are shared.
No background services were started, and all installation and validation processes exited.
Checkpoint: `.gnhf/checkpoints/iteration-1-auth-outage.patch`.
The change needs deployment before production behavior changes.

The user supplied 2026-10-30 21:58 America/New_York health evidence: Supabase GoTrue and Fly `/health` returned HTTP 200.
That supersedes the earlier DNS-outage snapshot below, but does not establish production sign-in or database-write readiness.
Remaining work includes callback/Temporal recovery auditing, coaching alignment, capture and failed-job recovery, and narrow-phone/Dynamic Type verification.
The loop stop condition is not met.

## Current GNHF iteration 2: terminal callback ordering

The HTTP lifecycle reproduction interleaves a failure or rejection callback after completion reads the job status and saves its result, but before it updates the job.
Both baseline cases returned HTTP 200 and overwrote the terminal status with completed.
Baseline evidence: `/tmp/spolysis-e894a3-callback-before.log` (two failing regression cases).
Completion now conditionally updates only pending, processing, or already completed jobs and returns HTTP 409 when a terminal decision wins the race.
The athlete retains the failure or rejection message, and the result endpoint refuses to expose the saved result for that terminal job.
Duplicate completion remains supported; late processing, failure, and rejection callbacks preserve completed results.

Validation: all 36 Python tests pass in 3.82 seconds; Ruff over `api pipeline tests`, changed Python-file formatting, and diff whitespace checks pass.
Two existing dependency deprecation warnings remain.
Tests exercise real HTTP handlers with isolated storage, workflow, and database adapters and deterministic callback ordering; they do not validate production Postgres concurrency or a deployed worker.
The existing two-write result/status contract can still leave an inaccessible result row when a terminal callback wins.
A database transaction could make those writes atomic, but requires a coordinated database function/migration and is deferred; the conditional status update is the recommended bounded fix within this iteration.
No schema, callback name, ownership rule, or deployment changed.
No background services were started.
Checkpoint: `.gnhf/checkpoints/iteration-2-terminal-callback.patch`.
Further Temporal delivery recovery, coaching alignment, and native narrow-phone verification remain in scope, so the loop stop condition is not met.

## Completed work

- Phase 1: completed-result retry, refreshed signed-link recovery for video and motion, bounded and cancellable motion download, and repaired native test interactions.
- Phase 2: progress routes identify each job or clip, result routes identify each job, and offscreen completion waits for focus before navigating.
- Pending jobs reopened from history can retry confirmation using the existing ownership-checked endpoint without uploading again.
- Confirmation failure explains that the video transfer finished and offers Start analysis again.
- Progress content scrolls when vertical space is limited.
- Background history polls no longer activate the native pull-to-refresh animation; manual refresh keeps its own loading state.
- Native tests cover distinct-job navigation, rejection guidance, pending-job restart, and confirmation retry with transfer counters.
- Recovery test setup resets fixture state before every test, because assertion aborts can bypass Swift defer cleanup.
- Sign-in waits for the delayed native password-save prompt before opening history.
- Phase 3: loaded history remains visible with a stale-status warning and retry when refresh fails; unavailable initial history no longer claims zero analyses.
- Failed pagination stops automatic requests after the normal retry budget and offers explicit retry for older analyses.
- Native history checks cover initial outage, a genuinely empty account, failed processing-job polling, and second-page recovery with bounded request counts.
- Phase 4: missing or invalid saved uploads clear the local upload-success assumption and retry the actual transfer when the selected clip remains available.
- History-only pending jobs direct the athlete to select the original video again after validation fails; pending jobs no longer show a reconstruction spinner before start.
- Storage service, permission, and connectivity failures return retryable 503 rather than claiming the athlete's video is invalid; ownership and the existing 400 validation contract remain intact.
- Native transfer-failure and missing-video checks assert transfer and confirmation counts plus recovered video readiness; nine new HTTP integration cases bring the Python suite to 24 passing tests.
- Signed-in tests reset the fixture independently so a failed recovery assertion cannot leak a simulated outage into the next journey.

- Phase 5: in-memory queries are cleared before a removed or changed authenticated identity is published, including automatic expiry and sign-out service failures.
- Sign-out feedback distinguishes removed local credentials from unconfirmed remote revocation; repeated submissions are disabled during the request.
- Two new native checks re-enter the same account without restarting JavaScript and verify that an unavailable history service cannot expose the previous session's cached rows.

## Native setup

The installed `com.spolysis.app` is a compatible development shell without an embedded JavaScript bundle.
Use Metro from this checkout; no native rebuild was required.
Simulator: iPhone 17 Pro, iOS 26.5, UDID `858FB450-9823-4060-AADB-CDB3CBB58445`.
The system Ruby has `xcodeproj` 1.28.1; CocoaPods is unnecessary for this installed shell.
Every command below runs from the repository root.

```sh
xcrun simctl boot 858FB450-9823-4060-AADB-CDB3CBB58445
xcrun simctl bootstatus 858FB450-9823-4060-AADB-CDB3CBB58445 -b
ruby app/e2e/create-project.rb /tmp/SpolysisOvernightUITests.xcodeproj
```

Start the fixture and Metro in separate terminals:

```sh
.venv-test/bin/python app/e2e/fixture.py --media-dir .gnhf/media --result .gnhf/media/result.json
```

```sh
EXPO_PUBLIC_SUPABASE_URL=http://localhost:8877 EXPO_PUBLIC_SUPABASE_ANON_KEY=fixture-anon EXPO_PUBLIC_API_URL=http://localhost:8877 npm --prefix app start -- --clear --port 8081
```

Actual pipeline media is in ignored `.gnhf/media/overlay.mp4`, `.gnhf/media/skeleton.json`, and `.gnhf/media/result.json`.
Phase 1 downloaded it read-only from `results/34406f21-3fa4-425e-918f-7f7efad187e3/` using main-checkout ignored configuration in memory.
No credentials were copied into this worktree or printed.
The simulator library already contains the overlay used for import; it exercises transfer behavior, not reconstruction accuracy on raw footage.
If the library is reset, use `xcrun simctl addmedia 858FB450-9823-4060-AADB-CDB3CBB58445 .gnhf/media/overlay.mp4`.
Fixture credentials must never enter a distribution build.

## Phase 5 verification

The corrected native baseline reproduces retained history after automatic expired-session removal and after a sign-out HTTP 503.
The real auth SDK receives the revoked-refresh-token response and removes the session; no app-only session bypass is used.
Its bundle is `/tmp/spolysis-overnight-phase5-baseline.xcresult`, log is `/tmp/spolysis-overnight-phase5-baseline.log`, and attachments are `.gnhf/evidence/phase5-baseline`.
Both checks fail on the expected missing cache cleanup before implementation.
The sign-out flow also visibly reports failure over the welcome screen after local credentials have already been removed.
An earlier revocation attempt used a still-valid token, which the installed SDK preserves after a proactive refresh rejection; that attempt is not evidence of failed session removal.
The corrected fixture issues a one-second token so the rejection occurs after real expiry.
The sign-in helper dismisses the delayed native password-save prompt before inspecting re-entry.

```sh
xcodebuild clean test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase5-final.xcresult CODE_SIGNING_ALLOWED=NO
```

The consolidated run passes 15 of 16 tests in 371.588 seconds.
Both new session checks pass, as do the other recovery flows, imported-video/viewer/share/sign-out journey, and authentication smoke.
The pagination test fails before its pagination assertions because its unrelated result-entry tap makes no detail request.
Its captured hierarchy remains on history with the intended row visible; the broader intermittent native input cause remains unestablished.
The pagination check now starts directly in history and avoids that unnecessary result visit without automatic tap retries.
Product code is unchanged after the consolidated run.
The updated pagination check passes twice with zero failures in 44.866 seconds:

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests/ResultRecoveryTests/testHistoryNextPageFailureOffersRetry -test-iterations 2 -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase5-pagination.xcresult CODE_SIGNING_ALLOWED=NO
```

There is no uninterrupted 16-test pass on the final test source in this phase.
The consolidated log is `/tmp/spolysis-overnight-phase5-final.log`; affected-flow log is `/tmp/spolysis-overnight-phase5-pagination.log`.
Attachments are `.gnhf/evidence/phase5-final` and `.gnhf/evidence/phase5-pagination`.
The four new session screenshots were inspected at 1206 x 2622.
The immediate revoked-session welcome capture occurs during navigation transition; it is not used as stable layout evidence.
The stable warning and re-entry outage captures are preserved under `docs/screenshots/session-*.png`.
The consolidated journey ends signed out; the later pagination checks sign back into the isolated fixture and end in history before termination.
Metro log: `/tmp/spolysis-overnight-phase5-metro.log`; fixture log: `/tmp/spolysis-overnight-phase5-fixture.log`.
Product and app-directory test files remain unchanged during the consolidated run.
TypeScript, ESLint, viewer build, Ruff, fixture formatting, changed TypeScript formatting, and diff whitespace checks pass.

```sh
npm --prefix app run typecheck
npm --prefix app run lint
npm --prefix app run build:viewer
.venv-test/bin/python -m ruff check api pipeline tests app/e2e/fixture.py
.venv-test/bin/python -m ruff format --check app/e2e/fixture.py
app/node_modules/.bin/prettier --check app/src/hooks/useAuth.ts app/src/screens/ProfileScreen.tsx
git diff --check
```

No API or pipeline implementation changed, so the Python regression suite is not repeated in this phase.
The phase 4 suite remains the latest CPU regression result at 24 passing tests.
This phase clears in-memory queries and unmounts the signed-in navigation tree; it does not claim secure erasure of exported files, operating-system media caches, or other devices' sessions.
Device airplane mode, production revocation, account deletion, and cross-account native testing remain separate claims.

## Phase 4 verification

The first native bundle reproduces missing-video start-only retry from history.
Its import test did not leave history after a tab tap, so the corrected import baseline uses the established result-to-capture path.
That baseline reproduces a successful-upload claim even after confirmation rejects the stored video.
Bundles: `/tmp/spolysis-overnight-phase4-before.xcresult` and `/tmp/spolysis-overnight-phase4-transfer-before.xcresult`.
Exported baseline attachments: `.gnhf/evidence/phase4-before` and `.gnhf/evidence/phase4-transfer-before`.

```sh
xcodebuild clean test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase4-verified.xcresult CODE_SIGNING_ALLOWED=NO
```

Consolidated result: all 14 tests pass with zero failures in 287.153 seconds.
This covers all 12 recovery tests, the signed-in journey with import/viewer/share/sign-out, and authentication screens.
Log: `/tmp/spolysis-overnight-phase4-verified.log`.
The first consolidated attempt, `/tmp/spolysis-overnight-phase4-final.xcresult`, passed 11 of 14 tests.
A dropped history tap made no detail request, the confirmation outage leaked into the following signed-in test, and the resulting missing sign-out blocked the authentication smoke.
Signed-in setup now resets the fixture independently, and confirmation import uses the shared result-to-capture helper.
History entry uses explicit visible-center coordinates without automatic tap retries.
The failed tap's recorded coordinates were already centered, so its root cause is not established; do not attribute every dropped simulator tap to polling.
The fresh consolidated pass did not repeat it.
Keep app-directory files unchanged during native validation to avoid Metro refresh interference.

The first recovered screenshots captured the result transition before proving video readiness.
After the consolidated pass, only the two transfer tests gained a native video-ready assertion; product code remained unchanged.
Both strengthened checks pass with zero failures in 67.183 seconds using this command:

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests/ResultRecoveryTests/testInvalidUploadedVideoRetriesTransfer -only-testing:SpolysisUITests/ResultRecoveryTests/testInterruptedTransferRetriesBeforeStartingAnalysis -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase4-playback.xcresult CODE_SIGNING_ALLOWED=NO
```

Affected-flow log: `/tmp/spolysis-overnight-phase4-playback.log`.
Final failure-state attachments are `.gnhf/evidence/phase4-verified`; strengthened playback captures are `.gnhf/evidence/phase4-playback`.
The five new failure and recovered states were visually inspected at 1206 x 2622.
Three failure screenshots are preserved under `docs/screenshots`.
The first consolidated attachments are `.gnhf/evidence/phase4-first-pass`.
The consolidated journey ends signed out; the later affected playback checks sign back into the isolated fixture and end on a result before termination.
Fixture and Metro logs: `/tmp/spolysis-overnight-phase4-fixture.log` and `/tmp/spolysis-overnight-phase4-metro.log`.
TypeScript, ESLint, viewer build during Metro startup, Ruff, and changed Python-file formatting pass.
Phase 4 static and CPU commands:

```sh
npm --prefix app run typecheck
npm --prefix app run lint
.venv-test/bin/python -m pytest -q
.venv-test/bin/python -m ruff check api pipeline tests app/e2e/fixture.py
.venv-test/bin/python -m ruff format --check api/r2.py api/routers/uploads.py tests/test_api_flow.py app/e2e/fixture.py
app/node_modules/.bin/prettier --check app/src/screens/UploadProgressScreen.tsx app/src/services/api.ts
git diff --check
```

The full Python suite passes all 24 tests in 8.11 seconds with two dependency deprecation warnings.
Those warnings concern Starlette's httpx test adapter and the existing Supabase gotrue package.
API/storage integration tests verify absent objects, invalid size/type, service and permission errors, connection failure, and start-only retry using the same pending job.
The fixture-native checks and HTTP integration tests are separate validation layers, not a production full-stack claim.
The API's storage error classification requires deployment before or alongside the app change, since the old API can also return 400 for a storage outage.
No deployment was performed.
HTTP transfer failures do not establish device airplane-mode or process-termination recovery.

## Earlier verification and evidence

Phase 3 uses the consolidated command below, with its own result bundle and log.
The fixture now supports real 20-row pagination and independent history and page-failure switches.
The initial pagination baseline reproduces repeated failed-page requests and no retry control.
Its first refresh test did not initiate a request, so the corrected refresh baseline uses the existing five-second processing-job poll.
That baseline verifies failed history responses and no stale-data warning.
The baseline bundles are `/tmp/spolysis-overnight-phase3-before.xcresult` and `/tmp/spolysis-overnight-phase3-refresh-before.xcresult`.
Their exported attachments are `.gnhf/evidence/phase3-before` and `.gnhf/evidence/phase3-refresh-before`.

```sh
xcodebuild clean test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase3-final.xcresult CODE_SIGNING_ALLOWED=NO
```

Final native result: all 11 tests pass with zero failures in 210.171 seconds.
This is one uninterrupted consolidated pass on the final product and native-test source.
All nine recovery tests, the signed-in imported-video journey with sign-out, and the authentication screens pass.
The new pagination assertion records three failed requests, then one successful explicit retry; the final older row becomes accessible.
All six new history screenshots were inspected at 1206 x 2622.
The three failure-state screenshots are preserved under `docs/screenshots/history-*.png`; all recovered states are in `.gnhf/evidence/phase3-final`.
The final journey ends signed out on the sign-in screen.
Log: `/tmp/spolysis-overnight-phase3-final.log`.
Fixture and Metro logs: `/tmp/spolysis-overnight-phase3-fixture.log` and `/tmp/spolysis-overnight-phase3-metro.log`.
TypeScript, ESLint, Prettier for HomeScreen, Python lint, fixture formatting, and diff whitespace checks pass.
The viewer build passed during Metro startup.
No API or pipeline implementation changed; the Python regression suite was not repeated.
Service outages use isolated HTTP 503 responses, not device airplane mode or production services.

### Earlier verification

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase2-verified.xcresult CODE_SIGNING_ALLOWED=NO
```

Use a new result-bundle path on each run.
The consolidated pass before the final history-refresh change passed seven of eight tests; the affected flows passed after repair as recorded below.
Its log is `/tmp/spolysis-overnight-phase2-verified.log` and fixture log is `/tmp/spolysis-overnight-phase2-fixture.log`.
The first consolidated attempt, `/tmp/spolysis-overnight-phase2-final.xcresult`, passed seven of eight tests.
Its completed-result check used leftover jobs from a failed baseline; per-test fixture reset fixes that setup failure.
The next consolidated pass, `/tmp/spolysis-overnight-phase2-verified.xcresult`, passed seven of eight tests in 183.346 seconds.
The pending test's history tap coincided with a background poll, made no detail request, and left the history visible.
The app had been activating the native refresh control for all background refetches.
Only manual refresh now activates it.
Affected history flows run twice with this command:

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests/ResultRecoveryTests/testPendingUploadCanResumeFromHistory -only-testing:SpolysisUITests/ResultRecoveryTests/testSwitchingPendingAnalysesShowsSelectedJob -only-testing:SpolysisUITests/SignedInTests -test-iterations 2 -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase2-history-verified.xcresult CODE_SIGNING_ALLOWED=NO
```

Affected-flow result: six executions, zero failures in 165.658 seconds.
Pending-job recovery, distinct-job selection, and the full signed-in journey each passed twice after the final history-refresh fix.
The phase 2 full-suite run also passed completed-result recovery, video recovery, motion and signed-link recovery, confirmation retry, and authentication smoke before that Home-only change.
The confirmation test recorded one upload and two start attempts; the pending-history test recorded no upload and one start attempt.
Phase 2 did not produce one uninterrupted eight-test pass on that iteration's final source; the phase 3 consolidated pass now covers those flows together.
Final affected-flow attachments are `.gnhf/evidence/phase2-history-verified`.
The pending and rejected screenshots under `docs/screenshots` come from the final repeated pass.
The confirmation screenshot comes from the earlier successful confirmation flow; its progress-screen implementation is unchanged.
Its log is `/tmp/spolysis-overnight-phase2-history-verified.log`.
Native baseline bundles are `/tmp/spolysis-overnight-phase2-before.xcresult` and `/tmp/spolysis-overnight-phase2-history-before.xcresult`.
The first switching baseline hit the delayed password-save dialog; the signed-in rerun reproduced the actual wrong-job defect.
Baseline attachments are under `.gnhf/evidence/phase2-before` and `.gnhf/evidence/phase2-history-before`.
The first consolidated attachments are under `.gnhf/evidence/phase2-final`.

Phase 1 passed five native tests with zero failures in 115.025 seconds.
Its bundle is `/tmp/spolysis-overnight-phase1-final.xcresult`, log is `/tmp/spolysis-overnight-phase1-final.log`, and attachments are `.gnhf/evidence/phase1-final`.
Together these journeys exercise isolated authentication, history, real pipeline overlay and motion playback, 3D controls, stroke/hand selection, library import, native upload, sharing, profile, sign-out, and recovery.
Production authentication and database writes are separate unverified claims.

The following static checks pass in phase 3:

```sh
npm --prefix app run typecheck
npm --prefix app run lint
npm --prefix app run build:viewer
.venv-test/bin/python -m ruff check api pipeline tests app/e2e/fixture.py
.venv-test/bin/python -m ruff format --check app/e2e/fixture.py
app/node_modules/.bin/prettier --check app/src/screens/HomeScreen.tsx
git diff --check
```

The viewer build ran during Metro startup.
No API or pipeline implementation changed, so the Python regression suite was not repeated in either phase.

## Remaining ranked work and deferred decisions

1. Actual network interruption, failed jobs, recording guidance, and app termination during transfer.
   HTTP transfer-failure and missing-upload recovery are implemented in phase 4.
2. Device-offline session behavior, privacy expectations, account deletion/retention, and cross-account native testing.
   Expired-session re-entry and sign-out service-error cleanup are implemented in phase 5; history service-failure and pagination recovery are implemented in phase 3.
3. Actionable coaching and comparison interpretation, including the mismatch between highlighted joint and coaching priority in the inspected volley result.
4. Dynamic Type, smaller screens, accessibility, and remaining empty/loading/error states.
5. Consolidated native validation and honest handoff after those phases.

See [Athlete review](athlete-review.md) for issue evidence and claim limits.
Production Supabase DNS was unavailable when checked on 2026-10-30 in phase 1.
Physical camera behavior, Android runtime, distribution signing, external account access, and model accuracy remain separate requirements.

Durable upload queues and abandoned-job cleanup require a coordinated lifecycle and retention decision.
A transfer retry currently creates a new pending job through the existing upload contract, so failed or abandoned pending rows may remain.
This phase repairs recovery without adding a renewal endpoint, changing the data model, or silently defining retention.
Recommendation for morning review: define explicit uploading, ready-to-start, and abandoned states with authenticated retry and retention before adding background transfers.
Phase 2 recovers confirmation using the existing contract and does not implement that larger change.

## Checkpoint and cleanup

Phase 1 checkpoint: `.gnhf/checkpoints/iteration-1-result-recovery.patch`.
Phase 2 checkpoint: `.gnhf/checkpoints/iteration-2-upload-recovery.patch`.
Phase 3 checkpoint: `.gnhf/checkpoints/iteration-3-history-recovery.patch`.
Phase 4 checkpoint: `.gnhf/checkpoints/iteration-4-upload-validation.patch`.
Phase 5 checkpoint: `.gnhf/checkpoints/iteration-5-session-boundary.patch`.
Each has an ignored status sidecar in `.gnhf/runs/objective-act-as-a-d-19111c/`.
Phase 5 Metro on 8081 and the fixture on 8877 are stopped; neither port has a listening process.
The test app was terminated and this worker-booted simulator was shut down, preserving its installation and data.
The phase 5 consolidated journey ends signed out; the affected pagination checks use a local fixture session and end in history before termination.
All worker-started long-running processes are stopped.
No useful-work exhaustion or production-release claim is made; continue the ranked backlog next iteration.

## Continuation run bfd94b, iteration 1: confirmation contract

The protected HTTP upload-confirmation baseline reproduced three incorrect 500 responses: Temporal connection failure, workflow-start failure, and metadata persistence failure after successful workflow start.
Temporal failures now return 503 with instructions to retry starting the saved video without uploading again.
A successful durable workflow start remains HTTP 200 if saving `temporal_run_id` fails; the server logs a warning, and callbacks continue to identify the job by its ID.
The existing deterministic Temporal workflow ID is preserved.
The regression tests exercise the HTTP lifecycle and real workflow-start helper with isolated Temporal and database adapters, including recovery and a processing callback after metadata failure.
They do not establish production connectivity or database availability.
All 49 Python tests pass; Ruff lint and formatting of changed Python files pass.
The suite reports existing Starlette/httpx and GoTrue deprecation warnings.
No app files changed, no background services were started, and no commit or deployment was made.
Ranked items 2-5 and 7-9 from the continuation objective remain for later iterations.
Captain verification remains required for the live Fly worker, private R2 configuration, applied migrations 001-004, a real signed-in job, and the Temporal tennis-analysis poller.

## Continuation bfd94b iteration 2: result availability

The HTTP lifecycle baseline completed a job and then fetched its result with missing, empty, or unavailable storage artifacts.
All three returned HTTP 200 because presigning did not check object availability; a signing exception returned HTTP 500.
The initial test setup omitted required callback fields and returned 422; the corrected baseline included those fields before reproducing the defects.
Download signing now checks object existence and nonzero length, and the result endpoint maps media/signing failures to retryable HTTP 503 without changing job status.
Canonical per-job object keys, ownership gating, private signed URLs, and optional historical media fields remain compatible.
Verification: `.venv-test/bin/python -m pytest -q` passes 57 tests; `.venv-test/bin/python -m ruff check api pipeline tests` passes.
The tests cover both artifact paths, storage recovery, and unauthorized requests issuing no storage calls.
Storage checks add HEAD requests and cannot guarantee an object will remain available after a URL is returned.
No production service was contacted or changed, and no background process was started.
Captain verification remains required for the live Fly worker, private R2 configuration, migrations 001-004, a real signed-in job, and the tennis-analysis Temporal poller.
Other ranked local work remains open; this iteration does not satisfy the full run stop condition.

## Continuation bfd94b iteration 3: upload URL lifetime

Protected HTTP issuance with real local SigV4 signing reproduced a 300-second expiry for both MP4 and MOV upload URLs.
The first baseline request omitted the required stroke type and returned 422; corrected requests reproduced the expiry contract.
The default upload URL lifetime is now 3600 seconds, providing a longer window for starting or retrying large transfers on slow connections.
Signed content-type binding, per-job object keys, ownership, pending status, and confirmation-time size/type validation remain intact.
Verification: all 59 Python tests pass, including existing oversized/empty/unsupported-upload rejection cases; Ruff and changed-file formatting pass.
These checks use dummy signing credentials and isolated database adapters without contacting storage.
They establish signed URL lifetime, not whether R2 interrupts an already-started PUT at expiry or whether a physical cellular upload succeeds.
The longer lifetime also extends the validity of the private upload capability to one hour.
No app files changed, no background process was started, and no commit or deployment was made.
Ranked local work remains, including analyzed-window clarity, import/recovery/privacy guidance, completion notification safety, workflow timeouts, and public endpoint hardening.
Captain verification remains required for the live Fly worker, private R2 configuration, migrations 001-004, a real signed-in job, and the tennis-analysis Temporal poller.

## Continuation bfd94b iteration 4: preserve analysis outcomes

The baseline HTTP regression saved a result, injected a completion status-write outage, then delivered the workflow's failure callback.
The athlete-facing job status incorrectly became failed, preventing completion recovery.
`fail_job` now no-ops when a result row exists, and the HTTP regression verifies successful completion retry and result access after recovery.
The previous terminal-callback race regression now injects failure/rejection before result persistence, preserving the rule that an earlier terminal outcome cannot be revived.
Completion and rejection delivery now execute outside the workflow's analysis-failure handler.
Four isolated workflow branch checks establish that only processing/analysis activity errors trigger the failure callback; they do not execute Temporal scheduling or retry behavior.

Validation: `.venv-test/bin/python -m pytest -q` passes all 64 tests; `.venv-test/bin/python -m ruff check api pipeline tests`, changed-Python Ruff formatting, and `git diff --check` pass.
No app changes, background processes, commits, deployment, or production writes were made.
The result-existence check and status mutation remain separate operations, so this is not a transactional concurrency guarantee.
An exhausted completion/rejection delivery still leaves the workflow failed and may leave the job processing; operational callback redelivery remains necessary.
Production rollout must account for existing Temporal histories; no live workflow replay or reset was performed.
Worker liveness/timeouts, remaining app guidance, and public API hardening remain available local follow-up work.
Captain verification remains required for the live Fly worker, private R2 access, migrations 001-004, a real signed-in job, and the tennis-analysis poller.

## Continuation bfd94b iteration 5: public API surface

The HTTP baseline returned 200 for unauthenticated requests to /docs, /redoc, and /openapi.json, and created an eleventh upload job within a minute.
The API now disables all three documentation routes and applies the existing SlowAPI limiter to upload URL issuance at 10 requests per minute per client address.
The shared limiter lives outside the application module to avoid circular imports from routers.
An over-limit request returns 429 before creating a job or signing a storage URL; confirmation and job reads remain usable for existing uploads.
The tests reset limiter storage between isolated HTTP lifecycles, keeping the production limiter enabled during regression checks.

All 68 Python tests pass; Ruff lint, changed-file formatting, and diff checks pass.
The checks use isolated database and storage adapters and do not establish production ingress behavior.
The existing limiter uses process-local memory and the ASGI client address, so replicas have separate counters and users sharing an address share a quota.
Production proxy address handling and aggregate multi-replica enforcement are not validated by these tests.
No app files, generated Fly configuration, or orchestrator notes were changed; no background services, commits, deployment, or production writes were made.
Workflow timeouts, analyzed-window clarity, and import/recovery/privacy guidance remain local follow-up work.
Captain verification remains required for the live Fly worker, private R2 access, migrations 001-004, a real signed-in job, and the tennis-analysis poller.
