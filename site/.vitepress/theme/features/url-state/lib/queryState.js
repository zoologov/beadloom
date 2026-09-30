// beadloom:component=site-url-state
// A view's state read from and written to a URL query string.
//
// Only a value that differs from its default is written, so an untouched view
// keeps a clean URL, and every parameter the state does not own is kept as it
// was. A boolean is written as `1`; every other value as its string, so what
// is read back is exactly what was written. An empty value whose default is not
// empty is written empty (`focus=`): on a node page the selection's default is
// the page's node, and a cleared selection left out of the URL would come back
// on a reload.

function readValue(raw, fallback) {
  if (typeof fallback === "boolean") return raw === "1" || raw === "true";
  return raw;
}

/** The state `defaults` describes, with each key the query carries taken from it. */
export function readQuery(search, defaults) {
  const params = new URLSearchParams(search);
  const state = {};
  for (const [key, fallback] of Object.entries(defaults)) {
    state[key] = params.has(key) ? readValue(params.get(key), fallback) : fallback;
  }
  return state;
}

/** `search` with the state's keys set to its non-default values and the rest removed. */
function isEmpty(value) {
  return value === "" || value === undefined || value === null;
}

export function writeQuery(search, state, defaults) {
  const params = new URLSearchParams(search);
  for (const [key, fallback] of Object.entries(defaults)) {
    const value = state[key];
    if (value === fallback || (isEmpty(value) && isEmpty(fallback))) {
      params.delete(key);
    } else if (isEmpty(value)) {
      params.set(key, "");
    } else {
      params.set(key, typeof value === "boolean" ? (value ? "1" : "0") : String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}
