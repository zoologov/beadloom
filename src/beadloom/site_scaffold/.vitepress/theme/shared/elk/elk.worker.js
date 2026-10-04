// beadloom:component=site-shared
// The Web Worker ELK lays a graph out in, so the page's main thread stays free meanwhile.
//
// elkjs ships its layout engine as a worker script: loaded in a worker, it
// answers ELK's own messages (`register`, then `layout`) on the worker's
// `onmessage`. Importing it is the whole worker. Vite bundles this module as a
// worker of its own because `layOut.js` names it with
// `new Worker(new URL("./elk.worker.js", import.meta.url))`.

import "elkjs/lib/elk-worker.min.js";
