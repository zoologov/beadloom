import XCTest
@testable import BeaconCore

final class ReadingTests: XCTestCase {
    func testAReadingBelowTwentyPercentIsLow() {
        XCTAssertTrue(Reading(beaconID: "ridge-7", percent: 12).isLow)
    }

    func testAPercentAboveOneHundredIsClamped() {
        XCTAssertEqual(Reading(beaconID: "ridge-7", percent: 140).percent, 100)
    }
}
