"""
Author: Hannes Saffrich
"""
from dataclasses import dataclass
from collections.abc import Iterator
from io import StringIO
import csv
from typing import Any


def drop(n: int, xs):
    for x in xs:
        if n > 0:
            n -= 1
        else:
            yield x


def align_r(width: int, s: str) -> str:
    return ' ' * (width - len(s)) + s


def align_l(width: int, s: str) -> str:
    return s + ' ' * (width - len(s))


@dataclass
class Labels:
    rows: bool
    cols: bool

    def transpose(self) -> 'Labels':
        return Labels(rows=self.cols, cols=self.rows)


NoLabels = Labels(rows=False, cols=False)
RowLabels = Labels(rows=True, cols=False)
ColLabels = Labels(rows=False, cols=True)
AllLabels = Labels(rows=True, cols=True)


def map_cells(f, cells):
    return ((f(x) for x in xs) for xs in cells)


def imap_rows(f, rows):
    return ((f(c, r, cell) for c, cell in enumerate(row)) for r, row in enumerate(rows))


def imap_cols(f, cols):
    return ((f(c, r, cell) for r, cell in enumerate(col)) for c, col in enumerate(cols))



str_formatter = lambda col_ix, row_ix, cell: str(cell)


align_left= lambda col_width, col_ix, s: align_l(col_width, s)
align_right = lambda col_width, col_ix, s: align_r(col_width, s)
align_none= lambda col_width, col_ix, s: s


def delimiter_from_path(file_path):
    ext = str(file_path)[-4:]
    if ext == ".csv":
        return ','
    elif ext == ".tsv":
        return '\t'
    else:
        assert False


@dataclass
class Cell:
    val: Any

    def __init__(self, val: Any):
        if type(val) is Cell:
            self.val = val.val
        else:
            self.val = val

    # todo: setter validation for val


