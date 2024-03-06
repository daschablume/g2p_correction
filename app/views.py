import json
import time

from flask import render_template, request, send_from_directory, redirect

from ipa_phonemizer import convert_text_to_phonemized, phonemes_to_string
from load_models import G2P
from matcha_utils import synthesize_matcha_audio


def text_to_audio():
    if request.method == 'POST':
        form = request.form
        text = form['text']
        if form.get('generate'):
            phonemized, word2phonemized, word2picked_phoneme = convert_text_to_phonemized(text, G2P)
            
        elif form.get('regenerate'):
            # it would have been nicer to get word2phonemized directly from the form, 
            # but json.loads() doesn't give a right encoding for IPA, 
            # and there is not enought time to fix it.
            _, word2phonemized, _ = convert_text_to_phonemized(text, G2P)
            word2picked_phoneme = {}
            for word in word2phonemized:
                if not word.isalpha():
                    continue
                phonemes = form.getlist(word)
                picked, manual = phonemes
                if not manual:          
                    word2picked_phoneme[word] = picked
                else:
                    # TODO: not complete functionality
                    phoneme = G2P.rewriter(manual)[0]
                    word2picked_phoneme[word] = phoneme

            phonemized = phonemes_to_string(word2picked_phoneme.values())
    
        audio = timestamp_audio(synthesize_matcha_audio(text, phonemized))

        return render_template(
                'text-to-audio.html', audio=audio,
                text=text, word2phonemized=word2phonemized,
                word2picked_phoneme=word2picked_phoneme
            )

    return render_template('text-to-audio.html')


def timestamp_audio(filename):
    # timestamp is needed since the audio is stored in the same path,
    # so the browser caches the audio and doesn't update it (== plays the old audio)
    timestamp = str(int(time.time()))
    return f'{filename}?v{timestamp}'