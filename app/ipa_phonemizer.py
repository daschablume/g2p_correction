from collections import defaultdict
import re

#from app import G2P

PUNCTUATION_STR = r"[!,.\"#$%&\(\)*+:;<=>?@^_`\{|\}~]"
PUNCT_PATTERN = re.compile(r'\s+(?=' + PUNCTUATION_STR + ')')
TOK_PATTERN = re.compile(f"\w+'?\w*|{PUNCTUATION_STR}")


def tokenize(text: str) -> list[str]:
    """Tokenize a string"""
    return re.findall(TOK_PATTERN, text.lower())


def convert_text_to_phonemized(input_str, g2p):
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
            phonemized = g2p.rewriter(word)
            phonemized = set(pho.replace(' ', '') for pho in phonemized)
            word2phonemized[word] = list(phonemized.union(word2phonemized[word]))
    
    # join phonemes into one list: one phoneme per word;
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
    
    # remove whitespaces before punctuation and join the phonemes
    phonemized_str = re.sub(PUNCT_PATTERN, '', ' '.join(phonemes))
    
    return phonemized_str, word2phonemized, word2picked_phoneme
