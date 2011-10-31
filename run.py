import sys

import antlr3
from build.JumpLexer import JumpLexer
from build.JumpParser import JumpParser
from graph.cfg import CFGraph

def main(fileobj):
    char_stream = antlr3.ANTLRInputStream(fileobj)
    tokens = antlr3.CommonTokenStream(JumpLexer(char_stream))
    parser = JumpParser(tokens)
    root = parser.prog()

    graph = CFGraph(root.tree)

    optimised = False
    code = [line for line in graph.generate()]
    while not optimised:
        graph.optimise(True)
        current_code = [line for line in graph.generate()]
        if code == current_code:
            optimised = True
        else:
            code = current_code
    
    print "\n".join(code)

    with open('cfg.dot', 'w') as f:
        graph.dotfile(f)


if __name__ == '__main__':
    if len(sys.argv) > 3 or (len(sys.argv) == 1 and sys.argv[1] in ('-h', '--help')):
        print >> sys.stderr, 'Usage: {0} [filename]'.format(sys.argv[0])
        sys.exit(1)

    if len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            main(f)
    else:
        main(sys.stdin)
