from collections import deque
from copy import deepcopy
from typing import cast, Callable, Literal, Union


Row = int
Col = str
CellKey = str
CellValue = Union[str, int, float, "Formula"]
Numeric = Union[int, float]
DIGITS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
OPERATIONS = ("+", "-", "*", "/")


CellGetter = Callable[[Union[CellKey]], CellValue]
class Spreadsheet:
    def __init__(self):
        self._cells: dict[Row, dict[Col, CellValue]] = {}

    def set_cell(self, cell_key: CellKey, cell_value: str) -> None:
        row, col = self._parse_key(cell_key)

        if row not in self._cells:
            self._cells[row] = {}


        stripped_val = cell_value.strip()

        if self._set_int(row, col, stripped_val):
            return
        elif self._set_float(row, col, stripped_val):
            return
        elif len(cell_value) > 0 and stripped_val[0] == "=":
            parser = FormulaParser()
            self._cells[row][col] = parser.parse_formula(self.get_cell, stripped_val)
        else:
            self._cells[row][col] = cell_value

    
    def _set_int(self, row: Row, col: Col, val: str) -> bool:
        try:
            self._cells[row][col] = int(val)
            return True
        except ValueError:
            return False

    def _set_float(self, row: Row, col: Col, val: str) -> bool:
        try:
            self._cells[row][col] = float(val)
            return True
        except ValueError:
            return False

    def get_cell(self, cell_key: Union[CellKey]) -> CellValue:
        return self._get_cell(cell_key)

    def _get_cell(self, cell_key: CellKey) -> CellValue:
        row, col = self._parse_key(cell_key)
        value = self._cells[row][col]

        if isinstance(value, int) or isinstance(value, float) or isinstance(value, str):
            return value

        if isinstance(value, Formula):
            return value.compute()
        
        raise ValueError(f"Unexpected cell contents: {str(value)}")

    def _parse_key(self, cell_key: CellKey) -> tuple[int, str]:
        if len(cell_key) < 2:
            raise KeyError("Malformed cell key.")

        col = cell_key[0]
        ord_col = ord(col)
        if ord("A") > ord_col or ord("Z") < ord_col:
            raise KeyError("Malformed cell key. Expected first half to be a character between A and Z.")

        try:
            row = int(cell_key[1:])
        except ValueError:
            raise KeyError("Malformed cell key. Expected second half to be integer row identifier")

        return row, col


Operand = Union["Formula", CellKey]
Operation = Literal["+", "-", "*", "/"]
# XXX: Is it possible to refactor expressions to be just another formula?
# One possibility might involve removing the tuples and sub-classing the formula
Expression = Union[Operand, tuple[Literal["="], "Expression"], tuple[Operation, "Expression", "Expression"]]
class Formula:
    def __init__(self, get_cell: CellGetter, expression: Expression, negated = False):
        self._get_cell = get_cell
        self._expression = expression
        self._negated = negated

    def compute(self) -> CellValue:
        val = self._compute_expression(self._expression)
        if self._negated:
            if isinstance(val, str):
                raise ValueError("Cannot negate a string.")
            val = -val
        return val
    
    def _compute_expression(self, expression: Expression) -> CellValue:
        if isinstance(expression, int) or isinstance(expression, float):
            return expression

        if isinstance(expression, CellKey):
            return self._get_cell(expression)

        if isinstance(expression, Formula):
            return expression.compute()

        if expression[0] == "=":
            return self._compute_expression(expression[1])
        
        left_hand = self._compute_expression(expression[1])
        right_hand = self._compute_expression(expression[2])

        if isinstance(left_hand, str) and isinstance(right_hand, str):
            if expression[0] == "+":
                return left_hand + right_hand

        if any([
            isinstance(left_hand, type1) and isinstance(right_hand, type2)
            for type1, type2 in [(int, int), (float, float), (int, float), (float, int)]
        ]):
            if expression[0] == "*":
                return left_hand * right_hand
            elif expression[0] == "/":
                return left_hand / right_hand
            elif expression[0] == "+":
                return left_hand + right_hand
            elif expression[0] == "-":
                return left_hand - right_hand

        raise ValueError(f"Unexpected operation '{expression[0]}' on operands '{left_hand}' and '{right_hand}'")


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
                i, sub_expression = self._parse_sub_expression(
                    i,
                    formula,
                    get_cell=get_cell,
                    negated=negate_value
                )
                symbols.append(sub_expression)
                negate_value = False
            elif c in OPERATIONS:
                if formula[i - 1] in ("=", *OPERATIONS) and not negate_value:
                    negate_value = True
                else:
                    symbols.append(cast(Operation, c))
            elif c == " ":
                pass
            else:
                parsed = False
                if not parsed:
                    try:
                        i, cell_key = self._parse_cell_key(i, formula)
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
                        i, numeric_literal = self._parse_numeric(i, formula)
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
    
    def _parse_sub_expression(self, index: int, formula: str, get_cell: CellGetter, negated: bool) -> tuple[int, "Formula"]:
        j = index + 1
        while formula[j] != ")":
            j += 1
        sub_expression = self.parse_formula(
            get_cell=get_cell,
            formula=f"={formula[index+1:j]}",
            negated=negated
        )
        return j, sub_expression

    # XXX: Think about simplifying this 
    def _parse_cell_key(self, index: int, formula: str) -> tuple[int, str]:
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
        if index != len(formula) and formula[index] not in (")", *OPERATIONS, " "):
            raise ValueError(f"Malformed cell key. Unexpecteded token: {formula[index]}")
        return index - 1, "".join(cell_key)

    def _parse_numeric(self, index: int, formula: str) -> tuple[int, Numeric]:
        numeric = []

        while index < len(formula) and formula[index] in DIGITS:
            numeric.append(formula[index])
            index += 1
        if index == len(formula) or formula[index] in (")", *OPERATIONS, " "):
            return index - 1, int("".join(numeric))

        if formula[index] != ".":
            raise ValueError(f"Malformed numeric. Unexpecteded token: {formula[index]}")
        numeric.append(".")
        index += 1

        while index < len(formula) and formula[index] in DIGITS:
            numeric.append(formula[index])
            index += 1
        if index != len(formula) and formula[index] not in (")", *OPERATIONS, " "):
            raise ValueError(f"Malformed numeric. Unexpecteded token: {formula[index]}")
        return index - 1, float("".join(numeric))
    
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



