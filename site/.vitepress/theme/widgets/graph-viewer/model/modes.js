// beadloom:component=site-graph-viewer
// The viewer's two data modes: the architecture graph and the landscape of contracts.
//
// One viewer core draws both (BDL-076 A4). A mode names what differs between
// them and nothing else: the data file it reads and how that file becomes
// nodes and edges, the filters in its slot of the toolbar and the set they
// show, and whether the impact mode is offered. Navigation, the neighbourhood,
// full screen, the panel, the legend and URL state are the core's, the same in
// both.
//
// The landscape offers no impact mode: impact walks the dependency edges
// backwards and summarises domains, services and layer boundaries, and the
// landscape has contracts between services, with no layers and no containers.
// Its neighbourhood, one step both ways by default, is what its old "Focus"
// control showed.
//
// The mode is the page's, not the URL's: the architecture page and the
// landscape page are two pages, and a query cannot turn one into the other.

import { useArchitectureData } from "../../../entities/architecture-data/index.js";
import { landscapeGraphOf, useLandscapeData } from "../../../entities/landscape-data/index.js";
import {
  CONTRACT_FILTER_DEFAULTS,
  ContractFilterControls,
  FILTER_DEFAULTS,
  FilterControls,
  contractFilterOptions,
  filterOptions,
  visibleContracts,
  visibleNodeIds,
} from "../../../features/filter-graph/index.js";

const list = (value) => (Array.isArray(value) ? value : []);

/** The mode a page names when it names none, or one the viewer does not know. */
export const DEFAULT_MODE = "architecture";

export const MODES = Object.freeze({
  architecture: Object.freeze({
    label: "Architecture graph",
    useData: useArchitectureData,
    graphOf: (data) => ({
      nodes: list(data?.nodes),
      edges: list(data?.edges),
      contracts: [],
      // The declared layers: the names the legend, the filter and the card show.
      layers: list(data?.layers),
    }),
    filterDefaults: FILTER_DEFAULTS,
    filterControls: FilterControls,
    filterOptions: (graph, layers) => filterOptions(graph.nodes, layers),
    visible: (graph, filters, context) => ({
      nodes: visibleNodeIds(graph.nodes, filters, context),
      contracts: null,
    }),
    impact: true,
  }),
  landscape: Object.freeze({
    label: "Landscape of contracts",
    useData: useLandscapeData,
    graphOf: (data) => landscapeGraphOf(data),
    filterDefaults: CONTRACT_FILTER_DEFAULTS,
    filterControls: ContractFilterControls,
    filterOptions: (graph) => contractFilterOptions(graph.contracts),
    visible: (graph, filters) => visibleContracts(graph, filters),
    impact: false,
  }),
});

/** The mode called `name`, or the default mode. */
export function modeOf(name) {
  return MODES[name] || MODES[DEFAULT_MODE];
}
