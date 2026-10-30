import XCTest

final class SmokeTests: XCTestCase {
  @MainActor
  func testWelcomeAndAuthenticationScreens() throws {
    continueAfterFailure = false
    let app = XCUIApplication(bundleIdentifier: "com.spolysis.app")
    app.launch()
    XCTAssertTrue(app.buttons["Get Started"].waitForExistence(timeout: 45))
    XCTAssertTrue(app.staticTexts["Your first analysis"].exists)
    XCTAssertTrue(app.staticTexts["Choose your stroke"].exists)
    XCTAssertTrue(app.staticTexts["Record or import a video"].exists)
    XCTAssertTrue(app.staticTexts["Explore your swing in 3D"].exists)
    XCTAssertTrue(app.buttons["Sign in"].exists)
    let welcome = XCTAttachment(screenshot: app.screenshot())
    welcome.name = "Get started"
    welcome.lifetime = .keepAlways
    add(welcome)
    if !app.buttons["Get Started"].isHittable { app.swipeUp() }
    app.buttons["Get Started"].tap()
    XCTAssertTrue(app.textFields["you@example.com"].waitForExistence(timeout: 10))
    XCTAssertTrue(app.secureTextFields["At least 8 characters"].exists)
    let attachment = XCTAttachment(screenshot: app.screenshot())
    attachment.name = "Create account"
    attachment.lifetime = .keepAlways
    add(attachment)
    app.buttons["Back"].tap()
    app.buttons["Sign in"].tap()
    XCTAssertTrue(app.textFields["you@example.com"].waitForExistence(timeout: 10))
    XCTAssertTrue(app.secureTextFields.firstMatch.exists)
  }
}

