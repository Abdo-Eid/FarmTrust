"""SITS-BERT-style Transformer models for FarmTrust cycle sequences."""

from __future__ import annotations

import math

import torch
from torch import nn

from kaggle.sits_bert.config import FarmTrustSITSConfig, config as default_config


class SITSBertEncoder(nn.Module):
    def __init__(self, config: FarmTrustSITSConfig = default_config) -> None:
        super().__init__()
        model_config = config.model
        self.hidden_size = model_config.hidden_size
        self.input_projection = nn.Linear(model_config.input_dim, model_config.hidden_size)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=model_config.hidden_size,
            nhead=model_config.num_attention_heads,
            dim_feedforward=model_config.intermediate_size,
            dropout=model_config.hidden_dropout_prob,
            activation="gelu",
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=model_config.num_layers)
        self.dropout = nn.Dropout(model_config.hidden_dropout_prob)
        self.last_attention_weights: torch.Tensor | None = None

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, doy: torch.Tensor) -> torch.Tensor:
        projected = self.input_projection(input_ids)
        encoded = projected + self._doy_encoding(doy, projected.dtype, projected.device)
        encoded = self.dropout(encoded)
        padding_mask = ~attention_mask.bool()
        return self.encoder(encoded, src_key_padding_mask=padding_mask)

    def _doy_encoding(self, doy: torch.Tensor, dtype: torch.dtype, device: torch.device) -> torch.Tensor:
        doy = doy.to(device=device, dtype=dtype).unsqueeze(-1) / 365.0
        half = self.hidden_size // 2
        frequencies = torch.exp(
            torch.arange(half, device=device, dtype=dtype) * (-math.log(10_000.0) / max(half - 1, 1))
        )
        angles = 2.0 * math.pi * doy * frequencies
        encoding = torch.cat([torch.sin(angles), torch.cos(angles)], dim=-1)
        if encoding.shape[-1] < self.hidden_size:
            encoding = torch.nn.functional.pad(encoding, (0, self.hidden_size - encoding.shape[-1]))
        return encoding

    def get_attention_weights(self) -> torch.Tensor | None:
        return self.last_attention_weights


class SITSBertPretraining(nn.Module):
    def __init__(self, config: FarmTrustSITSConfig = default_config) -> None:
        super().__init__()
        self.encoder = SITSBertEncoder(config)
        self.reconstruction_head = nn.Linear(config.model.hidden_size, config.model.input_dim)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        doy: torch.Tensor,
        mask_positions: torch.Tensor | None = None,
        reconstruction_target: torch.Tensor | None = None,
    ) -> torch.Tensor | dict[str, torch.Tensor]:
        hidden = self.encoder(input_ids, attention_mask, doy)
        reconstruction = self.reconstruction_head(hidden)
        if mask_positions is None or reconstruction_target is None:
            return reconstruction
        if mask_positions.any():
            loss = nn.functional.mse_loss(reconstruction[mask_positions], reconstruction_target[mask_positions])
        else:
            loss = reconstruction.sum() * 0.0
        return {"loss": loss, "reconstruction": reconstruction}


class SITSBertFinetune(nn.Module):
    def __init__(self, config: FarmTrustSITSConfig = default_config) -> None:
        super().__init__()
        self.config = config
        self.encoder = SITSBertEncoder(config)
        self.classifier = nn.Linear(config.model.hidden_size, config.model.num_classes)
        weights = torch.tensor(config.finetuning.class_weights, dtype=torch.float32)
        self.register_buffer("class_weights", weights)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        doy: torch.Tensor | None = None,
        labels: torch.Tensor | None = None,
    ) -> torch.Tensor | dict[str, torch.Tensor]:
        if attention_mask is None:
            attention_mask = torch.ones(input_ids.shape[:2], device=input_ids.device, dtype=torch.bool)
        if doy is None:
            doy = torch.zeros(input_ids.shape[:2], device=input_ids.device, dtype=torch.long)
        hidden = self.encoder(input_ids, attention_mask, doy)
        logits = self.classifier(hidden)
        if labels is None:
            return logits
        loss = nn.functional.cross_entropy(
            logits.view(-1, logits.shape[-1]),
            labels.view(-1),
            weight=self.class_weights.to(logits.device),
            ignore_index=-1,
            label_smoothing=self.config.finetuning.label_smoothing,
        )
        return {"loss": loss, "logits": logits}

    def get_attention_weights(self) -> torch.Tensor | None:
        return self.encoder.get_attention_weights()
