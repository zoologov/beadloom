// beadloom:component=site-shared
// A record keyed by the data file's ids, which holds every id as a key of its own.
//
// A plain object inherits `Object.prototype`: it answers `constructor` or
// `toString` for a key it was never given, and assigning to `__proto__` replaces
// its prototype instead of adding a key, so a node of that name drops out of every
// walk over the object's entries. The data's ids are whatever a project named its
// nodes, so a record keyed by them is made without a prototype: every id is a key
// like any other, and a key it was never given reads `undefined`.

/** A record without a prototype holding `entries`, any iterable of `[id, value]` pairs. */
export function idRecord(entries = []) {
  const record = Object.create(null);
  for (const [id, value] of entries) record[id] = value;
  return record;
}
