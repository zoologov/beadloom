package expo.modules.trailhaptics

import android.os.VibrationEffect
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class TrailHapticsModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("TrailHaptics")

    Function("pulse") {
      VibrationEffect.createOneShot(40, VibrationEffect.DEFAULT_AMPLITUDE)
    }
  }
}
