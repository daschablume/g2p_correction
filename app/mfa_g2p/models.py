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

import abc
import json
import os
from pathlib import Path
from typing import Optional, Union, Collection
from shutil import copy, copyfile, make_archive, move, rmtree, unpack_archive
import yaml

import pynini
import pywrapfst
from rich.pretty import pprint

from .helpers import mfa_open, EnhancedJSONEncoder

FORMAT = "zip"

# All the code is copied from montreal_forced_aligner.models
# Some functions are not implemented
class MfaModel(abc.ABC):
    """Abstract class for MFA models"""

    extensions: list[str]
    model_type = "base_model"

    @classmethod
    def pretrained_directory(cls) -> Path:
        """
        Directory that pretrained models are saved in.
        Copied without implementation from mfa_g2p.models.py
        """
        return Path('/Users/macuser/Documents/MFA/pretrained_models/g2p')

    @classmethod
    def get_available_models(cls) -> list[str]:
        """
        Get a list of available models for a given model type

        Returns
        -------
        list[str]
            List of model names
        """
        if not cls.pretrained_directory().exists():
            return []
        available = []
        for f in cls.pretrained_directory().iterdir():
            if cls.valid_extension(f):
                available.append(f.stem)
        return available

    @classmethod
    def get_pretrained_path(cls, name: str, enforce_existence: bool = True) -> Path:
        """
        Generate a path to a pretrained model based on its name and model type

        Parameters
        ----------
        name: str
            Name of model
        enforce_existence: bool
            Flag to return None if the path doesn't exist, defaults to True

        Returns
        -------
        Path
            Path to model
        """
        return cls.generate_path(cls.pretrained_directory(), name, enforce_existence)

    @classmethod
    @abc.abstractmethod
    def valid_extension(cls, filename: Path) -> bool:
        """Check whether a file has a valid extensions"""
        ...

    @classmethod
    @abc.abstractmethod
    def generate_path(
        cls, root: Path, name: str, enforce_existence: bool = True
    ) -> Optional[Path]:
        """Generate a path from a root directory"""
        ...

    @abc.abstractmethod
    def pretty_print(self) -> None:
        """Print the model's meta data"""
        ...

    @property
    @abc.abstractmethod
    def meta(self):
        """Metadata for the model"""
        ...

    @abc.abstractmethod
    def add_meta_file(self, trainer) -> None:
        """Add metadata to the model"""
        ...


