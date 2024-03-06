# matcha-related code: property of matcha-tts. link:
# https://github.com/shivammehta25/Matcha-TTS/blob/256adc55d3219053d2d086db3f9bd9a4bde96fb1/synthesis.ipynb

import os
import pathlib
import torch

# Hifigan imports
from matcha.hifigan.config import v1
from matcha.hifigan.denoiser import Denoiser
from matcha.hifigan.env import AttrDict
from matcha.hifigan.models import Generator as HiFiGAN
# Matcha imports
from matcha.models.matcha_tts import MatchaTTS
from matcha.utils.utils import get_user_data_dir
# G2P imports
from mfa_g2p.generator import PyniniWordListGenerator

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MATCHA_CHECKPOINT = get_user_data_dir()/"matcha_ljspeech.ckpt"
HIFIGAN_CHECKPOINT = get_user_data_dir() / "hifigan_T2_v1"
G2P_CHECKPOINT= os.path.join("mfa_g2p", "pretrained_models", "english_us_ipa.zip")


def load_matcha_model(checkpoint_path):
    model = MatchaTTS.load_from_checkpoint(checkpoint_path, map_location=DEVICE)
    model.eval()
    return model


def load_vocoder(checkpoint_path):
    h = AttrDict(v1)
    hifigan = HiFiGAN(h).to(DEVICE)
    hifigan.load_state_dict(torch.load(checkpoint_path, map_location=DEVICE)['generator'])
    _ = hifigan.eval()
    hifigan.remove_weight_norm()
    return hifigan


def load_g2p():
    '''
    A simple wrapper around the PyniniWordListGenerator class.
    '''
    g2p = PyniniWordListGenerator(
        g2p_model_path=pathlib.Path(G2P_CHECKPOINT))
    g2p.setup()
    return g2p


def load_matcha():
    count_params = lambda x: f"{sum(p.numel() for p in x.parameters()):,}"
    model = load_matcha_model(MATCHA_CHECKPOINT)
    print(f"Model loaded! Parameter count: {count_params(model)}")

    vocoder = load_vocoder(HIFIGAN_CHECKPOINT)
    denoiser = Denoiser(vocoder, mode='zeros')

    return model, vocoder, denoiser


MODEL, VOCODER, DENOISER = load_matcha()
G2P = load_g2p()
