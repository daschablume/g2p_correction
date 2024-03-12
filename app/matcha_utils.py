# matcha-related code: property of matcha-tts. link:
# https://github.com/shivammehta25/Matcha-TTS/blob/256adc55d3219053d2d086db3f9bd9a4bde96fb1/synthesis.ipynb

import datetime as dt
from functools import cache
import os
from pathlib import Path

import IPython.display as ipd
import numpy as np
import soundfile as sf
import torch
from types import SimpleNamespace

from matcha.text import sequence_to_text
from matcha.text.symbols import symbols
from matcha.utils.utils import intersperse

from app.ipa_phonemizer import is_word
from app.load_models import MATCHA_MODEL, VOCODER, DENOISER, DEVICE

HYPERPARAMS = SimpleNamespace(n_timesteps=10, temperature=1.0, length_scale=0.667)
OUTPUT_FOLDER = os.path.join('app', 'static', 'audio')


def phonemized_to_sequence(phonemized_text):
    """
    ### 
    Caution: Copied from matcha.text.__init__ with modifications in order to replace
    _clean_text from the same module. 
    _clean_text evokes english_cleaners2 function, which uses espeak phonemizer.
    Here, I pass a string of phonemes, taken from mfa g2p phonemizer instead.
    ###
    Converts a string of phonemized text to a sequence of IDs corresponding to the symbols in the text.
    Args:
      phonemized_text: phonemized string to convert to a sequence
    Returns:
      List of integers corresponding to the symbols in the text
    """
    _symbol_to_id = {s: i for i, s in enumerate(symbols)}
    sequence = []

    for symbol in phonemized_text:
        symbol_id = _symbol_to_id[symbol]
        sequence += [symbol_id]
    return sequence


@torch.inference_mode()
def process_text(text: str, phonemized_text: str):
    sequence = phonemized_to_sequence(phonemized_text)
    x = torch.tensor(
        intersperse(sequence, 0),
        dtype=torch.long,
        device=DEVICE)[None]
    x_lengths = torch.tensor([x.shape[-1]],dtype=torch.long, device=DEVICE)
    x_phones = sequence_to_text(x.squeeze(0).tolist())
    return {
        'x_orig': text,
        'x': x,
        'x_lengths': x_lengths,
        'x_phones': x_phones
    }


@torch.inference_mode()
def synthesise(text, phonemized_text, model, args=HYPERPARAMS, spks=None):
    text_processed = process_text(text, phonemized_text)
    start_t = dt.datetime.now()
    output = model.synthesise(
        text_processed['x'], 
        text_processed['x_lengths'],
        n_timesteps=args.n_timesteps,
        temperature=args.temperature,
        spks=spks,
        length_scale=args.length_scale
    )
    # merge everything to one dict    
    output.update({'start_t': start_t, **text_processed})
    return output


@torch.inference_mode()
def to_waveform(mel, vocoder, denoiser):
    audio = vocoder(mel).clamp(-1, 1)
    audio = denoiser(audio.squeeze(0), strength=0.00025).cpu().squeeze()
    return audio.cpu().squeeze()
    

def save_to_folder(filename: str, output: dict, folder: str):
    folder = Path(folder)
    folder.mkdir(exist_ok=True, parents=True)
    np.save(folder / f'{filename}', output['mel'].cpu().numpy())
    sf.write(folder / f'{filename}.wav', output['waveform'], 22050, 'PCM_24')
    return folder / f'{filename}.wav'


def synthesize_matcha_audios(
    text: str, phonemized: str, word2phonemes: dict[str, list[str]],
    model=MATCHA_MODEL, vocoder=VOCODER, denoiser=DENOISER, 
    output_folder=OUTPUT_FOLDER
):

    rtfs = []
    rtfs_w = []

    # synthesize the whole sentence first -- from user's input
    rtf, rtf_w, _ = synthesize_matcha_audio(
        text, phonemized,
        model=model, vocoder=vocoder, denoiser=denoiser, 
        output_folder=output_folder,
        utterance=True,
    )

    # it's a bit redundant to repeat list.append here
    # but functools.cache accepts only hashable arguments
    rtfs.append(rtf)
    rtfs_w.append(rtf_w)
    
    phonemes2audio_names = {}
    for word, phonemes in word2phonemes.items():
        if not is_word(word):
            continue
        for phoneme in phonemes:
            rtf, rtf_w, name = synthesize_matcha_audio(
                word, phoneme,
                model=model, vocoder=vocoder, denoiser=denoiser, 
                output_folder=output_folder
            )
            rtfs.append(rtf)
            rtfs_w.append(rtf_w)
            phonemes2audio_names[phoneme] = name

    print(f"Number of ODE steps: {HYPERPARAMS.n_timesteps}")
    print(f"Mean RTF:\t\t\t\t{np.mean(rtfs):.6f} ± {np.std(rtfs):.6f}")
    print(f"Mean RTF Waveform (incl. vocoder):\t{np.mean(rtfs_w):.6f} ± {np.std(rtfs_w):.6f}")
    print(f'Cache info: {synthesize_matcha_audio.cache_info()}')

    return phonemes2audio_names


@cache
def synthesize_matcha_audio(
    text: str, phonemized: str,
    model, vocoder, denoiser, output_folder,
    utterance=False
):
    output = synthesise(text, phonemized, model)
    output['waveform'] = to_waveform(output['mel'], vocoder, denoiser)

    # Compute Real Time Factor (RTF) with HiFi-GAN
    t = (dt.datetime.now() - output['start_t']).total_seconds()
    rtf_w = t * 22050 / (output['waveform'].shape[-1])
    
    ## Display the synthesised waveform
    ipd.display(ipd.Audio(output['waveform'], rate=22050))

    ## Save the generated waveform: with the name 'utterance.wav' if it's a sentence, 
    ## and to a hash if it's a phonemized word
    if utterance:
        name = "utterance"
    else:
        name = str(hash(phonemized))
        
    save_to_folder(name, output, output_folder)

    return output['rtf'], rtf_w, name

 