// Run only with e2e/fixture.py and Metro configured for localhost:8877.
final class SignedInTests: XCTestCase {
  @MainActor
  func testHistoryRealMotionAndRecordingSetup() throws {
    continueAfterFailure = false
    let app = XCUIApplication(bundleIdentifier: "com.spolysis.app")
    app.launch()
    let landing = app.staticTexts.matching(NSPredicate(format: "label IN %@", ["Spolysis", "Your analyses"])).firstMatch
    XCTAssertTrue(landing.waitForExistence(timeout: 45))
    let signingIn = app.buttons["Sign in"].exists
    if signingIn {
      app.buttons["Sign in"].tap()
      let email = app.textFields["you@example.com"]
      XCTAssertTrue(email.waitForExistence(timeout: 10))
      email.tap()
      email.typeText("ui-test@example.com")
      app.secureTextFields.firstMatch.tap()
      app.secureTextFields.firstMatch.typeText("fixture-password")
      app.buttons["Sign in"].tap()
    }
    XCTAssertTrue(app.staticTexts["Your analyses"].waitForExistence(timeout: 30))
    let system = XCUIApplication(bundleIdentifier: "com.apple.springboard")
    if app.buttons["Not Now"].waitForExistence(timeout: signingIn ? 10 : 1) {
      app.buttons["Not Now"].tap()
    } else if system.buttons["Not Now"].exists {
      system.buttons["Not Now"].tap()
    }
    let analysis = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Open analysis from'")).firstMatch
    XCTAssertTrue(analysis.waitForExistence(timeout: 15))
    let historyReady = expectation(for: NSPredicate(format: "hittable == true"), evaluatedWith: analysis)
    wait(for: [historyReady], timeout: 10)
    analysis.tap()
    XCTAssertTrue(app.staticTexts["CORRECTED OVERLAY"].waitForExistence(timeout: 20))
    XCTAssertFalse(app.staticTexts["Could not load result"].exists)
    capture(app, name: "Real analysis video")
    app.buttons["3D VIEW"].tap()
    XCTAssertTrue(app.webViews.firstMatch.waitForExistence(timeout: 20))
    XCTAssertTrue(app.webViews.buttons["Play"].waitForExistence(timeout: 20))
    app.webViews.buttons["Play"].tap()
    XCTAssertTrue(app.webViews.buttons["Pause"].exists)
    app.webViews.buttons["Pause"].tap()
    let viewer = app.webViews.firstMatch
    viewer.coordinate(withNormalizedOffset: CGVector(dx: 0.35, dy: 0.3))
      .press(
        forDuration: 0.1,
        thenDragTo: viewer.coordinate(withNormalizedOffset: CGVector(dx: 0.65, dy: 0.35))
      )
    XCTAssertTrue(app.webViews.buttons["Reset view"].waitForExistence(timeout: 5))
    app.webViews.buttons["Reset view"].tap()
    capture(app, name: "Real 3D motion")
    let edge = app.coordinate(withNormalizedOffset: CGVector(dx: 0.97, dy: 0.82))
    let top = app.coordinate(withNormalizedOffset: CGVector(dx: 0.97, dy: 0.20))
    edge.press(forDuration: 0.05, thenDragTo: top)
    edge.press(forDuration: 0.05, thenDragTo: top)
    XCTAssertTrue(app.buttons["Record another"].waitForExistence(timeout: 10))
    app.buttons["Record another"].tap()
    XCTAssertTrue(app.staticTexts["Your next better stroke"].waitForExistence(timeout: 10))
    app.buttons["Backhand"].tap()
    app.buttons["Left-handed"].tap()
    capture(app, name: "Recording setup")
    if !app.buttons["Choose a video"].isHittable { app.swipeUp() }
    XCTAssertTrue(app.buttons["Choose a video"].exists)
    app.buttons["Choose a video"].tap()
    let allow = app.buttons["Allow Full Access"]
    if allow.waitForExistence(timeout: 3) {
      allow.tap()
    } else if system.buttons["Allow Full Access"].exists {
      system.buttons["Allow Full Access"].tap()
    }
    let video = app.images.matching(NSPredicate(format: "label CONTAINS[c] 'Video'")).firstMatch
    if !video.waitForExistence(timeout: 10) { print(app.debugDescription) }
    XCTAssertTrue(video.exists)
    capture(app, name: "Video library")
    // Photos exposes its thumbnail as an image with no accessibility hit point.
    video.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
    let choose = app.buttons["Choose"]
    if choose.waitForExistence(timeout: 3) { choose.tap() }
    XCTAssertTrue(app.staticTexts["CORRECTED OVERLAY"].waitForExistence(timeout: 45))
    capture(app, name: "Imported video result")
    edge.press(forDuration: 0.05, thenDragTo: top)
    edge.press(forDuration: 0.05, thenDragTo: top)
    app.buttons["Share clip"].tap()
    let shareAction = app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS 'Save Video'")).firstMatch
    XCTAssertTrue(shareAction.waitForExistence(timeout: 15))
    capture(app, name: "Share video")
    app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.2)).tap()
    app.buttons["Profile, tab, 3 of 3"].tap()
    XCTAssertTrue(app.staticTexts["Your account"].waitForExistence(timeout: 10))
    XCTAssertTrue(app.staticTexts["ui-test@example.com"].exists)
    capture(app, name: "Account")
    app.buttons["Sign out"].tap()
    app.alerts.buttons["Sign out"].tap()
    XCTAssertTrue(app.buttons["Get Started"].waitForExistence(timeout: 15))
  }

  @MainActor
  private func capture(_ app: XCUIApplication, name: String) {
    let attachment = XCTAttachment(screenshot: app.screenshot())
    attachment.name = name
    attachment.lifetime = .keepAlways
    add(attachment)
  }
}

// Recovery checks use only the loopback fixture, never production services.
final class ResultRecoveryTests: XCTestCase {
  override func setUpWithError() throws {
    try super.setUpWithError()
    // XCTest may abort before Swift defer executes after an assertion failure.
    try fixturePost("/__test/reset")
  }

