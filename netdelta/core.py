# -*- coding: utf-8 -*-
"""快照差量同步"""

from dataclasses import dataclass


@dataclass
class Snapshot:
    """一帧状态快照。"""
    seq: int
    entities: dict


def Snapshot:
    """class"""
    raise NotImplementedError("Snapshot 尚未实现")


def diff(a, b):
    """算差量"""
    raise NotImplementedError("diff 尚未实现")


def apply(state, delta):
    """应用差量"""
    raise NotImplementedError("apply 尚未实现")


def seq_gap(seqs):
    """找序号缺口"""
    raise NotImplementedError("seq_gap 尚未实现")


def load_snapshots(path):
    """读入与落盘辅助"""
    raise NotImplementedError("load_snapshots 尚未实现")

