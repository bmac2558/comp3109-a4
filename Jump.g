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
}

prog :	statement* EOF -> ^(PROGRAM statement*) ;

statement   : stmt SCOL!
            | label stmt SCOL!
            ;

label   : LABEL COL! ;

stmt    : IDENT EQUAL expr -> ^(EQUAL IDENT expr)
        | IDENT EQUAL expr OP expr -> ^(OPEQUAL IDENT ^(OP expr*))
        | GOTO LABEL -> ^(GOTO LABEL)
        | IF expr GOTO LABEL -> ^(IFGOTO LABEL expr)
        | RETURN expr -> ^(RETURN expr)
        ;

expr    : IDENT
        | NUM
        ;

OP      :   ('+'|'-'|'*'|'/'|'<'|'>'|'==') ;

NUM     :   '-'? ('0'..'9')+ ;

IDENT   :   ('a'..'z') ('a'..'z'|'0'..'9')* ;

LABEL   :   ('A'..'Z') ('A'..'Z'|'0'..'9')* ;

WS  :       ( ' ' | '\t' | '\n' | '\r' | '\u000C' )+ { $channel = HIDDEN; } ;
