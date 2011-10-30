import sys
from collections import defaultdict
import build.JumpLexer as lex

from graph import JumpSyntaxError
from graph import LINR, GOTO, IFGOTO
from graph.statement import get_statement

class CFGraph(object):
    def __init__(self, root):
        self.gotos_expanded = True
        self.statements = []
        labels = {}

        # create all statements and link those that follow linearly
        last = None  # the current `stmt` is the LINR child of `last`, if `last`
        for i, node in enumerate(root.children):
            stmt = get_statement(node, i)
            self.statements.append(stmt)

            # add the linear `next` pointer to the previous statement
            # (ignore block markers (labels); the `next` pointer will be set to
            # the subsequent statement on the next pass)
            if last and node.type != lex.REFLABEL:
                last.next[LINR] = stmt

            if node.type == lex.REFLABEL:
                # a label points to the subsequent 'stmt' (as defined in Jump.g)
                label = node.children[0].text
                labels[label] = i + 1

            elif node.type == lex.RETURN:
                # terminal statement; has no `next`
                last = None

            elif node.type in (lex.GOTO, lex.IFGOTO):
                # goto; ensure the target is in the labels dict
                assert node.children[0].type == lex.LABEL
                target = node.children[0].text
                if target not in labels:
                    labels[target] = None

                # IFGOTOs have a LINR next; GOTOs do not
                if node.type == lex.GOTO:
                    last = None
                else:
                    last = stmt

            else:
                # assignment statement
                last = stmt

        # check that all GOTO targets exist
        for label, target in labels.iteritems():
            if target is None:
                raise JumpSyntaxError("GOTO target '{0}' does not exist."
                                      .format(label))

        # forge GOTO and IFGOTO links
        for i, stmt in enumerate(self.statements):
            if stmt.type in (lex.GOTO, lex.IFGOTO):
                edge_type = GOTO if stmt.type == lex.GOTO else IFGOTO
                target_label = root.children[i].children[0].text
                stmt.next[edge_type] = self.statements[labels[target_label]]

        # find the start (entry) statement
        idx = 0
        while self.statements[idx].type == lex.REFLABEL:
            idx += 1
            if idx > len(self.statements):
                # this should never happen; should be a syntax error in ANTLR
                raise RuntimeError("Cannot find an entry statement!")
        
        self.start = self.statements[idx]

        # NOTE equivalence of stmt.num and self.statements.index(stmt)
        # not guaranteed beyond this point

        self.eliminate_gotos()

    def eliminate_gotos(self):
        """
        Remove all GOTO statement nodes; preserving references.

        The references are preserved in the preceiding statement's GOTO pointer
        slot in its `next` attribute.

        """
        assert self.gotos_expanded

        for stmt in self.statements:
            # we need to repoint self.start if it's currently on a GOTO
            # about to be eliminated...
            move_start = (stmt == self.start and stmt.type == lex.GOTO)

            for edge_type in (LINR, GOTO, IFGOTO):

                snext = stmt.next[edge_type]

                if snext is None:
                    continue

                # work though any consecutive GOTO references until we hit a
                # 'concrete' statement
                visited = []
                while snext.type == lex.GOTO:
                    if snext in visited:
                        # XXX handle this better?  or is exploding appropriate?
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
                    assert edge_type == GOTO, \
                        "Should only be moving self.start if it points to a GOTO."
                    self.start = snext

        for stmt in self.statements:
            if stmt.type == lex.GOTO:
                stmt.next = [None, None, None]

        self.gotos_expanded = False

    def get_backrefs(self):
        """Return a backrefs mapping from each stmt to those that refer to it."""

        # { stmt: [ ( prev, type ), ... ], ... }; type in (LINR, GOTO, IFGOTO)
        backrefs = defaultdict(list)
        backrefs[self.start] = []

        for stmt in self.statements:
            for edge_type in (LINR, GOTO, IFGOTO):

                target = stmt.next[edge_type]
                if target is not None:
                    backrefs[target].append((stmt, edge_type))

        return dict(backrefs)

    def optimise(self):
        self.UCE()
        print
        print "  ---> Post-UCE:"
        print self
        self.JE()
        print
        print "  ---> Post-J:"
        print self
        self.DCE()
        print
        print "  ---> Post-DCE:"
        print self

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

    def JE(self):
        assert not self.gotos_expanded

        dists = dict()
        todo = [(self.start, 0)]
        visited = set()
        while todo:
            curr, dist = todo.pop(0)
            dists[curr] = dist
            todo.extend((t, dist + 1) for t in curr.next
                        if t and t not in visited)
            visited.update(set([t for t in curr.next if t]))

        # make a best-effort attempt to have as many stmts with one LINR
        # parent (backref) as possible
        backrefs = self.get_backrefs()
        for stmt, parents in backrefs.iteritems():
            if stmt == self.start:
                continue

            existing_linr = [p for p, edge_type in parents if edge_type == LINR]
            assert len(existing_linr) <= 1, "Cannot have multiple linear parents."
            existing_linr = existing_linr[0] if existing_linr else None

            f = lambda p: dists[p[0]]  # distance of parent from start node
            for parent, edge_type in sorted(parents, key=f):
                if parent == stmt:
                    continue
                if parent == existing_linr:
                    break
                if edge_type == GOTO and parent.next[LINR] is None:
                    parent.next[LINR] = stmt
                    parent.next[GOTO] = None
                    idx = backrefs[stmt].index((parent, GOTO))
                    backrefs[stmt][idx] = (parent, LINR)
                    if existing_linr:
                        existing_linr.next[LINR] = None
                        existing_linr.next[GOTO] = stmt
                        idx = backrefs[stmt].index((existing_linr, LINR))
                        backrefs[stmt][idx] = (existing_linr, GOTO)
                    break

    def DCE(self):
        """Dead code elimination."""

        backrefs = self.get_backrefs()

        terminal_nodes = []
        for stmt in self.statements:
            if stmt.next == [None, None, None]:
                terminal_nodes.append(stmt)
