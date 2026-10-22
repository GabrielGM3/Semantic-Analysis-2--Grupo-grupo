"""Construa um CFG auxiliar por função, preservando os nós da AST.

    BasicBlock
        statements: list[Stmt]
        terminator: Branch |
        Jump | Return
        predecessors: set[BlockId]
        successors: set[BlockId]

"""

from __future__ import annotations

import load_previous  # Disponibiliza os módulos das etapas anteriores.

from ast_nodes import Block, FunctionDecl, IfStmt, Stmt, WhileStmt, ReturnStmt
from cfg import BlockId, CFG, Jump, Branch, Return, ScopeExit


class CFGBuilder:
    def build(self, function: FunctionDecl) -> CFG:
        self.cfg = CFG(function)
        body_entry = self.cfg.new_block()
        self.cfg.terminate(self.cfg.entry, Jump(body_entry.id))
        continuation = self._build_block(function.body, body_entry.id)
        if continuation is not None:
            self.cfg.terminate(continuation, Jump(self.cfg.fallthrough_exit))
        return self.cfg

    def _build_block(self, block: Block, current: BlockId) -> BlockId | None:
        """Percorra um bloco da AST e devolva sua continuação normal.

        `current` identifica um bloco básico aberto. Comandos sequenciais
        permanecem nele. Comandos de controle podem mudar a continuação.
        None indica que os caminhos deste bloco não alcançam o próximo comando.
        """
        for stmt in block.statements:
            if current is None:
                break
            current = self._build_statement(stmt, current)
            
        # Registra a saída de escopo caso o fluxo normal alcance o fim do bloco
        if current is not None:
            scope = block.metadata.get("scope")
            if scope is not None:
                self.cfg.blocks[current].operations.append(ScopeExit(scope))
                
        return current

    def _build_statement(self, statement: Stmt, current: BlockId) -> BlockId | None:
        """Incorpore um comando ao CFG e devolva sua continuação normal."""
        if isinstance(statement, IfStmt):
            return self._build_if(statement, current)
        elif isinstance(statement, WhileStmt):
            return self._build_while(statement, current)
        elif isinstance(statement, ReturnStmt):

            self.cfg.terminate(current, Return(statement))
            return None
        elif isinstance(statement, Block):

            return self._build_block(statement, current)
        else:
            self.cfg.blocks[current].operations.append(statement)
            return current

    def _build_if(self, statement: IfStmt, current: BlockId) -> BlockId | None:
        """Construa o fluxo da condicional e devolva sua continuação."""
        then_block = self.cfg.new_block()
        merge_block = self.cfg.new_block()
        
        reached_merge = False

        if statement.else_block is not None:
            else_block = self.cfg.new_block()
            self.cfg.terminate(current, Branch(statement.condition, then_block.id, else_block.id))

            then_cont = self._build_block(statement.then_block, then_block.id)
            if then_cont is not None:
                self.cfg.terminate(then_cont, Jump(merge_block.id))
                reached_merge = True

            else_cont = self._build_block(statement.else_block, else_block.id)
            if else_cont is not None:
                self.cfg.terminate(else_cont, Jump(merge_block.id))
                reached_merge = True

        else:
            self.cfg.terminate(current, Branch(statement.condition, then_block.id, merge_block.id))
            reached_merge = True

            then_cont = self._build_block(statement.then_block, then_block.id)
            if then_cont is not None:
                self.cfg.terminate(then_cont, Jump(merge_block.id))


        return merge_block.id if reached_merge else None

    def _build_while(self, statement: WhileStmt, current: BlockId) -> BlockId | None:
        """Construa o fluxo do laço e devolva sua continuação."""
        header_block = self.cfg.new_block()
        body_block = self.cfg.new_block()

        self.cfg.terminate(current, Jump(header_block.id))


        cond = statement.condition
        is_infinite_loop = (
                getattr(cond, "value", None) is True
                or getattr(cond, "literal", None) is True
                or (type(cond).__name__ in ("BoolLiteral", "BooleanLiteral", "BoolExpr", "LiteralExpr") and getattr(
            cond, "lexeme", "") == "true")
        )

        if is_infinite_loop:
            
            self.cfg.terminate(header_block.id, Branch(statement.condition, body_block.id, body_block.id))
            continuation = None
        else:
            after_block = self.cfg.new_block()
            self.cfg.terminate(header_block.id, Branch(statement.condition, body_block.id, after_block.id))
            continuation = after_block.id

        body_cont = self._build_block(statement.body, body_block.id)
        if body_cont is not None:
            self.cfg.terminate(body_cont, Jump(header_block.id))

        return continuation