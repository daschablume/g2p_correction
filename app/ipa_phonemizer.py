from collections import defaultdict
import re
import typing as t

from app.mfa_g2p.generator import PyniniWordListGenerator
from app.load_models import G2P


PUNCTUATION_STR = r"[!,.\"#$%&\(\)*+:;<=>?@^_`\{|\}~]"
PUNCT_PATTERN = re.compile(r"\s+(?=" + PUNCTUATION_STR + ")")
TOK_PATTERN = re.compile(f"\w+'?-?\w*|{PUNCTUATION_STR}")


def tokenize(text: str) -> list[str]:
    """Tokenize a string"""
    return re.findall(TOK_PATTERN, text.lower())


def get_grapheme2phonemes_from_model(
    word_list: list, g2p: PyniniWordListGenerator=G2P
) -> dict[str, list[str]]:
    '''
    Converts text to a phonetized text, using the G2P model.
    Returns a dict with the word as a key and a list of phonemes as a value.
    '''
    word2phonemes = dict()  
    for word in word_list:
        # handle words like hel-loh or 'ello, but don't phonemize punctuation
        if not word.replace('-', '').replace('\'', '').isalpha():
            word2phonemes[word] = [word]
        else:
            phonemized = g2p.rewriter(word)
            phonemized = [collapse_whitespaces(pho) for pho in phonemized]
            word2phonemes[word] = phonemized
    return word2phonemes


def enrich_model_phonemes_with_db(
        word2model_phonemes: dict[str, list],
        word2db_phoneme: dict[str, str]
):
    '''
    Takes:
      a dict with words as keys and a list of phonemes as values, 
        generated by G2P model;
      a dict word-to-phoneme from db.
        
    Pickes one phoneme for each word: the one from the db if it exists,
        the first one from the model otherwise.

    Returns:
      the enriched dict and a dict with the picked phonemes.
    '''
    word2picked_phoneme = {}
    for word, phonemes in word2model_phonemes.items():
        db_phoneme = word2db_phoneme.get(word)
        if db_phoneme:
            word2picked_phoneme[word] = db_phoneme
            if db_phoneme not in phonemes:
                word2model_phonemes[word].append(db_phoneme)
        else:
            word2picked_phoneme[word] = phonemes[0]
    return word2model_phonemes, word2picked_phoneme


def phonemes_to_string(phonemes: t.Iterable[str]) -> str:
    # removes whitespaces before punctuation and joins the phonemes
    return re.sub(PUNCT_PATTERN, "", " ".join(phonemes))


def phonemize(
    word2model_phonemes: dict[str, list],
    word2db_phoneme: dict[str, str],
) -> tuple[dict[str, list], dict[str, str], str]:
    word2phonemized, word2picked_phoneme = enrich_model_phonemes_with_db(
        word2model_phonemes, word2db_phoneme)
    phonemized_str = phonemes_to_string(word2picked_phoneme.values())

    return word2phonemized, word2picked_phoneme, phonemized_str


def collapse_whitespaces(phoneme: str) -> str:
    # 'h ɛ l l o ʊ' => 'hɛlloʊ'
    return phoneme.replace(" ", "")
