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

from __future__ import annotations

import abc
import csv
import functools
import itertools
import multiprocessing as mp
import os
import shutil
import queue
import statistics
import time
import typing
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Optional, Any, Type, Union, get_type_hints
import yaml

import pynini
import pywrapfst
from pynini.lib import rewrite
from tqdm.rich import tqdm

from .config import (
    NUM_JOBS, QUIET, USE_MP, DEBUG, CLEAN,
    get_temporary_directory, NUM_JOBS,
    CURRENT_PROFILE_NAME
)
from .helpers import mfa_open, score_g2p, load_configuration
from .mixins import G2PTopLevelMixin
from .models import G2PModel


Metadict = dict[str, Any]
TEMPORARY_DIRECTORY = get_temporary_directory()
# Caution: logger has been deleted

def optimal_rewrites(
    string: pynini.FstLike,
    rule: pynini.Fst,
    input_token_type: Optional[pynini.TokenType] = None,
    output_token_type: Optional[pynini.TokenType] = None,
    threshold: float = 1,
) -> list[str]:
    """Returns all optimal rewrites.
    Args:
    string: Input string or FST.
    rule: Input rule WFST.
    input_token_type: Optional input token type, or symbol table.
    output_token_type: Optional output token type, or symbol table.
    threshold: Threshold for weights (1 is optimal only, 0 is for all paths)
    Returns:
    A tuple of output strings.
    """
    lattice = rewrite.rewrite_lattice(string, rule, input_token_type)
    lattice = threshold_lattice_to_dfa(lattice, threshold, 4)
    return rewrite.lattice_to_strings(lattice, output_token_type)


class PhonetisaurusRewriter:
    """
    Helper function for rewriting

    Parameters
    ----------
    fst: pynini.Fst
        G2P FST model
    grapheme_symbol_table: pynini.SymbolTable
        Grapheme symbol table
    phone_symbol_table: pynini.SymbolTable
        Phone symbol table
    num_pronunciations: int
        Number of pronunciations, default to 0.  If this is 0, thresholding is used
    threshold: float
        Threshold to use for pruning rewrite lattice, defaults to 1.5, only used if num_pronunciations is 0
    grapheme_order: int
        Maximum number of graphemes to consider single segment
    sequence_separator: str
        Separator to use between grapheme symbols
    """

    def __init__(
        self,
        fst: pynini.Fst,
        grapheme_symbol_table: pywrapfst.SymbolTable,
        phone_symbol_table: pywrapfst.SymbolTable,
        num_pronunciations: int = 0,
        threshold: float = 1.5,
        grapheme_order: int = 2,
        sequence_separator: str = "|",
        graphemes: set[str] = None,
        strict: bool = False,
    ):
        self.fst = fst
        self.sequence_separator = sequence_separator
        self.grapheme_symbol_table = grapheme_symbol_table
        self.phone_symbol_table = phone_symbol_table
        self.grapheme_order = grapheme_order
        self.graphemes = graphemes
        self.strict = strict
        if num_pronunciations > 0:
            self.rewrite = functools.partial(
                rewrite.top_rewrites,
                nshortest=num_pronunciations,
                rule=fst,
                input_token_type=None,
                output_token_type=self.phone_symbol_table,
            )
        else:
            self.rewrite = functools.partial(
                optimal_rewrites,
                threshold=threshold,
                rule=fst,
                input_token_type=None,
                output_token_type=self.phone_symbol_table,
            )

    def create_word_fst(self, word: str) -> typing.Optional[pynini.Fst]:
        if self.graphemes is not None:
            if self.strict and any(not self.grapheme_symbol_table.member(x) for x in word):
                return None
            word = [x for x in word if x in self.graphemes]
        if not word:
            return None
        fst = pynini.Fst()
        one = pywrapfst.Weight.one(fst.weight_type())
        max_state = 0
        for i in range(len(word)):
            start_state = fst.add_state()
            for j in range(1, self.grapheme_order + 1):
                if i + j <= len(word):
                    substring = self.sequence_separator.join(word[i : i + j])
                    ilabel = self.grapheme_symbol_table.find(substring)
                    if ilabel != pywrapfst.NO_LABEL:
                        fst.add_arc(start_state, pywrapfst.Arc(ilabel, ilabel, one, i + j))
                    if i + j >= max_state:
                        max_state = i + j
        for _ in range(fst.num_states(), max_state + 1):
            fst.add_state()
        fst.set_start(0)
        fst.set_final(len(word), one)
        fst.set_input_symbols(self.grapheme_symbol_table)
        fst.set_output_symbols(self.grapheme_symbol_table)
        return fst

    def __call__(self, graphemes: str) -> list[str]:  # pragma: no cover
        """Call the rewrite function"""
        if " " in graphemes:
            words = graphemes.split()
            hypotheses = []
            for w in words:
                w_fst = self.create_word_fst(w)
                if not w_fst:
                    continue
                hypotheses.append(self.rewrite(w_fst))
            hypotheses = sorted(set(" ".join(x) for x in itertools.product(*hypotheses)))
        else:
            fst = self.create_word_fst(graphemes)
            if not fst:
                return []
            hypotheses = self.rewrite(fst)
        hypotheses = [x.replace(self.sequence_separator, " ") for x in hypotheses if x]
        return hypotheses


