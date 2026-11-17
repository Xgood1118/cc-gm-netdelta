# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import netdelta as mod  # noqa: E402


def test_diff_applies():
    snaps = netdelta.load_snapshots("data/snapshots.json")
    d = netdelta.diff(snaps[0], snaps[1])
    st = netdelta.apply(snaps[0].entities, d)
    assert st == snaps[1].entities


def test_no_change_empty_diff():
    snaps = netdelta.load_snapshots("data/snapshots.json")
    d = netdelta.diff(snaps[1], snaps[1])
    assert d == [] or d == {}
