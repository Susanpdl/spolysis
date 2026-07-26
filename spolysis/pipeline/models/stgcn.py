from __future__ import annotations
import torch
import torch.nn as nn
import numpy as np

# COCO 17-joint skeleton adjacency for ST-GCN
COCO_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),      # head
    (5, 6), (5, 7), (7, 9),               # left arm
    (6, 8), (8, 10),                      # right arm
    (5, 11), (6, 12), (11, 12),           # torso
    (11, 13), (13, 15),                   # left leg
    (12, 14), (14, 16),                   # right leg
]
NUM_JOINTS = 17


def _build_adjacency(num_joints: int, edges: list[tuple[int, int]]) -> torch.Tensor:
    A = torch.zeros(num_joints, num_joints)
    for i, j in edges:
        A[i, j] = 1
        A[j, i] = 1
    A += torch.eye(num_joints)
    # Normalize
    D = A.sum(dim=1, keepdim=True).clamp(min=1)
    return A / D


class GraphConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, A: torch.Tensor):
        super().__init__()
        self.register_buffer("A", A)
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        self.bn = nn.BatchNorm2d(out_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (N, C, T, V)
        N, C, T, V = x.shape
        # Graph convolution: x * A
        x = x.permute(0, 2, 1, 3)  # (N, T, C, V)
        x = torch.matmul(x, self.A)  # (N, T, C, V)
        x = x.permute(0, 2, 1, 3)  # (N, C, T, V)
        x = self.conv(x)
        return self.bn(x)


class STGCNBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, A: torch.Tensor,
                 temporal_kernel: int = 9, stride: int = 1, dropout: float = 0.5):
        super().__init__()
        self.gcn = GraphConv(in_channels, out_channels, A)
        pad = (temporal_kernel - 1) // 2
        self.tcn = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(),
            nn.Conv2d(out_channels, out_channels, kernel_size=(temporal_kernel, 1),
                      padding=(pad, 0), stride=(stride, 1)),
            nn.BatchNorm2d(out_channels),
            nn.Dropout(dropout),
        )
        self.residual = (
            nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels),
            ) if in_channels != out_channels or stride != 1
            else nn.Identity()
        )
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.relu(self.tcn(self.gcn(x)) + self.residual(x))


class STGCN(nn.Module):
    """
    ST-GCN for tennis stroke classification.
    Input: (N, C, T, V, M) where C=3 (x,y,conf), T=frames, V=17 joints, M=1 person.
    Output: (N, num_class) logits.
    """

    def __init__(self, in_channels: int = 3, num_class: int = 12, num_point: int = NUM_JOINTS,
                 dropout: float = 0.5):
        super().__init__()
        A = _build_adjacency(num_point, COCO_EDGES)
        self.register_buffer("A", A)

        self.data_bn = nn.BatchNorm1d(in_channels * num_point)

        self.layers = nn.ModuleList([
            STGCNBlock(in_channels, 64, A, dropout=dropout),
            STGCNBlock(64, 64, A, dropout=dropout),
            STGCNBlock(64, 64, A, dropout=dropout),
            STGCNBlock(64, 128, A, stride=2, dropout=dropout),
            STGCNBlock(128, 128, A, dropout=dropout),
            STGCNBlock(128, 128, A, dropout=dropout),
            STGCNBlock(128, 256, A, stride=2, dropout=dropout),
            STGCNBlock(256, 256, A, dropout=dropout),
            STGCNBlock(256, 256, A, dropout=dropout),
        ])

        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(256, num_class)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (N, C, T, V, M)
        N, C, T, V, M = x.shape
        x = x.permute(0, 4, 3, 1, 2).contiguous()  # (N, M, V, C, T)
        x = x.view(N * M, V * C, T)
        x = self.data_bn(x)
        x = x.view(N, M, V, C, T).permute(0, 1, 3, 4, 2).contiguous()
        x = x.view(N * M, C, T, V)

        for layer in self.layers:
            x = layer(x)

        x = self.pool(x)  # (N*M, 256, 1, 1)
        x = x.view(N, M, -1).mean(dim=1)  # (N, 256)
        x = self.drop(x)
        return self.fc(x)
