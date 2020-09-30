# -*- coding: utf-8 -*-

from .defense import Defense
from .defense_backdoor import Defense_Backdoor
from .adv import *
from .backdoor import *

class_dict = {
    'defense': 'Defense',
    'defense_backdoor': 'Defense_Backdoor',

    'advmind': 'AdvMind',
    'curvature': 'Curvature',
    'grad_train': 'Grad_Train',
    'adv_train': 'Adv_Train',

    'neural_cleanse': 'Neural_Cleanse',
    'strip': 'STRIP',
    'abs': 'ABS',
    'tabor': 'Tabor',
    'activation_clustering': 'Activation_Clustering',
    'fine_pruning': 'Fine_Pruning',
    'deep_inspect': 'Deep_Inspect',
    'spectral_signature': 'Spectral_Signature',
    'neuron_inspect': 'Neuron_Inspect',
    'image_transform': 'Image_Transform',
}
