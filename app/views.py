from flask import render_template, request, url_for, redirect

import os

import tts_reader

def text_to_audio():
    print(f'{request.method=}')
    print(f'{request.form=}')
    if request.method == 'POST':
        text = request.form['text']
        if text:
            audio = tts_reader.read_text(text)
            word2phoneme_audio = tts_reader.read_words(text)
            print(f"{request.form.getlist('word')=}")
            return render_template(
                'text-to-audio.html', audio=audio,
                text=text, word2phoneme_audio=word2phoneme_audio
            )

    return render_template('text-to-audio.html')

            
