from collections import defaultdict
import build.JumpLexer as lex

from graph import JumpSyntaxError
from graph import LINR, GOTO, IFGOTO
from graph.statement import get_statement

class CFGraph(object):
    def __init__(self, root):
        self.statements = []
        blocks = {}

        # create all statements and link those that follow linearly
        last = None
        for i, child in enumerate(root.children):
            node = get_statement(child, i)
            self.statements.append(node)

            # add the linear `next` pointer to the previous statement
            # (ignore block markers (labels); the `next` pointer will be set to
            # the subsequent statement on the next pass)
            if last and child.type != lex.REFLABEL:
                last.next[LINR] = node

            if child.type == lex.REFLABEL:
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
        # forge links from (if)goto statements
        for i, stmt in enumerate(self.statements):
            if stmt.type == lex.GOTO:
                target = root.children[i].children[0].text
                stmt.next[GOTO] = self.statements[blocks[target]]
            elif stmt.type == lex.IFGOTO:
                target = root.children[i].children[0].text
                stmt.next[IFGOTO] = self.statements[blocks[target]]


        # find the start (entry) node
        idx = 0
        while self.statements[idx].type == lex.REFLABEL:
            idx += 1
            if idx > len(self.statements):
                raise RuntimeError("Cannot find an entry statement!")
        
        self.start = self.statements[idx]

        # NOTE equivalence of stmt.num and self.statements.index(stmt)
        # not guaranteed beyond this point

        self.eliminate_gotos()

    def eliminate_gotos(self):
        """
        """
        # eliminate GOTOs
        for stmt in self.statements:
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
###                    print "Moving start (was: {0})".format(stmt)
                    self.start = snext

        for stmt in self.statements:
            if stmt.type == lex.GOTO:
                stmt.next = [None, None, None]

    def optimise(self):
        self.UCE()
        self.DCE()

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

    def DCE(self):
        """Dead code elimination."""

        # first, find all backrefs of GOTOs
        # { stmt: [ ( prev, type ), ... ], ... }; type in (LINR, GOTO, IFGOTO)
        backrefs = defaultdict(list)
        terminal_nodes = []
        for stmt in self.statements:

            if stmt.next == [None, None, None]:
                terminal_nodes.append(stmt)
                continue

            for edge_type in (LINR, GOTO, IFGOTO):
                target = stmt.next[edge_type]
                if target is not None:
                    backrefs[target].append((stmt, edge_type))
        print
###        print "RIGHT HERE BOYZ!"
###        for key in sorted(backrefs.keys(), key=lambda x: x.num):
###            print key, backrefs[key]
        print "Terminal Nodes:", terminal_nodes

        gen = lambda stmt: set(stmt.rhs)
        kill = lambda stmt: set(stmt.lhs)
        fn = lambda node, x: gen(node).union((x - kill(node)))

        def out_stmt(stmt):
            in_ = set()
            for edge in stmt.next:
                if edge:
                    in_ |= out_stmt(edge)

            kill_it = (len(kill(stmt) - in_) > 0)

            return fn(stmt, in_), kill_it

        def destroy(stmt):
            """Eliminate a statement from the graph."""

            target = None
            for edge_type in (LINR, GOTO, IFGOTO):
                if stmt.next[edge_type]:
                    target = stmt.next[edge_type]
                    break

            for prev, prev_type in backref[stmt]:
                prev.next[prev_type] = target

            if target:
                backref[target].extend(backref[stmt])
            del backref[stmt]

            self.statements.remove(stmt)

        todo = terminal_nodes
        while todo:
            stmt = todo.pop(0)
            in_ = set()
            out, kill_it = out_stmt(stmt)
            if kill_it:
                todo.extend([b[0] for b in backrefs[stmt]])
                destroy(stmt)


    def generate(self):
        gotos = {}  # maps goto targets to unique numbers
        gotos[self.statements[0]] = 0

        for stmt in self.statements:
            if stmt.next[GOTO]:
                gotos[stmt.next[GOTO]] = len(gotos)
            if stmt.next[IFGOTO]:
                gotos[stmt.next[IFGOTO]] = len(gotos)

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
            if stmt.type not in (lex.REFLABEL, lex.GOTO):
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
