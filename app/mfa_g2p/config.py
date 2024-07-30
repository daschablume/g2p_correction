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
import os
import pathlib


MFA_ROOT_ENVIRONMENT_VARIABLE = "MFA_ROOT_DIR"
NUM_JOBS = 3
QUIET = False
USE_MP = True
DEBUG = False
CLEAN = False
CURRENT_PROFILE_NAME = os.getenv("MFA_PROFILE", "global")


def get_temporary_directory() -> pathlib.Path:
    """
    Get the root temporary directory for MFA

    Returns
    -------
    Path
        Root temporary directory

    Raises
    ------
        :class:`~montreal_forced_aligner.exceptions.RootDirectoryError`
    """
    TEMP_DIR = pathlib.Path(
        os.environ.get(MFA_ROOT_ENVIRONMENT_VARIABLE, "~/Documents/MFA")
    ).expanduser()
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        # caution: used to be RootDirectoryError
        raise KeyError(TEMP_DIR, MFA_ROOT_ENVIRONMENT_VARIABLE)
    return TEMP_DIR


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


def get_temporary_directory() -> pathlib.Path:
    """
    Get the root temporary directory for MFA

    Returns
    -------
    Path
        Root temporary directory

    Raises
    ------
        :class:`~montreal_forced_aligner.exceptions.RootDirectoryError`
    """
    TEMP_DIR = pathlib.Path(
        os.environ.get(MFA_ROOT_ENVIRONMENT_VARIABLE, "~/Documents/MFA")
    ).expanduser()
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        # in original code, this is a RootDirectoryError
        raise NotImplementedError
    return TEMP_DIR

