# Synthetic domain nodes

A three-node graph for the `reminder` example domain. Compile it from this
repository root:

```bash
python3 -B kernel/scripts/kernel.py compile \
  --source examples/domain-nodes --output /tmp/example-index.json

python3 -B kernel/scripts/kernel.py gate-index --index /tmp/example-index.json
```

`authority:reminder-product` is `confirmed L3` and its scope covers
`capability:reminder`, which is therefore allowed to be confirmed too. The
journey stays `candidate L1`, which is what an honest early graph looks like.
