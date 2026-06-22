"""Finetuning loop for FarmTrust SITS-BERT on Kaggle."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
from torch.optim import AdamW
from torch.utils.data import DataLoader, random_split

from .config import FarmTrustSITSConfig, config as default_config
from .dataset import FarmTrustDataset
from .model import SITSBertFinetune


def finetune(config: FarmTrustSITSConfig = default_config) -> dict[str, float]:
    torch.manual_seed(config.seed)
    device = _training_device()
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = FarmTrustDataset(
        config.dataset_path,
        mode="finetuning",
        normalization_stats_path=config.normalization_stats_path,
        seed=config.seed,
    )
    val_size = max(1, int(0.2 * len(dataset))) if len(dataset) > 1 else 1
    train_size = max(1, len(dataset) - val_size)
    if train_size + val_size > len(dataset):
        train_size, val_size = len(dataset), len(dataset)
        train_dataset = val_dataset = dataset
    else:
        train_dataset, val_dataset = random_split(
            dataset,
            [train_size, val_size],
            generator=torch.Generator().manual_seed(config.seed),
        )

    train_loader = DataLoader(train_dataset, batch_size=config.finetuning.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config.finetuning.batch_size)
    model = SITSBertFinetune(config).to(device)
    pretrained_path = Path(config.finetuning.pretrained_weights)
    if pretrained_path.exists():
        checkpoint = torch.load(pretrained_path, map_location=device)
        model.load_state_dict(checkpoint.get("model_state_dict", checkpoint), strict=False)

    optimizer = AdamW(model.parameters(), lr=config.finetuning.learning_rate)
    best_precision = -1.0
    best_metrics: dict[str, float] = {}
    stale_epochs = 0

    for epoch in range(1, config.finetuning.epochs + 1):
        freeze = epoch <= config.finetuning.freeze_encoder_epochs
        for parameter in model.encoder.parameters():
            parameter.requires_grad = not freeze
        model.train()
        for batch in train_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            output = model(**batch)
            output["loss"].backward()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)

        metrics, y_true, y_pred, y_prob = _evaluate(model, val_loader, device)
        print(f"epoch={epoch} metrics={metrics}")
        if metrics["precision_active"] > best_precision:
            best_precision = metrics["precision_active"]
            best_metrics = metrics
            stale_epochs = 0
            torch.save({"model_state_dict": model.state_dict(), "epoch": epoch, **metrics}, output_dir / "sits_bert_best.pt")
        else:
            stale_epochs += 1
            if stale_epochs >= config.finetuning.early_stopping_patience:
                break

    threshold_policy = _sweep_thresholds(y_true, y_prob, config)
    final_path = output_dir / "sits_bert_finetuned.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "threshold_policy": threshold_policy,
            **best_metrics,
        },
        final_path,
    )
    print(classification_report(y_true, y_pred, labels=[0, 1, 2, 3], target_names=["active", "bare", "sparse", "uncertain"], zero_division=0))
    print(confusion_matrix(y_true, y_pred, labels=[0, 1, 2, 3]))
    if best_metrics.get("precision_active", 0.0) < 0.88 or best_metrics.get("false_active_rate", 1.0) > 0.06:
        print("\033[91mWARNING: active precision or false-active constraint not met\033[0m")
    print("FINETUNE COMPLETE. Download: sits_bert_finetuned.pt")
    return best_metrics


def _evaluate(model: SITSBertFinetune, loader: DataLoader, device: torch.device) -> tuple[dict[str, float], np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    y_true_parts: list[np.ndarray] = []
    y_pred_parts: list[np.ndarray] = []
    y_prob_parts: list[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            labels = batch["labels"].to(device)
            logits = model(
                batch["input_ids"].to(device),
                batch["attention_mask"].to(device),
                batch["doy"].to(device),
            )
            probs = torch.softmax(logits, dim=-1)
            mask = labels != -1
            y_true_parts.append(labels[mask].cpu().numpy())
            y_pred_parts.append(probs.argmax(dim=-1)[mask].cpu().numpy())
            y_prob_parts.append(probs[mask].cpu().numpy())
    y_true = np.concatenate(y_true_parts) if y_true_parts else np.asarray([], dtype=np.int64)
    y_pred = np.concatenate(y_pred_parts) if y_pred_parts else np.asarray([], dtype=np.int64)
    y_prob = np.concatenate(y_prob_parts) if y_prob_parts else np.zeros((0, 4), dtype=np.float32)
    metrics = {
        "precision_active": float(precision_score(y_true, y_pred, labels=[0], average="macro", zero_division=0)),
        "recall_active": float(recall_score(y_true, y_pred, labels=[0], average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "false_active_rate": _false_active_rate(y_true, y_pred),
    }
    return metrics, y_true, y_pred, y_prob


def _false_active_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    negatives = y_true != 0
    if negatives.sum() == 0:
        return 0.0
    return float(((y_pred == 0) & negatives).sum() / negatives.sum())


def _training_device() -> torch.device:
    if not torch.cuda.is_available():
        return torch.device("cpu")
    major, _ = torch.cuda.get_device_capability(0)
    if major < 7:
        print("CUDA device is not compatible with this PyTorch wheel; using CPU.")
        return torch.device("cpu")
    return torch.device("cuda")


def _sweep_thresholds(y_true: np.ndarray, y_prob: np.ndarray, config: FarmTrustSITSConfig) -> dict[str, float]:
    best = {
        "confirmed_active": config.finetuning.confirmed_active_threshold,
        "possible_active": config.finetuning.possible_active_threshold,
    }
    for threshold in np.arange(0.40, 0.91, 0.01):
        y_pred = np.where(y_prob[:, 0] >= threshold, 0, np.argmax(y_prob, axis=1))
        precision = precision_score(y_true, y_pred, labels=[0], average="macro", zero_division=0)
        if precision >= config.evaluation.primary_constraint:
            best["confirmed_active"] = float(threshold)
            break
    return best
