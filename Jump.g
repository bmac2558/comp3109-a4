grammar Jump;

options {
    language=Python;
    output=AST;
}

tokens {
//    FUNC = 'func';
//    END = 'end';
//    LBRA = '(';
//    RBRA = ')';
//    COMMA = ',';
//    VAR = 'var';
    SCOL = ';';
    COL = ':';
    EQUAL = '=';
//    PLUS = '+';
//    MINUS = '-';
//    MULT = '*';
//    DIVIDE = '/';
//    MIN = 'min';
    GOTO = 'goto';
    RETURN = 'return';
    IF = 'if';

    PROGRAM;
//    FUNCTION;
//   PARAMS;
//    LOCALS;
//    STATEMENTS;
    ASSIGN;
//    EXPRMIN;
    STATEMENT;
    OPEQUAL;
    IFGOTO;
}

prog :	statement* EOF
        -> ^(PROGRAM statement*)
    ;

statement : label? stmt SCOL
            -> ^(STATEMENT stmt label?)
        ;

label   : LABEL COL -> LABEL;

stmt    : IDENT EQUAL expr -> ^(EQUAL IDENT expr)
        | IDENT EQUAL expr OP expr -> ^(OPEQUAL IDENT expr*)
        | GOTO LABEL -> ^(GOTO LABEL)
        | IF expr GOTO LABEL -> ^(IFGOTO LABEL expr)
        | RETURN expr
        ;

expr    : IDENT
        | NUM
        ;

//f   :
//        FUNC
//        ID
//        p
//        d
//        ss
//        END
//        -> ^(FUNCTION ID p d ss)
//    ;
//
//p   :	LBRA l RBRA
//        -> ^(PARAMS l*)
//    ;
//
//l   :	ID (COMMA! ID)*
//    ;
//
//d   :	(VAR l SCOL)*
//        -> ^(LOCALS l*)
//    ;
//
//ss  :   (s (SCOL s)* )?
//        -> ^(STATEMENTS s*)
//    ;
//
//s   :	ID EQUAL e
//        -> ^(ASSIGN ID e)
//    ;
//
//plus_or_minus : PLUS | MINUS ;
//e   :	e2 (plus_or_minus^ e)?
//    ;
//
//mult_or_div : MULT | DIVIDE ;
//e2  :	e3 (mult_or_div^ e2)?
//    ;
//
//e3  :	MIN LBRA e COMMA e RBRA
//        -> ^(EXPRMIN e*)
//    |	LBRA e RBRA
//        -> e
//    |	ID
//    |	NUM
//    ;

OP      :   ('+'|'-'|'*'|'/'|'<'|'>'|'==') ;

NUM     :   '-'? ('0'..'9')+ ;

IDENT   :   ('a'..'z') ('a'..'z'|'0'..'9')* ;

LABEL   :   ('A'..'Z') ('A'..'Z'|'0'..'9')* ;

//ID  :	    ('a'..'z'|'A'..'Z'|'_') ('a'..'z'|'A'..'Z'|'0'..'9'|'_')* ;

//NUM :	    ('0'..'9')+ ('.'('0'..'9')+)? ;

WS  :       ( ' ' | '\t' | '\n' | '\r' | '\u000C' )+ { $channel = HIDDEN; } ;