class PyniniGenerator(G2PTopLevelMixin):
    """
    Class for generating pronunciations from a Pynini G2P model

    Parameters
    ----------
    g2p_model_path: str
        Path to G2P model
    strict_graphemes: bool
        Flag for whether to be strict with missing graphemes and skip words containing new graphemes

    See Also
    --------
    :class:`~montreal_forced_aligner.g2p.mixins.G2PTopLevelMixin`
        For top level G2P generation parameters

    Attributes
    ----------
    g2p_model: G2PModel
        G2P model
    """

    def __init__(
        self,
        word_list: list[str] = None,
        g2p_model_path: Path = None,
        strict_graphemes: bool = False,
        **kwargs,
    ):
        self.strict_graphemes = strict_graphemes
        super().__init__(**kwargs)
        self.g2p_model = G2PModel(
            g2p_model_path, root_directory=getattr(self, "workflow_directory", None)
        )
        self.output_token_type = "utf8"
        self.input_token_type = "utf8"
        self.rewriter = None
        if word_list is None:
            word_list = []
        self.word_list = word_list

    @property
    def words_to_g2p(self) -> list[str]:
        """Words to produce pronunciations"""
        return self.word_list

    @property
    def data_source_identifier(self) -> str:
        """Dummy "validation" data source"""
        return "validation"

    @property
    def working_directory(self) -> Path:
        """Data directory"""
        return None

    @property
    def data_directory(self) -> Path:
        """Data directory"""
        return self.working_directory

    def setup(self):
        self.fst = pynini.Fst.read(self.g2p_model.fst_path)
        if self.g2p_model.meta["architecture"] == "phonetisaurus":
            self.output_token_type = pywrapfst.SymbolTable.read_text(self.g2p_model.sym_path)
            self.input_token_type = pywrapfst.SymbolTable.read_text(
                self.g2p_model.grapheme_sym_path
            )
            self.fst.set_input_symbols(self.input_token_type)
            self.fst.set_output_symbols(self.output_token_type)
            self.rewriter = PhonetisaurusRewriter(
                self.fst,
                self.input_token_type,
                self.output_token_type,
                num_pronunciations=self.num_pronunciations,
                threshold=self.g2p_threshold,
                grapheme_order=self.g2p_model.meta["grapheme_order"],
                graphemes=self.g2p_model.meta["graphemes"],
            )
        else:
            if self.g2p_model.sym_path is not None and os.path.exists(self.g2p_model.sym_path):
                self.output_token_type = pywrapfst.SymbolTable.read_text(self.g2p_model.sym_path)

            self.rewriter = Rewriter(
                self.fst,
                self.input_token_type,
                self.output_token_type,
                num_pronunciations=self.num_pronunciations,
                threshold=self.g2p_threshold,
                graphemes=self.g2p_model.meta["graphemes"],
            )

    def generate_pronunciations(self) -> dict[str, list[str]]:
        """
        Generate pronunciations

        Returns
        -------
        dict[str, list[str]]
            Mappings of keys to their generated pronunciations
        """

        num_words = len(self.words_to_g2p)
        begin = time.time()
        missing_graphemes = set()
        if self.rewriter is None:
            self.setup()
        to_return = {}
        skipped_words = 0
        if not USE_MP or num_words < 30 or NUM_JOBS == 1:
            with tqdm(total=num_words, disable=QUIET) as pbar:
                for word in self.words_to_g2p:
                    w, m = clean_up_word(word, self.g2p_model.meta["graphemes"])
                    pbar.update(1)
                    missing_graphemes = missing_graphemes | m
                    if self.strict_graphemes and m:
                        skipped_words += 1
                        continue
                    if not w:
                        skipped_words += 1
                        continue
                    try:
                        prons = self.rewriter(w)
                    except rewrite.Error:
                        continue
                    to_return[word] = prons
        else:
            stopped = mp.Event()
            job_queue = mp.Queue()
            for word in self.words_to_g2p:
                w, m = clean_up_word(word, self.g2p_model.meta["graphemes"])
                missing_graphemes = missing_graphemes | m
                if self.strict_graphemes and m:
                    skipped_words += 1
                    continue
                if not w:
                    skipped_words += 1
                    continue
                job_queue.put(w)
            error_dict = {}
            return_queue = mp.Queue()
            procs = []
            for _ in range(NUM_JOBS):
                p = RewriterWorker(
                    job_queue,
                    return_queue,
                    self.rewriter,
                    stopped,
                )
                procs.append(p)
                p.start()
            num_words -= skipped_words
            with tqdm(total=num_words, disable=QUIET) as pbar:
                while True:
                    try:
                        word, result = return_queue.get(timeout=1)
                        if stopped.is_set():
                            continue
                    except queue.Empty:
                        for proc in procs:
                            if not proc.finished.is_set():
                                break
                        else:
                            break
                        continue
                    pbar.update(1)
                    if isinstance(result, Exception):
                        error_dict[word] = result
                        continue
                    to_return[word] = result

            for p in procs:
                p.join()
            if error_dict:
                # in original: PyniniGenerationError
                raise ValueError(error_dict)
        return to_return


