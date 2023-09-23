#!/usr/bin/python3.8
from enum import Enum
import lark
from lark import Lark
from lark.indenter import Indenter
import ctypes

import argparse

if_num = 1
for_num = 1
while_num = 1


class SymbolType(Enum):
	UNKNOWN = 0
	CHAR = 1
	INT = 2
	FLOAT = 3
	CHAR_ARR = 4
	INT_ARR = 5
	FLOAT_ARR = 6
	FUNCTION = 7
	VOID = 8
	LABEL = 9


def get_symbol_type_size(sym_type):
	if sym_type == SymbolType.UNKNOWN or sym_type == SymbolType.LABEL:
		raise ValueError('Symbol not defined')
	elif sym_type == SymbolType.CHAR:
		return 1
	elif sym_type == SymbolType.INT or sym_type == SymbolType.FLOAT:
		return 4
	else:
		return 0


class Symbol:
	def __init__(self, sym_type=SymbolType.UNKNOWN, sym_size=0, is_arg=False):
		self.sym_type = sym_type
		if sym_type.value < 4:
			sym_size = 0
		self.sym_size = sym_size
		self.is_arg = is_arg
		self.address = 0

	def get_size(self):
		if self.sym_type.value < 4:
			return get_symbol_type_size(self.sym_type)
		else:
			return self.sym_size

	def get_element_size(self):
		if self.sym_type == 0:
			return get_symbol_type_size(self.sym_type)
		return get_symbol_type_size(SymbolType(self.sym_type.value - 3))

	def get_num_elements(self):
		if self.sym_size == 0:
			return 1
		return self.sym_size // self.get_element_size()

	def __str__(self):
		if self.sym_size == 0:
			return 'Symbol: ' + str(self.sym_type)
		else:
			return 'Symbol: ' + str(self.sym_type) + '[' + str(self.get_num_elements()) + ']'

	def __repr__(self):
		if self.sym_size == 0:
			return 'Symbol: ' + str(self.sym_type)
		else:
			return 'Symbol: ' + str(self.sym_type) + '[' + str(self.get_num_elements()) + ']'

	def __eq__(self, other):
		if isinstance(other, Symbol):
			if (other.sym_type.value > 3 and other.sym_size == 0) or (self.sym_type.value > 3 and self.sym_size):
				return other.sym_type == self.sym_type
			return other.sym_type == self.sym_type and other.sym_size == self.sym_size
		return False


def serialize_string(string:str):
	strbytes = string.encode('utf8')
	if len(strbytes) > 16:
		strbytes = strbytes[0:16]
	elif len(strbytes) < 16:
		strbytes += bytearray(1)
	return strbytes

class TableFormat(Enum):
	Invalid = 0
	Uint8 = 1
	Int8 = 2
	Uint16 = 3
	Int16 = 4
	Uint32 = 5
	Int32 = 6
	Float = 7

class DataColumn:
	def __init__(self):
		self.data_format = TableFormat.Invalid
		self.name = ''


class Table:
	def __init__(self):
		self.name = ''
		self.columns = []
		self.period = 0

	def serialization(self):
		outval = bytearray()
		outval += serialize_string(self.name)
		outval += bytearray([self.period])
		if len(self.columns) > 16:
			self.columns = self.columns[0:16]
		for col in self.columns:
			outval += bytearray([col.data_format.value])
			outval += serialize_string(col.name)
		if len(self.columns) < 16:
			outval += bytearray(1)
		return outval

	def __str__(self):
		ret_string = 'TABLE ' + self.name + '\n'
		ret_string += 'PERIOD ' + str(self.period) + '\n'

		ret_string += 'COLUMNS ' + str(len(self.columns)) + '\n'
		for col in self.columns:
			if col.data_format == TableFormat.Int32:
				ret_string += 'INT'
			elif col.data_format == TableFormat.Float:
				ret_string += 'FLOAT'
			ret_string += ':' + col.name + '\n'
		ret_string += 'ENDTABLE\n'

		return ret_string


class FunctionSignature:
	def __init__(self):
		self.ret_type = None
		self.address = 0
		self.param_types = []
		self.param_order = []

	def __str__(self):
		ret_str = ''
		for idx in range(len(self.param_order)):
			ret_str += str(self.param_order[idx]) + ': ' + str(self.param_types[idx]) + ', '
		return 'Function: [' + ret_str[:-2] + ']-> ' + str(self.ret_type)

	def __repr__(self):
		ret_str = ''
		for idx in range(len(self.param_order)):
			ret_str += str(self.param_order[idx]) + ': ' + str(self.param_types[idx]) + ', '
		return 'Function: [' + ret_str[:-2] + ']-> ' + str(self.ret_type)

	def signature(self):
		ret_val = ''
		for idx, param in enumerate(self.param_order):
			ret_val += '*' + param + ',' + str(self.param_types[idx].get_size()) + '\n'
		return ret_val

	def get_arg_type(self, arg_name):
		for idx, local_arg in enumerate(self.param_order):
			if arg_name == local_arg:
				return self.param_types[idx]
		return None


