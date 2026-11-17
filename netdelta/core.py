# -*- coding: utf-8 -*-
"""快照差量同步"""

import copy
import json
from dataclasses import dataclass

__all__ = ["Snapshot", "diff", "apply", "seq_gap", "load_snapshots", "Receiver"]


@dataclass
class Snapshot:
    """一帧状态快照。"""
    seq: int
    entities: dict


def diff(a, b):
    """计算 b 相对 a 的最小差量。

    返回操作列表，每个操作定位到一个叶子字段：
      {"op": "set", "path": [...], "value": ...}
      {"op": "del", "path": [...]}
    无变化时返回空列表。键按字典序遍历，同一对输入永远得到同一结果。
    """
    ops = []
    _walk(a.entities, b.entities, (), ops)
    return ops


def _walk(a, b, path, ops):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a:
                ops.append({"op": "set", "path": list(path) + [key],
                            "value": copy.deepcopy(b[key])})
            elif key not in b:
                ops.append({"op": "del", "path": list(path) + [key]})
            else:
                _walk(a[key], b[key], path + (key,), ops)
    elif a != b:
        ops.append({"op": "set", "path": list(path), "value": copy.deepcopy(b)})


def apply(state, delta):
    """把差量应用到 state 的深拷贝上，返回新状态（不改原对象）。"""
    result = copy.deepcopy(state)
    for op in delta:
        path = op["path"]
        if not path:
            result = copy.deepcopy(op["value"]) if op["op"] == "set" else {}
            continue
        node = result
        for key in path[:-1]:
            node = node[key]
        if op["op"] == "set":
            node[path[-1]] = copy.deepcopy(op["value"])
        elif op["op"] == "del":
            del node[path[-1]]
        else:
            raise ValueError("未知操作: %r" % (op["op"],))
    return result


def seq_gap(seqs):
    """返回已收序号中缺失的序号列表（升序）。"""
    if not seqs:
        return []
    have = set(seqs)
    return [s for s in range(min(have), max(have) + 1) if s not in have]


def load_snapshots(path):
    """从 JSON 文件读入快照序列。"""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Snapshot(seq=int(item["seq"]), entities=item["entities"])
            for item in raw]


class Receiver:
    """接收端：按序号应用差量，发现缺口时请求补齐。

    规则：差量帧 (base, seq) 仅当 base == 当前已应用序号且
    seq == base + 1 时才应用；否则丢弃，请求发送方用最新帧的
    全量快照补齐，缺口期间的差量绝不应用到旧状态上。
    """

    def __init__(self):
        self.state = None
        self.seq = 0
        self.resyncs = 0

    def receive_full(self, snap):
        """首次同步或补齐：直接采用全量快照。"""
        self.state = copy.deepcopy(snap.entities)
        self.seq = snap.seq

    def receive_delta(self, base, seq, ops):
        """返回 True 表示已应用；False 表示序号不连续，已拒绝。"""
        if self.state is None:
            return False
        if base != self.seq or seq != base + 1:
            return False
        self.state = apply(self.state, ops)
        self.seq = seq
        return True

    def request_resync(self):
        self.resyncs += 1
