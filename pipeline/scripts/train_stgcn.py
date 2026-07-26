"""
Train ST-GCN on the professor's labeled tennis dataset.

Dataset format (JSONL, one entry per clip):
  {"video_path": "...", "stroke_type": "forehand", "fault_label": "late_contact", "keypoints": [...]}

where keypoints is a list of (T, 17, 3) arrays (x, y, conf).

Usage:
  python -m pipeline.scripts.train_stgcn --data /data/labels/ --output /tmp/stgcn_checkpoint.pt
"""
from __future__ import annotations
import argparse
import json
import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pipeline.models.stgcn import STGCN

STROKE_LABELS = ["forehand", "backhand", "serve", "volley"]
FAULT_LABELS = [
    "late_contact", "open_stance", "low_follow_through", "arm_only",
    "no_hip_rotation", "grip_issue", "no_trophy_position", "low_toss",
]
TARGET_LEN = 90


class TennisDataset(Dataset):
    def __init__(self, data_dir: str):
        self.samples: list[dict] = []
        for fname in os.listdir(data_dir):
            if not fname.endswith(".jsonl"):
                continue
            with open(os.path.join(data_dir, fname)) as f:
                for line in f:
                    entry = json.loads(line.strip())
                    self.samples.append(entry)
        print(f"Loaded {len(self.samples)} samples from {data_dir}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        s = self.samples[idx]
        kps = np.array(s["keypoints"], dtype=np.float32)  # (T, 17, 3)
        T = kps.shape[0]

        # Pad/truncate to TARGET_LEN
        if T < TARGET_LEN:
            pad = np.zeros((TARGET_LEN - T, 17, 3), dtype=np.float32)
            kps = np.concatenate([kps, pad], axis=0)
        else:
            kps = kps[:TARGET_LEN]

        # (TARGET_LEN, 17, 3) -> (3, TARGET_LEN, 17, 1)
        x = torch.from_numpy(kps).permute(2, 0, 1).unsqueeze(-1)

        stroke_label = torch.tensor(STROKE_LABELS.index(s["stroke_type"]), dtype=torch.long)
        fault = s.get("fault_label")
        fault_label = torch.tensor(FAULT_LABELS.index(fault) if fault in FAULT_LABELS else -1, dtype=torch.long)

        return x, stroke_label, fault_label


def train(data_dir: str, output_path: str, epochs: int = 50, lr: float = 1e-3, batch_size: int = 16):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on {device}")

    dataset = TennisDataset(data_dir)
    n_train = int(len(dataset) * 0.85)
    n_val = len(dataset) - n_train
    train_ds, val_ds = torch.utils.data.random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=batch_size, num_workers=2)

    num_stroke = len(STROKE_LABELS)
    num_fault = len(FAULT_LABELS)
    model = STGCN(in_channels=3, num_class=num_stroke + num_fault, num_point=17).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss(ignore_index=-1)

    best_val_acc = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss, correct, total = 0.0, 0, 0

        for x, stroke_lbl, fault_lbl in train_loader:
            x = x.to(device)
            stroke_lbl = stroke_lbl.to(device)
            fault_lbl = fault_lbl.to(device)

            logits = model(x)
            stroke_logits = logits[:, :num_stroke]
            fault_logits = logits[:, num_stroke:]

            loss = criterion(stroke_logits, stroke_lbl)
            fault_mask = fault_lbl >= 0
            if fault_mask.any():
                loss += 0.5 * criterion(fault_logits[fault_mask], fault_lbl[fault_mask])

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item()
            correct += (stroke_logits.argmax(1) == stroke_lbl).sum().item()
            total += len(stroke_lbl)

        scheduler.step()

        # Validation
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for x, stroke_lbl, _ in val_loader:
                logits = model(x.to(device))
                val_correct += (logits[:, :num_stroke].argmax(1) == stroke_lbl.to(device)).sum().item()
                val_total += len(stroke_lbl)

        train_acc = correct / total if total > 0 else 0
        val_acc = val_correct / val_total if val_total > 0 else 0
        print(f"Epoch {epoch:3d} | loss={total_loss/len(train_loader):.4f} | train_acc={train_acc:.3f} | val_acc={val_acc:.3f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "state_dict": model.state_dict(),
                "epoch": epoch,
                "val_acc": val_acc,
                "num_stroke_classes": num_stroke,
                "num_fault_classes": num_fault,
                "stroke_labels": STROKE_LABELS,
                "fault_labels": FAULT_LABELS,
            }, output_path)
            print(f"  -> Saved checkpoint (val_acc={val_acc:.3f})")

    print(f"Training complete. Best val_acc: {best_val_acc:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Directory containing .jsonl label files")
    parser.add_argument("--output", required=True, help="Output checkpoint path (.pt)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    train(args.data, args.output, args.epochs, args.lr, args.batch_size)