@dataclass
class Table:
    _labels: Labels
    _rows: list[list[Cell]]

    def __init__(self, labels: Labels, rows):
        assert rows == [] or type(rows[0]) is list, "Invalid Table init: rows have to be lists of lists."
        self._labels = labels
        self._rows = [[Cell(val) for val in row] for row in rows]

    def num_rows(self) -> int:
        return len(self._rows)

    def num_cols(self) -> int:
        return len(self._rows[0]) if self.num_rows() > 0 else 0

    def size(self):
        return self.num_cols(), self.num_rows()

    def _skip(self, labels: Labels = AllLabels):
        rows = 0
        if not labels.cols and self._labels.cols:
            rows = 1
        cols = 0
        if not labels.rows and self._labels.rows:
            cols = 1
        return cols, rows

    def irows(self, labels: Labels = AllLabels):
        c, r = self._skip(labels)
        return drop(r, ((ri, drop(c, enumerate(row))) for ri, row in enumerate(self._rows)))

    def icols(self, labels: Labels = AllLabels):
        c, r = self._skip(labels)
        return ((i, ((j, row[i + c]) for j, row in drop(r, enumerate(self._rows))))
                for i in range(c, self.num_cols()))

    def rows(self, labels: Labels = AllLabels):
        c, r = self._skip(labels)
        return drop(r, (drop(c, row) for row in self._rows))

    def cols(self, labels: Labels = AllLabels):
        c, r = self._skip(labels)
        return ((row[i + c] for row in drop(r, self._rows))
                for i in range(0, self.num_cols()))

    def col_labels(self):
        if not self._labels.cols:
            assert False
        return self._rows[0]

    def labeled_rows(self):
        ls = self.col_labels()
        for row in self.rows(NoLabels):
            yield {l.val: c for l, c in zip(ls, row)}

    def find_row_by_label(self, label, val):
        for row in self.labeled_rows():
            if row[label].val == val:
                return row

    def col_by_label(self, label: str):
        if not self._labels.cols:
            assert False
        ix = self.col_labels().index(Cell(label))
        return next(drop(ix, self.cols(NoLabels)))

    def add_row(self, row):
        row = [Cell(val) for val in row]
        if len(self._rows) > 0:
            assert len(row) == len(self._rows[0])
        self._rows.append(row)

    def transpose(self) -> 'Table':
        return Table(
            labels=self._labels.transpose(),
            rows=list(list(c) for c in self.cols())
        )

    def col_widths(self,
                   formatter = str_formatter,
                   labels: Labels = AllLabels
                   ):
        return (max(len(formatter(c, r, cell.val)) for r, cell in col) for c, col in self.icols(labels))

    # Writing to String

    def to_str_rows(self,
                    formatter = str_formatter,
                    align = align_left,
                    labels: Labels = AllLabels
                    ):
        col_widths = list(self.col_widths(formatter, labels))
        return ((align(col_width, c, formatter(c, r, cell.val))
                 for col_width, (c, cell) in zip(col_widths, row))
                for r, row in self.irows(labels))

    def to_str_lines(self,
                     col_spacing: int = 2,
                     formatter = str_formatter,
                     align = align_left,
                     labels: Labels = AllLabels
                     ):
        sp = ' ' * col_spacing
        return (sp.join(row) for row in self.to_str_rows(formatter, align, labels))

    def to_str(self,
               col_spacing: int = 2,
               formatter = str_formatter,
               align = align_left,
               labels: Labels = AllLabels
               ) -> str:
        return '\n'.join(self.to_str_lines(col_spacing, formatter, align, labels))

    def __str__(self) -> str:
        return self.to_str()

    # Reading from CSV
    @staticmethod
    def from_csv_fd(labels: Labels, fd, delimiter: str = ',', quotechar: str = '"') -> 'Table':
        reader = csv.reader(fd, delimiter=delimiter, quotechar=quotechar)
        rows = [[val for val in row] for row in reader]
        return Table(labels, rows)

    @staticmethod
    def from_csv_file(labels: Labels, file_path: str) -> 'Table':
        with open(file_path) as fd:
            return Table.from_csv_fd(labels, fd, delimiter=delimiter_from_path(file_path), quotechar='"')

    @staticmethod
    def from_csv_str(labels: Labels, s: str, delimiter: str = ',', quotechar: str = '"') -> 'Table':
        return Table.from_csv_fd(labels, StringIO(s), delimiter, quotechar)

    @staticmethod
    def from_csv_lines(labels: Labels, lines, delimiter: str = ',', quotechar: str = '"') -> 'Table':
        return Table.from_csv_str(labels, '\n'.join(lines), delimiter, quotechar)

    # Writing to CSV

    def to_csv_fd(self,
                  fd,
                  formatter = str_formatter,
                  labels = AllLabels,
                  delimiter: str = ',',
                  quotechar: str = '"'
                  ):
        w = csv.writer(fd,
                       delimiter=delimiter,
                       quotechar=quotechar,
                       quoting=csv.QUOTE_MINIMAL)
        for row in self.to_str_rows(formatter=formatter,
                                    align=align_none,
                                    labels=labels):
            w.writerow(row)

    def to_csv_str(self,
                   formatter = str_formatter,
                   labels: Labels = AllLabels,
                   delimiter: str = ',',
                   quotechar: str = '"'
                   ) -> str:
        s = StringIO()
        self.to_csv_fd(s, formatter, labels, delimiter, quotechar)
        return s.getvalue()

    def to_csv_file(self,
                    path: str,
                    formatter = str_formatter,
                    labels: Labels = AllLabels,
                    delimiter: str = ',',
                    quotechar: str = '"'
                    ):
        with open(path, 'w', newline='') as csvfile:
            self.to_csv_fd(csvfile, formatter, labels, delimiter, quotechar)

    # Writing to Github Markdown
    # TODO Github Markdown has alignment annotations
    def to_markdown_lines(self,
                          formatter = str_formatter,
                          align = align_left,
                          labels: Labels = AllLabels
                          ):
        align2 = lambda col_width, col_ix, s: align(max(col_width, 3), col_ix, s)
        rows = self.to_str_rows(formatter, align2, labels)
        col_widths = self.col_widths(formatter, labels)
        if labels.cols and self._labels.cols:
            for row in rows:
                yield '| ' + ' | '.join(row) + ' |'
                break
            yield '| ' + ' | '.join('-' * max(w, 3) for w in col_widths) + ' |'

        for row in rows:
            yield '| ' + ' | '.join(row) + ' |'

    def to_markdown_str(self,
                        formatter = str_formatter,
                        align = align_left,
                        labels: Labels = AllLabels
                        ):
        return '\n'.join(self.to_markdown_lines(formatter, align, labels))

    def to_markdown_file(self,
                         path: str,
                         formatter = str_formatter,
                         align = align_left,
                         labels: Labels = AllLabels
                         ):
        with open(path, 'w', newline='') as f:
            for line in self.to_markdown_lines(formatter, align, labels):
                f.write(line + "\n")

# t = Table(AllLabels, [
#     [ "",  "Name", "Points" ],
#     [ "1", "Foo",  12 ],
#     [ "2", "Bar",  15 ],
#     [ "3", "Baz",  73 ],
# ])

# print("–– Rows –––––––––––––––––––––––––––––––––")
# for r in t.rows():
#     print(list(r))

# print("–– Cols –––––––––––––––––––––––––––––––––")
# for c in t.cols():
#     print(list(c))

# print("–– Rows –––––––––––––––––––––––––––––––––")
# for r in t.transpose().rows():
#     print(list(r))

# print("–– String Conversion ––––––––––––––––––––")
# print(t)

# # print("–– CSV Files ––––––––––––––––––––––––––––")
# # t = Table.from_csv_file(NoLabels, "tutors.tsv")
# # print(t)
# # t.to_csv_file("tutors_out.csv")

# print("–– CSV Strings ––––––––––––––––––––––––––")
# t = Table.from_csv_lines(ColLabels, [
#     ",Name,Points",
#     "1,Foo,12",
#     "2,Bar,15",
#     "3,Baz,73",
# ])
# print(t)
# print(t.to_csv_str())

# print("–– Markdown Strings –––––––––––––––––––––")
# print(t.to_markdown_str())
# # print(t.to_markdown_file("table.md"))
