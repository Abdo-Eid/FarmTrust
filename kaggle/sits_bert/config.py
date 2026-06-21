"""Dataclass configuration for FarmTrust SITS-BERT Kaggle runs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    input_dim: int = 10
    hidden_size: int = 256
    num_layers: int = 3
    num_attention_heads: int = 8
    intermediate_size: int = 512
    hidden_dropout_prob: float = 0.1
    attention_dropout_prob: float = 0.1
    max_position_embeddings: int = 64
    num_classes: int = 4


@dataclass
class PretrainingConfig:
    mask_prob: float = 0.30
    learning_rate: float = 0.0001
    batch_size: int = 256
    epochs: int = 80
    warmup_steps: int = 5000
    weight_decay: float = 0.01


@dataclass
class FinetuningConfig:
    pretrained_weights: str = "sits_bert_pretrained.pt"
    learning_rate: float = 0.00005
    batch_size: int = 64
    epochs: int = 50
    early_stopping_patience: int = 10
    freeze_encoder_epochs: int = 5
    class_weights: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])
    confirmed_active_threshold: float = 0.80
    possible_active_threshold: float = 0.65
    label_smoothing: float = 0.1


@dataclass
class EvaluationConfig:
    primary_metric: str = "precision_class_active"
    primary_constraint: float = 0.90
    hard_constraint_false_active_rate: float = 0.05


@dataclass
class FarmTrustSITSConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    pretraining: PretrainingConfig = field(default_factory=PretrainingConfig)
    finetuning: FinetuningConfig = field(default_factory=FinetuningConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    seed: int = 42
    dataset_path: str = "/kaggle/input/farmtrust-sits/sits_dataset.npz"
    normalization_stats_path: str = "/kaggle/working/normalization_stats.json"
    output_dir: str = "/kaggle/working"


config = FarmTrustSITSConfig()
