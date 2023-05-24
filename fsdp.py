"""
torchrun --standalone --nproc_per_node=2 test_basic.py
"""
import os
import torch
import torch.distributed as dist
import torch.nn as nn
import torch._dynamo
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp.wrap import ModuleWrapPolicy
def init():
    torch.manual_seed(0)
    fsdp_kwargs = {
        "use_orig_params": True,
        "auto_wrap_policy": ModuleWrapPolicy({nn.Linear}),
    }
    model = nn.Sequential(
        nn.Linear(3, 3, device="cuda"), nn.ReLU(), nn.Linear(3, 3, device="cuda")
    )
    model = FSDP(
        model,
        **fsdp_kwargs,
    )
    # TODO: Add `model = torch.compile(model)` here if desired
    optim = torch.optim.SGD(model.parameters(), lr=1e-3)
    return model, optim

def run(model, optim):
    losses = []
    torch.manual_seed(dist.get_rank() + 1)
    inp = torch.randn((2, 3), device="cuda")
    explain = torch._dynamo.explain(model, inp)
    print(explain[0])
    for g in explain[2]:
        g.graph.print_tabular()
    for _ in range(3):
        optim.zero_grad(set_to_none=True)
        inp = torch.randn((2, 3), device="cuda")
        out = model(inp)
        loss = out.sum()
        losses.append(loss)
        loss.backward()
        optim.step()
    return losses

def main():
    dist.init_process_group(backend="nccl")
    gpu_id = int(os.environ["LOCAL_RANK"])
    device = f"cuda:{gpu_id}"
    torch.cuda.set_device(device)
    model, optim = init()
    run(model, optim)

if __name__ == "__main__":
    main()

