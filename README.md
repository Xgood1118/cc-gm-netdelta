# 快照差量同步

一个能算出最小差量、并在丢包时按序号补齐的快照同步器

## 保留签名

- `Snapshot`
- `diff(a, b)`
- `apply(state, delta)`
- `seq_gap(seqs)`

## 自测

```
python -m pytest tests -q
python -m netdelta.cli data/snapshots.json --out deltas.json
```