# TODO: Handle ranges and functions (start with SUM over a range)
s = Spreadsheet()
s.set_cell("A1", "3")
s.set_cell("A2", "2")
s.set_cell("A3", "a")
s.set_cell("A4", "=A1+A2")
s.set_cell("A5", "=A1+A3")
s.set_cell("A6", "=A3+A3")
s.set_cell("A7", "=A6+A3")
s.set_cell("A8", "=A1-A2")
s.set_cell("A9", "=A1*A2")
s.set_cell("A10", "=A1/A1")
s.set_cell("A11", "=A1+A2*A2")
s.set_cell("A12", "=(A1+A2)*A2")
assert s.get_cell("A1") == 3
assert s.get_cell("A4") == 5
assert s.get_cell("A6") == "aa"
assert s.get_cell("A7") == "aaa"
assert s.get_cell("A8") == 1
assert s.get_cell("A9") == 6
assert s.get_cell("A10") == 1
assert s.get_cell("A11") == 7
assert s.get_cell("A12") == 10

s.set_cell("A14", "=-A1")
assert s.get_cell("A14") == -cast(int, s.get_cell("A1"))
s.set_cell("A13", "=-A12")
assert s.get_cell("A12") == -cast(int, s.get_cell("A13"))
s.set_cell("A13", "=-(A12+A12)")
assert 2 * cast(int, s.get_cell("A12")) == -cast(int, s.get_cell("A13"))
s.set_cell("A13", "=-A12+A12")
assert s.get_cell("A13") == 0
s.set_cell("A13", "=-(A12)+A12")
assert s.get_cell("A13") == 0
s.set_cell("A12", "a")
s.set_cell("A13", "=-A12")
value_error = False
try:
    s.get_cell("A13")
except ValueError:
    value_error = True
assert value_error

value_error = False
try:
    s.get_cell("A5")
except ValueError:
    value_error = True
assert value_error

key_error = False
try:
    s.set_cell("b3", "3")
except KeyError:
    key_error = True
assert key_error

key_error = False
try:
    s.set_cell("23", "3")
except KeyError:
    key_error = True
assert key_error

s.set_cell("A1", " a")
assert s.get_cell("A1") == " a"
s.set_cell("A1", " 2")
assert s.get_cell("A1") == 2
s.set_cell("A2", " =A1")
assert s.get_cell("A2") == 2
s.set_cell("A2", "= A1")
assert s.get_cell("A2") == 2
s.set_cell("A2", " =A1 +A1")
assert s.get_cell("A2") == 4
s.set_cell("A2", "=A1 + A1")
assert s.get_cell("A2") == 4

s.set_cell("A1", "3.4")
assert s.get_cell("A1") == 3.4
s.set_cell("A2", "2.3")
s.set_cell("A3", "=A1+A2")
assert s.get_cell("A3") == 3.4 + 2.3

s.set_cell("A3", "=A1+2")
assert s.get_cell("A3") == 3.4 + 2
s.set_cell("A3", "=A1+2.3")
assert s.get_cell("A3") == 3.4 + 2.3
