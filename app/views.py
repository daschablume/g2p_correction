from flask import render_template, request, send_from_directory, redirect

from load_models import MODEL, VOCODER, DENOISER, G2P
from matcha_utils import synthesize_matcha_audio, get_audio


def text_to_audio():
    if request.method == 'POST':
        text = request.form['text']
        if text:
            _, word2phonemized, word2picked_phoneme = synthesize_matcha_audio(text)
            audio = get_audio()
            return render_template(
                'text-to-audio.html', audio=audio,
                text=text, word2phonemized=word2phonemized,
                word2picked_phoneme=word2picked_phoneme
            )

    return render_template('text-to-audio.html')

