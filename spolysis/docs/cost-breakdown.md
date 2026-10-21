# Cost measurement for the 3D analysis pipeline

The current runtime has one analysis path and deterministic coaching text.
This document describes what to measure before choosing pricing or infrastructure changes.
It does not assert a measured cost per analysis, a subscription price, or a profitability forecast.

## Cost components

| Component | Measurement needed |
|---|---|
| GPU analysis | Billed container duration, GPU type, cold starts, failed attempts, and retries |
| API and workflow worker | Actual running instances and monthly invoices |
| Workflow orchestration | Usage reported by the configured Temporal namespace |
| Database and authentication | Actual plan, storage, and usage |
| Storage | Raw uploads, image observations, overlays, skeletons, retention time, and object operations |
| Cache | Request volume and actual plan |
| App distribution | Build usage and chosen distribution accounts |

The CPU workflow worker and the GPU analysis container are separate processes.
Do not model a continuously running CPU worker as a continuously billed GPU.
The pipeline reconstructs a selected swing window, while frame extraction and image observations still depend on the full uploaded clip.
Clip duration therefore matters even when the final result covers a single swing.

## Proposed measurement approach

Group representative runs by stroke, clip length, image size, and whether a new container was started.
Include rejected uploads and retried attempts rather than counting only successful GPU runs.
Record median and tail latency alongside the total billable work.
Allocate fixed monthly service costs separately from per-job costs.

A useful calculation is total variable spend divided by the number of successfully delivered analyses over the same period.
Retention assumptions must include all persisted artifacts, including unsuccessful job artifacts and abandoned uploads.
Any pricing decision also needs the applicable distribution fees, refund behavior, and actual usage distribution.
No dollar estimate or margin target is selected here.

## Decisions still open

Pricing, retention, quotas, and orchestration changes are described as alternatives in [v2.md](../v2.md).
Measure the current pipeline before choosing warm capacity, a different GPU, or stage-level retry checkpoints.
Use current provider invoices and pricing pages when making a spending decision.
