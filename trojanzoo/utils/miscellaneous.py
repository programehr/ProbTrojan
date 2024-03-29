#!/usr/bin/env python3

from .output import ansi, prints

import torch
import sys

from typing import Union    # TODO: python 3.10


def get_name(name: str = None, module: Union[str, object] = None, arg_list: list[str] = []) -> str:
    if module is not None:
        if isinstance(module, str):
            return module
        try:
            return getattr(module, 'name')
        except AttributeError:
            raise TypeError(f'{type(module)}    {module}')
    if name is not None:
        return name
    argv = sys.argv
    for arg in arg_list:
        try:
            idx = argv.index(arg)
            name: str = argv[idx + 1]
        except ValueError:
            continue
    return name


def summary(indent: int = 0, **kwargs):
    for key, value in kwargs.items():
        prints('{yellow}{0:<10s}{reset}'.format(key, **ansi), indent=indent)
        try:
            value.summary()
        except AttributeError:
            prints(value, indent=10)
        prints('-' * 30, indent=indent)
        print()


def normalize_mad(values: torch.Tensor, side: str = None) -> torch.Tensor:
    if not isinstance(values, torch.Tensor):
        values = torch.tensor(values, dtype=torch.float)
    median = values.median()
    abs_dev = (values - median).abs()
    mad = abs_dev.median()
    measures = abs_dev / mad / 1.4826
    if side == 'double':    # TODO: use a loop to optimie code
        dev_list = []
        for i in range(len(values)):
            if values[i] <= median:
                dev_list.append(float(median - values[i]))
        mad = torch.tensor(dev_list).median()
        for i in range(len(values)):
            if values[i] <= median:
                measures[i] = abs_dev[i] / mad / 1.4826

        dev_list = []
        for i in range(len(values)):
            if values[i] >= median:
                dev_list.append(float(values[i] - median))
        mad = torch.tensor(dev_list).median()
        for i in range(len(values)):
            if values[i] >= median:
                measures[i] = abs_dev[i] / mad / 1.4826
    return measures


def soft_median(values):
    # use avg of mid values when length is even (like numpy and unlike torch)
    n = len(values)
    values, indices = values.sort()
    if n % 2 == 0:
        mid1 = values[n//2]
        mid2 = values[n//2-1]
        return (mid1 + mid2) / 2
    else:
        return values[n // 2]


def outlier_ix(values, soft=True):
    if not isinstance(values, torch.Tensor):
        values = torch.tensor(values, dtype=torch.float)
    if soft:
        median = soft_median(values)
    else:
        median = values.median()
    abs_dev = (values - median).abs()
    mad = abs_dev.median()
    measures = abs_dev / mad / 1.4826

    ix = []
    n = len(values)
    for i in range(n):
        if values[i] < median and measures[i] > 2:
            ix.append(i)
    return ix


def outlier_ix_val(values, soft=True):
    if not isinstance(values, torch.Tensor):
        values = torch.tensor(values, dtype=torch.float)
    if soft:
        median = soft_median(values)
    else:
        median = values.median()
    abs_dev = (values - median).abs()
    mad = abs_dev.median()
    measures = abs_dev / mad / 1.4826
    # Consider these two examples:
    # values = [0.0, 0.01, 0.01, 0.02, 0.1]
    # values = [10.0, 10.01, 10.01, 10.02, 10.1]
    # in both cases the MAD value will be 9.0 while the second set of values are not too different.
    # So we examine std/median
    if values.std() / median < 1e-3:
        measures = 0 * measures

    ix = []
    left_ix = []
    n = len(values)
    for i in range(n):
        if values[i] <= median and measures[i] > 2:
            ix.append(i)
        if values[i] <= median:
            left_ix.append(i)
    measure = measures[left_ix].max()

    return ix, measures, median, measure


def jaccard_idx(mask: torch.Tensor, real_mask: torch.Tensor, select_num: int = 9) -> float:
    mask = mask.to(dtype=torch.float)
    real_mask = real_mask.to(dtype=torch.float)
    detect_mask = mask > mask.flatten().topk(select_num)[0][-1]
    sum_temp = detect_mask.int() + real_mask.int()
    overlap = (sum_temp == 2).sum().float() / (sum_temp >= 1).sum().float()
    return float(overlap)


def output_memory(device: Union[str, torch.device] = None, full: bool = False, indent: int = 0, **kwargs):
    if full:
        prints(torch.cuda.memory_summary(device=device, **kwargs))
    else:
        prints('memory allocated: '.ljust(20),
               bytes2size(torch.cuda.memory_allocated(device=device)), indent=indent)
        prints('memory reserved: '.ljust(20),
               bytes2size(torch.cuda.memory_reserved(device=device)), indent=indent)


def bytes2size(_bytes: int) -> str:
    if _bytes < 2 * 1024:
        return '%d bytes' % _bytes
    elif _bytes < 2 * 1024 * 1024:
        return '%.3f KB' % (float(_bytes) / 1024)
    elif _bytes < 2 * 1024 * 1024 * 1024:
        return '%.3f MB' % (float(_bytes) / 1024 / 1024)
    else:
        return '%.3f GB' % (float(_bytes) / 1024 / 1024 / 1024)


class AverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self, name: str, fmt: str = ':f'):
        self.name: str = name
        self.fmt = fmt
        self.reset()

    def reset(self):
        self.val = 0.
        self.avg = 0.
        self.sum = 0.
        self.count = 0

    def update(self, val: float, n: int = 1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count

    def __str__(self):
        fmtstr = '{name} {val' + self.fmt + '} ({avg' + self.fmt + '})'
        return fmtstr.format(**self.__dict__)


# class CrossEntropy(nn.Module):
#     def forward(self, logits, y):
#         return -(F.log_softmax(logits, dim=1) * y).sum(1).mean()


# class ProgressMeter(object):
#     def __init__(self, num_batches, meters, prefix=''):
#         self.batch_fmtstr = self._get_batch_fmtstr(num_batches)
#         self.meters = meters
#         self.prefix = prefix

#     def display(self, batch):
#         entries = [self.prefix + self.batch_fmtstr.format(batch)]
#         entries += [str(meter) for meter in self.meters]
#         print('\t'.join(entries))

#     def _get_batch_fmtstr(self, num_batches):
#         num_digits = len(str(num_batches // 1))
#         fmt = '{:' + str(num_digits) + 'd}'
#         return '[' + fmt + '/' + fmt.format(num_batches) + ']'