def symbol_type_from_str(size_name):
	param_type = SymbolType.UNKNOWN
	if size_name == 'FLOAT' or size_name == 'FLOATING':
		param_type = SymbolType.FLOAT
	elif size_name == 'INT' or size_name == 'DECIMAL':
		param_type = SymbolType.INT
	elif size_name == 'LONG':
		param_type = SymbolType.INT
	elif size_name == 'SHORT':
		param_type = SymbolType.INT
	elif size_name == 'CHAR':
		param_type = SymbolType.CHAR
	return param_type


def read_builtin_functions(path=None):
	if path is None:
		return {}
	parser = Lark.open('builtin_funcs.g', parser='lalr')
	builtin_tree = parser.parse(open(path).read())
	func_signatures = {}
	builtin_addr = 0
	for fun_tree in builtin_tree.children:
		if fun_tree.data != 'funcdef':
			raise ValueError('unrecognized entry in ' + path)
		fun_name = fun_tree.children[1].value
		func_signatures[fun_name] = FunctionSignature()
		func_signatures[fun_name].address = builtin_addr + 65536
		builtin_addr += 1
		ret_type = fun_tree.children[0].children[0].children[0].type
		if ret_type == 'VOID':
			func_signatures[fun_name].ret_type = Symbol(SymbolType.VOID)
		elif ret_type == 'INT' or ret_type == 'SHORT' or ret_type == 'LONG':
			func_signatures[fun_name].ret_type = Symbol(SymbolType.INT)
		elif ret_type == 'FLOAT':
			func_signatures[fun_name].ret_type = Symbol(SymbolType.FLOAT)
		elif ret_type == 'CHAR':
			func_signatures[fun_name].ret_type = Symbol(SymbolType.CHAR)
		if len(fun_tree.children) > 2:
			for arg in fun_tree.children[2].children:
				if arg.children[0].data == 'type':
					param_type = symbol_type_from_str(arg.children[0].children[0].children[0].type)
					if len(arg.children[0].children) > 1:
						if arg.children[0].children[1].data == 'pointer':
							param_type = SymbolType(param_type.value+3)

				elif arg.children[1].data == 'size':
					param_type = symbol_type_from_str(arg.children[1].children[0].children[0].type)
				else:
					raise ValueError('error in ' + path)
				func_signatures[fun_name].param_types += [Symbol(param_type, 0, True)]
				func_signatures[fun_name].param_order += [arg.children[1].value]
	return func_signatures


def get_ret_symbol_type(tree_branch):
	var_type = symbol_type_from_str(tree_branch.children[0].children[0].type)
	size = 0
	if len(tree_branch.children) > 1:
		if tree_branch.children[1].data == 'array_ind':
			size = int(tree_branch.children[1].children[0].value)*get_symbol_type_size(var_type)
			var_type = SymbolType(var_type.value + 3)  # upcast to array
	return Symbol(var_type, size)


def build_symbol_table(tree_branch, path):
	symbol_table = {'_global_': {}}
	stack = [('_global_', tree_branch)]
	func_signatures = read_builtin_functions(path)
	for func in func_signatures:
		sym = Symbol()
		sym.sym_type = SymbolType.LABEL
		sym.address = func_signatures[func].address
		symbol_table['_global_'][func] = sym
	tables = []
	m_varAddresses = {'_global_': 0}
	while len(stack) > 0:
		scope, tree_item = stack.pop()

		if tree_item.data == 'vardef':
			var_type = symbol_type_from_str(tree_item.children[0].children[0].children[0].type)
			var_name = tree_item.children[1].value
			sym_size = 0
			if len(tree_item.children) > 2:
				if tree_item.children[2].data == 'array_ind':
					sym_size = int(tree_item.children[2].children[0].children[0].value)*get_symbol_type_size(var_type)
					var_type = SymbolType(var_type.value + 3)
			symbol_table[scope][var_name] = Symbol(var_type, sym_size)
			symbol_table[scope][var_name].address = m_varAddresses[scope]
			m_varAddresses[scope] += sym_size

		elif tree_item.data == 'funcdef':
			ret_value = get_ret_symbol_type(tree_item.children[0])
			func_name = tree_item.children[1].value
			if func_name in func_signatures:
				raise ValueError('Function with name \'' + func_name + '\' redefined')
			func_signatures[func_name] = FunctionSignature()
			func_signatures[func_name].ret_type = ret_value
			symbol_table[func_name] = {}
			m_varAddresses[func_name] = 0
			if len(tree_item.children) > 3:
				for param in tree_item.children[2].children:
					var_type = symbol_type_from_str(param.children[0].children[0].children[0].type)
					var_name = param.children[1].value
					if len(param.children) > 2:
						if param.children[2].data == 'array_ind':
							sym_size = int(param.children[2].children[0].value)*get_symbol_type_size(var_type)
							var_type = SymbolType(var_type.value + 3)
					else:
						sym_size = 0
					func_signatures[func_name].param_types += [Symbol(var_type, sym_size)]
					func_signatures[func_name].param_order += [var_name]
					symbol_table[func_name][var_name] = Symbol(var_type, sym_size, True)
			stack.append((func_name, tree_item.children[-1])) # compile suite (2 or 3)

		elif tree_item.data == 'tabledef':
			table_obj, table_st = compile_table(tree_item)
			tables += [table_obj]
			for element in table_st:
				symbol_table['_global_'][element] = table_st[element]
				symbol_table['_global_'][element].address = m_varAddresses['_global_']
				m_varAddresses['_global_'] += table_st[element].get_size()

		elif len(tree_item.children) > 0:
			for child in tree_item.children[::-1]:
				if type(child) == type(tree_branch):
					stack.append((scope, child))

	return symbol_table, func_signatures, tables


