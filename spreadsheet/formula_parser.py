from collections import deque
from copy import deepcopy
from typing import Union, cast

from formula import Expression, Formula, Operand, Operation
from sheet_primitives import CellGetter, Numeric, DIGITS, ARITHMETIC_OPERATIONS

Symbol = Union[Operand, Operation]
Grammar = Union[Expression, Symbol]
class FormulaParser:
    def parse_formula(self, get_cell: CellGetter, formula: str, negated = False) -> Formula:
        if len(formula) <= 0 or formula[0] != "=":
            raise ValueError("Formula must be non-empty and start with a = sign")
        symbols = deque[Symbol]()
        i = 1
        negate_value = False
        while i < len(formula):
            c = formula[i]
            if c == "(":
                sub_expression, i = self._parse_sub_expression(
                    formula,
                    i,
                    get_cell=get_cell,
                    negated=negate_value
                )
                symbols.append(sub_expression)
                negate_value = False
            elif c in ARITHMETIC_OPERATIONS:
                if formula[i - 1] in ("=", *ARITHMETIC_OPERATIONS) and not negate_value:
                    negate_value = True
                else:
                    symbols.append(cast(Operation, c))
            elif c == " ":
                pass
            else:
                parsed = False
                if not parsed:
                    try:
                        cell_key, i = self._parse_cell_key(formula, i)
                        symbols.append(Formula(
                            get_cell=get_cell,
                            expression=("=", cell_key),
                            negated=negate_value
                        ))
                        parsed = True
                    except ValueError:
                        pass
                if not parsed:
                    try:
                        numeric_literal, i = self._parse_numeric(formula, i)
                        symbols.append(-numeric_literal if negate_value else numeric_literal)
                        parsed = True
                    except ValueError:
                        pass
                negate_value = False
                if not parsed:
                    raise ValueError(f"Unexpected token in formula: {c}")
            i += 1

        return Formula(
            get_cell=get_cell,
            expression=self._operands_to_expression(symbols),
            negated=negated,
        )
    
    def _parse_sub_expression(self, formula: str, index: int, get_cell: CellGetter, negated: bool) -> tuple["Formula", int]:
        j = index + 1
        while formula[j] != ")":
            j += 1
        sub_expression = self.parse_formula(
            get_cell=get_cell,
            formula=f"={formula[index+1:j]}",
            negated=negated
        )
        return sub_expression, j

    # XXX: Think about simplifying this 
    def _parse_cell_key(self, formula: str, index: int) -> tuple[str, int]:
        cell_key = []
        while index < len(formula) and ord("A") <= ord(formula[index]) <= ord("Z"):
            cell_key.append(formula[index])
            index +=1
        if len(cell_key) <= 0:
            raise ValueError(f"Malformed cell key. Expected at least one character between A and Z. Got: {formula[index]}")
        len_col = len(cell_key)
        while index < len(formula) and formula[index] in DIGITS:
            cell_key.append(formula[index])
            index += 1
        if len(cell_key) == len_col:
            raise ValueError(f"Malformed cell key. Expected at least one digit. Got: {formula[index]}")
        if index != len(formula) and formula[index] not in (")", *ARITHMETIC_OPERATIONS, " "):
            raise ValueError(f"Malformed cell key. Unexpecteded token: {formula[index]}")
        return "".join(cell_key), index - 1

    def _parse_numeric(self, formula: str, index: int) -> tuple[Numeric, int]:
        numeric = []
        while index < len(formula) and formula[index] in DIGITS:
            numeric.append(formula[index])
            index += 1
        if index == len(formula) or formula[index] in (")", *ARITHMETIC_OPERATIONS, " "):
            return int("".join(numeric)), index - 1

        if formula[index] != ".":
            raise ValueError(f"Malformed numeric. Unexpecteded token: {formula[index]}")
        numeric.append(".")
        index += 1

        while index < len(formula) and formula[index] in DIGITS:
            numeric.append(formula[index])
            index += 1
        if index != len(formula) and formula[index] not in (")", *ARITHMETIC_OPERATIONS, " "):
            raise ValueError(f"Malformed numeric. Unexpecteded token: {formula[index]}")
        return float("".join(numeric)), index - 1
 
    def _operands_to_expression(self, symbols: deque[Symbol]) -> Expression:
        try:
            grammar_objects = deepcopy(
                cast(deque[Grammar], symbols) # Casting because a deque is invariant in its parameter
            )
            expression = self._split_by_operations(
                self._split_by_operations(
                    grammar_objects,
                    set(["*", "/"])
                ),
                set(["+", "-"])
            )
        except ValueError as e:
            raise ValueError(", ".join(map(lambda x: str(x), symbols))) from e
        if len(expression) != 1 or expression[0] in ("+", "-", "*", "/"):
            raise ValueError(f"Malformed expression: {expression}")
        # TODO: Simplify grammar/expression typing. Debt is starting to accumulate quickly.
        return cast(Expression, expression[0])
 
    # TODO: Test this method
    def _split_by_operations(self, symbols: deque[Grammar], operations: set[Operation]) -> deque[Grammar]:
        split_exp = deque[Grammar]()
        while symbols:
            symbol = symbols.pop()
            if symbol in operations:
                symbol = cast(Operation, symbol) # XXX: Why does vscode correctly identify this type as Operation but mypy does not?
                try:
                    left_operand = split_exp.pop()
                    right_operand = symbols.pop()
                except IndexError:
                    raise ValueError("Malformed expression.")
                ops = ("+", "-", "*", "/")
                if left_operand in ops or right_operand in ops:
                    raise ValueError("Operands cannot be operations")
                # XXX: Why did typing break here?
                split_exp.append((symbol, cast(Expression, left_operand), cast(Expression, right_operand)))
            else:
                split_exp.append(symbol)
        return split_exp
