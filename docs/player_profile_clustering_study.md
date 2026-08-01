# Player profile clustering study

- Players in pool: **527**
- Eligible for clustering (xP profile bars): **251**
- Core feature count: **27**

## Existing rule-based archetypes

- xP profile archetypes in use today: **6** (limitado, impacto, elite, regular, seguranca, criativo)
- Progression archetypes (pass-side): **1**

## Dimensionality

- Components for 80% variance: **4**
- Components for 90% variance: **8**
- First PCA component: **41.6%**

## Model selection (KMeans, standardized within position group)

| k | Silhouette ↑ | Calinski-Harabasz ↑ | Davies-Bouldin ↓ |
|---:|---:|---:|---:|
| 2 | 0.226 | 93.6 | 1.555 |
| 3 | 0.199 | 78.1 | 1.604 |
| 4 | 0.148 | 61.4 | 1.829 |
| 5 | 0.148 | 55.7 | 1.830 |
| 6 | 0.137 | 49.6 | 1.774 |
| 7 | 0.126 | 45.9 | 1.807 |
| 8 | 0.129 | 43.9 | 1.760 |
| 9 | 0.127 | 40.6 | 1.727 |
| 10 | 0.117 | 36.6 | 1.746 |

**Best silhouette k:** 2
**Recommended k (balanced):** 3

## Recommendation

Statistically, silhouette peaks at **k=2** (0.226) — a coarse split between high and lower xP passers. For scouting dashboards, **3 profiles** is the better product compromise: enough granularity for Connector / Progressor / Creator / Finisher-style scouting without fragmenting into hard-to-explain micro-clusters. PCA suggests ~4 independent dimensions for 80% variance (~8 for 90%), aligning with 4 radar axes plus execution style.

## Cluster profiles at recommended k

### Cluster 0 — Balanced / mixed — 72 players (28.7%)
- Mean xP pass rating: **0.77**
- xP archetype mix: seguranca (32), elite (25), impacto (6), regular (4), criativo (3), limitado (2)
- Origin mix: campo_defensivo (46), campo_ofensivo (26)
- Top standardized features:
  - `impact_passes_p90`: +1.06
  - `xpass_residual_p90`: +1.06
  - `construction_aip_p90`: +1.05
  - `pass_efficiency_display`: +1.02
  - `pass_buildup_display`: +1.02
  - `pass_impact_display`: +1.00
- Examples:
  - Joshua Kimmich (FC Bayern München) — xP 0.832, Safety
  - Manuel Locatelli (Juventus) — xP 0.832, Elite
  - Aleix García (Bayer 04 Leverkusen) — xP 0.8319, Safety
  - Vitinha (Paris Saint-Germain) — xP 0.8319, Safety
  - Luka Modrić (AC Milan) — xP 0.8316, Elite

### Cluster 2 — Balanced / mixed — 80 players (31.9%)
- Mean xP pass rating: **0.62**
- xP archetype mix: regular (25), limitado (19), criativo (12), elite (11), impacto (10), seguranca (3)
- Origin mix: campo_defensivo (42), campo_ofensivo (38)
- Top standardized features:
  - `pass_completion_pct`: -0.96
  - `xpass_expected_pct`: -0.89
  - `xpass_coe_pct`: -0.76
  - `xp_quality_index`: +0.74
  - `xpass_residual_p90`: -0.71
  - `pass_efficiency_display`: -0.57
- Examples:
  - Florian Wirtz (Liverpool FC) — xP 0.7332, Impact
  - Lamine Camara (AS Monaco) — xP 0.7248, Elite
  - Mamadou Sangare (RC Lens) — xP 0.7187, Elite
  - Henrikh Mkhitaryan (Inter) — xP 0.718, Impact
  - Casemiro (Manchester United) — xP 0.7128, Elite

### Cluster 1 — Balanced / mixed — 99 players (39.4%)
- Mean xP pass rating: **0.61**
- xP archetype mix: limitado (75), regular (12), seguranca (12)
- Origin mix: campo_defensivo (81), campo_ofensivo (18)
- Top standardized features:
  - `xp_archetype_builder_display`: -0.87
  - `pass_buildup_display`: -0.85
  - `xp_archetype_creator_display`: -0.85
  - `pass_chance_creation_display`: -0.84
  - `xp_creator_index`: -0.80
  - `xpv_per_pass`: -0.80
- Examples:
  - Nico González (Manchester City) — xP 0.7685, Safety
  - Ryan Gravenberch (Liverpool FC) — xP 0.7526, Safety
  - Bernardo Silva (Manchester City) — xP 0.7492, Safety
  - João Neves (Paris Saint-Germain) — xP 0.7387, Safety
  - Sofyan Amrabat (Real Betis) — xP 0.7355, Safety

## Options for the product

**Option A — 4 macro profiles (simplest):** Connector / Progressor / Creator / Finisher. Good for UI and compare tabs; loses specialists.

**Option B — 5 data-driven profiles (recommended):** keep KMeans k=5 on the core feature set; name clusters from top z-scores (builder, creator, progressor, safety, limited).

**Option C — 6 profiles (align with current xP archetypes):** reuse existing rule labels (elite, creative, safety, impact, regular, limited) — already implemented, but overlaps in practice.

**Option D — 7–8 profiles (max detail):** only if you need fine-grained recruitment filters; silhouette gain vs k=5 is small and clusters become harder to explain.
