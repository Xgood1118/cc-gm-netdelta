# -*- coding: utf-8 -*-
"""命令行：对快照序列算差量、模拟丢包补齐、输出差量文件。"""

import argparse
import json

import netdelta as m


def run(path):
    """逐帧算差量并模拟接收：序号不连续时丢弃差量、全量补齐。"""
    snaps = m.load_snapshots(path)
    rx = m.Receiver()
    frames = []
    delta_bytes = 0
    delta_fields = 0
    for i, snap in enumerate(snaps):
        if i == 0:
            rx.receive_full(snap)
            frames.append({"type": "full", "seq": snap.seq,
                           "entities": snap.entities})
            continue
        prev = snaps[i - 1]
        ops = m.diff(prev, snap)
        if rx.receive_delta(prev.seq, snap.seq, ops):
            frames.append({"type": "delta", "base": prev.seq,
                           "seq": snap.seq, "ops": ops})
            delta_bytes += len(json.dumps(ops, ensure_ascii=False,
                                          sort_keys=True).encode("utf-8"))
            delta_fields += len(ops)
        else:
            rx.request_resync()
            rx.receive_full(snap)
            frames.append({"type": "full", "seq": snap.seq,
                           "entities": snap.entities, "reason": "resync"})
    equivalent = rx.state == snaps[-1].entities
    stats = {
        "frames": len(snaps),
        "delta_bytes": delta_bytes,
        "delta_fields": delta_fields,
        "resyncs": rx.resyncs,
        "equivalent": equivalent,
    }
    return {"frames": frames, "stats": stats}


def main():
    ap = argparse.ArgumentParser(description="快照差量同步")
    ap.add_argument("input", help="快照 JSON 文件")
    ap.add_argument("--out", required=True, help="差量输出文件")
    a = ap.parse_args()
    result = run(a.input)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    s = result["stats"]
    print("帧数: %d" % s["frames"])
    print("差量字节数: %d" % s["delta_bytes"])
    print("差量字段数: %d" % s["delta_fields"])
    print("补齐次数: %d" % s["resyncs"])
    print("等价校验: %s" % ("OK" if s["equivalent"] else "FAIL"))


if __name__ == "__main__":
    main()
