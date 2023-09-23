start:( funcdef | _NEWLINE)+

funcdef: type NAME "(" varlist? ");"

varlist: var ("," var)*
var: type NAME

type: unsign? size pointer?

unsign: "unsigned"
!size: 	"char"
		| "short"
		| "long"
		| "int"
		| "float"
		| "void"

pointer: "[]"

NAME: /[a-zA-Z_]\w*/
PREPROCESSOR: /#[^\n]*/
COMMENT: /\/\/[^\n]*/
_NEWLINE: ( /\r?\n[\t ]*/ | COMMENT )+

number: DECIMAL | FLOATING

STRING: /".*"/

DECIMAL: /0|-?[1-9]\d*/
FLOATING: /-?\d*\.\d*((e|E)\d+)?/

%ignore /[\t \f]+/  // WS
%ignore /\\[\t \f]*\r?\n/   // LINE_CONT
%ignore COMMENT
%ignore PREPROCESSOR