class TemporaryDirectoryMixin(metaclass=abc.ABCMeta):
    """
    Abstract mixin class for MFA temporary directories
    """

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._corpus_output_directory = None
        self._dictionary_output_directory = None
        self._language_model_output_directory = None
        self._acoustic_model_output_directory = None
        self._g2p_model_output_directory = None
        self._ivector_extractor_output_directory = None
        self._current_workflow = None

    @property
    @abc.abstractmethod
    def identifier(self) -> str:
        """Identifier to use in creating the temporary directory"""
        ...

    @property
    @abc.abstractmethod
    def data_source_identifier(self) -> str:
        """Identifier for the data source (generally the corpus being used)"""
        ...

    @property
    @abc.abstractmethod
    def output_directory(self) -> Path:
        """Root temporary directory"""
        ...

    def clean_working_directory(self) -> None:
        """Clean up previous runs"""
        shutil.rmtree(self.output_directory, ignore_errors=True)

    @property
    def corpus_output_directory(self) -> Path:
        """Temporary directory containing all corpus information"""
        if self._corpus_output_directory:
            return self._corpus_output_directory
        return self.output_directory.joinpath(f"{self.data_source_identifier}")

    @corpus_output_directory.setter
    def corpus_output_directory(self, directory: Path) -> None:
        self._corpus_output_directory = directory

    @property
    def dictionary_output_directory(self) -> Path:
        """Temporary directory containing all dictionary information"""
        if self._dictionary_output_directory:
            return self._dictionary_output_directory
        return self.output_directory.joinpath("dictionary")

    @property
    def model_output_directory(self) -> Path:
        """Temporary directory containing all dictionary information"""
        return self.output_directory.joinpath("models")

    @dictionary_output_directory.setter
    def dictionary_output_directory(self, directory: Path) -> None:
        self._dictionary_output_directory = directory

    @property
    def language_model_output_directory(self) -> Path:
        """Temporary directory containing all dictionary information"""
        if self._language_model_output_directory:
            return self._language_model_output_directory
        return self.model_output_directory.joinpath("language_model")

    @language_model_output_directory.setter
    def language_model_output_directory(self, directory: Path) -> None:
        self._language_model_output_directory = directory

    @property
    def acoustic_model_output_directory(self) -> Path:
        """Temporary directory containing all dictionary information"""
        if self._acoustic_model_output_directory:
            return self._acoustic_model_output_directory
        return self.model_output_directory.joinpath("acoustic_model")

    @acoustic_model_output_directory.setter
    def acoustic_model_output_directory(self, directory: Path) -> None:
        self._acoustic_model_output_directory = directory


