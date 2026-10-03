// beadloom:component=site-graph-viewer
// The id of a viewer's panel, which its toolbar's "Panel" button controls.
//
// A constant id gave two viewers on one page one id, and the second button
// controlled the first panel. Vue's `useId` is unique within the app and the
// same on the server and in the browser, so it is called in the viewer's setup.

import { useId } from "vue";

/** The panel id of the viewer whose setup calls it. */
export function usePanelId() {
  return `bl-viewer-panel-${useId()}`;
}
