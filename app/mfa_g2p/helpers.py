# all code is from montreal forced aligner.
# link: https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner/tree/main/
# Copyright (c) 2016 Montreal Corpus Tools
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from contextlib import contextmanager
import dataclassy
import itertools
import json
from pathlib import Path
from typing import Any, Union
import yaml

import numpy


# copied from montreal_forced_aligner/helpers.py
@contextmanager
def mfa_open(path, mode="r", encoding="utf8", newline=""):
    if "r" in mode:
        if "b" in mode:
            file = open(path, mode)
        else:
            file = open(path, mode, encoding=encoding)
    else:
        if "b" in mode:
            file = open(path, mode)
        else:
            file = open(path, mode, encoding=encoding, newline=newline)
    try:
        yield file
    finally:
        file.close()


class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON serialization"""

    def default(self, o: Any) -> Any:
        """Get the dictionary of a dataclass"""
        if dataclassy.functions.is_dataclass_instance(o):
            return dataclassy.asdict(o)
        if isinstance(o, set):
            return list(o)
        return dataclassy.asdict(o)


# copied from montreal_forced_aligner/helper.py
def score_g2p(gold: list[str], hypo: list[str]) -> tuple[int, int]:
    """
    Computes sufficient statistics for LER calculation.

    Parameters
    ----------
    gold: WordData
        The reference labels
    hypo: WordData
        The hypothesized labels

    Returns
    -------
    int
        Edit distance
    int
        Length of the gold labels
    """
    for h in hypo:
        if h in gold:
            return 0, len(h)
    edits = 100000
    best_length = 100000
    for (g, h) in itertools.product(gold, hypo):
        e = edit_distance(g.split(), h.split())
        if e < edits:
            edits = e
            best_length = len(g)
        if not edits:
            best_length = len(g)
            break
    return edits, best_length


# copied from montreal_forced_aligner/helper.py
def edit_distance(x: list[str], y: list[str]) -> int:
    """
    Compute edit distance between two sets of labels

    See Also
    --------
    `https://gist.github.com/kylebgorman/8034009 <https://gist.github.com/kylebgorman/8034009>`_
         For a more expressive version of this function

    Parameters
    ----------
    x: list[str]
        First sequence to compare
    y: list[str]
        Second sequence to compare

    Returns
    -------
    int
        Edit distance
    """
    idim = len(x) + 1
    jdim = len(y) + 1
    table = numpy.zeros((idim, jdim), dtype=numpy.uint8)
    table[1:, 0] = 1
    table[0, 1:] = 1
    for i in range(1, idim):
        for j in range(1, jdim):
            if x[i - 1] == y[j - 1]:
                table[i][j] = table[i - 1][j - 1]
            else:
                c1 = table[i - 1][j]
                c2 = table[i][j - 1]
                c3 = table[i - 1][j - 1]
                table[i][j] = min(c1, c2, c3) + 1
    return int(table[-1][-1])


def load_configuration(config_path: Union[str, Path]) -> dict[str, Any]:
    """
    Load a configuration file

    Parameters
    ----------
    config_path: :class:`~pathlib.Path`
        Path to yaml or json configuration file

    Returns
    -------
    dict[str, Any]
        Configuration dictionary
    """
    data = {}
    if not isinstance(config_path, Path):
        config_path = Path(config_path)
    with mfa_open(config_path, "r") as f:
        if config_path.suffix == ".yaml":
            data = yaml.load(f, Loader=yaml.Loader)
        elif config_path.suffix == ".json":
            data = json.load(f)
    if not data:
        return {}
    return data