class MfaWorker(metaclass=abc.ABCMeta):
    """
    Abstract class for MFA workers

    Attributes
    ----------
    dirty: bool
        Flag for whether an error was encountered in processing
    """

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.dirty = False

    @classmethod
    def extract_relevant_parameters(cls, config: Metadict) -> tuple[Metadict, list[str]]:
        """
        Filter a configuration dictionary to just the relevant parameters for the current worker

        Parameters
        ----------
        config: dict[str, Any]
            Configuration dictionary

        Returns
        -------
        dict[str, Any]
            Filtered configuration dictionary
        list[str]
            Skipped keys
        """
        skipped = []
        new_config = {}
        for k, v in config.items():
            if k in cls.get_configuration_parameters():
                new_config[k] = v
            else:
                skipped.append(k)
        return new_config, skipped

    @classmethod
    def get_configuration_parameters(cls) -> dict[str, Type]:
        """
        Get the types of parameters available to be configured

        Returns
        -------
        dict[str, Type]
            dictionary of parameter names and their types
        """
        mapping = {dict: dict, tuple: tuple, list: list, set: set}
        configuration_params = {}
        for t, ty in get_type_hints(cls.__init__).items():
            configuration_params[t] = ty
            try:
                if ty.__origin__ == Union:
                    configuration_params[t] = ty.__args__[0]
            except AttributeError:
                pass

        for c in cls.mro():
            try:
                for t, ty in get_type_hints(c.__init__).items():
                    configuration_params[t] = ty
                    try:
                        if ty.__origin__ == Union:
                            configuration_params[t] = ty.__args__[0]
                    except AttributeError:
                        pass
            except AttributeError:
                pass
        for t, ty in configuration_params.items():
            for v in mapping.values():
                try:
                    if ty.__origin__ == v:
                        configuration_params[t] = v
                        break
                except AttributeError:
                    break
        return configuration_params

    @property
    def configuration(self) -> Metadict:
        """Configuration parameters"""
        return {
            "dirty": self.dirty,
        }

    @property
    @abc.abstractmethod
    def working_directory(self) -> Path:
        """Current working directory"""
        ...

    @property
    def working_log_directory(self) -> Path:
        """Current working log directory"""
        return self.working_directory.joinpath("log")

    @property
    @abc.abstractmethod
    def data_directory(self) -> Path:
        """Data directory"""
        ...


