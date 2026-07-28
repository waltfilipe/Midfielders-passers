# Impact Pass Composite Study (offline)

Base: **308,469** completed midfielder passes (European leagues).

## Feature summary

- xP mean / P90: 0.3502 / 0.6917
- Residual mean / P90: 0.0066 / 0.1511
- Progress ratio mean: 0.0584 (forward share 52.1%)
- Corr(xP, residual): 0.5267
- Corr(xP, progress): 0.6445

## Data-driven weights (robust z per distance band)

- PCA: xP 0.314 · residual 0.513 · progress 0.173
- Inverse variance: xP 0.339 · residual 0.176 · progress 0.485

## Current baseline

- `is_threat_m4` flag rate: **7.21%**
  (residual > P90 band AND xP ≥ P75 band)

## Top 10 variants (flag rate 2–12%, ranked by separation score)

| Variant | Flag % | Jaccard vs M4 | ρ player rates | d(xP) | d(res) | d(prog) |
|---|---:|---:|---:|---:|---:|---:|
| global_z · Value+surprise (45/45/10) · P97 global | 3.0 | 0.3561 | 0.6498 | 2.822 | 3.993 | 1.784 |
| global_z · PCA band (0.31/0.51/0.17) · P97 global | 3.0 | 0.3683 | 0.6459 | 2.726 | 4.09 | 1.775 |
| global_z · Residual-heavy (30/50/20) · P97 global | 3.0 | 0.3686 | 0.6391 | 2.726 | 4.085 | 1.783 |
| global_z · xP+residual only (50/50/0) · P97 global | 3.0 | 0.3552 | 0.6549 | 2.808 | 4.014 | 1.754 |
| global_z · Progress-heavy (35/35/30) · P97 global | 3.0 | 0.3558 | 0.6299 | 2.844 | 3.925 | 1.85 |
| global_z · Equal (⅓ each) · P97 global | 3.0 | 0.3551 | 0.6224 | 2.848 | 3.91 | 1.86 |
| global_z · Balanced (45/35/20) · P97 global | 3.0 | 0.3449 | 0.6355 | 2.901 | 3.865 | 1.833 |
| global_z · xP-heavy (50/35/15) · P97 global | 3.0 | 0.3396 | 0.6384 | 2.931 | 3.828 | 1.826 |
| band_z · Value+surprise (45/45/10) · P97 per-band | 3.0 | 0.4067 | 0.6719 | 2.702 | 3.912 | 1.776 |
| global_z · Value+surprise (45/45/10) · P97 per-band | 3.0 | 0.4048 | 0.6689 | 2.699 | 3.915 | 1.775 |

## Ablation (progress contribution)

| Variant | Flag % | Jaccard vs M4 | d(prog) |
|---|---:|---:|---:|
| ablation · Equal (⅓ each) · P90 band | 10.0 | 0.6913 | 1.762 |
| ablation · Balanced (45/35/20) · P90 band | 10.0 | 0.7031 | 1.679 |
| ablation · xP+residual only (50/50/0) · P90 band | 10.0 | 0.7112 | 1.52 |

## Recommended starting points

- **global_z · Value+surprise (45/45/10) · P97 global**: flag 3.0%, Jaccard 0.3561, player ρ 0.6498
- **band_z · Value+surprise (45/45/10) · P97 per-band**: flag 3.0%, Jaccard 0.4067, player ρ 0.6719

## Interpretation notes

- **band_z** normalisation is preferred: short/long passes have different xP/residual scales.
- **Balanced (45/35/20)** or **PCA-derived** weights give interpretable trade-offs.
- Progress adds separation (higher Cohen's d) but lowers Jaccard vs `is_threat_m4` (expected — M4 ignores progress).
- Target operational flag rate: **~5–8%** for a rare 'impact' event label.
