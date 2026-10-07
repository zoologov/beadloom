// beadloom:component=site-layer
// Public API of the `layer` entity.

export {
  LAYER_FILL_SHARE,
  LAYER_TONES,
  UNLAYERED_NAME,
  UNLAYERED_TONE,
  hasUnlayeredNode,
  layerOfNode,
  layerToneOf,
  layersOf,
} from "./model/layers.js";
export { default as LayerLegend } from "./ui/LayerLegend.vue";