class Archive(MfaModel):
    """
    Class representing data in a directory or archive file (zip, tar,
    tar.gz/tgz)

    Based on the prosodylab-aligner
    (https://github.com/prosodylab/Prosodylab-Aligner) archive class.

    Parameters
    ----------
    source: :class:`~pathlib.Path`
        Source path
    root_directory: :class:`~pathlib.Path`
        Root directory to unpack and store temporary files
    """

    extensions = [".zip"]

    model_type = None

    def __init__(
        self,
        source: Union[str, Path],
        root_directory: Optional[Union[str, Path]] = None,
    ):
        from .config import get_temporary_directory

        if isinstance(source, str):
            source = Path(source)
        source = source.resolve()
        if root_directory is None:
            root_directory = get_temporary_directory().joinpath(
                "extracted_models", self.model_type
            )
        if isinstance(root_directory, str):
            root_directory = Path(root_directory)
        self.root_directory = root_directory
        self.source = source
        self._meta = {}
        self.name = source.stem
        if os.path.isdir(source):
            self.dirname = source
        else:
            self.dirname = root_directory.joinpath(f"{self.name}_{self.model_type}")
            if self.dirname.exists():
                rmtree(self.dirname, ignore_errors=True)

            os.makedirs(root_directory, exist_ok=True)
            unpack_archive(source, self.dirname)
            files = [x for x in self.dirname.iterdir()]
            old_dir_path = self.dirname.joinpath(files[0])
            if len(files) == 1 and old_dir_path.is_dir():  # Backwards compatibility
                for f in old_dir_path.iterdir():
                    f = f.relative_to(old_dir_path)
                    move(old_dir_path.joinpath(f), self.dirname.joinpath(f))
                old_dir_path.rmdir()

    def parse_old_features(self) -> None:
        """
        Parse MFA model's features and ensure that they are up-to-date with current functionality
        """
        if "features" not in self._meta:
            return
        feature_key_remapping = {
            "type": "feature_type",
            "deltas": "uses_deltas",
            "fmllr": "uses_speaker_adaptation",
        }

        for key, new_key in feature_key_remapping.items():
            if key in self._meta["features"]:
                self._meta["features"][new_key] = self._meta["features"][key]
                del self._meta["features"][key]
        if "uses_splices" not in self._meta["features"]:  # Backwards compatibility
            self._meta["features"]["uses_splices"] = os.path.exists(
                self.dirname.joinpath("lda.mat")
            )
        if "uses_speaker_adaptation" not in self._meta["features"]:
            self._meta["features"]["uses_speaker_adaptation"] = os.path.exists(
                self.dirname.joinpath("final.alimdl")
            )

    def get_subclass_object(
        self,
    ):
        """
        Instantiate subclass models based on files contained in the archive

        Returns
        -------
        :class:`~montreal_forced_aligner.models.AcousticModel`, :class:`~montreal_forced_aligner.models.G2PModel`, :class:`~montreal_forced_aligner.models.LanguageModel`, or :class:`~montreal_forced_aligner.models.IvectorExtractorModel`
            Subclass model that was auto detected

        Raises
        ------
        :class:`~montreal_forced_aligner.exceptions.ModelLoadError`
            If the model type cannot be determined

        # Caution: copied from the original code without implementation
        """
        raise NotImplementedError

    @classmethod
    def valid_extension(cls, filename: Path) -> bool:
        """
        Check whether a file has a valid extension for the given model archive

        Parameters
        ----------
        filename: :class:`~pathlib.Path`
            File name to check

        Returns
        -------
        bool
            True if the extension matches the models allowed extensions
        """
        if filename.suffix in cls.extensions:
            return True
        return False

    @classmethod
    def generate_path(
        cls, root: Path, name: str, enforce_existence: bool = True
    ) -> Optional[Path]:
        """
        Generate a path for a given model from the root directory and the name of the model

        Parameters
        ----------
        root: :class:`~pathlib.Path`
            Root directory for the full path
        name: str
            Name of the model
        enforce_existence: bool
            Flag to return None if the path doesn't exist, defaults to True

        Returns
        -------
        Path
           Full path in the root directory for the model
        """
        for ext in cls.extensions:
            path = root.joinpath(name + ext)
            if path.exists() or not enforce_existence:
                return path
        return None

    def pretty_print(self) -> None:
        """
        Pretty print the archive's meta data using rich

        """
        pprint({"Archive": {"name": self.name, "data": self.meta}})

    @property
    def meta(self) -> dict:
        """
        Get the meta data associated with the model
        """
        if not self._meta:
            meta_path = self.dirname.joinpath("meta.json")
            format = "json"
            if not os.path.exists(meta_path):
                meta_path = self.dirname.joinpath("meta.yaml")
                format = "yaml"
            with mfa_open(meta_path, "r") as f:
                if format == "yaml":
                    self._meta = yaml.load(f, Loader=yaml.Loader)
                else:
                    self._meta = json.load(f)
        self.parse_old_features()
        return self._meta


    def add(self, source: str):
        """
        Add file into archive

        Parameters
        ----------
        source: str
            Path to file to copy into the directory
        """
        copy(source, self.dirname)

    def __repr__(self) -> str:
        """Representation string of a model"""
        return f"{self.__class__.__name__}(dirname={self.dirname!r})"

    def clean_up(self) -> None:
        """Remove temporary directory"""
        rmtree(self.dirname)

    def dump(self, path: Path, archive_fmt: str = FORMAT) -> str:
        """
        Write archive to disk, and return the name of final archive

        Parameters
        ----------
        path: :class:`~pathlib.Path`
            Path to write to
        archive_fmt: str, optional
            Archive extension to use, defaults to ".zip"

        Returns
        -------
        str
            Path of constructed archive
        """
        return make_archive(os.path.splitext(path)[0], archive_fmt, *os.path.split(self.dirname))