def write_symbol_table(symbol_table, scope):
	ret_val = ''
	for var in symbol_table[scope]:
		var_type = symbol_table[scope][var]
		if var_type.sym_type == SymbolType.LABEL:
			continue
		if var_type.is_arg:
			ret_val += '*'
		else:
			ret_val += '%'
		ret_val += var + ',' + str(var_type.get_size()) + '\n'
	return ret_val


def get_value_type(tree_branch, symbol_table, func_sig, scope):
	var_name = ''
	if tree_branch.data == 'var':
		var_name = tree_branch.children[0].value
		var_type = symbol_table[scope][var_name]
		if len(tree_branch.children) > 1:  # es un array_ind, que habrá que ajustar en compile branch
			if var_type.sym_size == 0:
				raise ValueError(var_name + ' in ' + scope + ' is not an array')
			return Symbol(SymbolType(var_type.sym_type.value-3), 0)
		return var_type  # en este caso no hay acceso

	elif tree_branch.data == 'funccall':
		var_name = tree_branch.children[0].children[0].value
		return func_sig[var_name].ret_type

	elif tree_branch.data == 'arith_expr' or tree_branch.data == 'term':
		factors = (len(tree_branch.children) - 1) // 2
		factor_types = [get_value_type(tree_branch.children[0], symbol_table, func_sig, scope)]
		for i in range(factors):
			factor_types += [get_value_type(tree_branch.children[2 + i * 2], symbol_table, func_sig, scope)]
		return get_dst_value(factor_types)

	elif tree_branch.data == 'comparison':
		return Symbol(SymbolType.CHAR, 0)
	elif tree_branch.data == 'number':
		return Symbol(symbol_type_from_str(tree_branch.children[0].type))

	elif tree_branch.data == 'string':
		str_len = len(tree_branch.children[0].value)-1
		return Symbol(SymbolType.CHAR_ARR, str_len)

	else:
		raise ValueError('Value ' + var_name + ' not declared')


def get_dst_value(type_list):
	type_dst = Symbol(SymbolType.UNKNOWN)
	for type_val in type_list:
		if type_dst.sym_type.value < type_val.sym_type.value:
			type_dst.sym_type = type_val.sym_type
	return type_dst


def cast_values(src_type, dst_type):
	if src_type == dst_type:
		return ''
	elif src_type.sym_type == SymbolType.CHAR:
		if dst_type.sym_type == SymbolType.INT:
			return 'CHAR2INT\n'
		elif dst_type.sym_type == SymbolType.FLOAT:
			return 'CHAR2INT\nINT2FLOAT\n'
		elif dst_type.sym_type == SymbolType.CHAR:
			return ''
		else:
			raise ValueError('Casting not permitted')
	elif src_type.sym_type == SymbolType.INT:
		if dst_type.sym_type == SymbolType.FLOAT:
			return 'INT2FLOAT\n'
		elif dst_type.sym_type == SymbolType.INT:
			return ''
		else:
			raise ValueError('Casting not permitted')
	elif src_type.sym_type == SymbolType.FLOAT:
		if dst_type.sym_type == SymbolType.FLOAT:
			return ''


