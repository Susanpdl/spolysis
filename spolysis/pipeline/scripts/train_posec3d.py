"""
Fine-tune PoseC3D on THETIS for tennis stroke and fault classification.

Two separate models are trained:
  1. Stroke model (4 classes): forehand, backhand, serve, volley
  2. Fault model  (8 classes): weak labels from beginner/expert joint angle deltas

Input data format (annotation pickle per MMAction2 convention):
  A list of dicts, one per clip:
  {
    "keypoint":       np.ndarray  (M, T, V, 2)  - x, y normalized [0, 1]
    "keypoint_score": np.ndarray  (M, T, V)      - confidence
    "total_frames":   int
    "label":          int          - class index
    "filename":       str          - for logging
  }
  where M=1 (single player), T=clip length, V=17 (COCO joints).

Preprocessing THETIS clips before running this script:
  1. python data/scripts/preprocess_thetis.py  (extract RTMPose-x keypoints)
  2. python data/scripts/build_thetis_annotations.py  (produce .pkl annotation files)
  See data/scripts/ for those tools.

Usage:
  # Stroke model
  python -m pipeline.scripts.train_posec3d \\
    --annotations data/thetis/stroke_annotations.pkl \\
    --task stroke \\
    --pretrained pipeline/weights/posec3d_ntu60_xsub.pth \\
    --output pipeline/weights/posec3d_stroke.pth

  # Fault model
  python -m pipeline.scripts.train_posec3d \\
    --annotations data/thetis/fault_annotations.pkl \\
    --task fault \\
    --pretrained pipeline/weights/posec3d_ntu60_xsub.pth \\
    --output pipeline/weights/posec3d_fault.pth
"""
from __future__ import annotations

import argparse
import pickle
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from pipeline.models.posec3d import (
    ALL_FAULTS,
    STROKE_LABELS,
    _BACKBONE_CFG,
    _HEAD_IN_CHANNELS,
    generate_pseudo_heatmap,
)

TASKS = {
    "stroke": STROKE_LABELS,
    "fault": ALL_FAULTS,
}

# PoseC3D clip parameters
CLIP_LEN = 48          # temporal window fed to the 3D CNN
HEATMAP_SIZE = (56, 56)
SIGMA = 0.6


class SkeletonDataset(Dataset):
    """
    Loads MMAction2-format skeleton annotations and generates pseudo-heatmap volumes.
    """

    def __init__(self, annotations: list[dict], num_classes: int, augment: bool = True) -> None:
        self.samples = annotations
        self.num_classes = num_classes
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        s = self.samples[idx]

        # (M, T, V, 2) -> take first person -> (T, V, 2)
        kp_xy = np.array(s["keypoint"][0], dtype=np.float32)
        scores = np.array(s["keypoint_score"][0], dtype=np.float32)  # (T, V)
        label = int(s["label"])
        T = kp_xy.shape[0]

        # --- Temporal sampling to CLIP_LEN ---
        if T >= CLIP_LEN:
            # Uniform sampling with optional random offset (augmentation)
            if self.augment:
                start = random.randint(0, T - CLIP_LEN)
            else:
                start = (T - CLIP_LEN) // 2
            kp_xy = kp_xy[start: start + CLIP_LEN]
            scores = scores[start: start + CLIP_LEN]
        else:
            # Pad with zeros at the end
            pad_len = CLIP_LEN - T
            kp_xy = np.concatenate([kp_xy, np.zeros((pad_len, 17, 2), dtype=np.float32)], axis=0)
            scores = np.concatenate([scores, np.zeros((pad_len, 17), dtype=np.float32)], axis=0)

        # --- Optional augmentation: horizontal flip ---
        if self.augment and random.random() < 0.5:
            kp_xy = kp_xy.copy()
            kp_xy[..., 0] = 1.0 - kp_xy[..., 0]
            # Swap left/right joint pairs for COCO-17
            SWAP_PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
            for l, r in SWAP_PAIRS:
                kp_xy[:, [l, r]] = kp_xy[:, [r, l]]
                scores[:, [l, r]] = scores[:, [r, l]]

        heatmaps = generate_pseudo_heatmap(kp_xy, scores, heatmap_size=HEATMAP_SIZE, sigma=SIGMA)
        # (17, CLIP_LEN, 56, 56)

        x = torch.from_numpy(heatmaps)
        y = torch.tensor(label, dtype=torch.long)
        return x, y


