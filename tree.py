import build.JumpLexer as lex

LINR = 0
GOTO = 1

class CFGraph(object):
    def __init__(self, root):
        self.statements = []
        blocks = {}

        last = None
        for i, child in enumerate(root.children):
            node = Statement(child, i)
            self.statements.append(node)

            # add the next pointer to the previous statement
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

        print 'Without GOTOs:'
        print self

        # link via goto statements
        last = None
        for i, stmt in enumerate(self.statements):
            if stmt.type in (lex.GOTO, lex.IFGOTO):
                target = root.children[i].children[0].text
                stmt.next[GOTO] = self.statements[blocks[target]]

                if stmt.type == lex.GOTO:
                    last = None
                else:
                    last = stmt

            elif stmt.type == lex.RETURN:
                last = None

            else:
                last = stmt

        print 'With GOTOs:'
        print self
            
    def dotfile(self, fileobj):
        fileobj.write('digraph CFGraph {\n')

        for stmt in self.statements:
            fileobj.write('    s{0} [label="{1}"] [shape="box"];\n'.format(
                stmt.num, stmt.stmt))

        for stmt in self.statements:
            for edge_type in (LINR, GOTO):
                target = stmt.next[edge_type]
                if target:
                    fileobj.write('    s{0} -> s{1};\n'.format(stmt.num, target.num))

        fileobj.write('}\n')

    def __repr__(self):
        return '\n'.join([repr(stmt) for stmt in self.statements])
            
class Statement(object):
    """Has a statement for evaluation and a list of pointers to the next Statements"""
    def __init__(self, node, num):
        self.num = num
        self.type = node.type
        self.stmt = node.toStringTree()
        self.next = [None, None]

    def __repr__(self):
        nextnum = lambda idx: self.next[idx].num if self.next[idx] else '//'
        return "<Statement #{0:0>2} | LINR -> {3:0>2} | GOTO -> {4:0>2} | {1:0>2} '{2}' ".format(
                self.num, self.type, self.stmt, nextnum(0), nextnum(1))