class TopLevelMfaWorker(MfaWorker, TemporaryDirectoryMixin, metaclass=abc.ABCMeta):
    """
    Abstract mixin for top-level workers in MFA.  This class holds properties about the larger workflow run.

    Parameters
    ----------
    num_jobs: int
        Number of jobs and processes to use
    clean: bool
        Flag for whether to remove any old files in the work directory
    """

    nullable_fields = [
        "punctuation",
        "compound_markers",
        "clitic_markers",
        "quote_markers",
        "word_break_markers",
    ]

    def __init__(
        self,
        **kwargs,
    ):
        kwargs, skipped = type(self).extract_relevant_parameters(kwargs)
        super().__init__(**kwargs)
        self.initialized = False
        self.start_time = time.time()
        # self.setup_logger()

    def cleanup_logger(self):
        # deleted, since logger is not used
        return NotImplementedError

    def setup(self) -> None:
        """setup for worker"""
        self.check_previous_run()
        if hasattr(self, "initialize_database"):
            self.initialize_database()
        if hasattr(self, "inspect_database"):
            self.inspect_database()

    @property
    def working_directory(self) -> Path:
        """Alias for a folder that contains worker information, separate from the data directory"""
        return self.output_directory.joinpath(self._current_workflow)

    @classmethod
    def parse_args(
        cls, args: Optional[dict[str, Any]], unknown_args: Optional[list[str]]
    ) -> Metadict:
        """
        Class method for parsing configuration parameters from command line arguments

        Parameters
        ----------
        args: dict[str, Any]
            Parsed arguments
        unknown_args: list[str]
            Optional list of arguments that were not parsed

        Returns
        -------
        dict[str, Any]
            dictionary of specified configuration parameters
        """
        param_types = cls.get_configuration_parameters()
        params = {}
        unknown_dict = {}
        if unknown_args:
            for i, a in enumerate(unknown_args):
                if not a.startswith("--"):
                    continue
                name = a.replace("--", "")
                if name not in param_types:
                    continue
                if i == len(unknown_args) - 1 or unknown_args[i + 1].startswith("--"):
                    val = True
                else:
                    val = unknown_args[i + 1]
                unknown_dict[name] = val
        for name, param_type in param_types.items():
            if (name.endswith("_directory") and name != "audio_directory") or (
                name.endswith("_path") and name not in {"rules_path", "phone_groups_path"}
            ):
                continue
            if args is not None and name in args and args[name] is not None:
                params[name] = param_type(args[name])
            elif name in unknown_dict:
                params[name] = param_type(unknown_dict[name])
                if param_type == bool and not isinstance(unknown_dict[name], bool):
                    if unknown_dict[name].lower() == "false":
                        params[name] = False
        return params

    @classmethod
    def parse_parameters(
        cls,
        config_path: Optional[Path] = None,
        args: Optional[dict[str, Any]] = None,
        unknown_args: Optional[typing.Iterable[str]] = None,
    ) -> Metadict:
        """
        Parse configuration parameters from a config file and command line arguments

        Parameters
        ----------
        config_path: :class:`~pathlib.Path`, optional
            Path to yaml configuration file
        args: dict[str, Any]
            Parsed arguments
        unknown_args: list[str]
            Optional list of arguments that were not parsed

        Returns
        -------
        dict[str, Any]
            dictionary of specified configuration parameters
        """
        global_params = {}
        if config_path and os.path.exists(config_path):
            data = load_configuration(config_path)
            for k, v in data.items():
                if v is None and k in cls.nullable_fields:
                    v = []
                global_params[k] = v
        global_params.update(cls.parse_args(args, unknown_args))
        return global_params

    @property
    def worker_config_path(self) -> str:
        """Path to worker's configuration in the working directory"""
        return os.path.join(self.output_directory, f"{self.data_source_identifier}.yaml")

    def cleanup(self) -> None:
        """
        Clean up loggers and output final message for top-level workers
        """
        try:
            if hasattr(self, "cleanup_connections"):
                self.cleanup_connections()
            if self.dirty:
                # caution: logger has been deleted
                print("There was an error in the run, please see the log.")
            else:
                # caution: logger has been deleted
                print(f"Done! Everything took {time.time() - self.start_time:.3f} seconds")
            self.save_worker_config()
            self.cleanup_logger()
        except (NameError, ValueError):  # already cleaned up
            pass

    def save_worker_config(self) -> None:
        """Export worker configuration to its working directory"""
        if not os.path.exists(self.output_directory):
            return
        with mfa_open(self.worker_config_path, "w") as f:
            yaml.dump(self.configuration, f)

    def _validate_previous_configuration(self, conf: Metadict) -> None:
        """
        Validate the current configuration against a previous configuration

        Parameters
        ----------
        conf: dict[str, Any]
            Previous run's configuration

        Caution: was removed!
        """
        

    def check_previous_run(self) -> None:
        """
        Check whether a previous run has any conflicting settings with the current run.

        Returns
        -------
        bool
            Flag for whether the current run is compatible with the previous one
        """
        if not os.path.exists(self.worker_config_path):
            return True
        try:
            conf = load_configuration(self.worker_config_path)
            self._validate_previous_configuration(conf)
            if not CLEAN and self.dirty:
                # logger was here!
                print(
                    "The previous run had a different configuration than the current, which may cause issues."
                    " Please see the log for details or use --clean flag if issues are encountered."
                )
        except yaml.error.YAMLError:
            # logger was here!
            print("The previous run's configuration could not be loaded.")
            return False

    @property
    def identifier(self) -> str:
        """Combined identifier of the data source and workflow"""
        return self.data_source_identifier

    @property
    def output_directory(self) -> Path:
        """Root temporary directory to store all of this worker's files"""
        return TEMPORARY_DIRECTORY.joinpath(self.identifier)

    @property
    def log_file(self) -> Path:
        """Path to the worker's log file"""
        return self.output_directory.joinpath(f"{self.data_source_identifier}.log")

    def setup_logger(self) -> None:
        """
        Construct a logger for a command line run
        """
        raise NotImplementedError
        from montreal_forced_aligner.helper import configure_logger
        from montreal_forced_aligner.utils import get_mfa_version

        current_version = get_mfa_version()
        # Remove previous directory if versions are different
        clean = False
        if os.path.exists(self.worker_config_path):
            conf = load_configuration(self.worker_config_path)
            if conf.get("version", current_version) != current_version:
                clean = True
        os.makedirs(self.output_directory, exist_ok=True)
        configure_logger("mfa", log_file=self.log_file)
        logger = logging.getLogger("mfa")
        logger.debug(f"Beginning run for {self.data_source_identifier}")
        logger.debug(f'Using "{CURRENT_PROFILE_NAME}" profile')
        if USE_MP:
            logger.debug(f"Using multiprocessing with {NUM_JOBS}")
        else:
            logger.debug(f"NOT using multiprocessing with {config.NUM_JOBS}")
        logger.debug(f"set up logger for MFA version: {current_version}")
        if clean or CLEAN:
            logger.debug("Cleaned previous run")


