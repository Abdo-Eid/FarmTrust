"""Pretraining loop for FarmTrust SITS-BERT on Kaggle."""

from __future__ import annotations

import json
import math
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader

from kaggle.sits_bert.config import FarmTrustSITSConfig, config as default_config
from kaggle.sits_bert.dataset import FarmTrustDataset
from kaggle.sits_bert.model import SITSBertPretraining


def _lr_lambda(step: int, *, warmup_steps: int, total_steps: int) -> float:
    if step < warmup_steps:
        return float(step) / float(max(1, warmup_steps))
    progress = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
    return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))


def pretrain(config: FarmTrustSITSConfig = default_config) -> list[float]:
    torch.manual_seed(config.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = FarmTrustDataset(
        config.dataset_path,
        mode="pretraining",
        normalization_stats_path=config.normalization_stats_path,
        mask_prob=config.pretraining.mask_prob,
        seed=config.seed,
    )
    loader = DataLoader(dataset, batch_size=config.pretraining.batch_size, shuffle=True)
    model = SITSBertPretraining(config).to(device)
    optimizer = AdamW(model.parameters(), lr=config.pretraining.learning_rate, weight_decay=config.pretraining.weight_decay)
    total_steps = max(1, len(loader) * config.pretraining.epochs)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lambda step: _lr_lambda(step, warmup_steps=config.pretraining.warmup_steps, total_steps=total_steps),
    )

    losses: list[float] = []
    global_step = 0
    for epoch in range(1, config.pretraining.epochs + 1):
        model.train()
        for batch in loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            output = model(**batch)
            loss = output["loss"]
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            global_step += 1
            losses.append(float(loss.item()))
            if global_step % 50 == 0:
                print(f"step={global_step} loss={loss.item():.6f} lr={scheduler.get_last_lr()[0]:.8f}")
        if epoch % 20 == 0:
            torch.save({"model_state_dict": model.state_dict(), "epoch": epoch}, output_dir / f"sits_bert_pretrained_epoch_{epoch}.pt")

    final_path = output_dir / "sits_bert_pretrained.pt"
    torch.save({"model_state_dict": model.state_dict(), "epoch": config.pretraining.epochs}, final_path)
    stats_path = output_dir / "normalization_stats.json"
    if hasattr(dataset, "stats"):
        stats_path.write_text(json.dumps(dataset.stats, indent=2), encoding="utf-8")
    print("PRETRAIN COMPLETE. Download: sits_bert_pretrained.pt")
    return losses
