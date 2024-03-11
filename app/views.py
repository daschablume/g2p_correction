import json
import time

from flask import render_template, request, redirect, url_for

from app.ipa_phonemizer import (
    phonemize, get_grapheme2phonemes_from_model,
    enrich_model_phonemes_with_db, phonemes_to_string,
    tokenize
)
from app.matcha_utils import synthesize_matcha_audio


def text_to_audio_view():
    # import here, otherwise circular import
    from app import db
    from app.db_utils import add_graphemes_and_log, fetch_grapheme2phoneme

    if request.method == 'POST':
        form = request.form
        print(80*'=')
        print(form)
        text = form['text']
        words = tokenize(text)

        if form.get('generate'):
            word2db_phoneme = fetch_grapheme2phoneme(words)
            word2model_phonemes = get_grapheme2phonemes_from_model(words)
            word2phonemes, word2picked_phoneme, phonemized_str = (
                phonemize(word2model_phonemes, word2db_phoneme)
            )
            
        elif form.get('regenerate') or form.get('confirm'):
            # TODO: it would be nice to show to a user "saved"
            # TODO: handle situation with the wrong input from the user
            word2model_phonemes = json.loads(form['jsoned_word2model_phonemes'])
            word2phonemes = json.loads(form["jsoned_word2phonemes"])
            word2phonemes, word2picked_phoneme = pick_phoneme_from_form(
                word2phonemes, form)
            phonemized_str = phonemes_to_string(word2picked_phoneme.values())

            if form.get('confirm'):
                try:
                    add_graphemes_and_log(word2picked_phoneme)
                    db.session.commit()
                except Exception as e:
                    # TODO: show the error to the user
                    db.session.rollback()
                    print(e)
                    return redirect(url_for('interface.text_to_audio_view'))
            
            # fetch db phonemes after saving them to db
            word2db_phoneme = fetch_grapheme2phoneme(words)

        else:
            raise NotImplementedError

        audio = timestamp_audio(synthesize_matcha_audio(text, phonemized_str))

        return render_template(
            'text-to-audio.html', audio=audio,
            text=text, word2phonemes=word2phonemes,
            word2picked_phoneme=word2picked_phoneme,
            jsoned_word2phonemes=json.dumps(word2phonemes, ensure_ascii=False),
            word2db_phoneme=word2db_phoneme,
            word2model_phonemes=word2model_phonemes,
            jsoned_word2model_phonemes = json.dumps(
                word2model_phonemes, ensure_ascii=False),
        )

    return render_template('text-to-audio.html')


def timestamp_audio(filename):
    # timestamp is needed since the audio is stored in the same path,
    # so the browser caches the audio and doesn't update it (== plays the old audio)
    timestamp = str(int(time.time()))
    return f'{filename}?v{timestamp}'


def pick_phoneme_from_form(word2phonemes, form):
    from app.db_utils import fetch_grapheme2phoneme

    word2picked_phoneme = {}
    for word, all_phonemes in word2phonemes.items() :
        if not word.isalpha():
            continue
        # form phonemes: radio input -- either picked or orthographic
        form_phonemes = form.getlist(word)
        picked, manual_input = form_phonemes
        # manual for now is orthographic only!
        # there is no any validation here!
        if not manual_input:          
            word2picked_phoneme[word] = picked
        else:
            # if the phoneme is orthographic:
                # 1. get the phonemes from the model
                # 2. enrich the model phonemes with db phonemes
                # 3. pick the phoneme
                # 4. extend the word2phonemes with the new phonemes
            ipa_input = f'ipa_{word}'
            if form.get(ipa_input):
                word2picked_phoneme[word] = manual_input
                word2phonemes[word].append(manual_input)
            else:
                orthograpic = manual_input
                orthograpic2model_phonemes = get_grapheme2phonemes_from_model(
                    [orthograpic])
                orthograpic2db_phoneme = fetch_grapheme2phoneme([orthograpic])
                orthograpic2phonemes, orthograpic2picked_phoneme = (
                    enrich_model_phonemes_with_db(
                        orthograpic2model_phonemes,
                        orthograpic2db_phoneme))
                new_phonemes = [
                    phoneme 
                    for phoneme in orthograpic2phonemes[orthograpic] 
                    if phoneme not in all_phonemes
                ]
                picked_phoneme = orthograpic2picked_phoneme[orthograpic]
                word2picked_phoneme[word] = picked_phoneme
                word2phonemes[word].extend(new_phonemes)
    
    return word2phonemes, word2picked_phoneme   
