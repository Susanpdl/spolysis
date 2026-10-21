import XCTest

final class SmokeTests: XCTestCase {
  @MainActor
  func testWelcomeAndAuthenticationScreens() throws {
    continueAfterFailure = false
    let app = XCUIApplication(bundleIdentifier: "com.spolysis.app")
    app.launch()
    XCTAssertTrue(app.buttons["Create account"].waitForExistence(timeout: 45))
    XCTAssertTrue(app.buttons["Sign in"].exists)
    XCTAssertFalse(app.staticTexts["2D fault detection - free, instant"].exists)
    app.buttons["Create account"].press(forDuration: 0.15)
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
      app.buttons["Sign in"].press(forDuration: 0.15)
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
    analysis.press(forDuration: 0.15)
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
    app.buttons["Choose a video"].press(forDuration: 0.15)
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
    XCTAssertTrue(app.buttons["Create account"].waitForExistence(timeout: 15))
  }

  @MainActor
  private func capture(_ app: XCUIApplication, name: String) {
    let attachment = XCTAttachment(screenshot: app.screenshot())
    attachment.name = name
    attachment.lifetime = .keepAlways
    add(attachment)
  }
}
