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
