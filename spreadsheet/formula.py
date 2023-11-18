from typing import Literal, Union

from sheet_primitives import CellGetter, CellKey, CellValue

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