class PyniniValidator(PyniniGenerator, TopLevelMfaWorker):
    """
    Class for running validation for G2P model training

    Parameters
    ----------
    word_list: list[str]
        list of words to generate pronunciations

    See Also
    --------
    :class:`~montreal_forced_aligner.g2p.generator.PyniniGenerator`
        For parameters to generate pronunciations
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def evaluation_csv_path(self) -> Path:
        """Path to working directory's CSV file"""
        return self.working_directory.joinpath("pronunciation_evaluation.csv")

    @property
    def working_directory(self) -> Path:
        """Data directory"""
        return self.output_directory.joinpath(self._current_workflow)

    def setup(self) -> None:
        """set up the G2P validator"""
        TopLevelMfaWorker.setup(self)
        if self.initialized:
            return
        self._current_workflow = "validation"
        os.makedirs(self.working_log_directory, exist_ok=True)
        self.g2p_model.validate(self.words_to_g2p)
        PyniniGenerator.setup(self)
        self.initialized = True
        self.wer = None
        self.ler = None

    def compute_validation_errors(
        self,
        gold_values: dict[str, set[str]],
        hypothesis_values: dict[str, list[str]],
    ):
        """
        Computes validation errors

        Parameters
        ----------
        gold_values: dict[str, set[str]]
            Gold pronunciations
        hypothesis_values: dict[str, list[str]]
            Hypothesis pronunciations
        """
        begin = time.time()
        # Word-level measures.
        correct = 0
        incorrect = 0
        # Label-level measures.
        total_edits = 0
        total_length = 0
        # Since the edit distance algorithm is quadratic, let's do this with
        # multiprocessing.
        to_comp = []
        indices = []
        hyp_pron_count = 0
        gold_pron_count = 0
        output = []
        for word, gold_pronunciations in gold_values.items():
            if word not in hypothesis_values:
                incorrect += 1
                gold_length = statistics.mean(len(x.split()) for x in gold_pronunciations)
                total_edits += gold_length
                total_length += gold_length
                output.append(
                    {
                        "Word": word,
                        "Gold pronunciations": ", ".join(gold_pronunciations),
                        "Hypothesis pronunciations": "",
                        "Accuracy": 0,
                        "Error rate": 1.0,
                        "Length": gold_length,
                    }
                )
                continue
            hyp = hypothesis_values[word]
            if not isinstance(hyp, list):
                hyp = [hyp]
            for h in hyp:
                if h in gold_pronunciations:
                    correct += 1
                    total_length += len(h)
                    output.append(
                        {
                            "Word": word,
                            "Gold pronunciations": ", ".join(gold_pronunciations),
                            "Hypothesis pronunciations": ", ".join(hyp),
                            "Accuracy": 1,
                            "Error rate": 0.0,
                            "Length": len(h),
                        }
                    )
                    break
            else:
                incorrect += 1
                indices.append(word)
                to_comp.append((gold_pronunciations, hyp))  # Multiple hypotheses to compare
            hyp_pron_count += len(hyp)
            gold_pron_count += len(gold_pronunciations)
        with ThreadPool(NUM_JOBS) as pool:
            gen = pool.starmap(score_g2p, to_comp)
            for i, (edits, length) in enumerate(gen):
                word = indices[i]
                gold_pronunciations = gold_values[word]
                hyp = hypothesis_values[word]
                output.append(
                    {
                        "Word": word,
                        "Gold pronunciations": ", ".join(gold_pronunciations),
                        "Hypothesis pronunciations": ", ".join(hyp),
                        "Accuracy": 1,
                        "Error rate": edits / length,
                        "Length": length,
                    }
                )
                total_edits += edits
                total_length += length
        with mfa_open(self.evaluation_csv_path, "w") as f:
            writer = csv.dictWriter(
                f,
                fieldnames=[
                    "Word",
                    "Gold pronunciations",
                    "Hypothesis pronunciations",
                    "Accuracy",
                    "Error rate",
                    "Length",
                ],
            )
            writer.writeheader()
            for line in output:
                writer.writerow(line)
        self.wer = 100 * incorrect / (correct + incorrect)
        self.ler = 100 * total_edits / total_length

    def evaluate_g2p_model(self, gold_pronunciations: dict[str, set[str]]) -> None:
        """
        Evaluate a G2P model on the word list

        Parameters
        ----------
        gold_pronunciations: dict[str, set[str]]
            Gold pronunciations
        """
        output = self.generate_pronunciations()
        self.compute_validation_errors(gold_pronunciations, output)


