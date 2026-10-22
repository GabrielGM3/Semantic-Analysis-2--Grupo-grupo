from __future__ import annotations

import load_previous

from name_resolver import resolve_names
from type_checker import check_types
from flow_analysis import check_flow


class SemanticAnalyzer:
    def analyze(self, program):
        resolve_names(program)
        check_types(program)
        check_flow(program)
        return program


def analyze_semantics(program):
    return SemanticAnalyzer().analyze(program)