def compile_table(tree_branch):
	table_obj = Table()
	table_obj.name = tree_branch.children[0].value
	time_value = int(tree_branch.children[1].children[0].value)
	table_st = {}
	if time_value <= 0:
		raise ValueError('Invalid time value')

	time_multiplier = tree_branch.children[1].children[1].children[0].value
	if time_multiplier == 's':
		if time_value > 60:
			raise ValueError('Invalid time value')
	elif time_multiplier == 'm':
		if time_value > 60:
			raise ValueError('Invalid time value')
		time_value += 59
	elif time_multiplier == 'h':
		if time_value > 24:
			raise ValueError('Invalid time value')
		time_value += 118
	else:
		raise ValueError('Error in table definition')

	table_obj.period = time_value

	for entry in tree_branch.children[2].children:
		var_type = entry.children[0].children[0].value.upper()
		var_name = entry.children[1].value

		col = DataColumn()
		col.name = var_name

		if var_type == 'INT':
			table_st[var_name] = Symbol(SymbolType.INT)
			col.data_format = TableFormat.Int32
		elif var_type == 'FLOAT':
			table_st[var_name] = Symbol(SymbolType.FLOAT)
			col.data_format = TableFormat.Float

		table_obj.columns += [col]

	return table_obj, table_st


def compile_branch_var(tree_branch, symbol_table, scope, load=False):
	ret_string = ''
	if tree_branch.data == 'number':
		if tree_branch.children[0].type == 'DECIMAL':
			ret_string += 'LITERAL4 ' + str(tree_branch.children[0].value) + '\n'
		elif tree_branch.children[0].type == 'FLOATING':
			ret_string += 'LITERAL4 ' + str(float(tree_branch.children[0].value)) + '\n'
	elif tree_branch.data == 'var':
		var_name = tree_branch.children[0].value
		var_type = symbol_table[scope][var_name]

		if (var_type.sym_type.value-3) == 1:
			size_ind = '1'
		else:
			size_ind = '4'

		if len(tree_branch.children) > 1:  # it is a sentence like this: var[idx]
			if var_type.sym_type.value < 4:
				raise ValueError(var_name + ' in ' + scope + ' is not an array')

			ret_string += 'LITERAL4 #' + str(var_name) + '\n'

			ret_string += compile_branch_var(tree_branch.children[1], symbol_table, scope, True)
			ret_string += 'LITERAL4 ' + str(var_type.get_element_size()) + '\n'

			ret_string += 'MUL\n'

			if load:
				ret_string += 'LOAD' + str(size_ind) + '\n'
			else:
				ret_string += 'STORE' + str(size_ind) + '\n'

		else:  # it's a sentence like this: var
			if var_type.sym_type.value < 4:  # this is not an array
				ret_string += 'LITERAL' + size_ind + ' #' + var_name + '\n'  # load the address of the variable
				if load:
					ret_string += 'LOAD' + size_ind + '\n'
				else:
					ret_string += 'STORE' + size_ind + '\n'
			else:  # array loading
				if load:
					ret_string += 'LITERAL4 ' + str(var_type.sym_size) + '\n'  # the length of the array should be written
					ret_string += 'LITERAL4 #' + var_name + '\n'  # starting addr of array
					ret_string += 'LOAD' + str(size_ind) + '_ARRAY\n'
				else:
					ret_string += 'LITERAL4 #' + var_name + '\n'
					ret_string += 'STORE' + str(size_ind) + '_ARRAY\n'

	elif tree_branch.data == 'array_ind':
		ret_string += compile_branch_var(tree_branch.children[0], symbol_table, scope, load)

	elif tree_branch.data == 'string':
		ret_string += 'LITERAL1_ARRAY "' + tree_branch.children[0].value[1:-1] + '"\n'

	elif tree_branch.data == 'const_true':
		ret_string += 'LITERAL1 1\n'

	elif tree_branch.data == 'const_false':
		ret_string += 'LITERAL1 0\n'

	elif tree_branch.data == 'vardef':
		pass

	else:
		raise ValueError('Tree branch not recognised')

	return ret_string


