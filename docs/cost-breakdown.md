# Spolysis - Infrastructure Cost Breakdown

This document covers the full cost structure of running Spolysis in production: one-time setup costs, fixed monthly overhead, and per-analysis variable costs across both tiers.
All prices are as of mid-2026 and sourced from each vendor's public pricing page.

---

## One-time costs

| Item | Cost | Notes |
|---|---|---|
| Apple Developer Account | $99/year | Required to distribute iOS app on App Store |
| Google Play Developer Account | $25 one-time | Required to distribute Android app on Play Store |

---

## Fixed monthly costs (independent of user volume)

These are the costs you pay even at zero users.

| Service | Free tier | Paid tier | Notes |
|---|---|---|---|
| **Fly.io** (FastAPI backend) | - | ~$5-8/month | 1 shared CPU, 512 MB RAM, always-on. Handles auth, job creation, webhooks. |
| **Supabase** (database + auth) | Free up to 500 MB DB, 50K monthly active users | $25/month (Pro) | Free tier is sufficient until ~2K monthly active users. |
| **Upstash Redis** (cache + rate limiting) | 10K requests/day free | $0.20 per 100K requests | At low volume this is effectively free. |
| **Temporal Cloud** (workflow orchestration) | 10M state transitions free/month | $25 per additional million | 10M transitions is roughly 50K+ pipeline runs. Free tier covers early scale. |
| **Expo EAS** (mobile CI/CD + OTA updates) | Free tier (limited builds) | $29/month (Production plan, 30 builds/month) | Needed for App Store submission and OTA deploys. |
| **Cloudflare R2** (storage) | Free up to 10 GB storage | $0.015/GB-month above 10 GB | Egress is always free. 1000 analyses ≈ 50-100 GB = ~$0.60-$1.35/month at scale. |
| **RevenueCat** (subscriptions) | Free up to $2,500 MTR | 1% of MTR above $2,500 | Handles iOS + Android subscription state, receipts, entitlements. |

**Estimated fixed baseline: ~$35-70/month** at early launch, mostly Fly.io + Supabase Pro.
Supabase free tier reduces this to ~$10-15/month until you hit real user volume.

---

## Variable costs - per analysis

### 2D free tier (RTMPose-x + PoseC3D + Claude Haiku)

| Step | Service | Estimated cost |
|---|---|---|
| GPU compute (Modal A10G) | Modal | ~$0.045-0.065 |
| Claude Haiku (coaching text) | Anthropic | ~$0.0004 |
| R2 storage (amortized 6 months) | Cloudflare | ~$0.005 |
| **Total per free analysis** | | **~$0.05-0.07** |

**GPU time breakdown (free tier, 5-minute video):**
- Frame extraction at 30 fps → 9,000 frames
- RTMPose-x on A10G processes ~80-120 fps → 75-112 seconds
- PoseC3D classification: ~15-30 seconds
- Overhead (download, upload, quality gate): ~30 seconds
- **Total Modal wall time: ~2-3 minutes = ~$0.037-0.055 at $0.000306/second (A10G)**

### 3D premium tier (adds MotionBERT/PoseMamba + DTW + IK + rendering)

| Step | Service | Estimated cost |
|---|---|---|
| GPU compute (Modal A10G) | Modal | ~$0.15-0.25 |
| Claude Haiku (coaching text) | Anthropic | ~$0.001 |
| R2 storage - result video + artifacts (amortized) | Cloudflare | ~$0.02 |
| **Total per premium analysis** | | **~$0.17-0.27** |

**GPU time breakdown (premium tier, 5-minute video):**
- Shared front half (same as free tier): ~2-3 minutes
- MotionBERT/PoseMamba 3D lifting: ~3-5 minutes
- SmoothNet, DTW, IK correction: ~30-60 seconds
- OpenCV overlay + ffmpeg H.264 encode: ~1-2 minutes
- **Total Modal wall time: ~7-11 minutes = ~$0.13-0.20 at A10G rate**

This is comfortably within the $0.15-$0.50 target stated in the architecture.
The upper bound assumes a full 5-minute video with all 3D stages running.
Most real tennis clips are 30-90 seconds, which brings cost to ~$0.05-0.09.

---

## Unit economics at different price points

### Subscription model