  @MainActor
  func testHistoryInitialFailureDoesNotClaimEmptyAccount() throws {
    continueAfterFailure = false
    try fixturePost("/__test/jobs", body: [])
    try failures(["history": true])
    let app = try openHistory()
    XCTAssertTrue(app.staticTexts["Could not load analyses"].waitForExistence(timeout: 20))
    XCTAssertTrue(app.staticTexts["Total unavailable"].exists)
    XCTAssertFalse(app.staticTexts["0 total"].exists)
    XCTAssertFalse(app.buttons["Start your first analysis"].exists)
    capture(app, name: "History initial load interrupted")
    try failures(["history": false])
    app.buttons["Retry"].tap()
    XCTAssertTrue(app.buttons["Start your first analysis"].waitForExistence(timeout: 15))
    XCTAssertTrue(app.staticTexts["0 total"].exists)
    XCTAssertTrue(app.staticTexts["Choose your stroke"].exists)
    capture(app, name: "History genuinely empty")
  }

  @MainActor
  func testHistoryRefreshFailureKeepsSavedRowsAndRecovers() throws {
    continueAfterFailure = false
    try fixturePost("/__test/jobs", body: [
      ["id": "refresh-processing", "tier": "premium", "status": "processing", "created_at": "2026-10-17T12:00:00Z"]
    ])
    let app = try openAnalysis(waitForResult: false)
    app.buttons["Back to analyses"].tap()
    let row = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Open analysis from'")).firstMatch
    XCTAssertTrue(row.waitForExistence(timeout: 10))
    try failures(["history": true])
    // Wait for the processing-job poll, as when connection drops while waiting.
    let stale = app.staticTexts["Could not update analyses"]
    let visible = stale.waitForExistence(timeout: 20)
    capture(app, name: "History refresh interrupted")
    XCTAssertTrue(visible, "Cached rows must not silently look current after a refresh fails")
    XCTAssertTrue(row.exists)
    XCTAssertTrue(app.buttons["Retry updating analyses"].exists)
    try failures(["history": false])
    app.buttons["Retry updating analyses"].tap()
    let recovered = expectation(for: NSPredicate(format: "exists == false"), evaluatedWith: stale)
    wait(for: [recovered], timeout: 15)
    XCTAssertTrue(row.exists)
    capture(app, name: "History refresh recovered")
  }

  @MainActor
  func testHistoryNextPageFailureOffersRetry() throws {
    continueAfterFailure = false
    let seeded = (0..<22).map { index -> [String: Any] in
      ["id": "history-\(index)", "tier": "premium", "status": "completed",
       "created_at": String(format: "2026-10-%02dT12:00:00Z", 28 - index)]
    }
    try fixturePost("/__test/jobs", body: seeded)
    try failures(["history_page": true])
    let app = try openAnalysis()
    app.buttons["Analyses, tab, 1 of 3"].tap()
    for _ in 0..<7 { app.swipeUp() }
    let error = app.staticTexts["Could not load more analyses"]
    let visible = error.waitForExistence(timeout: 20)
    capture(app, name: "History next page interrupted")
    XCTAssertTrue(visible, "An incomplete history must explain why the remaining analyses are absent")
    XCTAssertTrue(app.buttons["Retry loading more"].exists)
    let interrupted = try fixtureState()
    XCTAssertEqual(interrupted["history_pages"] as? Int, 3, "Stop after the normal two query retries, rather than repeatedly fetching a failed page")
    try failures(["history_page": false])
    app.buttons["Retry loading more"].tap()
    let last = app.buttons["Open analysis from 10/7/2026"]
    if !last.waitForExistence(timeout: 3) { app.swipeUp() }
    XCTAssertTrue(last.waitForExistence(timeout: 15))
    XCTAssertFalse(error.exists)
    let recovered = try fixtureState()
    XCTAssertEqual(recovered["history_pages"] as? Int, 4)
    capture(app, name: "History next page recovered")
  }

