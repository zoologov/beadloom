import BeaconCore
import Foundation

/// Turns a reading into the line the base station expects.
public struct ReadingEncoder {
    public init() {}

    public func encode(_ reading: Reading) -> Data {
        Data("\(reading.beaconID);\(reading.percent)\n".utf8)
    }
}
