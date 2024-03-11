# all code is from montreal forced aligner.
# link: https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner/tree/main/

import abc
from typing import get_type_hints, Union
from pathlib import Path

from .helpers import mfa_open

Metadict = dict[str, any]


# copied from montreal_forced_aligner/abc.py
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
        config: dict[str, any]
            Configuration dictionary

        Returns
        -------
        dict[str, any]
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
    def get_configuration_parameters(cls) -> dict[str, type]:
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


class G2PMixin(metaclass=abc.ABCMeta):
    """
    Abstract mixin class for G2P functionality

    Parameters
    ----------
    num_pronunciations: int
        Number of pronunciations to generate, defaults to 0
    g2p_threshold: float
        Weight threshold for generating pronunciations between 0 and 1,
        1 returns the optimal path only, 0 returns all pronunciations, defaults to 0.99 (only used if num_pronunciations is 0)
    include_bracketed: bool
        Flag for whether to generate pronunciations for fully bracketed words, defaults to False
    """

    def __init__(
        self,
        num_pronunciations: int = 0,
        g2p_threshold: float = 1.5,
        include_bracketed: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.num_pronunciations = num_pronunciations
        self.g2p_threshold = g2p_threshold
        self.include_bracketed = include_bracketed

    def generate_pronunciations(self) -> dict[str, list[str]]:
        """
        Generate pronunciations

        Returns
        -------
        dict[str, list[str]]
            Mappings of keys to their generated pronunciations
        """
        raise NotImplementedError

    @property
    def words_to_g2p(self) -> list[str]:
        """Words to produce pronunciations"""
        raise NotImplementedError


# CAUTION: DictionaryMixin is not inherited here, might lead to an error
class G2PTopLevelMixin(MfaWorker, G2PMixin):
    """
    Abstract mixin class for top-level G2P functionality

    See Also
    --------
    :class:`~montreal_forced_aligner.abc.MfaWorker`
        For base MFA parameters
    :class:`~montreal_forced_aligner.dictionary.mixins.dictionaryMixin`
        For dictionary parsing parameters
    :class:`~montreal_forced_aligner.g2p.mixins.G2PMixin`
        For base G2P parameters
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def generate_pronunciations(self) -> dict[str, list[str]]:
        """
        Generate pronunciations

        Returns
        -------
        dict[str, list[str]]
            Mappings of keys to their generated pronunciations
        """
        raise NotImplementedError

    def export_pronunciations(self, output_file_path: Union[str, Path]) -> None:
        """
        Output pronunciations to text file

        Parameters
        ----------
        output_file_path: :class:`~pathlib.Path`
            Path to save
        """
        if isinstance(output_file_path, str):
            output_file_path = Path(output_file_path)
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        results = self.generate_pronunciations()
        with mfa_open(output_file_path, "w") as f:
            for (orthography, pronunciations) in results.items():
                if not pronunciations:
                    continue
                for p in pronunciations:
                    if not p:
                        continue
                    f.write(f"{orthography}\t{p}\n")
