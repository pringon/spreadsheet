from collections import deque
from copy import deepcopy
from typing import cast, Callable, Literal, Union

from formula import Formula
from formula_parser import FormulaParser
from sheet_primitives import CellKey, CellValue, Col, Row

class Spreadsheet:
    def __init__(self):
        self._cells: list[dict[Col, CellValue]] = []

    def set_cell(self, cell_key: CellKey, cell_value: str) -> None:
        row, col = self._parse_key(cell_key)

        if row >= len(self._cells):
            self._extend_rows(2 * row + 1)


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

    def get_cell(self, cell_key: Union[CellKey]) -> CellValue:
        return self._get_cell(cell_key)

    def sort_rows_by_column(self, col: Col, reverse = False) -> None:
        to_sort = sorted(
            filter(lambda row: col in row, self._cells),
            key=lambda row: row[col],
            reverse=reverse
        )
        no_val = filter(lambda row: col not in row, self._cells)
        self._cells = to_sort + list(no_val)


    def _extend_rows(self, num_rows: int) -> None:
        for _ in range(num_rows - len(self._cells)):
            self._cells.append({})
    
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
            row = int(cell_key[1:]) - 1
        except ValueError:
            raise KeyError("Malformed cell key. Expected second half to be integer row identifier")
        if row < 0:
            raise KeyError("Malformed cell key. Expected row identifier to be greater than 0.")

        return row, col



# TODO: Column filtering
# TODO: Handle ranges and functions (start with SUM over a range)
# TODO: Implement performance profiler
if __name__ == "__main__":
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
    assert s.get_cell("A14") == -int(s.get_cell("A1"))
    s.set_cell("A13", "=-A12")
    assert s.get_cell("A12") == -int(s.get_cell("A13"))
    s.set_cell("A13", "=-(A12+A12)")
    assert 2 * int(s.get_cell("A12")) == -int(s.get_cell("A13"))
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

    new_s = Spreadsheet()
    new_s.set_cell("A1", "3")
    new_s.set_cell("B1", "a")
    new_s.set_cell("A2", "1")
    new_s.set_cell("B2", "b")

    new_s.sort_rows_by_column("A")
    assert new_s.get_cell("A1") == 1
    assert new_s.get_cell("B1") == "b"
    new_s.sort_rows_by_column("B")
    assert new_s.get_cell("A1") == 3
    assert new_s.get_cell("B1") == "a"
    new_s.sort_rows_by_column("B", reverse=True)
    assert new_s.get_cell("A1") == 1
    assert new_s.get_cell("B1") == "b"
