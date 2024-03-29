#!/usr/bin/env python3

from trojanvision.optim import PGD as PGD_Optimizer
from trojanzoo.attacks import Attack
from trojanzoo.utils import to_list
from trojanzoo.utils.output import prints

import torch
import argparse
from collections.abc import Callable
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from trojanvision.datasets import ImageSet
    from trojanvision.models import ImageModel


class PGD(Attack, PGD_Optimizer):
    r"""PGD Adversarial Attack.
    Args:
        pgd_alpha (float): learning rate :math:`\alpha`. Default: :math:`\frac{3}{255}`.
        pgd_eps (float): the perturbation threshold :math:`\epsilon` in input space. Default: :math:`\frac{8}{255}`.
    """

    name: str = 'pgd'

    @classmethod
    def add_argument(cls, group: argparse._ArgumentGroup):
        super().add_argument(group)
        group.add_argument('--pgd_alpha', dest='pgd_alpha', type=float,
                           help='PGD learning rate per step, defaults to 2.0/255')
        group.add_argument('--pgd_eps', dest='pgd_eps', type=float,
                           help='Projection norm constraint, defaults to 8.0/255')
        group.add_argument('--iteration', dest='iteration', type=int,
                           help='Attack Iteration, defaults to 7')
        group.add_argument('--stop_threshold', dest='stop_threshold', type=float,
                           help='early stop confidence, defaults to 0.99')
        group.add_argument('--target_idx', dest='target_idx', type=int,
                           help='Target label order in original classification, defaults to -1 '
                           '(0 for untargeted attack, 1 for most possible class, -1 for most unpossible class)')
        group.add_argument('--test_num', dest='test_num', type=int,
                           help='total number of test examples for PGD, defaults to 1000.')

        group.add_argument('--grad_method', dest='grad_method',
                           help='gradient estimation method, defaults to \'white\'')
        group.add_argument('--query_num', dest='query_num', type=int,
                           help='query numbers for black box gradient estimation, defaults to 100.')
        group.add_argument('--sigma', dest='sigma', type=float,
                           help='gaussian sampling std for black box gradient estimation, defaults to 1e-3')

    def __init__(self, target_idx: int = -1, test_num: int = 1000, **kwargs):
        self.target_idx = target_idx
        self.test_num = test_num
        super().__init__(**kwargs)
        self.param_list['pgd'].extend(['target_idx', 'test_num'])
        self.dataset: ImageSet
        self.model: ImageModel

    def attack(self, verbose: bool = True, **kwargs) -> tuple[float, float]:
        # model._validate()
        correct = 0
        total = 0
        total_iter = 0
        total_conf = 0.0
        succ_conf = 0.0
        loader = self.dataset.get_dataloader(mode='test', shuffle=True)
        for data in loader:
            if total >= self.test_num:
                break
            _input, _label = self.model.remove_misclassify(data)
            if len(_label) == 0:
                continue
            target = self.generate_target(_input, idx=self.target_idx)
            adv_input, _iter = self.craft_example(_input, target=target, **kwargs)
            total += 1
            org_conf = float(self.model.get_target_prob(_input, target))
            adv_conf = float(self.model.get_target_prob(adv_input, target))
            total_conf += adv_conf
            if _iter:
                correct += 1
                total_iter += _iter
                succ_conf += adv_conf
            else:
                total_iter += self.iteration
            if verbose:
                print(f'{correct} / {total}')
                print(f'current iter: {str(_iter):8}')
                print(f'org target conf: {org_conf:<10.3f}    adv target conf: {adv_conf:<10.3f}')
                print('succ rate: ', float(correct) / total)
                print('avg  iter: ', float(total_iter) / total)
                print(f'total conf: {total_conf / total:<10.3f}')
                if correct > 0:
                    print(f'succ  conf: {succ_conf / correct:<10.3f}')
                print('-------------------------------------------------')
                print()
        return float(correct) / total, float(total_iter) / total

    def craft_example(self, _input: torch.Tensor, loss_fn: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] = None,
                      target: Union[torch.Tensor, int] = None, target_idx: int = None, **kwargs) -> tuple[torch.Tensor, int]:
        if len(_input) == 0:
            return _input, None
        target_idx = self.target_idx if target_idx is None else target_idx
        if target is None:
            target = self.generate_target(_input, idx=target_idx)
        elif isinstance(target, int):
            target = target * torch.ones(len(_input), dtype=torch.long, device=_input.device)
        else:
            assert isinstance(target, torch.Tensor)
        if loss_fn is None and self.loss_fn is None:
            def _loss_fn(_X: torch.Tensor, **kwargs):
                t = target
                if len(_X) != len(target) and len(target) == 1:
                    t = target * torch.ones(len(_X), dtype=torch.long, device=_X.device)
                loss = self.model.loss(_X, t, **kwargs)
                return loss if target_idx else -loss
            loss_fn = _loss_fn
        return self.optimize(_input, loss_fn=loss_fn, target=target, **kwargs)

    def early_stop_check(self, X: torch.Tensor, target: torch.Tensor = None, loss_fn=None, **kwargs):
        if not self.stop_threshold:
            return False
        with torch.no_grad():
            _confidence = self.model.get_target_prob(X, target)
        if self.target_idx and _confidence.min() > self.stop_threshold:
            return True
        if not self.target_idx and _confidence.max() < self.stop_threshold:
            return True
        return False

    def output_info(self, _input: torch.Tensor, noise: torch.Tensor, target: torch.Tensor, **kwargs):
        super().output_info(_input, noise, **kwargs)
        # prints('Original class     : ', to_list(_label), indent=self.indent)
        # prints('Original confidence: ', to_list(_confidence), indent=self.indent)
        with torch.no_grad():
            _confidence = self.model.get_target_prob(_input + noise, target)
        prints('Target   class     : ', to_list(target), indent=self.indent)
        prints('Target   confidence: ', to_list(_confidence), indent=self.indent)
