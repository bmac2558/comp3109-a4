import operator as op

import build.JumpLexer as lex

from graph import JumpSyntaxError
from graph import LINR, GOTO, IFGOTO

OPERATORS = {
    '+': op.add,
    '-': op.sub,
    '*': op.mul,
    '/': op.div,
    '<': op.lt,
    '>': op.gt,
    '==': op.eq,
}

def get_varlit(node, force=None):
    if force is None or node.type == force:
        if node.type == lex.NUM:
            return int(node.text)
        if node.type == lex.IDENT:
            return str(node.text)

    raise JumpSyntaxError("Inappropriate type '{0}'.".format(node.type))

class Statement(object):
    """Has a statement for evaluation and a list of pointers to the next Statements"""
    def __init__(self, node, num):
        self.num = num
        self.type = node.type
        self.stmt = node.toStringTree()
        self.next = [None, None, None]  # LINR, GOTO, IFGOTO
        self.lhs = self.rhs = []

    def generate(self, gotos):
        if self.next[GOTO]:
            yield '  goto L{0};'.format(gotos[self.next[GOTO]])

    def __repr__(self):
        linr_next = self.next[LINR].num if self.next[LINR] else '//'
        goto_next = self.next[GOTO].num if self.next[GOTO] else '//'
        ifgoto_next = self.next[IFGOTO].num if self.next[IFGOTO] else '//'

        return "<Statement #{0:0>2} | LINR -> {1:0>2} | GOTO -> {2:0>2} | " \
               "IFGOTO -> {3:0>2} | {4:0>2} '{5}' >" .format(
                    self.num, linr_next, goto_next, ifgoto_next, self.type,
                    self.stmt)

class ReturnStmt(Statement):
    def __init__(self, node, num):
        super(ReturnStmt, self).__init__(node, num)
        self.var = get_varlit(node.children[0],)
        self.rhs = [self.var]

    def update(self, values):
        if isinstance(self.var, str):
            self.var = values.get(self.var, self.var)

    def generate(self, gotos):
        yield '  return {0};'.format(self.var)
        for line in super(ReturnStmt, self).generate(gotos):
            yield line

class AssignStmt(Statement):
    def __init__(self, node, num):
        super(AssignStmt, self).__init__(node, num)
        self.var = get_varlit(node.children[0], lex.IDENT)
        self.lhs = [self.var]
        self.source = get_varlit(node.children[1])
        self.rhs = [self.source] if isinstance(self.source, str) else []

    def update(self, values):
        """Replace RHS variables with literals, if in values; cull any LHS vars."""

        if isinstance(self.source, str):
            self.source = values.get(self.source, self.source)
        if self.var in values:
            del values[self.var]

        if isinstance(self.source, int):
            values[self.var] = self.source
        elif self.var in values:
            del values[self.var]

    def generate(self, gotos):
        yield '  {0} = {1};'.format(self.var, self.source)
        for line in super(AssignStmt, self).generate(gotos):
            yield line

class AssignOpStmt(Statement):
    def __init__(self, node, num):
        super(AssignOpStmt, self).__init__(node, num)
        self.var = get_varlit(node.children[0], lex.IDENT)
        self.lhs = [self.var]
        self.operator = node.children[2].text
        self.operands = [get_varlit(node.children[1]),
                         get_varlit(node.children[3])]
        self.rhs = [oper for oper in self.operands if isinstance(oper, str)]

    def update(self, values):
        """Replace RHS variables with literals, if in values; cull any LHS vars."""

        for i, op in enumerate(self.operands):
            if isinstance(op, str):
                self.operands[i] = values.get(self.operands[i], self.operands[i])

        op1 = self.operands[0]
        op2 = self.operands[1]

        if isinstance(op1, int) and isinstance(op2, int):
            result = OPERATORS[self.operator](op1, op2)
            if result is True:
                result = 1
            elif result is False:
                result = 0
            assert isinstance(result, int)
            values[self.var] = result
        elif self.var in values:
            del values[self.var]

    def generate(self, gotos):
        yield '  {0} = {1} {2} {3};'.format(self.var, self.operands[0],
                                            self.operator, self.operands[1])
        for line in super(AssignOpStmt, self).generate(gotos):
            yield line

class IfGotoStmt(Statement):
    def __init__(self, node, num):
        super(IfGotoStmt, self).__init__(node, num)
        self.cond = get_varlit(node.children[1],)
        self.rhs = [self.cond]

    def get_next(self, values):
        """Returns None if next is undecidable."""
        if self.cond in values:
            return IFGOTO if values[self.cond] != 0 else LINR
        return None

    def generate(self, gotos):
        yield '  if {0} goto L{1};'.format(self.cond, gotos[self.next[IFGOTO]])
        for line in super(IfGotoStmt, self).generate(gotos):
            yield line

class GotoStmt(Statement):
    def generate(self, gotos):
        yield '  goto L{0};'.format(self.next[GOTO])

class LabelStmt(Statement):
    def __init__(self, node, num):
        super(LabelStmt, self).__init__(node, num)
        self.name = node.text

    def generate(self, gotos):
        yield '  {0};'.format(self.name)
        for line in super(LabelStmt, self).generate(gotos):
            yield line

def get_statement(node, num):
    if node.type == lex.ASSIGN:
        return AssignStmt(node, num)
    elif node.type == lex.ASSIGNOP:
        return AssignOpStmt(node, num)
    elif node.type == lex.GOTO:
        return GotoStmt(node, num)
    elif node.type == lex.IFGOTO:
        return IfGotoStmt(node, num)
    elif node.type == lex.RETURN:
        return ReturnStmt(node, num)
    elif node.type == lex.REFLABEL:
        return LabelStmt(node, num)
