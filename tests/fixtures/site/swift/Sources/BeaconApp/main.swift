import BeaconCore
import BeaconNetwork
import Foundation

let reading = Reading(beaconID: "ridge-7", percent: 64)
let line = ReadingEncoder().encode(reading)
FileHandle.standardOutput.write(line)
