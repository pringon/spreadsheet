from typing import Callable, Union

Row = int
Col = str
CellKey = str
CellValue = Union[str, int, float, "Formula"]
CellGetter = Callable[[Union[CellKey]], CellValue]
Numeric = Union[int, float]
DIGITS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
ARITHMETIC_OPERATIONS = ("+", "-", "*", "/")
