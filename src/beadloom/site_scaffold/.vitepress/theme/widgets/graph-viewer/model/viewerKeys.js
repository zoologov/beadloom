// beadloom:component=site-graph-viewer
// The viewer's keyboard shortcuts, active while focus is inside the viewer.
//
// `+` and `-` zoom, `0` fits, `f` toggles full screen and `Esc` clears the
// selection. A key typed into a field of the toolbar is the field's.

const FIELD_TAGS = new Set(["INPUT", "SELECT", "TEXTAREA"]);

/** The shortcut table: key → the action's name in `actions`. */
export const SHORTCUTS = Object.freeze({
  "+": "zoomIn",
  "=": "zoomIn",
  "-": "zoomOut",
  0: "fit",
  f: "fullscreen",
  Escape: "clear",
});

/** A `keydown` handler that runs `actions[SHORTCUTS[key]]`. */
export function keyHandler(actions) {
  return function onKeydown(event) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (FIELD_TAGS.has(event.target?.tagName)) return;
    const action = actions[SHORTCUTS[event.key]];
    if (!action) return;
    event.preventDefault();
    action();
  };
}