def compile_branch(tree_branch, symbol_table, func_sig, scope, load=False):
	global if_num, for_num, while_num

	ret_string = ''

	if tree_branch.data == 'compound_stmt':
		ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope)

	elif tree_branch.data == 'simple_stmt':
		if len(tree_branch.children) == 1:
			ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope)  # llamar funciones, pero sin devolver
			type_branch = get_value_type(tree_branch.children[0], symbol_table, func_sig, scope)
			if type_branch.sym_type == SymbolType.INT or type_branch.sym_type == SymbolType.FLOAT:
				ret_string += 'POP4\n'
			elif type_branch.sym_type == SymbolType.CHAR:
				ret_string += 'POP1\n'
		elif len(tree_branch.children) == 2:
			type_dst = get_value_type(tree_branch.children[0], symbol_table, func_sig, scope)
			type_src = get_value_type(tree_branch.children[1], symbol_table, func_sig, scope)
			if type_dst.sym_type.value < type_src.sym_type.value:
				raise ValueError('Variable downcasting not permitted in variable ' + tree_branch.children[0].children[0].value)
			if tree_branch.children[1].data == 'funccall':
				ret_string += compile_branch(tree_branch.children[1], symbol_table, func_sig, scope)
			else:
				ret_string += compile_branch(tree_branch.children[1], symbol_table, func_sig, scope, True)  # operacion aritmética
			ret_string += cast_values(type_src, type_dst)
			ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope, False)  # this includes save
		else:
			type_dst = get_value_type(tree_branch.children[0], symbol_table, func_sig, scope)
			type_src = get_value_type(tree_branch.children[2], symbol_table, func_sig, scope)
			if tree_branch.children[1].data == 'auto_assign':
				ret_string += compile_branch(tree_branch.children[2], symbol_table, func_sig, scope, True)
				ret_string += cast_values(type_src, type_dst)
				ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope, True)
				aassign_val = tree_branch.children[1].children[0].value
				type_str = ''
				op_str = ''
				if type_dst.sym_type == SymbolType.FLOAT:
					type_str = 'F'
				if aassign_val == '+=':
					op_str = 'ADD'
				elif aassign_val == '-=':
					op_str = 'SUB'
				elif aassign_val == '*=':
					op_str = 'MUL'
				elif aassign_val == '/=':
					op_str = 'DIV'
				elif aassign_val == '%=':
					op_str = 'MOD'
				elif aassign_val == '&=':
					op_str = 'BIT_AND'
				elif aassign_val == '|=':
					op_str = 'BIT_OR'
				if len(op_str) == 0:
					raise ValueError('Auto assign not recognised')
				ret_string += type_str + op_str + '\n'
				ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope, False)  # this includes save

	elif tree_branch.data == 'tabledef':
		pass  # ret_string += compile_table(tree_branch)

	elif tree_branch.data == 'funcdef':
		func_name = tree_branch.children[1].value

		ret_string += 'LITERAL4 @func_end_' + func_name + '\n'
		ret_string += 'JMP\n'
		ret_string += '$' + func_name + '\n'

		ret_string += write_symbol_table(symbol_table, func_name)

		ret_string += compile_branch(tree_branch.children[-1], symbol_table, func_sig, func_name)  # compilar suite
		if tree_branch.children[-1].children[-1].data != 'return_stmt':
			ret_string += 'RETURN\n'
		ret_string += '@func_end_' + func_name + '\n'
		ret_string += '$_global_\n'

	elif tree_branch.data == 'return_stmt':
		ret_type = SymbolType.UNKNOWN
		if len(tree_branch.children) > 0:
			ret_type = get_value_type(tree_branch.children[0], symbol_table, func_sig, scope)
			ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope, True)
		if ret_type.sym_type != func_sig[scope].ret_type.sym_type:
			raise ValueError('Function ' + scope + ' should return value of type ' + str(ret_type))
		ret_string += 'RETURN\n'

	elif tree_branch.data == 'funccall':  # TODO añadir el pasar arrays como variables
		fun_name = tree_branch.children[0].children[0].value
		if fun_name == 'waitNextMeasure':
			ret_string += 'WAIT_TABLE\n'
		elif fun_name == 'delay':
			ret_string += compile_branch_var(tree_branch.children[1].children[0], symbol_table, scope)
			ret_string += 'DELAY\n'
		elif fun_name == 'saveTable':
			ret_string += 'SAVE_TABLE\n'

		elif fun_name not in func_sig:
			raise ValueError('Function ' + fun_name + ' is not defined\n')
		else:
			# los parámetros se ponen en la pila en orden inverso porque pasa de una estructura filo a fifo
			for idx, arg in enumerate(tree_branch.children[1].children[::-1]):
				func_arg_type = func_sig[fun_name].param_types[idx]
				func_call_arg_type = get_value_type(arg, symbol_table, func_sig, scope)
				ret_string += compile_branch_var(arg, symbol_table, scope, True)
				ret_string += cast_values(func_call_arg_type, func_arg_type)
			ret_string += 'LITERAL4 #' + tree_branch.children[0].children[0].value + '\n'
			ret_string += 'CALL\n'

	elif tree_branch.data == 'if_stmt':
		local_ifnum = if_num  # como es una variable global, para evitar cambios en la variable en llamadas a compile_branch
		if_num += 1
		ret_string += 'LITERAL4 @if_stmt_' + str(local_ifnum) + '\n'
		ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope)
		ret_string += 'NOT\n'
		ret_string += 'JMP_IF\n'
		ret_string += compile_branch(tree_branch.children[1], symbol_table, func_sig, scope)
		ret_string += '@if_stmt_' + str(local_ifnum) + '\n\n'

	elif tree_branch.data == 'while_stmt':
		local_whilenum = while_num
		while_num += 1
		ret_string += '@while_comp_' + str(local_whilenum) + '\n'
		ret_string += 'LITERAL4 @while_end_' + str(local_whilenum) + '\n'
		ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope)
		ret_string += 'NOT\nJMP_IF\n'
		ret_string += compile_branch(tree_branch.children[1], symbol_table, func_sig, scope)
		ret_string += 'LITERAL4 @while_comp_' + str(local_whilenum) + '\n'
		ret_string += 'JMP\n'
		ret_string += '@while_end_' + str(local_whilenum) + '\n'

	elif tree_branch.data == 'for_stmt':
		local_for = for_num
		for_num += 1
		if len(tree_branch.children[1].children) == 1:
			ret_string += 'LITERAL4 0\n'
			ret_string += compile_branch_var(tree_branch.children[0], symbol_table, scope)
			ret_string += '@for_start_' + str(local_for) + '\n'
			ret_string += compile_branch(tree_branch.children[2], symbol_table, func_sig, scope)  # compilar la suite
			ret_string += compile_branch_var(tree_branch.children[0], symbol_table, scope, True)
			ret_string += 'INC_S\n'
			ret_string += compile_branch_var(tree_branch.children[0], symbol_table, scope)
			ret_string += 'LITERAL4 @for_start_' + str(local_for) + '\n'  # cargar la dirección de la salida del bloque
			ret_string += compile_branch_var(tree_branch.children[0], symbol_table, scope, True)
			ret_string += 'LITERAL4 ' + str(tree_branch.children[1].children[0].children[0].value) + '\n'
			ret_string += 'LESS\n'  # comparo loop var name con el número del final (se podrá resolver mejor de alguna forma, de momento así)
			ret_string += 'JMP_IF\n'  # compara #loop_var_name y LITERAL4 y salta a @for_start si se cumple

	elif tree_branch.data == 'arith_expr' or tree_branch.data == 'term':
		factors = (len(tree_branch.children) - 1) // 2
		factor_types = [get_value_type(tree_branch.children[0], symbol_table, func_sig, scope)]
		for i in range(factors):
			factor_types += [get_value_type(tree_branch.children[2+i*2], symbol_table, func_sig, scope)]
		type_dst = Symbol(SymbolType.UNKNOWN, 0)
		for type_val in factor_types:
			if type_dst.sym_type.value < type_val.sym_type.value:
				type_dst = type_val

		ret_string += compile_branch(tree_branch.children[0], symbol_table, func_sig, scope, True)
		ret_string += cast_values(factor_types[0], type_dst)
		for i in range(factors):
			ret_string += compile_branch(tree_branch.children[2 + i * 2], symbol_table, func_sig, scope, True)
			ret_string += cast_values(factor_types[i+1], type_dst)
			type_str = ''
			if type_dst.sym_type == SymbolType.FLOAT:
				type_str = 'F'
			if tree_branch.children[1 + i * 2].value == '+':
				op_str = 'ADD'
			elif tree_branch.children[1 + i * 2].value == '-':
				op_str = 'SUB'
			elif tree_branch.children[1+i*2].value == '*':
				op_str = 'MUL'
			elif tree_branch.children[1 + i * 2].value == '/':
				op_str = 'DIV'
			ret_string += type_str + op_str + '\n'

	elif tree_branch.data == 'comparison':
		int_comp_ops = {'==': 'EQUALS', '<': 'LESS', '>': 'GREATER', '!=': 'EQUALS\nNOT'}
		float_comp_ops = {'==': 'FEQUALS', '<': 'FLESS', '>': 'FGREATER', '!=': 'FEQUALS\nNOT'}
		factor_types = [get_value_type(tree_branch.children[0], symbol_table, func_sig, scope), get_value_type(tree_branch.children[2], symbol_table, func_sig, scope)]
		type_dst = get_dst_value(factor_types)
		ret_string += compile_branch_var(tree_branch.children[0], symbol_table, scope, True)
		ret_string += compile_branch(tree_branch.children[2], symbol_table, func_sig, scope)
		comp_op = tree_branch.children[1].value
		if type_dst.sym_type == SymbolType.INT:
			ret_string += int_comp_ops[comp_op] + '\n'
		elif type_dst.sym_type == SymbolType.FLOAT:
			ret_string += float_comp_ops[comp_op] + '\n'
		else:
			raise ValueError('Unrecognized types for comparison')

	elif tree_branch.data == 'vardef':
		pass

	elif tree_branch.data == 'start' or tree_branch.data == 'input' or tree_branch.data == 'suite':
		for tree_child in tree_branch.children:
			ret_string += compile_branch(tree_child, symbol_table, func_sig, scope)
	else:
		ret_string += compile_branch_var(tree_branch, symbol_table, scope, load)
	return ret_string