  @MainActor
  func testSwitchingPendingAnalysesShowsSelectedJob() throws {
    continueAfterFailure = false
    defer { try? fixturePost("/__test/reset") }
    try fixturePost("/__test/jobs", body: [
      ["id": "pending-one", "tier": "premium", "status": "processing", "created_at": "2026-10-17T12:00:00Z"],
      ["id": "rejected-two", "tier": "premium", "status": "rejected", "created_at": "2026-10-16T12:00:00Z", "rejection_reason": "Your feet are out of frame. Record with your full body visible."]
    ])
    let app = try openAnalysis(waitForResult: false)
    XCTAssertTrue(app.staticTexts["Reconstructing your stroke in 3D..."].waitForExistence(timeout: 15))
    app.buttons["Back to analyses"].tap()
    let other = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Open analysis from'")).element(boundBy: 1)
    XCTAssertTrue(other.waitForExistence(timeout: 10))
    other.tap()
    let rejected = app.staticTexts["Your feet are out of frame. Record with your full body visible."]
    let visible = rejected.waitForExistence(timeout: 15)
    capture(app, name: "Second analysis selected")
    XCTAssertTrue(visible, "The selected rejected analysis must not keep showing the previous processing job")
    XCTAssertTrue(app.buttons["Choose another video"].exists)
    // A different analysis finishing in the background must not replace this screen.
    try fixturePost("/__test/jobs", body: [
      ["id": "pending-one", "tier": "premium", "status": "completed", "created_at": "2026-10-17T12:00:00Z"],
      ["id": "rejected-two", "tier": "premium", "status": "rejected", "created_at": "2026-10-16T12:00:00Z", "rejection_reason": "Your feet are out of frame. Record with your full body visible."]
    ])
    app.buttons["Choose another video"].tap()
    XCTAssertTrue(app.staticTexts["Your next better stroke"].waitForExistence(timeout: 10))
  }

  @MainActor
  func testPendingUploadCanResumeFromHistory() throws {
    continueAfterFailure = false
    defer { try? fixturePost("/__test/reset") }
    try fixturePost("/__test/jobs", body: [
      ["id": "uploaded-pending", "tier": "premium", "status": "pending", "created_at": "2026-10-17T12:00:00Z"]
    ])
    let app = try openAnalysis(waitForResult: false)
    XCTAssertTrue(app.staticTexts["Your analysis has not started yet."].waitForExistence(timeout: 15))
    capture(app, name: "Pending upload reopened from history")
    XCTAssertTrue(app.buttons["Retry starting analysis"].exists)
    app.buttons["Retry starting analysis"].tap()
    XCTAssertTrue(app.staticTexts["CORRECTED OVERLAY"].waitForExistence(timeout: 30))
    let state = try fixtureState()
    XCTAssertEqual(state["uploads"] as? Int, 0)
    XCTAssertEqual(state["confirmations"] as? Int, 1)
  }

