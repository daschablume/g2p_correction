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

