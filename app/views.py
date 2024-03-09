import json
import time

from flask import render_template, request

from app.ipa_phonemizer import (
    phonemize_text, get_grapheme2phonemes_from_model,
    enrich_model_phonemes_with_db, phonemes_to_string
)
from app.matcha_utils import synthesize_matcha_audio


def text_to_audio_view():
    # import here, otherwise circular import
    from app import db
    from app.db_utils import add_graphemes_and_log

    if request.method == 'POST':
        form = request.form
        text = form['text']

        if form.get('generate'):
            word2phonemes, word2picked_phoneme, phonemized_str = phonemize_text(text)
            
        elif form.get('regenerate') or form.get('confirm'):
            # todo: it would be nice to show to a user "saved" 
            word2phonemes = json.loads(form["jsoned_word2phonemes"])
            word2phonemes, word2picked_phoneme = pick_phoneme_from_form(word2phonemes, form)
            phonemized_str = phonemes_to_string(word2picked_phoneme.values())

            if form.get('confirm'):
                try:
                    add_graphemes_and_log(word2picked_phoneme)
                    db.session.commit()
                except Exception as e:
                    # TODO: show the error to the user
                    db.session.rollback()
                    print(e)

        else:
            raise NotImplementedError

        audio = timestamp_audio(synthesize_matcha_audio(text, phonemized_str))
        jsoned_word2phonemes = json.dumps(word2phonemes, ensure_ascii=False)

        return render_template(
                'text-to-audio.html', audio=audio,
                text=text, word2phonemes=word2phonemes,
                word2picked_phoneme=word2picked_phoneme,
                jsoned_word2phonemes=jsoned_word2phonemes,
            )

    return render_template('text-to-audio.html')


def timestamp_audio(filename):
    # timestamp is needed since the audio is stored in the same path,
    # so the browser caches the audio and doesn't update it (== plays the old audio)
    timestamp = str(int(time.time()))
    return f'{filename}?v{timestamp}'


def pick_phoneme_from_form(word2phonemes, form):
    word2picked_phoneme = {}
    for word, all_phonemes in word2phonemes.items() :
        if not word.isalpha():
            continue
        # form phonemes: radio input -- either picked or orthographic
        form_phonemes = form.getlist(word)
        picked, orthograpic = form_phonemes
        # manual for now is orthographic only!
        # there is no any validation here!
        if not orthograpic:          
            word2picked_phoneme[word] = picked
        else:
            # if the phoneme is orthographic:
                # 1. get the phonemes from the model
                # 2. enrich the model phonemes with the db phonemes
                # 3. pick the phoneme
                # 4. extend the word2phonemes with the new phonemes
            orthograpic2phonemes = get_grapheme2phonemes_from_model(orthograpic)
            orthograpic2phonemes, orthograpic2picked_phoneme = (
                enrich_model_phonemes_with_db(orthograpic2phonemes))
            new_phonemes = orthograpic2phonemes[orthograpic]
            new_phonemes = [ph for ph in new_phonemes if ph not in all_phonemes]
            picked_phoneme = orthograpic2picked_phoneme[orthograpic]
            word2picked_phoneme[word] = picked_phoneme
            word2phonemes[word].extend(new_phonemes)
    
    return word2phonemes, word2picked_phoneme

