def read_text(text):
    # TODO: implement the real tts
    audio = 'static/audio/example-audio.aac'
    return audio


def read_words(text):
    words = text.split()
    word2phoneme_audio = {}
    for word in words:
        audio = f'static/audio/{word}.ogg'
        phoneme = [f'{char } ' for char in word.upper()]
        audio_phonemes = [(phoneme, audio) for _ in range(3)]
        word2phoneme_audio[word] = audio_phonemes
    return word2phoneme_audio