def compile_value(string_value, scope, symbol_table, elem_size):
	ret_val = bytes()
	if string_value[0] == '#':  # its a variable
		ret_val = bytes(ctypes.c_int32(symbol_table[scope][string_value[1:]].address))
	elif string_value[0] == '@':  # its a label
		ret_val = bytes(ctypes.c_int32(symbol_table['_global_'][string_value[1:]].address))
	elif string_value[0] == "'":  # its a char
		ret_val = bytes([ord(string_value[1])])
	elif string_value.isdigit():
		num_val = int(string_value)
		if num_val > 2**(elem_size*8):
			raise ValueError('Value will overflow: ' + string_value)
		if elem_size == 1:
			ret_val = bytes(ctypes.c_char(num_val))
		elif elem_size == 4:
			ret_val = bytes(ctypes.c_int32(num_val))
	else:
		try:
			if elem_size != 4:
				raise ValueError('WTF bro')
			ret_val = bytes(ctypes.c_float(float(string_value)))
		except ValueError:
			raise ValueError('Not float: ' + string_value)
	remain_size = elem_size - len(ret_val)
	if remain_size < 0:
		raise ValueError('Value won\'t fit in place: ' + string_value)
	else:
		ret_val += bytes(remain_size)
	return ret_val


def get_var_address(assembly):
	base_address = 0
	for line in assembly.split('\n'):
		if line[0] == '$' or line[0] == '%' or line[0] == '*' or line[0] == '@':
			pass
		elif line.startswith('LITERAL4_ARRAY'):
			base_address += 5
			base_address += len(line[15:].split(','))*4
		elif line.startswith('LITERAL1_ARRAY'):
			base_address += 5
			base_address += len(line[15:].split(','))
		elif line.startswith('LITERAL4'):
			base_address += 5
		elif line.startswith('LITERAL1'):
			base_address += 2
		else:
			base_address += 1
	return base_address


