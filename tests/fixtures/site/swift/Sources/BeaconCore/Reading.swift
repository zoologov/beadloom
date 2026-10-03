/// One battery reading from one beacon.
public struct Reading: Equatable {
    public let beaconID: String
    public let percent: Int

    public init(beaconID: String, percent: Int) {
        self.beaconID = beaconID
        self.percent = min(max(percent, 0), 100)
    }

    public var isLow: Bool { percent < 20 }
}