class PyniniWordListGenerator(PyniniValidator):
    # Caution: DatabaseMixin is not inherited here, might lead to an error
    """
    Top-level worker for generating pronunciations from a word list and a Pynini G2P model

    Parameters
    ----------
    word_list_path: :class:`~pathlib.Path`
        Path to word list file

    See Also
    --------
    :class:`~montreal_forced_aligner.g2p.generator.PyniniGenerator`
        For Pynini G2P generation parameters
    :class:`~montreal_forced_aligner.abc.TopLevelMfaWorker`
        For top-level parameters

    Attributes
    ----------
    word_list: list[str]
        Word list to generate pronunciations
    """

    def __init__(self, **kwargs):
        # caution: there is no input path for the word list here
        self.initialized = False
        super().__init__(**kwargs)

    @property
    def data_directory(self) -> Path:
        """Data directory"""
        return self.working_directory

    def setup(self) -> None:
        """set up the G2P generator"""
        if self.initialized:
            return
        # CAUTION: in original code, here the path of the file is opened and read;
        # here, I pass directly the input list
        super().setup()
        self.g2p_model.validate(self.words_to_g2p)
        self.initialized = True

def threshold_lattice_to_dfa(
    lattice: pynini.Fst, threshold: float = 1.0, state_multiplier: int = 2
) -> pynini.Fst:
    """Constructs a (possibly pruned) weighted DFA of output strings.
    Given an epsilon-free lattice of output strings (such as produced by
    rewrite_lattice), attempts to determinize it, pruning non-optimal paths if
    optimal_only is true. This is valid only in a semiring with the path property.
    To prevent unexpected blowup during determinization, a state threshold is
    also used and a warning is logged if this exact threshold is reached. The
    threshold is a multiplier of the size of input lattice (by default, 4), plus
    a small constant factor. This is intended by a sensible default and is not an
    inherently meaningful value in and of itself.

    Parameters
    ----------
    lattice: :class:`~pynini.Fst`
        Epsilon-free non-deterministic finite acceptor.
    threshold: float
        Threshold for weights, 1.0 is optimal only, 0 is for all paths, greater than 1
        prunes the lattice to include paths with costs less than the optimal path's score times the threshold
    state_multiplier: int
        Max ratio for the number of states in the DFA lattice to the NFA lattice; if exceeded, a warning is logged.

    Returns
    -------
    :class:`~pynini.Fst`
        Epsilon-free deterministic finite acceptor.
    """
    weight_type = lattice.weight_type()
    weight_threshold = pynini.Weight(weight_type, threshold)
    state_threshold = 256 + state_multiplier * lattice.num_states()
    lattice = pynini.determinize(lattice, nstate=state_threshold, weight=weight_threshold)
    return lattice


