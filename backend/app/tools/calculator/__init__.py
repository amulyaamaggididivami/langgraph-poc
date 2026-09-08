"""Calculation Agent's tool set (TASK-ORCHESTRATION-006) — one function
per file, assembled into TOOLS here for build_calc_agent() to register
with deepagents.create_deep_agent().

BRD §Scope also names "group-based aggregation" and "derived metrics"
as in-scope aggregation types. Neither is a single well-shaped
function — "group-based aggregation" implies a grouping key the Query
Tool's predefined queries would need to supply, and "derived metrics"
is undefined beyond that label. Both need PTL clarification before they
get a tool file here.
"""

from app.tools.calculator.average import average
from app.tools.calculator.count import count_values
from app.tools.calculator.maximum import maximum
from app.tools.calculator.minimum import minimum
from app.tools.calculator.percentage import percentage
from app.tools.calculator.percentage_change import percentage_change
from app.tools.calculator.ratio import ratio
from app.tools.calculator.sum import sum_values

TOOLS = [sum_values, average, minimum, maximum, count_values, percentage, percentage_change, ratio]

__all__ = [
    "TOOLS",
    "sum_values",
    "average",
    "minimum",
    "maximum",
    "count_values",
    "percentage",
    "percentage_change",
    "ratio",
]
