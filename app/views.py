import json
import time

from flask import render_template, request

from ipa_phonemizer import (
    convert_text_to_phonemized, phonemes_to_string,
    collapse_whitespaces, get_all_phonemes
)
from load_models import G2P
from matcha_utils import synthesize_matcha_audio


def text_to_audio_view():
    if request.method == 'POST':
        form = request.form
        text = form['text']

        if form.get('generate'):
            phonemized, word2phonemized, word2picked_phoneme = (
                convert_text_to_phonemized(text, G2P)
            )
            
        elif form.get('regenerate'):
            word2phonemized = json.loads(form["jsoned_word2phonemized"])
            word2picked_phoneme = get_word2phoneme_from_front(word2phonemized, form)
            phonemized = phonemes_to_string(word2picked_phoneme.values())
    
        audio = timestamp_audio(synthesize_matcha_audio(text, phonemized))
        jsoned_word2phonemized = json.dumps(word2phonemized, ensure_ascii=False)

        return render_template(
                'text-to-audio.html', audio=audio,
                text=text, word2phonemized=word2phonemized,
                word2picked_phoneme=word2picked_phoneme,
                jsoned_word2phonemized=jsoned_word2phonemized
            )

    return render_template('text-to-audio.html')


def timestamp_audio(filename):
    # timestamp is needed since the audio is stored in the same path,
    # so the browser caches the audio and doesn't update it (== plays the old audio)
    timestamp = str(int(time.time()))
    return f'{filename}?v{timestamp}'


def get_word2phoneme_from_front(word2phonemized, form):
    print(f'form: {form}')
    print(f'word2phonemized: {word2phonemized}')
    word2picked_phoneme = {}
    for word in word2phonemized:
        if not word.isalpha():
            continue
        phonemes = form.getlist(word)
        picked, manual = phonemes
        if not manual:          
            word2picked_phoneme[word] = picked
        else:
            all_phonemes, new_phonemes = get_all_phonemes(
                g2p=G2P, word=manual.lower(), current_phonemes=set(
                    word2phonemized[word])
            )
            word2phonemized[word] = all_phonemes
            word2picked_phoneme[word] = new_phonemes[0]
    
    return word2picked_phoneme