class G2PModel(Archive):
    """
    Class for G2P models

    Parameters
    ----------
    source: str
        Path to source archive
    root_directory: str
        Path to save exported model
    """

    extensions = [".zip", ".g2p"]

    model_type = "g2p"

    def __init__(
        self,
        source: Union[str, Path],
        root_directory: Optional[Union[str, Path]] = None,
    ):
        if source in G2PModel.get_available_models():
            source = G2PModel.get_pretrained_path(source)

        super().__init__(source, root_directory)

    @property
    def fst(self):
        return pynini.Fst.read(self.fst_path)

    @property
    def phone_table(self):
        return pywrapfst.SymbolTable.read_text(self.sym_path)

    @property
    def grapheme_table(self):
        return pywrapfst.SymbolTable.read_text(self.grapheme_sym_path)

    @property
    def rewriter(self):
        if not self.grapheme_sym_path.exists():
            return None
        if self.meta["architecture"] == "phonetisaurus":
            from montreal_forced_aligner.g2p.generator import PhonetisaurusRewriter

            rewriter = PhonetisaurusRewriter(
                self.fst,
                self.grapheme_table,
                self.phone_table,
                num_pronunciations=1,
                grapheme_order=self.meta["grapheme_order"],
                graphemes=self.meta["graphemes"],
                sequence_separator=self.meta["sequence_separator"],
                strict=True,
            )
        else:
            from montreal_forced_aligner.g2p.generator import Rewriter

            rewriter = Rewriter(
                self.fst, self.grapheme_table, self.phone_table, num_pronunciations=1, strict=True
            )
        return rewriter

    def add_meta_file(self, g2p_trainer) -> None:
        """
        Construct metadata information for the G2P model from the dictionary it was trained from

        Parameters
        ----------
        g2p_trainer: :class:`~montreal_forced_aligner.g2p.trainer.G2PTrainer`
            Trainer for the G2P model
        """

        with mfa_open(self.dirname.joinpath("meta.json"), "w") as f:
            json.dump(g2p_trainer.meta, f, cls=EnhancedJSONEncoder)

    @property
    def meta(self) -> dict:
        """Metadata for the G2P model"""
        if not self._meta:
            meta_path = self.dirname.joinpath("meta.json")
            format = "json"
            if not os.path.exists(meta_path):
                meta_path = self.dirname.joinpath("meta.yaml")
                format = "yaml"
            if not os.path.exists(meta_path):
                self._meta = {"version": "0.9.0", "architecture": "phonetisaurus"}
            else:
                with mfa_open(meta_path, "r") as f:
                    if format == "json":
                        self._meta = json.load(f)
                    else:
                        self._meta = yaml.load(f, Loader=yaml.Loader)
            self._meta["phones"] = set(self._meta.get("phones", []))
            self._meta["graphemes"] = set(self._meta.get("graphemes", []))
            self._meta["evaluation"] = self._meta.get("evaluation", [])
            self._meta["training"] = self._meta.get("training", [])
        return self._meta

    @property
    def fst_path(self) -> Path:
        """G2P model's FST path"""
        return self.dirname.joinpath("model.fst")

    @property
    def sym_path(self) -> Path:
        """G2P model's symbols path"""
        path = self.dirname.joinpath("phones.txt")
        if path.exists():
            return path
        return self.dirname.joinpath("phones.sym")

    @property
    def grapheme_sym_path(self) -> Path:
        """G2P model's grapheme symbols path"""
        path = self.dirname.joinpath("graphemes.txt")
        if path.exists():
            return path
        return self.dirname.joinpath("graphemes.sym")

    def add_sym_path(self, source_directory: Path) -> None:
        """
        Add symbols file into archive

        Parameters
        ----------
        source_directory: str
            Source directory path
        """
        if not os.path.exists(self.sym_path):
            copyfile(os.path.join(source_directory, "phones.txt"), self.sym_path)
        if not os.path.exists(self.grapheme_sym_path) and os.path.exists(
            os.path.join(source_directory, "graphemes.txt")
        ):
            copyfile(os.path.join(source_directory, "graphemes.txt"), self.grapheme_sym_path)

    def add_fst_model(self, source_directory: Path) -> None:
        """
        Add FST file into archive

        Parameters
        ----------
        source_directory: str
            Source directory path
        """
        if not self.fst_path.exists():
            copyfile(os.path.join(source_directory, "model.fst"), self.fst_path)

    def export_fst_model(self, destination: str) -> None:
        """
        Extract FST model path to destination

        Parameters
        ----------
        destination: str
            Destination directory
        """
        os.makedirs(destination, exist_ok=True)
        copy(self.fst_path, destination)

    def validate(self, word_list: Collection[str]) -> bool:
        """
        Validate the G2P model against a word list to ensure that all graphemes are known

        Parameters
        ----------
        word_list: Collection[str]
            Word list to validate against

        Returns
        -------
        bool
            False if missing graphemes were found
        """
        graphemes = set()
        for w in word_list:
            graphemes.update(w)
        missing_graphemes = graphemes - self.meta["graphemes"]
        if missing_graphemes:
            return False
        else:
            return True