| Plan | Price | Premium analyses/month at breakeven | Realistic usage (est.) | Margin |
|---|---|---|---|---|
| Basic | $4.99/month | 2D only, no limit (cost ~$0.06 each) | 5-20 per month | ~$3.60-$3.80 gross |
| Premium | $9.99/month | ~43 3D analyses at $0.23 each | 10-30 per month | ~$2.30-$7.30 gross |
| Premium | $14.99/month | ~65 3D analyses at $0.23 each | 10-30 per month | ~$8.20-$12.30 gross |

**Recommendation: price the premium subscription at $14.99/month.**
At the realistic usage estimate of 10-30 analyses per month, that is a 36-55% gross margin on compute before platform fees (Apple/Google take 30% of subscription revenue in year 1, then 15% after).
After App Store cut: $14.99 × 0.70 = $10.49 net, minus ~$3-7 compute = $3-7.50 profit per subscriber per month.

### Pay-per-analysis

| Tier | Cost to produce | Suggested price | Margin |
|---|---|---|---|
| 2D free analysis | ~$0.06 | $0.99 | ~93% |
| 3D premium analysis | ~$0.23 | $1.99 | ~88% |

Pay-per-analysis is positioned as the entry product for users who do not want to commit to a subscription.
After App Store cut on $1.99: $1.39 net minus $0.23 cost = $1.16 profit.

---

## Cost at scale (monthly)

| Monthly active users | Free analyses/month | Premium analyses/month | Variable GPU cost | Fixed infra | Total monthly |
|---|---|---|---|---|---|
| 100 users | 500 | 200 | ~$75 | ~$35 | ~$110 |
| 1,000 users | 5,000 | 2,000 | ~$750 | ~$60 | ~$810 |
| 10,000 users | 50,000 | 20,000 | ~$7,500 | ~$150 | ~$7,650 |
| 100,000 users | 500,000 | 200,000 | ~$75,000 | ~$500 | ~$75,500 |

Revenue at 10,000 users (assuming 20% premium at $14.99/month, 80% free):
- 2,000 premium subscribers × $14.99 × 0.70 (after App Store) = $20,986/month
- Variable cost: ~$7,650/month
- **Gross profit: ~$13,336/month at 10,000 MAU**

**The model is profitable well before 1,000 MAU.**
Even at 100 MAU with 20% premium conversion: 20 × $14.99 × 0.70 = $210 revenue, $110 costs = $100 margin.
The business is cash-flow positive from the first paying subscriber.

---

## Cold-start and Modal optimization

Modal bills from the moment a container starts to when it finishes.
Without optimization, each analysis would cold-start a new GPU container (RTMPose-x + mmcv CUDA ops loading takes ~90-120 seconds) before doing any real work.

**Mitigations in place:**
- `min_containers=1` on the Temporal worker keeps one container always warm (adds ~$0.000306/second × 86,400 seconds = ~$26/month for one always-on A10G).
  This is justified at launch when average analysis latency is a product-defining metric.
  At scale, swap to `scaler` policy with a minimum of 0 and rely on queue depth to spin up.
- The Temporal worker architecture also means the GPU container stays alive between jobs as long as jobs are arriving, dramatically reducing cold starts in practice.
- Model weights are baked into the Modal image (wget at image build time), not downloaded at runtime.

**Alternative at scale:** Move to Modal's `keep_warm` scaler tied to queue depth.
At 10,000 MAU with steady traffic you would have enough continuous volume that cold starts are rare with no always-on cost.

---

## Summary

| Scenario | Monthly cost | Monthly revenue (est.) | Margin |
|---|---|---|---|
| Pre-launch (testing only) | ~$35-70 | $0 | - |
| 100 MAU, 20% premium | ~$110 | ~$210 | ~48% |
| 1,000 MAU, 20% premium | ~$810 | ~$2,099 | ~61% |
| 10,000 MAU, 20% premium | ~$7,650 | ~$20,986 | ~64% |

The dominant cost is Modal GPU compute, not infrastructure.
The infrastructure overhead is low and scales slowly.
The per-analysis GPU cost is the lever to optimize - primarily by reducing video length accepted (a 60-second clip is 10% the cost of a 5-minute clip) and by benchmarking whether T4 or A100 gives better cost/throughput for the specific MMPose + MMAction2 workload.
