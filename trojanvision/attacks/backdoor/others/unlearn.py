#!/usr/bin/env python3

from trojanvision.attacks.backdoor.badnet import BadNet

import torch
import argparse

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import torch.utils.data


class Unlearn(BadNet):

    name: str = 'unlearn'

    @classmethod
    def add_argument(cls, group: argparse._ArgumentGroup):
        super().add_argument(group)
        group.add_argument('--attack_source', dest='attack_source', type=str,
                           help='attack source, defaults to ``badnet``')
        group.add_argument('--mark_source', dest='mark_source', type=str,
                           help='mark source, defaults to ``attack``')

    def __init__(self, mark_source: str = 'attack', attack_source: str = 'badnet', **kwargs):
        self.attack_source = attack_source
        mark_source = mark_source if mark_source != 'attack' else attack_source
        self.mark_source = mark_source
        super().__init__(**kwargs)

    def get_data(self, data: tuple[torch.Tensor, torch.Tensor],
                 keep_org: bool = True, poison_label=False, **kwargs) -> tuple[torch.Tensor, torch.Tensor]:
        return super().get_data(data, keep_org=keep_org, poison_label=poison_label, **kwargs)

    def get_filename(self, **kwargs):
        return f'{self.attack_source}_{self.mark_source}_{self.train_mode}_' + super().get_filename(**kwargs)

    def mix_dataset(self, poison_label: bool = False) -> torch.utils.data.Dataset:
        return super().mix_dataset(poison_label=poison_label)