def _build_model(num_classes: int) -> nn.Module:
    from mmaction.registry import MODELS

    cfg = dict(
        type="Recognizer3D",
        backbone=_BACKBONE_CFG,
        cls_head=dict(
            type="I3DHead",
            in_channels=_HEAD_IN_CHANNELS,
            num_classes=num_classes,
            spatial_type="avg",
            dropout_ratio=0.5,
        ),
        data_preprocessor=dict(
            type="ActionDataPreprocessor",
            mean=[0.0],
            std=[1.0],
        ),
    )
    return MODELS.build(cfg)


def _load_pretrained(model: nn.Module, pretrained_path: str) -> None:
    """Load NTU RGB+D pretrained weights, skipping the classification head."""
    checkpoint = torch.load(pretrained_path, map_location="cpu", weights_only=True)
    state_dict = checkpoint.get("state_dict", checkpoint)

    # Drop cls_head weights - different num_classes in pretrained vs fine-tune target
    state_dict = {k: v for k, v in state_dict.items() if not k.startswith("cls_head")}

    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    print(f"Pretrained weights loaded. Missing: {len(missing)}, Unexpected: {len(unexpected)}")


def train(
    annotations_path: str,
    task: str,
    output_path: str,
    pretrained_path: str | None = None,
    epochs: int = 30,
    lr: float = 1e-4,
    batch_size: int = 8,
    val_split: float = 0.15,
) -> None:
    labels = TASKS[task]
    num_classes = len(labels)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Task: {task} ({num_classes} classes)  Device: {device}")

    with open(annotations_path, "rb") as f:
        all_samples = pickle.load(f)
    print(f"Loaded {len(all_samples)} samples from {annotations_path}")

    random.shuffle(all_samples)
    n_val = max(1, int(len(all_samples) * val_split))
    train_samples = all_samples[n_val:]
    val_samples = all_samples[:n_val]

    train_ds = SkeletonDataset(train_samples, num_classes, augment=True)
    val_ds = SkeletonDataset(val_samples, num_classes, augment=False)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, num_workers=4)

    model = _build_model(num_classes).to(device)

    if pretrained_path:
        _load_pretrained(model, pretrained_path)
    else:
        print("No pretrained weights - training from scratch (not recommended)")

    # Fine-tune: lower LR on backbone, full LR on head
    backbone_params = list(model.backbone.parameters())
    head_params = list(model.cls_head.parameters())
    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": lr * 0.1},
        {"params": head_params,    "lr": lr},
    ], weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = correct = total = 0

        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            # Call backbone + cls_head directly to avoid MMAction2 data dict requirements
            feats = model.backbone(x)
            logits = model.cls_head(feats)
            loss = criterion(logits, y)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            correct += (logits.argmax(1) == y).sum().item()
            total += len(y)

        scheduler.step()

        model.eval()
        val_correct = val_total = 0
        with torch.no_grad():
            for x, y in val_loader:
                x = x.to(device)
                feats = model.backbone(x)
                logits = model.cls_head(feats)
                val_correct += (logits.argmax(1) == y.to(device)).sum().item()
                val_total += len(y)

        train_acc = correct / total if total else 0.0
        val_acc = val_correct / val_total if val_total else 0.0
        print(
            f"Epoch {epoch:3d}/{epochs} | loss={total_loss/len(train_loader):.4f} "
            f"| train={train_acc:.3f} | val={val_acc:.3f}"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "epoch": epoch,
                    "val_acc": val_acc,
                    "task": task,
                    "labels": labels,
                    "num_classes": num_classes,
                },
                output_path,
            )
            print(f"  -> checkpoint saved (val_acc={val_acc:.3f})")

    print(f"Done. Best val_acc: {best_val_acc:.3f}  Checkpoint: {output_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", required=True, help="Path to annotation .pkl file")
    ap.add_argument("--task", required=True, choices=["stroke", "fault"])
    ap.add_argument("--output", required=True, help="Output checkpoint .pth path")
    ap.add_argument("--pretrained", help="NTU RGB+D pretrained PoseC3D weights (.pth)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch-size", type=int, default=8)
    args = ap.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    train(
        annotations_path=args.annotations,
        task=args.task,
        output_path=args.output,
        pretrained_path=args.pretrained,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
    )
