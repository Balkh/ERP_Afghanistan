"""
Phase 5A.5.5 — Architecture Freeze Tests.

Validates:
- Topology manifest is deterministic and versioned
- Dependency graph has no circular references
- Orchestration flow map is stable
- Bounded-memory inventory is correct
- Concurrency boundary map is complete
"""
import unittest
from core.operations.architecture.manifest import (
    generate_topology_manifest, get_bounded_memory_inventory,
    ENGINE_TOPOLOGY, DEPENDENCY_GRAPH, ARCHITECTURE_VERSION,
)
from core.operations.architecture.concurrency import get_concurrency_boundary_map
from core.operations.architecture.orchestration import (
    get_orchestration_flow_map, get_interaction_graph,
)


class TopologyManifestTest(unittest.TestCase):
    """Topology manifest is deterministic and versioned."""

    def test_manifest_is_deterministic(self):
        """Two calls produce deterministic output."""
        m1 = generate_topology_manifest()
        m2 = generate_topology_manifest()
        self.assertIn("manifest_id", m1)
        self.assertIn("architecture_version", m1)
        self.assertIn("engine_topology", m1)
        self.assertEqual(m1["architecture_version"], m2["architecture_version"])
        self.assertEqual(m1["engine_topology"], m2["engine_topology"])

    def test_manifest_has_version(self):
        """Manifest has a version string."""
        self.assertEqual(ARCHITECTURE_VERSION, "1.0.0")

    def test_manifest_has_engine_topology(self):
        """Manifest contains engine topology."""
        manifest = generate_topology_manifest()
        topology = manifest["engine_topology"]
        expected_engines = ["ControlCenterEngine", "ControlCenterRouter",
                            "ReplayEngine", "DigitalTwin", "ObservabilityAPI"]
        for engine in expected_engines:
            self.assertIn(engine, topology, f"Missing engine: {engine}")

    def test_manifest_has_dependency_graph(self):
        """Manifest contains dependency graph."""
        manifest = generate_topology_manifest()
        self.assertIn("dependency_graph", manifest)

    def test_manifest_has_orchestration_flow(self):
        """Manifest contains orchestration flow."""
        manifest = generate_topology_manifest()
        self.assertIn("orchestration_flow", manifest)


class DependencyGraphStabilityTest(unittest.TestCase):
    """Dependency graph has no circular dependencies."""

    def test_no_circular_dependencies(self):
        """No circular dependencies in the graph."""
        visited = set()
        path = set()

        def dfs(node):
            if node in path:
                self.fail(f"Circular dependency detected: {node}")
            if node in visited:
                return
            visited.add(node)
            path.add(node)
            deps = DEPENDENCY_GRAPH.get(node, {}).get("depends_on", [])
            for dep in deps:
                if dep in DEPENDENCY_GRAPH:
                    dfs(dep)
            path.remove(node)

        for node in DEPENDENCY_GRAPH:
            dfs(node)

    def test_all_nodes_defined(self):
        """All depended-on nodes exist in graph."""
        for node, info in DEPENDENCY_GRAPH.items():
            for dep in info.get("depends_on", []):
                self.assertIn(dep, DEPENDENCY_GRAPH,
                              f"Node {node} depends on undefined {dep}")

    def test_dependency_graph_bidirectional_consistent(self):
        """Dependency relationships are bidirectional consistent."""
        for node, info in DEPENDENCY_GRAPH.items():
            for dependent in info.get("depended_by", []):
                self.assertIn(dependent, DEPENDENCY_GRAPH)
                self.assertIn(node, DEPENDENCY_GRAPH[dependent].get("depends_on", []),
                              f"{node} lists {dependent} as depended_by but not vice versa")


class OrchestrationGraphValidationTest(unittest.TestCase):
    """Orchestration flow map is complete and stable."""

    def test_orchestration_flow_has_signal_pipeline(self):
        """Orchestration flow map contains signal pipeline."""
        flow = get_orchestration_flow_map()
        self.assertIn("signal_pipeline", flow)

    def test_orchestration_flow_has_query_routing(self):
        """Orchestration flow map contains query routing."""
        flow = get_orchestration_flow_map()
        self.assertIn("query_routing", flow)

    def test_orchestration_flow_versioned(self):
        """Orchestration flow map is versioned."""
        flow = get_orchestration_flow_map()
        self.assertEqual(flow["version"], "1.0.0")

    def test_signal_pipeline_11_steps(self):
        """Signal pipeline has 11 steps."""
        flow = get_orchestration_flow_map()
        pipeline = flow["signal_pipeline"]
        self.assertEqual(len(pipeline["steps"]), 11)

    def test_query_routing_7_routes(self):
        """Query routing has 7 defined routes."""
        flow = get_orchestration_flow_map()
        routes = flow["query_routing"]["routes"]
        self.assertEqual(len(routes), 7)

    def test_interaction_graph(self):
        """Interaction graph covers all engines."""
        graph = get_interaction_graph()
        expected = ["ControlCenterEngine", "ControlCenterRouter",
                    "ObservabilityAPI", "ReplayEngine", "DigitalTwin"]
        for engine in expected:
            self.assertIn(engine, graph)


class BoundedMemoryInventoryTest(unittest.TestCase):
    """Bounded memory inventory is correct."""

    def test_bounded_containers_count(self):
        """Bounded memory inventory has correct count."""
        inventory = get_bounded_memory_inventory()
        self.assertGreater(inventory["count"], 0)

    def test_all_containers_have_maxlen(self):
        """All containers have a maxlen."""
        inventory = get_bounded_memory_inventory()
        for container in inventory["bounded_containers"]:
            self.assertIn("maxlen", container)
            self.assertIsNotNone(container["maxlen"])

    def test_control_center_containers(self):
        """ControlCenterEngine has bounded containers."""
        inventory = get_bounded_memory_inventory()
        cce_containers = [c for c in inventory["bounded_containers"]
                          if c["engine"] == "ControlCenterEngine"]
        self.assertGreater(len(cce_containers), 10)


class ConcurrencyBoundaryTest(unittest.TestCase):
    """Concurrency boundary map is complete."""

    def test_concurrency_map_has_thread_boundaries(self):
        """Concurrency map has thread boundaries."""
        cmap = get_concurrency_boundary_map()
        self.assertIn("thread_boundaries", cmap)

    def test_concurrency_map_has_deadlock_prevention(self):
        """Concurrency map has deadlock prevention section."""
        cmap = get_concurrency_boundary_map()
        self.assertIn("deadlock_prevention", cmap)
