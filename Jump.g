grammar Jump;

options {
    language=Python;
    output=AST;
}

tokens {
    SCOL = ';';
    COL = ':';
    EQUAL = '=';
    GOTO = 'goto';
    RETURN = 'return';
    IF = 'if';

    PROGRAM;
    ASSIGN;
    STATEMENT;
    OPEQUAL;
    IFGOTO;
    BLOCK;
}

prog :	statement* EOF -> ^(PROGRAM statement*) ;

statement   : stmt SCOL!
            | label stmt SCOL!
            ;

label   : LABEL COL -> ^(BLOCK LABEL) ;

stmt    : IDENT EQUAL expr -> ^(IDENT EQUAL expr)
        | IDENT EQUAL expr OP expr2 -> ^(IDENT EQUAL expr OP expr2)
        | GOTO LABEL -> ^(GOTO LABEL)
        | IF expr GOTO LABEL -> ^(IF expr GOTO LABEL)
        | RETURN expr -> ^(RETURN expr)
        ;

expr    : IDENT
        | NUM
        ;

expr2   : expr
        ;

OP      :   ('+'|'-'|'*'|'/'|'<'|'>'|'==') ;

NUM     :   '-'? ('0'..'9')+ ;

IDENT   :   ('a'..'z') ('a'..'z'|'0'..'9')* ;

LABEL   :   ('A'..'Z') ('A'..'Z'|'0'..'9')* ;

WS  :       ( ' ' | '\t' | '\n' | '\r' | '\u000C' )+ { $channel = HIDDEN; } ;
