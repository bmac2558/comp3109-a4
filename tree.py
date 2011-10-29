import build.JumpLexer as lex

class CFGraph(object):
    def __init__(self, root):
        statements = []
        blocks = {}
        for i, child in enumerate(root.children):
            if child.type == lex.BLOCK:
                blocks[child.children[0].text] = root.children[i + 1]

        for i, child in enumerate(root.children):
            if child.type == lex.BLOCK:
                pass
            elif child.type == lex.IF:
                pass
            elif child.type == lex.RETURN:
                pass
            elif child.type == lex.GOTO:
                pass
            else:
                node = Statement(child)
                
        print blocks

    def dotfile(self, fileobj):
        pass
            
class Statement(object):
    """Has a statement for evaluation and a list of pointers to the next Statements"""
    def __init__(self, node):
        self.type = node.type
        self.next = []
        self.stmt = node.toStringTree()
