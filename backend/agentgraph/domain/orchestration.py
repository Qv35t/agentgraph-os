from dataclasses import dataclass
from uuid import UUID


class TeamGraphError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class TeamNode:
    id: str
    label: str
    agent_id: UUID
    instructions: str | None


@dataclass(frozen=True, slots=True)
class TeamEdge:
    id: str
    source: str
    target: str


@dataclass(frozen=True, slots=True)
class TeamGraph:
    nodes: tuple[TeamNode, ...]
    edges: tuple[TeamEdge, ...]

    def predecessors(self, node_id: str) -> tuple[str, ...]:
        return tuple(edge.source for edge in self.edges if edge.target == node_id)

    def successors(self, node_id: str) -> tuple[str, ...]:
        return tuple(edge.target for edge in self.edges if edge.source == node_id)


def parse_team_graph(graph: dict[str, object], max_workers: int) -> TeamGraph:
    if set(graph) - {"version", "runtime", "nodes", "edges"}:
        raise TeamGraphError("INVALID_TEAM_GRAPH", "Team graph contains unsupported fields")
    if graph.get("version") != 2 or graph.get("runtime") != "team-v1":
        raise TeamGraphError("INVALID_TEAM_GRAPH", "team-v1 requires graph version 2")
    raw_nodes = graph.get("nodes")
    raw_edges = graph.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise TeamGraphError("INVALID_TEAM_GRAPH", "Team graph nodes and edges must be lists")
    if not raw_nodes:
        raise TeamGraphError("INVALID_TEAM_GRAPH", "Team graph requires at least one worker")
    if len(raw_nodes) > max_workers:
        raise TeamGraphError("WORKER_LIMIT_EXCEEDED", f"Team graph supports at most {max_workers} workers")
    if len(raw_edges) > 200:
        raise TeamGraphError("INVALID_TEAM_GRAPH", "Team graph has too many edges")

    nodes: list[TeamNode] = []
    node_ids: set[str] = set()
    for raw in raw_nodes:
        if not isinstance(raw, dict) or set(raw) - {"id", "type", "label", "position", "agent_id", "instructions"}:
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team node contains unsupported fields")
        node_id = raw.get("id")
        label = raw.get("label")
        agent_id = raw.get("agent_id")
        instructions = raw.get("instructions")
        if raw.get("type") != "agent-ref" or not isinstance(node_id, str) or not node_id or not isinstance(label, str):
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team nodes must be agent-ref nodes")
        if node_id in node_ids:
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team node IDs must be unique")
        if not isinstance(agent_id, str):
            raise TeamGraphError("INVALID_TEAM_GRAPH", "agent-ref requires an agent_id")
        if instructions is not None and (not isinstance(instructions, str) or len(instructions) > 4_000):
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Node instructions exceed the allowed size")
        try:
            parsed_agent_id = UUID(agent_id)
        except ValueError as error:
            raise TeamGraphError("INVALID_TEAM_GRAPH", "agent-ref agent_id must be a UUID") from error
        node_ids.add(node_id)
        nodes.append(TeamNode(node_id, label, parsed_agent_id, instructions))

    edges: list[TeamEdge] = []
    edge_ids: set[str] = set()
    for raw in raw_edges:
        if not isinstance(raw, dict) or set(raw) - {"id", "source", "target"}:
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team edge contains unsupported fields")
        edge_id, source, target = raw.get("id"), raw.get("source"), raw.get("target")
        if not all(isinstance(value, str) and value for value in (edge_id, source, target)):
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team edges require ID, source, and target")
        assert isinstance(edge_id, str) and isinstance(source, str) and isinstance(target, str)
        if edge_id in edge_ids:
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team edge IDs must be unique")
        if source not in node_ids or target not in node_ids:
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team edge references a missing node")
        if source == target:
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team graph cannot contain a self-cycle")
        edge_ids.add(edge_id)
        edges.append(TeamEdge(edge_id, source, target))

    graph_value = TeamGraph(tuple(nodes), tuple(edges))
    _ensure_dag(graph_value)
    return graph_value


def _ensure_dag(graph: TeamGraph) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise TeamGraphError("INVALID_TEAM_GRAPH", "Team graph must be a DAG")
        if node_id in visited:
            return
        visiting.add(node_id)
        for successor in graph.successors(node_id):
            visit(successor)
        visiting.remove(node_id)
        visited.add(node_id)

    for node in graph.nodes:
        visit(node.id)
