# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import netdelta as mod  # noqa: E402
netdelta = mod


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_hex(path):
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def test_diff_applies():
    snaps = netdelta.load_snapshots("data/snapshots.json")
    d = netdelta.diff(snaps[0], snaps[1])
    st = netdelta.apply(snaps[0].entities, d)
    assert st == snaps[1].entities


def test_no_change_empty_diff():
    snaps = netdelta.load_snapshots("data/snapshots.json")
    d = netdelta.diff(snaps[1], snaps[1])
    assert d == [] or d == {}


def test_diff_minimal():
    # 只有 b.x 从 1 变 2，差量必须只含这一个叶子字段
    snaps = netdelta.load_snapshots("data/snapshots.json")
    d = netdelta.diff(snaps[0], snaps[1])
    assert d == [{"op": "set", "path": ["b", "x"], "value": 2}]


def test_diff_deterministic():
    snaps = netdelta.load_snapshots("data/snapshots.json")
    assert netdelta.diff(snaps[0], snaps[1]) == netdelta.diff(snaps[0], snaps[1])
    assert netdelta.diff(snaps[1], snaps[2]) == netdelta.diff(snaps[1], snaps[2])


def test_apply_chain_equals_full():
    # 逐帧应用差量，最终状态必须与最后一帧全量一致
    snaps = netdelta.load_snapshots("data/snapshots.json")
    state = snaps[0].entities
    for prev, cur in zip(snaps, snaps[1:]):
        state = netdelta.apply(state, netdelta.diff(prev, cur))
    assert state == snaps[-1].entities


def test_apply_does_not_mutate_input():
    snaps = netdelta.load_snapshots("data/snapshots.json")
    before = netdelta.apply(snaps[0].entities, [])
    netdelta.apply(snaps[0].entities, netdelta.diff(snaps[0], snaps[1]))
    assert snaps[0].entities == before


def test_seq_gap_finds_missing():
    assert netdelta.seq_gap([1, 2, 4]) == [3]
    assert netdelta.seq_gap([3, 4, 5]) == []
    assert netdelta.seq_gap([]) == []
    assert netdelta.seq_gap([5, 1, 3]) == [2, 4]


def test_gap_triggers_resync_and_recovers():
    snaps = [netdelta.Snapshot(seq=i, entities={"e": {"v": i}})
             for i in (1, 2, 3, 4)]
    rx = netdelta.Receiver()
    rx.receive_full(snaps[0])
    # 连续帧正常应用（只应用 1->2，seq 3 的差量随后模拟丢失）
    assert rx.receive_delta(1, 2, netdelta.diff(snaps[0], snaps[1]))
    # seq 3 丢失：base=3 的差量到达时本地只到 seq 2，必须拒绝
    d34 = netdelta.diff(snaps[2], snaps[3])
    assert not rx.receive_delta(3, 4, d34)
    assert rx.state == snaps[1].entities  # 未被误应用到旧状态
    # 补齐：全量重发最新帧，状态与不丢包一致
    rx.request_resync()
    rx.receive_full(snaps[3])
    assert rx.state == snaps[3].entities
    assert rx.resyncs == 1


def test_first_sync_requires_full():
    rx = netdelta.Receiver()
    assert not rx.receive_delta(0, 1, [])
    rx.receive_full(netdelta.Snapshot(seq=1, entities={"a": 1}))
    assert rx.state == {"a": 1}


def test_empty_frame_delete_all():
    a = netdelta.Snapshot(seq=1, entities={"x": {"v": 1}, "y": {"v": 2}})
    b = netdelta.Snapshot(seq=2, entities={})
    d = netdelta.diff(a, b)
    assert netdelta.apply(a.entities, d) == {}
    # 首次同步：空状态到全量
    d0 = netdelta.diff(netdelta.Snapshot(seq=0, entities={}), a)
    assert netdelta.apply({}, d0) == a.entities
