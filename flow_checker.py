"""Verificações de fluxo de dados e controle."""

from __future__ import annotations

import load_previous

from ast_nodes import (
    Assignment,
    BinaryExpr,
    CallExpr,
    CallStmt,
    Expr,
    IdentifierExpr,
    PrintStmt,
    TypeName,
    UnaryExpr,
    VarDecl,
)
from cfg import Branch, CFG, Return, ScopeExit
from initialization import InitializationFacts, symbol_of
from semantic_errors import SemanticDiagnostic, SemanticErrorKind


class ReadChecker:
    def __init__(self) -> None:
        self.diagnostics: list[SemanticDiagnostic] = []

    def check(
        self, cfg: CFG, reachable: set[int], initialization: InitializationFacts
    ) -> list[SemanticDiagnostic]:
        self.diagnostics = []

        for block_id in sorted(reachable):
            block = cfg.blocks[block_id]
            state = set(initialization.initialized_in[block_id])

            for op in block.operations:
                self._check_operation(op, state)

            self._check_terminator(block.terminator, state)

        return self.diagnostics

    def _check_operation(self, op, state: set) -> None:
        if isinstance(op, VarDecl):
            sym = symbol_of(op)
            state.discard(sym)
            if op.initializer is not None:
                self._check_expr(op.initializer, state)
                state.add(sym)

        elif isinstance(op, Assignment):
            self._check_expr(op.value, state)
            state.add(symbol_of(op.target))

        elif isinstance(op, PrintStmt):
            for item in op.items:
                if isinstance(item, Expr):
                    self._check_expr(item, state)

        elif isinstance(op, CallStmt):
            self._check_expr(op.call, state)

        elif isinstance(op, ScopeExit):
            state.difference_update(op.scope.symbols.values())

    def _check_terminator(self, terminator, state: set) -> None:
        if terminator is None:
            return

        if isinstance(terminator, Branch):
            self._check_expr(terminator.condition, state)

        elif isinstance(terminator, Return):
            if terminator.statement.value is not None:
                self._check_expr(terminator.statement.value, state)

    def _check_expr(self, expr: Expr | None, state: set) -> None:
        if expr is None:
            return

        if isinstance(expr, IdentifierExpr):
            sym = symbol_of(expr)
            if sym not in state:
                self.diagnostics.append(
                    SemanticDiagnostic(
                        kind=SemanticErrorKind.UNINITIALIZED_READ,
                        message=f"Leitura da variável '{expr.name}' sem inicialização garantida.",
                        span=expr.span,
                    )
                )

        elif isinstance(expr, BinaryExpr):
            self._check_expr(expr.left, state)
            self._check_expr(expr.right, state)

        elif isinstance(expr, UnaryExpr):
            self._check_expr(expr.operand, state)

        elif isinstance(expr, CallExpr):
            for arg in expr.arguments:
                self._check_expr(arg, state)


def check_function_exit(cfg: CFG, reachable: set[int]) -> list[SemanticDiagnostic]:
    """Verifica se uma função não-void pode alcançar o fim de seu corpo."""
    if cfg.function.return_type != TypeName.VOID and cfg.fallthrough_exit in reachable:
        return [
            SemanticDiagnostic(
                kind=SemanticErrorKind.MISSING_RETURN,
                message=f"A função não-void '{cfg.function.name}' pode alcançar o fim sem retornar um valor.",
                span=cfg.function.span,
            )
        ]
    return []