  @MainActor
  func testUploadConfirmationRetryKeepsUploadedVideo() throws {
    continueAfterFailure = false
    try failures(["confirm": true])
    defer { try? fixturePost("/__test/reset") }
    let app = try openAnalysis()
    app.buttons["Record, tab, 2 of 3"].tap()
    // Return directly to capture from this existing result.
    let edge = app.coordinate(withNormalizedOffset: CGVector(dx: 0.97, dy: 0.82))
    let top = app.coordinate(withNormalizedOffset: CGVector(dx: 0.97, dy: 0.20))
    edge.press(forDuration: 0.05, thenDragTo: top)
    edge.press(forDuration: 0.05, thenDragTo: top)
    app.buttons["Record another"].tap()
    if !app.buttons["Choose a video"].isHittable { app.swipeUp() }
    app.buttons["Choose a video"].tap()
    let system = XCUIApplication(bundleIdentifier: "com.apple.springboard")
    if app.buttons["Allow Full Access"].waitForExistence(timeout: 2) {
      app.buttons["Allow Full Access"].tap()
    } else if system.buttons["Allow Full Access"].exists {
      system.buttons["Allow Full Access"].tap()
    }
    let video = app.images.matching(NSPredicate(format: "label CONTAINS[c] 'Video'")).firstMatch
    XCTAssertTrue(video.waitForExistence(timeout: 10))
    video.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
    if app.buttons["Choose"].waitForExistence(timeout: 3) { app.buttons["Choose"].tap() }
    let uploaded = app.staticTexts["Video uploaded, analysis not started"]
    let visible = uploaded.waitForExistence(timeout: 20)
    capture(app, name: "Upload confirmation interrupted")
    XCTAssertTrue(visible)
    XCTAssertTrue(app.staticTexts["Your video was uploaded. Retry starting the analysis without uploading it again."].exists)
    try failures(["confirm": false])
    app.buttons["Start analysis again"].tap()
    XCTAssertTrue(app.staticTexts["CORRECTED OVERLAY"].waitForExistence(timeout: 30))
    capture(app, name: "Upload confirmation recovered")
    let state = try fixtureState()
    XCTAssertEqual(state["uploads"] as? Int, 1)
    XCTAssertEqual(state["confirmations"] as? Int, 2)
  }

  @MainActor
  func testCompletedAnalysisCanRetryResult() throws {
    continueAfterFailure = false
    try failures(["result": true, "finishing": true, "motion": false, "video": false])
    defer { try? failures(["result": false, "finishing": false]) }
    let app = try openAnalysis(waitForResult: false)
    // The fixture reports processing in history, then completed on the detail poll.
    let message = app.staticTexts["Analysis ready, result unavailable"]
    let appeared = message.waitForExistence(timeout: 20)
    capture(app, name: "Completed analysis result interrupted")
    XCTAssertTrue(appeared)
    XCTAssertTrue(app.buttons["Retry result"].exists)
    try failures(["result": false, "finishing": false])
    app.buttons["Retry result"].tap()
    XCTAssertTrue(app.staticTexts["CORRECTED OVERLAY"].waitForExistence(timeout: 20))
    capture(app, name: "Completed analysis result recovered")
  }

  @MainActor
  func testUnavailableMotionCanRetry() throws {
    continueAfterFailure = false
    try failures(["motion": true, "video": false, "result": false])
    defer { try? failures(["motion": false, "result": false]) }
    let app = try openAnalysis()
    app.buttons["3D VIEW"].tap()
    XCTAssertTrue(app.staticTexts.matching(NSPredicate(format: "label CONTAINS %@ OR label CONTAINS %@", "3D data is unavailable", "3D motion could not load")).firstMatch.waitForExistence(timeout: 15))
    capture(app, name: "Motion download interrupted")
    XCTAssertTrue(app.buttons["Retry 3D view"].exists)
    try failures(["result": true])
    app.buttons["Retry 3D view"].tap()
    XCTAssertTrue(app.staticTexts["Could not refresh the link. Check your connection and retry."].waitForExistence(timeout: 15))
    capture(app, name: "Motion link refresh interrupted")
    try failures(["motion": false, "result": false])
    app.buttons["Retry 3D view"].tap()
    XCTAssertTrue(app.webViews.buttons["Play"].waitForExistence(timeout: 20))
    capture(app, name: "Motion download recovered")
  }

