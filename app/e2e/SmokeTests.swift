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
    if app.buttons["Sign in"].exists {
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
    if system.buttons["Not Now"].waitForExistence(timeout: 3) {
      system.buttons["Not Now"].tap()
    } else if app.buttons["Not Now"].exists {
      app.buttons["Not Now"].tap()
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
  private func openAnalysis(waitForResult: Bool = true) throws -> XCUIApplication {
    let app = XCUIApplication(bundleIdentifier: "com.spolysis.app")
    app.launch()
    let landing = app.staticTexts.matching(NSPredicate(format: "label IN %@", ["Spolysis", "Your analyses"])).firstMatch
    XCTAssertTrue(landing.waitForExistence(timeout: 45))
    if app.buttons["Sign in"].exists {
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
    if system.buttons["Not Now"].waitForExistence(timeout: 2) {
      system.buttons["Not Now"].tap()
    } else if app.buttons["Not Now"].exists {
      app.buttons["Not Now"].tap()
    }
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
