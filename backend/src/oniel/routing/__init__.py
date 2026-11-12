"""Grafo de rutas y escenarios: por dónde se va de un nodo a otro con la red así, y cuánto cuesta."""

from oniel.routing.graph import (
    DEFAULT_MAX_CHANGES,
    DEFAULT_MAX_RATIO,
    Detour,
    Edge,
    Graph,
    GraphNode,
    Route,
    RouteLeg,
    build_graph,
    closure_detours,
    find_routes,
)
from oniel.routing.scenario import Scenario, ScenarioError, SketchLink, SpeedChange

__all__ = [
    "DEFAULT_MAX_CHANGES",
    "DEFAULT_MAX_RATIO",
    "Detour",
    "Edge",
    "Graph",
    "GraphNode",
    "Route",
    "RouteLeg",
    "Scenario",
    "ScenarioError",
    "SketchLink",
    "SpeedChange",
    "build_graph",
    "closure_detours",
    "find_routes",
]