###        print
###        print "RIGHT HERE BOYZ!"
###        for key in sorted(backrefs.keys(), key=lambda x: x.num):
###            print key, backrefs[key]
###        print "Terminal Nodes:", terminal_nodes

        gen = lambda stmt: set(stmt.rhs)
        kill = lambda stmt: set(stmt.lhs)
        fn = lambda node, x: gen(node).union((x - kill(node)))

        def out_stmt(stmt, visited=None):
            visited = visited or []
            in_ = set()
            for edge in stmt.next:
                if edge and edge not in visited:
                    visited.append(edge)
                    in_ |= out_stmt(edge, visited)[0]

            kill_it = (len(kill(stmt) - in_) > 0)
###            print "IN:", in_, stmt

            return fn(stmt, in_), kill_it

        def destroy(stmt):
            """Eliminate a statement from the graph."""

            assert stmt.type != lex.IFGOTO

            for prev, _ in backrefs[stmt]:
                for edge_type in (LINR, GOTO):
                    prev.next[edge_type] = stmt.next[edge_type]

            for edge_type in (LINR, GOTO):
                target = stmt.next[edge_type]
                if target:
                    backrefs[target].extend(backrefs[stmt])
            del backrefs[stmt]

            self.statements.remove(stmt)

        sys.setrecursionlimit(20)
        todo = []
        todo.extend(terminal_nodes)
        visited = []
        while todo:
###            print stmt
            stmt = todo.pop(0)
            if stmt in visited:
                continue
            visited.append(stmt)
            in_ = set()
            out, kill_it = out_stmt(stmt)
###            print "OUT", out, kill_it, stmt
            todo.extend([b[0] for b in backrefs[stmt]])
            if kill_it:
                destroy(stmt)


    def generate(self):
        gotos = {}  # maps goto targets to unique numbers
        gotos[self.start] = 0

        for stmt in self.statements:
            for edge_type in (GOTO, IFGOTO):
                target = stmt.next[edge_type]
                if target == self.start:
                    continue
                if target:
                    gotos[target] = len(gotos)

        # start and the start node and print linearly where possible;
        # sticking goto targets on the todo stack
        todo = [self.start]
        visited = [self.start]
        while todo:
            stmt = todo.pop()

            label_num = gotos.get(stmt)
            if label_num is not None:
                yield 'L{0}:'.format(label_num)

            for line in stmt.generate(gotos):
                yield line

            for edge_type in (GOTO, IFGOTO, LINR):
                target = stmt.next[edge_type]
                if target and target not in visited:
                    todo.append(target)
                    visited.append(target)

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
