import sys

import antlr3
from build.JumpLexer import JumpLexer
from build.JumpParser import JumpParser

def main(fileobj):
    char_stream = antlr3.ANTLRInputStream(fileobj)
    tokens = antlr3.CommonTokenStream(JumpLexer(char_stream))
    parser = JumpParser(tokens)
    root = parser.prog()

    print root.tree.toStringTree()


if __name__ == '__main__':
    if len(sys.argv) > 2 or (len(sys.argv) == 1 and sys.argv[1] in ('-h', '--help')):
        print >> sys.stderr, 'Usage: {0} [filename]'.format(sys.argv[0])
        sys.exit(1)

    if len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            main(f)
    else:
        main(sys.stdin)