def get_opcode(strop):
	opcodes = {
		'LITERAL1': 0,
		'LITERAL4': 1,
		'LITERAL1_ARRAY': 2,
		'LITERAL4_ARRAY': 3,
		'LOAD1': 4,
		'LOAD4': 5,
		'LOAD1_ARRAY': 6,
		'LOAD4_ARRAY': 7,
		'STORE1': 8,
		'STORE4': 9,
		'STORE1_ARRAY': 10,
		'STORE4_ARRAY': 11,
		'LOAD1_LCL': 12,
		'LOAD4_LCL': 13,
		'LOAD1_ARRAY_LCL': 14,
		'LOAD4_ARRAY_LCL': 15,
		'STORE1_LCL': 16,
		'STORE4_LCL': 17,
		'STORE1_ARRAY_LCL': 18,
		'STORE4_ARRAY_LCL': 19,
		'LOAD1_ARG': 20,
		'LOAD4_ARG': 21,
		'LOAD1_ARRAY_ARG': 22,
		'LOAD4_ARRAY_ARG': 23,
		'STORE1_ARG': 24,
		'STORE4_ARG': 25,
		'STORE1_ARRAY_ARG': 26,
		'STORE4_ARRAY_ARG': 27,
		'POP1': 28,
		'POP4': 29,
		'CLONE1': 30,
		'CLONE4': 31,
		'ALLOC': 32,
		'FREE': 33,
		'ADD': 34,
		'SUB': 35,
		'MUL': 36,
		'DIV': 37,
		'MOD': 38,
		'FADD': 39,
		'FSUB': 40,
		'FMUL': 41,
		'FDIV': 42,
		'DEC_S': 43,
		'INC_S': 44,
		'LESS': 45,
		'GREATER': 46,
		'NOT': 47,
		'EQUALS': 48,
		'FLESS': 49,
		'FGREATER': 50,
		'FNOT': 51,
		'FEQUALS': 52,
		'CHAR2INT': 53,
		'INT2FLOAT': 54,
		'FLOAT2INT': 55,
		'INT2CHAR': 56,
		'BIT_AND': 57,
		'BIT_OR': 58,
		'BIT_LS': 59,
		'BIT_RS': 60,
		'JMP': 61,
		'JMP_IF': 62,
		'JMP_SZ': 63,
		'CALL': 64,
		'RETURN': 65,
		'DELAY': 66,
		'WAIT_TABLE': 67,
		'SAVE_TABLE': 68,
		'NOP': 0x7f,
		'BAD': 0xff
	}

	return bytes(ctypes.c_char(opcodes[strop]))


