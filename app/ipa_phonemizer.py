from collections import defaultdict
import re

from mfa_g2p.generator import PyniniWordListGenerator

PUNCTUATION_STR = r"[!,.\"#$%&\(\)*+:;<=>?@^_`\{|\}~]"
PUNCT_PATTERN = re.compile(r"\s+(?=" + PUNCTUATION_STR + ")")
TOK_PATTERN = re.compile(f"\w+'?\w*|{PUNCTUATION_STR}")


def tokenize(text: str) -> list[str]:
    """Tokenize a string"""
    return re.findall(TOK_PATTERN, text.lower())


def convert_text_to_phonemized(input_str: str, g2p: PyniniWordListGenerator):
    '''
    Converts text to a phonetized text.
    Returns three variables: 
        1) phonetized text in a string; 
        2) a dict in the format {word: list of phonemized options};
        3) a dict in the format {word: picked phonemized option}.
    '''
    word_list = tokenize(input_str)
    word2phonemized = defaultdict(list)  
    for word in word_list:
        if not word.isalpha():
            word2phonemized[word].append(word)
        else:
            word2phonemized[word], _ = get_all_phonemes(
                g2p, word, set(word2phonemized[word])
            )

    # join phonemes into one dict: one phoneme per word;
    word2picked_phoneme = {}
    phonemes = []
    for word in word_list:
        for phoneme in word2phonemized[word]:
            # in order to pick the second phoneme
            # in case like this: 'the' => ['ð', 'ðə'...]
            if len(word) > 1 and len(phoneme) == 1:
                continue
            break
        word2picked_phoneme[word] = phoneme
        phonemes.append(phoneme)

    phonemized_str = phonemes_to_string(phonemes)
    
    return phonemized_str, word2phonemized, word2picked_phoneme


def phonemes_to_string(phonemes: list[str]) -> str:
    # removes whitespaces before punctuation and joins the phonemes
    return re.sub(PUNCT_PATTERN, "", " ".join(phonemes))


def collapse_whitespaces(phoneme: str) -> str:
    # 'h ɛ l l o ʊ' => 'hɛlloʊ'
    return phoneme.replace(" ", "")


def get_all_phonemes(
    g2p: PyniniWordListGenerator, word: str, current_phonemes: set
) -> tuple[list, list]:
    # joins current phonemes for a word with the output of G2P model
    phonemized = g2p.rewriter(word)
    phonemized = [collapse_whitespaces(pho) for pho in phonemized]
    return list(current_phonemes.union(phonemized)), phonemized
