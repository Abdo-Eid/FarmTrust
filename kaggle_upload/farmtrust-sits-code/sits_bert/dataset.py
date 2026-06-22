"""Dataset utilities for FarmTrust SITS-BERT Kaggle training."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset


class FarmTrustDataset(Dataset):
    def __init__(
        self,
        npz_path: str | Path,
        *,
        mode: str = "finetuning",
        normalization_stats_path: str | Path | None = None,
        mask_prob: float = 0.30,
        seed: int = 42,
    ) -> None:
        if mode not in {"pretraining", "finetuning"}:
            raise ValueError("mode must be 'pretraining' or 'finetuning'")
        self.mode = mode
        self.mask_prob = float(mask_prob)
        self.rng = np.random.default_rng(seed)
        data = np.load(npz_path, allow_pickle=True)
        self.features = data["features"].astype(np.float32)
        self.attention_mask = data["attention_mask"].astype(bool)
        self.doy = data["doy"].astype(np.int64)
        self.labels = data["labels"].astype(np.int64)
        self.stats = self._load_stats(normalization_stats_path)

    def __len__(self) -> int:
        return int(self.features.shape[0])

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        original = self._normalize(self.features[index])
        attention_mask = self.attention_mask[index]
        item = {
            "input_ids": torch.from_numpy(original.copy()).float(),
            "attention_mask": torch.from_numpy(attention_mask.copy()).bool(),
            "doy": torch.from_numpy(self.doy[index].copy()).long(),
            "labels": torch.from_numpy(self.labels[index].copy()).long(),
        }
        if self.mode == "pretraining":
            real_positions = np.where(attention_mask)[0]
            mask_positions = np.zeros(attention_mask.shape[0], dtype=bool)
            if len(real_positions):
                sampled = self.rng.random(len(real_positions)) < self.mask_prob
                if not sampled.any():
                    sampled[self.rng.integers(0, len(real_positions))] = True
                mask_positions[real_positions[sampled]] = True
            masked = original.copy()
            masked[mask_positions] = 0.0
            item["input_ids"] = torch.from_numpy(masked).float()
            item["reconstruction_target"] = torch.from_numpy(original.copy()).float()
            item["mask_positions"] = torch.from_numpy(mask_positions).bool()
        return item

    def _load_stats(self, path: str | Path | None) -> dict[str, Any]:
        if path and Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
        flat = self.features[self.attention_mask]
        mean = flat.mean(axis=0)
        std = flat.std(axis=0)
        std = np.where(std < 1e-6, 1.0, std)
        return {"mean": mean.tolist(), "std": std.tolist()}

    def _normalize(self, features: np.ndarray) -> np.ndarray:
        mean = np.asarray(self.stats["mean"], dtype=np.float32)
        std = np.asarray(self.stats["std"], dtype=np.float32)
        std = np.where(std < 1e-6, 1.0, std)
        normalized = (np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0) - mean) / std
        return np.clip(np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0), -5.0, 5.0).astype(np.float32)
