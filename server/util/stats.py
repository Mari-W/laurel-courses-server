"""
Author: Hannes Saffrich
"""

# Example:
#
#   >>> from stats import StatsTable
#   >>> st = StatsTable()
#   >>> st.add_row("Item 1", range(0,  10))
#   >>> st.add_row("Item 2", range(10, 20))
#   >>> print(st)
#   ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
#   Name    Minimum  Quartile 1  Median  Quartile 3  Maximum  Average  Mean Deriv  Variance  Samples
#   ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
#   Item 1     0.00        2.00    5.00        7.00     9.00     4.50        8.25      2.50       10
#   Item 2    10.00       12.00   15.00       17.00    19.00    14.50        8.25      2.50       10
#   ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
#   Total      0.00        5.00   10.00       15.00    19.00     9.50       33.25      5.00       20
#   ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

from dataclasses import dataclass, field
from typing import Optional
from table import Table, ColLabels, align_right, align_left


@dataclass
class Stats:
    minimum: float
    quartile1: float
    median: float
    quartile3: float
    maximum: float
    average: float
    mean_abs_deriv: float
    variance: float
    samples: int

    @staticmethod
    def from_iter(it) -> 'Stats':
        data = list(sorted(map(float, it)))
        avg = sum(data) / len(data)
        return Stats(
            minimum=data[0],
            quartile1=data[(len(data) * 1) // 4],
            median=data[(len(data) * 2) // 4],
            quartile3=data[(len(data) * 3) // 4],
            maximum=data[len(data) - 1],
            average=avg,
            variance=sum(map(lambda x: (x - avg) ** 2, data)) / len(data),
            mean_abs_deriv=sum(map(lambda x: abs(x - avg), data)) / len(data),
            samples=len(data)
        )

    @staticmethod
    def labels() -> list[str]:
        return [
            "Minimum",
            "Quartile 1",
            "Median",
            "Quartile 3",
            "Maximum",
            "Average",
            "Mean Deriv",
            "Variance",
            "Samples",
        ]

    def fields(self) -> list[float]:
        return [
            self.minimum,
            self.quartile1,
            self.median,
            self.quartile3,
            self.maximum,
            self.average,
            self.mean_abs_deriv,
            self.variance,
            self.samples,
        ]


@dataclass
class StatsTable:
    stats: list[(str, Stats)] = field(default_factory=list)
    key_heading: str = "Name"
    has_total_row: bool = True
    total_row: list[float] = field(default_factory=list)

    def add_row(self, name: str, it: list[float]):
        if self.has_total_row:
            start_ix = len(self.total_row)
            for x in it:
                self.total_row.append(x)
            it = self.total_row[start_ix:]

        self.stats.append((name, Stats.from_iter(it)))
        return self

    def total_stats(self) -> Optional[Stats]:
        if self.has_total_row:
            return Stats.from_iter(self.total_row)

    def to_table(self) -> Table:
        t = Table(ColLabels, [[self.key_heading] + Stats.labels()])
        t.def_formatter = StatsTable.formatter()
        t.def_align = StatsTable.align()
        stats = self.stats
        stats.sort(key=lambda t: t[0])
        for name, stat in stats:
            t.add_row([name] + stat.fields())
        if self.has_total_row:
            total = self.total_stats()
            t.add_row(["Total"] + total.fields())
        return t

    @staticmethod
    def align():
        return lambda col_width, col_ix, s: \
            (align_left if col_ix == 0 else align_right)(col_width, col_ix, s)

    @staticmethod
    def formatter(round_to: int = 2):
        def round_to_str(x: float, round_to: int = round_to) -> str:
            return ('{:.' + str(round_to) + 'f}').format(x)

        return lambda col_ix, row_ix, cell: \
            str(round_to_str(cell, 2)) if type(cell) == float else str(cell)

    def show(self, round_to: int = 2, show_hlines: bool = True) -> str:
        lines = self.to_table().to_str_lines(
            align=StatsTable.align(),
            formatter=StatsTable.formatter(round_to),
        )
        if show_hlines:
            lines = list(lines)
            table_width = max(len(l) for l in lines)
            bar = table_width * '–'
            lines = lines[0:1] + [bar] + lines[1:]
            if self.has_total_row:
                lines = lines[:-1] + [bar] + lines[-1:]
        return '\n'.join(lines)

    def __str__(self) -> str:
        return self.show()
