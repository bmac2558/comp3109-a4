import build.JumpLexer as lex

# Each node in the CFG may have up to two potential subsequent nodes (typical
# statements and unconditional GOTOs have one, conditional GOTOs have two and
# return statements have none (along with some dangling code)).
# We define every node to have a 2-element list of pointers to the "next" node;
# the first we take to point to the next line of code, linearly following the
# current, and the second we take to point to the target of a GOTO statement.
LINR = 0
GOTO = 1
IFGOTO = 2

class JumpSyntaxError(ValueError): pass

class CFGraph(object):
    def __init__(self, root):
        self.statements = []
        blocks = {}

        # create all statements and link those that follow linearly
        last = None
        for i, child in enumerate(root.children):
            node = Statement(child, i)
            self.statements.append(node)

            # add the linear `next` pointer to the previous statement
            # (ignore block markers (labels); the `next` pointer will be set to
            # the subsequent statement on the next pass)
            if last and child.type != lex.BLOCK:
                last.next[LINR] = node

            if child.type == lex.BLOCK:
                # a BLOCK p
                target = child.children[0].text
                blocks[target] = i + 1

            elif child.type == lex.RETURN:
                # terminal node
                last = None

            elif child.type in (lex.GOTO, lex.IFGOTO):
                # goto; ensure the target is in the blocks dict
                assert child.children[0].type == lex.LABEL
                target = child.children[0].text
                if target not in blocks:
                    blocks[target] = None

                if child.type == lex.GOTO:
                    last = None
                else:
                    last = node

            else:
                # assignment statement
                last = node

        # check that all GOTO targets exist
        for label, target in blocks.iteritems():
            if target is None:
                raise JumpSyntaxError("GOTO target '{0}' does not exist."
                                      .format(label))

        # link via goto statements
        for i, stmt in enumerate(self.statements):
            if stmt.type == lex.GOTO:
                target = root.children[i].children[0].text
                stmt.next[GOTO] = self.statements[blocks[target]]
            elif stmt.type == lex.IFGOTO:
                target = root.children[i].children[0].text
                stmt.next[IFGOTO] = self.statements[blocks[target]]


        # find the start (entry) node
        idx = 0
        while self.statements[idx].type == lex.BLOCK:
            idx += 1
            if idx > len(self.statements):
                raise RuntimeError("Cannot find an entry statement!")
        
        self.start = self.statements[idx]

        # NOTE equivalence of stmt.num and self.statements.index(stmt)
        # not guaranteed beyond this point

        # eliminate GOTOs
        for stmt in self.statements:
            print stmt
            for edge_type in (LINR, GOTO, IFGOTO):

                snext = stmt.next[edge_type]

                if snext is None:
                    continue

                # we need to repoint self.start if it's currently on a GOTO
                # about to be eliminated...
                move_start = (stmt == self.start and stmt.type == lex.GOTO)

                visited = []
                while snext.type == lex.GOTO:
                    if snext in visited:
                        raise JumpSyntaxError("OMG INFINITE GOTO LOOPSIES!")
                    visited.append(snext)
                    snext = snext.next[GOTO]

                # maintain the [LINR, GOTO, IFGOTO] convention
                if stmt.next[edge_type].type == lex.GOTO:
                    if edge_type == LINR:
                        stmt.next[LINR] = None
                        stmt.next[GOTO] = snext
                    else:
                        stmt.next[edge_type] = snext
                else:
                    stmt.next[edge_type] = snext

                if move_start:
                    print "Moving start (was: {0})".format(stmt)
                    self.start = snext

        for stmt in self.statements:
            if stmt.type == lex.GOTO:
                stmt.next = [None, None, None]

    def UCE(self):
        """Unreachable code elimination."""

        cur_nodes = [self.start]
        for node in cur_nodes:
###            print "Curr:", cur_nodes
            for target_node in node.next:
###                print "  Tgt:", target_node
                if target_node not in cur_nodes and target_node != None:
                    cur_nodes.append(target_node)

        self.statements = sorted(cur_nodes, key=lambda x: x.num)

    def reconstitute(self):
        """Inserts GOTOs; """
        code = []
        gotos = {}  # maps goto targets to unique numbers
        gotos[self.statements[0]] = 0
        for stmt in self.statements:
            print stmt, stmt.next
            if stmt.next[GOTO]:
                gotos[stmt.next[GOTO]] = len(gotos)
            if stmt.next[IFGOTO]:
                gotos[stmt.next[IFGOTO]] = len(gotos)
        return gotos

    def generate(self):
        gotos = self.reconstitute()
        print gotos

        for stmt in self.statements:
            label_num = gotos.get(stmt)
            if label_num is not None:
                yield 'L{0}:'.format(label_num)
            for line in stmt.generate(gotos):
                yield line

    def dotfile(self, fileobj):
        """Write to fileobj a .dot (GraphViz) representation of the graph."""

        fileobj.write('digraph CFGraph {\n')

        # declare all the nodes (typically staements)
        fileobj.write('    start;\n')
        for stmt in self.statements:
            if stmt.type not in (lex.BLOCK, lex.GOTO):
                fileobj.write('    s{0} [label="{1}"] [shape="box"];\n'
                              .format(stmt.num, stmt.stmt))

        # declare all the edges
        fileobj.write('    start -> s{0};\n'.format(self.start.num))
        for stmt in self.statements:
            for edge_type in (LINR, GOTO, IFGOTO):
                target = stmt.next[edge_type]
                if target:
                    fileobj.write('    s{0} -> s{1};\n'
                                  .format(stmt.num, target.num))

        fileobj.write('}\n')

    def __repr__(self):
        return '\n'.join([repr(stmt) for stmt in self.statements])
            
class Statement(object):
    """Has a statement for evaluation and a list of pointers to the next Statements"""
    def __init__(self, node, num):
        self.num = num
        self.type = node.type
        self.stmt = node.toStringTree()
        self.next = [None, None, None]  # LINR, GOTO, IFGOTO

    def generate(self, gotos):
        if self.type == lex.IFGOTO:
            _, _, cond = self.stmt.strip('()').split()
            yield '  if {0} goto L{1}'.format(cond, gotos[self.next[IFGOTO]])
        else:
            yield '  ' + self.stmt.strip('()')
        if self.next[GOTO]:
            yield '  goto L{0}'.format(gotos[self.next[GOTO]])

    def __repr__(self):
        linr_next = self.next[LINR].num if self.next[LINR] else '//'
        goto_next = self.next[GOTO].num if self.next[GOTO] else '//'
        ifgoto_next = self.next[IFGOTO].num if self.next[IFGOTO] else '//'

        return "<Statement #{0:0>2} | LINR -> {1:0>2} | GOTO -> {2:0>2} | " \
               "IFGOTO -> {3:0>2} | {4:0>2} '{5}' >" .format(
                    self.num, linr_next, goto_next, ifgoto_next, self.type,
                    self.stmt)