def compile_asm(assembly, symbol_table, function_signatures, tables, stack_size):
	out_bytes = bytearray()
	asm_lines = assembly.split('\n')
	out_bytes += bytearray([len(tables)])
	num_instructions = 0
	scope = '_global_'

	for table in tables:
		out_bytes += table.serialization()
	out_bytes += bytes(ctypes.c_int32(stack_size))

	for line in assembly.split('\n'):
		if len(line) == 0:
			continue
		if line[0] == '@':
			sym = Symbol()
			sym.sym_type = SymbolType.LABEL
			sym.address = num_instructions
			symbol_table['_global_'][line[1:]] = sym
		elif line[0] == '$':
			if line[1:] != '_global_':
				function_signatures[line[1:]].address = num_instructions
				sym = Symbol()
				sym.sym_type = SymbolType.LABEL
				sym.address = num_instructions
				symbol_table['_global_'][line[1:]] = sym
		elif line[0] == '%' or line[0] == '*':  # symbol table built
			pass
		elif line.startswith('LITERAL4_ARRAY'):
			num_instructions += 5
			num_instructions += len(line[15:].split(',')) * 4
		elif line.startswith('LITERAL1_ARRAY'):
			num_instructions += 5
			num_instructions += len(line[15:].split(','))
		elif line.startswith('LITERAL4'):
			num_instructions += 5
		elif line.startswith('LITERAL1'):
			num_instructions += 2
		else:
			num_instructions += 1

	for symbol in symbol_table['_global_']:
		if symbol_table['_global_'][symbol].sym_type == SymbolType.LABEL:
			if symbol_table['_global_'][symbol].address < 65536:
				symbol_table['_global_'][symbol].address += stack_size  # labels are placed inside the program
		else:
			symbol_table['_global_'][symbol].address += stack_size + num_instructions  # global vars are placed after the program

	for line in asm_lines:
		if len(line) == 0:
			continue
		if line[0] == '@' or line[0] == '%' or line[0] == '*':
			pass
		elif line[0] == '$':
			scope = line[1:]
		elif line.startswith('LITERAL4_ARRAY'):
			out_bytes += get_opcode('LITERAL4_ARRAY')  # TODO recalcular los opcodes
			vals = line[15:].split(',')
			out_bytes += bytes(ctypes.c_int32(len(vals)))
			for val in vals:
				out_bytes += compile_value(val, scope, symbol_table, 4)
		elif line.startswith('LITERAL1_ARRAY'):
			out_bytes += get_opcode('LITERAL1_ARRAY')
			vals = line[15:].split(',')
			out_bytes += bytes(ctypes.c_int32(len(vals)))
			for val in vals:
				out_bytes += compile_value(val, scope, symbol_table, 1)
		elif line.startswith('LITERAL4'):
			out_bytes += get_opcode('LITERAL4')
			out_bytes += compile_value(line[9:], scope, symbol_table, 4)
		elif line.startswith('LITERAL1'):
			out_bytes += get_opcode('LITERAL1')
			out_bytes += compile_value(line[9:], scope, symbol_table, 1)
		else:
			out_bytes += get_opcode(line)
	return out_bytes


def culevmpile(tree_branch, builtin_path=None):
	global if_num, for_num, while_num
	if_num = 1
	for_num = 1
	while_num = 1
	symbol_table, function_signatures, tables = build_symbol_table(tree_branch, builtin_path)
	assembly = '$_global_\n' + write_symbol_table(symbol_table, '_global_')
	assembly += compile_branch(tree_branch, symbol_table, function_signatures, '_global_') + 'NOP\n'
	bin_out = compile_asm(assembly, symbol_table, function_signatures, tables, 150)
	#bin_out = ''
	asm_prefix = 'TABLES ' + str(len(tables)) + '\n'
	for table in tables:
		asm_prefix += str(table)
	assembly = asm_prefix + assembly
	return assembly, bin_out


if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Compile FL files to binary')
	parser.add_argument('-i', '--input', help='Input file')
	parser.add_argument('-o', '--output', help='Output file')
	parser.add_argument('-s', '--assembly', help='Outputs assembly language instead of the binary file', action='store_true')
	parser.add_argument('-d', '--debug', help='Outputs debug in stdout', action='store_true')

	args = parser.parse_args()

	if args.input is None or (args.output is None and (not args.debug)):
		print('Error, input and output should be submitted')

	class PythonIndenter(Indenter):
		NL_type = '_NEWLINE'
		OPEN_PAREN_types = ['LPAR', 'LSQB', 'LBRACE']
		CLOSE_PAREN_types = ['RPAR', 'RSQB', 'RBRACE']
		INDENT_type = '_INDENT'
		DEDENT_type = '_DEDENT'
		tab_len = 8


	p = Lark.open('grammar.g', parser='lalr', postlex=PythonIndenter(), propagate_positions=True)

	text = open(args.input).read()
	try:
		tree = p.parse(text)
	except lark.UnexpectedToken as ut:
		print('[UT]Error on line: ' + str(ut.line))
		exit(1)
	except lark.UnexpectedCharacters as uc:
		print('[UC]Error on line: ' + str(uc.line))
		exit(1)
	except lark.UnexpectedInput as ui:
		print('[UI]Error on line: ' + str(ui.line))
		exit(1)

	asm, binary = culevmpile(tree, 'Compiler_VMBuiltin.h')

	if args.debug:
		print(asm)
	else:
		if args.assembly:
			open(args.output, 'w').write(asm)
		else:
			open(args.output, 'wb').write(binary)

