# matcha-related code: property of matcha-tts. link:
# https://github.com/shivammehta25/Matcha-TTS/blob/256adc55d3219053d2d086db3f9bd9a4bde96fb1/synthesis.ipynb
# Copyright (c) 2023 Shivam Mehta
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
from app.mfa_g2p.generator import PyniniWordListGenerator

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MATCHA_CHECKPOINT = get_user_data_dir()/"matcha_ljspeech.ckpt"
HIFIGAN_CHECKPOINT = get_user_data_dir() / "hifigan_T2_v1"
G2P_CHECKPOINT= os.path.join("app", "mfa_g2p", "pretrained_models", "english_us_ipa.zip")


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


MATCHA_MODEL, VOCODER, DENOISER = load_matcha()
G2P = load_g2p()
