import json
import os
import tempfile
import time

from flask import render_template, request, redirect, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.ipa_phonemizer import (
    phonemize, get_grapheme2phonemes_from_model,
    enrich_model_phonemes_with_db, phonemes_to_string,
    tokenize, is_word
)
from app.matcha_utils import synthesize_matcha_audios
from app.utils import get_word2phones_from_textgrid

AUDIO = 'static/audio/utterance.wav'
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mb


def text_to_audio_view():
    # import here, otherwise circular import
    from app import db
    from app.db_utils import (
        add_graphemes_and_log, fetch_grapheme2phoneme,
        fetch_grapheme_ids_by_name
    )

    if request.method == 'POST':
        form = request.form
        text = form['text']
        words = tokenize(text)

        if form.get('generate'):
            word2db_phoneme = fetch_grapheme2phoneme(words)
            word2grapheme_id = fetch_grapheme_ids_by_name(
                word2db_phoneme.keys())
            word2model_phonemes = get_grapheme2phonemes_from_model(words)
            word2phonemes, word2picked_phoneme, phonemized_str = (
                phonemize(words, word2model_phonemes, word2db_phoneme)
            )
            
        elif form.get('regenerate') or form.get('confirm'):
            # TODO: it would be nice to show to a user "saved"
            # TODO: handle situation with the wrong input from the user
            word2model_phonemes = json.loads(form['jsoned_word2model_phonemes'])
            word2phonemes = json.loads(form["jsoned_word2phonemes"])
            word2phonemes, word2picked_phoneme = pick_phoneme_from_form(
                word2phonemes, form)
            phonemized_str = phonemes_to_string(words, word2picked_phoneme)

            if form.get('confirm'):
                try:
                    add_graphemes_and_log(word2picked_phoneme)
                    db.session.commit()
                except SQLAlchemyError as e:
                    # TODO: show the error to the user
                    db.session.rollback()
                    print("Error!", e)
                    return redirect(url_for('interface.text_to_audio_view'))
            
            # fetch db phonemes after saving them to db
            word2db_phoneme = fetch_grapheme2phoneme(words)
            word2grapheme_id = fetch_grapheme_ids_by_name(word2db_phoneme.keys())

        else:
            raise NotImplementedError

        phoneme2audio = synthesize_matcha_audios(text, phonemized_str, word2phonemes)
        audio = timestamp_audio(AUDIO)

        return render_template(
            'text-to-audio.html', audio=audio,
            phoneme2audio=phoneme2audio,
            text=text, word2phonemes=word2phonemes,
            word2picked_phoneme=word2picked_phoneme,
            jsoned_word2phonemes=json.dumps(word2phonemes, ensure_ascii=False),
            word2db_phoneme=word2db_phoneme,
            word2model_phonemes=word2model_phonemes,
            jsoned_word2model_phonemes = json.dumps(
                word2model_phonemes, ensure_ascii=False),
            word2grapheme_id=word2grapheme_id,
            is_word=is_word
        )

    return render_template('text-to-audio.html')


def grapheme_log_view(grapheme_id):
    from app.db_utils import fetch_grapheme_logs, fetch_grapheme
    from app.models import Grapheme

    grapheme_logs = fetch_grapheme_logs(grapheme_id)
    grapheme, phoneme = fetch_grapheme(grapheme_id)

    return render_template(
        'grapheme-log.html', 
        grapheme=grapheme,
        phoneme=phoneme,
        grapheme_logs=grapheme_logs)


def upload_file_view():
    # imported here due to circular import
    from app import db
    from app.db_utils import filter_out_existing_words, save_word2phones

    save_flag = False
    errors = []
    new_words2phones = {}
    file_name = None
    discarded_words = []
    
    file = request.files.get('file')
    
    if file:
        file_name = file.filename[:50]
        file_content = file.read()
        if len(file_content) > MAX_FILE_SIZE:
            errors.append('Please upload a file which is less than 5 Mb')
        else: 
            file.seek(0)

            # Create a temporary file with a secure filename in order for textgrid to read it
            # (textgrid can't read from a file object, it needs a path in a str format)
            _, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
            
            try:
                with open(temp_path, 'wb') as temp_file:
                    temp_file.write(file_content)
                word2phones = get_word2phones_from_textgrid(temp_path)
                if not word2phones:
                    errors.append('No words found in the TextGrid. Please upload a new TextGrid.')
                new_words2phones = filter_out_existing_words(word2phones)
                if not new_words2phones:
                    errors.append('All words from the TextGrid are already in the database.')

            except Exception as e:
                errors.append(f'An error happened during uploading of your file: {e}')

            finally:
                os.remove(temp_path)

    elif request.form.get('confirm_changes'):
        form = request.form
        print('form:', form)

        file_name  = form['file_name']
        new_words2phones = {}
        discarded_words = []
        for word in json.loads(form['jsoned_new_words2phones']):
            phones_from_form = form.getlist(word)
            picked_phones = [phone for phone in phones_from_form if phone]
            if not picked_phones or picked_phones[0] == 'discard':
                picked_phone = None
                discarded_words.append(word)
            else:
                picked_phone = picked_phones[0]
            new_words2phones[word] = picked_phone
        print(f'{new_words2phones=}')
        print(f'{discarded_words=}')
        try:                
            save_word2phones(new_words2phones)
            db.session.rollback()
            #db.session.commit()
            save_flag = True
        except SQLAlchemyError as e:
            print(f'Error: {e}')
            errors.append('An error happened during saving of your file')
            db.session.rollback()
            
        # in order to display it in the same format in html (word: [phones]),
        # wrap each phone in a list
        new_words2phones = {
            word: [phone] 
            if phone is not None 
            else [] 
            for word, phone in new_words2phones.items()
        }

    print(f'{errors=}')

    return render_template('upload-file.html', 
        new_words2phones=new_words2phones,
        file_name=file_name,
        jsoned_new_words2phones=json.dumps(new_words2phones, ensure_ascii=False),
        save_flag=save_flag,
        errors=errors,
        discarded_words=discarded_words,
    )


def timestamp_audio(filename):
    # timestamp is needed since the audio is stored in the same path,
    # so the browser caches the audio and doesn't update it (== plays the old audio)
    timestamp = str(int(time.time()))
    return f'{filename}?v{timestamp}'


def pick_phoneme_from_form(word2phonemes, form):
    from app.db_utils import fetch_grapheme2phoneme

    word2picked_phoneme = {}
    for word, all_phonemes in word2phonemes.items() :
        if not is_word(word):
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
