import logging
from typing import List, Dict, Any, Optional
from services.graph_service import GraphService

logger = logging.getLogger(__name__)


class ArchitectureAnalyzer:
    """Analyzes architecture issues using dependency graph."""
    
    def __init__(self):
        self.graph_service = GraphService()
        self.high_coupling_threshold = 10  # Services with >10 dependencies
    
    def analyze(
        self,
        repository_id: str,
        services: List[Dict[str, Any]],
        dependency_graph: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Analyze architecture issues."""
        debt_items = []
        
        if not dependency_graph:
            # Get dependency graph from Neo4j
            try:
                dependency_graph = self.graph_service.get_dependency_graph(repository_id)
            except Exception as e:
                logger.error(f"Error getting dependency graph: {e}")
                return debt_items
        
        # Detect circular dependencies
        circular_items = self._detect_circular_dependencies(dependency_graph)
        debt_items.extend(circular_items)
        
        # Detect tight coupling
        coupling_items = self._detect_tight_coupling(dependency_graph, services)
        debt_items.extend(coupling_items)
        
        # Detect god objects
        god_object_items = self._detect_god_objects(services, dependency_graph)
        debt_items.extend(god_object_items)
        
        return debt_items
    
    def _detect_circular_dependencies(
        self,
        dependency_graph: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect circular dependencies using graph traversal."""
        items = []
        edges = dependency_graph.get("edges", [])
        nodes = {node["id"]: node for node in dependency_graph.get("nodes", [])}
        
        # Build adjacency list
        graph = {}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source not in graph:
                graph[source] = []
            graph[source].append(target)
        
        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []
        
        def has_cycle(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        for node in graph:
            if node not in visited:
                has_cycle(node, [])
        
        # Create debt items for cycles
        for cycle in cycles:
            if len(cycle) > 2:  # Only report cycles with 3+ nodes
                cycle_str = " → ".join(cycle)
                items.append({
                    "id": f"circular_{cycle[0]}",
                    "category": "architecture",
                    "severity": "high",
                    "title": "Circular dependency detected",
                    "description": f"Circular dependency chain: {cycle_str}",
                    "impact_score": 0.8,
                    "effort_estimate": "days",
                    "metadata": {"cycle": cycle},
                })
        
        return items
    
    def _detect_tight_coupling(
        self,
        dependency_graph: Dict[str, Any],
        services: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect services with high coupling."""
        items = []
        edges = dependency_graph.get("edges", [])
        
        # Count dependencies per service
        dependency_count = {}
        for edge in edges:
            source = edge.get("source")
            dependency_count[source] = dependency_count.get(source, 0) + 1
        
        # Find highly coupled services
        for service_id, count in dependency_count.items():
            if count > self.high_coupling_threshold:
                service_name = next(
                    (s["name"] for s in services if s["id"] == service_id),
                    service_id
                )
                items.append({
                    "id": f"tight_coupling_{service_id}",
                    "category": "architecture",
                    "severity": "medium" if count < 20 else "high",
                    "title": f"Tight coupling: {service_name}",
                    "description": f"Service '{service_name}' has {count} dependencies (threshold: {self.high_coupling_threshold})",
                    "impact_score": min(count / 30, 1.0),
                    "effort_estimate": "days",
                    "metadata": {"dependency_count": count, "service_id": service_id},
                })
        
        return items
    
    def _detect_god_objects(
        self,
        services: List[Dict[str, Any]],
        dependency_graph: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect god objects (services with too many responsibilities)."""
        items = []
        edges = dependency_graph.get("edges", [])
        
        # Count incoming and outgoing dependencies
        incoming = {}
        outgoing = {}
        
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            outgoing[source] = outgoing.get(source, 0) + 1
            incoming[target] = incoming.get(target, 0) + 1
        
        # God objects have many dependencies and many dependents
        for service in services:
            service_id = service["id"]
            out_count = outgoing.get(service_id, 0)
            in_count = incoming.get(service_id, 0)
            total = out_count + in_count
            
            if total > 15:  # High threshold for god object
                items.append({
                    "id": f"god_object_{service_id}",
                    "category": "architecture",
                    "severity": "high",
                    "title": f"God object: {service['name']}",
                    "description": f"Service '{service['name']}' has {total} total dependencies ({out_count} outgoing, {in_count} incoming), suggesting too many responsibilities",
                    "impact_score": min(total / 25, 1.0),
                    "effort_estimate": "weeks",
                    "metadata": {
                        "outgoing": out_count,
                        "incoming": in_count,
                        "service_id": service_id,
                    },
                })
        
        return items