  @MainActor
  func testUnavailableVideoCanRetry() throws {
    continueAfterFailure = false
    try failures(["motion": false, "video": true, "result": false])
    defer { try? failures(["video": false]) }
    let app = try openAnalysis()
    XCTAssertTrue(app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "Video could not load")).firstMatch.waitForExistence(timeout: 20))
    capture(app, name: "Video download interrupted")
    XCTAssertTrue(app.buttons["Retry video"].exists)
    try failures(["video": false])
    app.buttons["Retry video"].tap()
    XCTAssertTrue(app.otherElements["Analysis video ready"].waitForExistence(timeout: 20))
    XCTAssertFalse(app.staticTexts["Video could not load"].exists)
    capture(app, name: "Video download recovered")
  }

  @MainActor
  private func openHistory() throws -> XCUIApplication {
    let app = XCUIApplication(bundleIdentifier: "com.spolysis.app")
    app.launch()
    let landing = app.staticTexts.matching(NSPredicate(format: "label IN %@", ["Spolysis", "Your analyses"])).firstMatch
    XCTAssertTrue(landing.waitForExistence(timeout: 45))
    let signingIn = app.buttons["Sign in"].exists
    if signingIn {
      app.buttons["Sign in"].tap()
      let email = app.textFields["you@example.com"]
      XCTAssertTrue(email.waitForExistence(timeout: 10))
      email.tap()
      email.typeText("ui-test@example.com")
      app.secureTextFields.firstMatch.tap()
      app.secureTextFields.firstMatch.typeText("fixture-password")
      app.buttons["Sign in"].tap()
    }
    XCTAssertTrue(app.staticTexts["Your analyses"].waitForExistence(timeout: 30))
    let system = XCUIApplication(bundleIdentifier: "com.apple.springboard")
    if app.buttons["Not Now"].waitForExistence(timeout: signingIn ? 10 : 1) {
      app.buttons["Not Now"].tap()
    } else if system.buttons["Not Now"].exists {
      system.buttons["Not Now"].tap()
    }
    return app
  }

  @MainActor
  private func openAnalysis(waitForResult: Bool = true) throws -> XCUIApplication {
    let app = try openHistory()
    let analysis = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Open analysis from'")).firstMatch
    XCTAssertTrue(analysis.waitForExistence(timeout: 15))
    let ready = expectation(for: NSPredicate(format: "hittable == true"), evaluatedWith: analysis)
    wait(for: [ready], timeout: 10)
    analysis.tap()
    if waitForResult {
      XCTAssertTrue(app.staticTexts["CORRECTED OVERLAY"].waitForExistence(timeout: 20))
    }
    return app
  }

  private func fixturePost(_ path: String, body: Any = [:]) throws {
    var request = URLRequest(url: URL(string: "http://localhost:8877" + path)!)
    request.httpMethod = "POST"
    request.httpBody = try JSONSerialization.data(withJSONObject: body)
    let done = expectation(description: "Configure isolated fixture")
    URLSession.shared.dataTask(with: request) { _, response, error in
      XCTAssertNil(error)
      XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
      done.fulfill()
    }.resume()
    wait(for: [done], timeout: 5)
  }

  private func fixtureState() throws -> [String: Any] {
    let done = expectation(description: "Read isolated fixture counters")
    var state: [String: Any] = [:]
    URLSession.shared.dataTask(with: URL(string: "http://localhost:8877/__test/state")!) { data, _, error in
      XCTAssertNil(error)
      if let data = data { state = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:] }
      done.fulfill()
    }.resume()
    wait(for: [done], timeout: 5)
    return state
  }

  private func failures(_ values: [String: Bool]) throws {
    var request = URLRequest(url: URL(string: "http://localhost:8877/__test/failures")!)
    request.httpMethod = "POST"
    request.httpBody = try JSONSerialization.data(withJSONObject: values)
    let done = expectation(description: "Configure local fixture failures")
    URLSession.shared.dataTask(with: request) { _, response, error in
      XCTAssertNil(error)
      XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
      done.fulfill()
    }.resume()
    wait(for: [done], timeout: 5)
  }

  @MainActor
  private func capture(_ app: XCUIApplication, name: String) {
    let attachment = XCTAttachment(screenshot: app.screenshot())
    attachment.name = name
    attachment.lifetime = .keepAlways
    add(attachment)
  }
}
