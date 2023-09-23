// hay que definir un postlexer para que sea capaz de parsear la identación
//class PythonIndenter(Indenter):
//    NL_type = '_NEWLINE'
//    OPEN_PAREN_types = ['LPAR', 'LSQB', 'LBRACE']
//    CLOSE_PAREN_types = ['RPAR', 'RSQB', 'RBRACE']
//    INDENT_type = '_INDENT'
//    DEDENT_type = '_DEDENT'
//    tab_len = 8


start:input

input: (_NEWLINE | stmt)*

?stmt: simple_stmt | compound_stmt | flow_stmt | vardef

compound_stmt: if_stmt | for_stmt | funcdef | while_stmt | tabledef

?flow_stmt: pass_stmt | break_stmt | continue_stmt | yield_stmt | return_stmt

pass_stmt: "pass"
break_stmt: "break"
return_stmt: "return" test? _NEWLINE?
continue_stmt: "continue"
yield_stmt: "yield"

simple_stmt: test ((auto_assign | "=") test)* _NEWLINE // hay que poner el newline porque tal y como he definido suite, las newlines van incorporadas (requiere \n para funcionar, como repl)

assign: "="
!auto_assign: ("+=" | "-=" | "*="  | "/=" | "%=" | "&=" | "|=" | "^=" | "<<=" | ">>=" | "**=" | "//=")

tabledef: "table" NAME "(" table_period ")" ":" table_suite
table_suite: NAME | _NEWLINE _INDENT (table_stmt|_NEWLINE)+ _DEDENT
?table_stmt:  var_sizes ":" NAME
table_period: DECIMAL table_time
!table_time: 	"s"
			|	"m"
			|	"h"

funcdef: var_type NAME "(" params? ")" ":" suite?
vardef: var_type NAME array_ind? ("=" test)? _NEWLINE?

array_ind: "[" (number | atom) "]"

var_type: var_sizes array_ind?

!var_sizes:  	"int"
			|	"float"
			|	"char"
			|	"string"
			|	"void"

params: vardef ("," vardef)*

while_stmt: "while" expr ":" suite
for_stmt: "for" expr "in" for_rep ":" suite
if_stmt: "if" test ":" suite ["else:" suite]

for_rep: "range" "(" number ("," number)? ")"

suite: simple_stmt | _NEWLINE _INDENT stmt+ _DEDENT //suite es lo que va dentro de las cosas

?expression: test

?test: or_test ("if" or_test "else" test)* // test representa todas las cosas que resultan en un valor (por sustitución)
?or_test: and_test ("or" and_test)*
?and_test: not_test ("and" not_test)*
?not_test: "not" not_test -> not | comparison
?comparison: expr (_comp_op expr)*

?expr: xor_expr ("|" xor_expr)* // esto es una concatenación de forma que expr es el primer hijo con el que coincida se convierte en el tipo dominante
?xor_expr: and_expr ("^" and_expr)*
?and_expr: shift_expr ("&" shift_expr)*
?shift_expr: arith_expr (_shift_op arith_expr)*
?arith_expr: term (_add_op term)*
?term: factor (_mul_op factor)*
?factor: _factor_op factor | power
?power: atom_expr ("**" factor)?

!_factor_op: "+" | "-" | "~"
!_add_op: "+" | "-"
!_mul_op: "*" | "/"
!_shift_op: "<<" | ">>"
!_comp_op: "<" | ">" | "==" | ">=" | "<=" | "<>" | "!="


?atom_expr: atom_expr "(" [arguments] ")"      -> funccall //lo que devuelve valores
          | atom_expr "[" DECIMAL "]"  -> getitem
          | atom

arguments: atom ("," atom)*

?atom: NAME array_ind? -> var // representa los literales
     | number | string+
     | "..." -> ellipsis
     | "None"    -> const_none
     | "True"    -> const_true
     | "False"   -> const_false

NAME: /[a-zA-Z_]\w*/
COMMENT: /#[^\n]*/
_NEWLINE: ( /\r?\n[\t ]*/ | COMMENT )+

string: STRING
number: DECIMAL | FLOATING

STRING: /'.*'/

DECIMAL: /0|-?[1-9]\d*/
FLOATING: /-?\d*\.\d*((e|E)\d+)?/

%ignore /[\t \f]+/  // WS
%ignore /\\[\t \f]*\r?\n/   // LINE_CONT
%ignore COMMENT
%declare _INDENT _DEDENT