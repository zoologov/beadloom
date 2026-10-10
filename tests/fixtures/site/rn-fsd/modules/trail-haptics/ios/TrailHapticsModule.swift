import ExpoModulesCore
import UIKit

public class TrailHapticsModule: Module {
  public func definition() -> ModuleDefinition {
    Name("TrailHaptics")

    Function("pulse") {
      UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }
  }
}