class Rewriter:
    """
    Helper object for rewriting

    Parameters
    ----------
    fst: pynini.Fst
        G2P FST model
    input_token_type: pynini.TokenType
        Grapheme symbol table or "utf8"
    output_token_type: pynini.SymbolTable
        Phone symbol table
    num_pronunciations: int
        Number of pronunciations, default to 0.  If this is 0, thresholding is used
    threshold: float
        Threshold to use for pruning rewrite lattice, defaults to 1.5, only used if num_pronunciations is 0
    """

    def __init__(
        self,
        fst: pynini.Fst,
        input_token_type: pynini.TokenType,
        phone_symbol_table: pynini.SymbolTable,
        num_pronunciations: int = 0,
        threshold: float = 1,
        graphemes: set[str] = None,
        strict: bool = False,
    ):
        self.graphemes = graphemes
        self.input_token_type = input_token_type
        self.phone_symbol_table = phone_symbol_table
        self.strict = strict
        if num_pronunciations > 0:
            self.rewrite = functools.partial(
                rewrite.top_rewrites,
                nshortest=num_pronunciations,
                rule=fst,
                input_token_type=None,
                output_token_type=self.phone_symbol_table,
            )
        else:
            self.rewrite = functools.partial(
                optimal_rewrites,
                threshold=threshold,
                rule=fst,
                input_token_type=None,
                output_token_type=self.phone_symbol_table,
            )

    def create_word_fst(self, word: str) -> pynini.Fst:
        if self.graphemes is not None:
            if self.strict and any(x not in self.graphemes for x in word):
                return None
            word = "".join([x for x in word if x in self.graphemes])
        fst = pynini.accep(word, token_type=self.input_token_type)
        return fst

    def __call__(self, graphemes: str) -> list[str]:  # pragma: no cover
        """Call the rewrite function"""
        if " " in graphemes:
            words = graphemes.split()
            hypotheses = []
            for w in words:
                w_fst = self.create_word_fst(w)
                if not w_fst:
                    continue
                hypotheses.append(self.rewrite(w_fst))
            hypotheses = sorted(set(" ".join(x) for x in itertools.product(*hypotheses)))
        else:
            fst = self.create_word_fst(graphemes)
            if not fst:
                return []
            hypotheses = self.rewrite(fst)
        return [x for x in hypotheses if x]

def clean_up_word(word: str, graphemes: set[str]) -> tuple[str, set[str]]:
    """
    Clean up word by removing graphemes not in a specified set

    Parameters
    ----------
    word : str
        Input string
    graphemes: set[str]
        set of allowable graphemes

    Returns
    -------
    str
        Cleaned up word
    set[str]
        Graphemes excluded
    """
    new_word = []
    missing_graphemes = set()
    for c in word:
        if c not in graphemes:
            missing_graphemes.add(c)
        else:
            new_word.append(c)
    return "".join(new_word), missing_graphemes


class RewriterWorker(mp.Process):
    """
    Rewriter process

    Parameters
    ----------
    job_queue: :class:`~multiprocessing.Queue`
        Queue to pull words from
    return_queue: :class:`~multiprocessing.Queue`
        Queue to put pronunciations
    rewriter: :class:`~montreal_forced_aligner.g2p.generator.Rewriter`
        Function to generate pronunciations of words
    stopped: :class:`~threading.Event`
        Stop check
    """

    def __init__(
        self,
        job_queue: mp.Queue,
        return_queue: mp.Queue,
        rewriter: Rewriter,
        stopped: mp.Event,
    ):
        super().__init__()
        self.job_queue = job_queue
        self.return_queue = return_queue
        self.rewriter = rewriter
        self.stopped = stopped
        self.finished = mp.Event()

    def run(self) -> None:
        """Run the rewriting function"""
        while True:
            try:
                word = self.job_queue.get(timeout=1)
            except queue.Empty:
                break
            if self.stopped.is_set():
                continue
            try:
                rep = self.rewriter(word)
                self.return_queue.put((word, rep))
            except rewrite.Error:
                pass
            except Exception as e:  # noqa
                self.stopped.set()
                self.return_queue.put(e)
                raise
        self.finished.set()
