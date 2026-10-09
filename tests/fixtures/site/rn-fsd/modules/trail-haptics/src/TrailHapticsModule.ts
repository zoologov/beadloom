import { requireNativeModule } from 'expo'

export default requireNativeModule<{ pulse(): void }>('TrailHaptics')
