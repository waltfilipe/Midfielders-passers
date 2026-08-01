# Estudo estatístico de perfis de médios — resumo (PT)

## Metodologia

- **Base:** 527 médios europeus no pool; **251 elegíveis** para clustering (com barras xP completas e `xp_pass_rating`).
- **Features (27):** índices xP (builder, creator, progressor, finisher, quality, consistency), radar de arquétipos xP, scores de passe (volume, eficiência, buildup, chance creation, impact), execução xPass (COE, residual, xPv/pass), e estilo de passe de impacto (AIP construção/agressão, passes de impacto, risco).
- **Pré-processamento:** imputação mediana + padronização **dentro do grupo de posição**.
- **Algoritmo:** KMeans, k=2..10, com silhouette, Calinski-Harabasz e Davies-Bouldin.
- **Artefatos:** `scripts/study_player_profiles_clustering.py`, `docs/player_profile_clustering_study.json`.

## Dimensão dos dados (PCA)

| Métrica | Valor |
|---|---|
| Componentes para 80% variância | **4** |
| Componentes para 90% variância | **8** |
| 1.ª componente | **41,6%** |

Interpretação: existem ~4 eixos independentes dominantes — alinhados com Connector / Progressor / Creator / Finisher + execução de passe.

## Seleção de k

| k | Silhouette ↑ | Calinski-Harabasz ↑ | Davies-Bouldin ↓ |
|---:|---:|---:|---:|
| **2** | **0,226** | 93,6 | 1,555 |
| 3 | 0,199 | 78,1 | 1,604 |
| 4 | 0,148 | 61,4 | 1,829 |
| 5 | 0,148 | 55,7 | 1,830 |
| 6+ | ≤0,137 | — | — |

- **Melhor k estatístico:** 2 (separação mais forte, mas grosseira).
- **k recomendado para produto:** **4–5 perfis** (ver opções abaixo).
- Silhouette global é modesta (<0,25) — esperado em dados de performance esportiva com sobreposição natural entre jogadores.

## Perfis com k=2 (split estatístico)

| Cluster | % | xP médio | Perfil | Exemplos |
|---|---:|---:|---|---|
| Alto desempenho | 53% | 0,71 | Elite + Safety + builder/creator | Kimmich, Locatelli, Vitinha, Modrić |
| Abaixo do benchmark | 47% | 0,60 | Limitado dominante, baixo builder/creator | Camavinga, Amrabat, vários pivôs defensivos |

## Perfis com k=3 (compromisso mínimo)

| Cluster | % | xP médio | Sinal estatístico | Exemplos |
|---|---:|---:|---|---|
| **Elite construtor** | 29% | 0,77 | +impacto, +execução xPass, +buildup | Kimmich, Locatelli, Vitinha |
| **Criativo / impacto** | 32% | 0,62 | −completion, +quality relativo | Wirtz, Mkhitaryan, Casemiro |
| **Retenção / limitado** | 39% | 0,61 | −builder, −creator, −chance creation | Neves, Gravenberch, Amrabat |

## Perfis com k=5 (granularidade para scouting)

| Cluster | % | xP médio | Perfil sugerido | Exemplos |
|---|---:|---:|---|---|
| 1 | 17% | 0,79 | **Organizador elite** — execução xPass acima da média | Kimmich, Vitinha, Modrić |
| 2 | 16% | 0,73 | **Criador de finalização** — finisher + agressão AIP | Bruno Fernandes, Barella, Szoboszlai |
| 3 | 20% | 0,62 | **Pivô defensivo limitado** — baixo creator/builder | Camavinga, Pepelu, James |
| 4 | 26% | 0,62 | **Misto ofensivo** — completion baixa, perfil variado | Wirtz, Casemiro, Rabiot |
| 5 | 21% | 0,59 | **Segurança sem progressão** — baixo progressor/finisher | Neves, Zubimendi, Seiwald |

## Segmentação por origem de campo

| Origem | n | Melhor k | Silhouette |
|---|---:|---:|---:|
| Campo defensivo | 169 | 2 | 0,257 |
| Campo ofensivo | 82 | 2 | 0,209 |

Mesmo separando por origem, o melhor k estatístico continua sendo 2 — reforça que a variância principal é **nível global de qualidade de passe**, não sub-estilo tático.

## Arquétipos já existentes (regra)

Distribuição nos 251 elegíveis:

| Arquétipo xP | n |
|---|---:|
| Limitado | 96 |
| Segurança | 47 |
| Regular | 41 |
| Elite | 36 |
| Impacto | 16 |
| Criativo | 15 |

Os 6 labels atuais já cobrem variedade, mas **sobrepõem-se** nos clusters (ex.: cluster “elite” mistura Safety e Elite). Os arquétipos de progressão (`player_archetypes`) quase não aparecem porque dependem de ratings de progressão completos no pipeline de estudo.

## Recomendação

| Perspectiva | k ideal | Porquê |
|---|---|---|
| **Estatística pura** | **2** | Silhouette máxima; separa “acima vs abaixo do benchmark”. |
| **Produto / UI** | **4 ou 5** | Alinha com os 4 eixos do radar xP + bucket “limitado”; interpretável para recrutadores. |
| **Manter como está** | **6** | Labels xP já implementados; úteis mas com overlap. |
| **Evitar** | 7–8 | Ganho estatístico mínimo; clusters difíceis de explicar. |

**Recomendação final:** implementar **4 perfis macro** (Connector / Progressor / Creator / Finisher) derivados dos índices xP existentes, com um **5.º bucket “Limitado”** para jogadores abaixo do limiar — ou usar **k=5 data-driven** se quiserem nomes calibrados pela base (organizador, criador, pivô, misto, segurança).

## Opções para o produto

- **Opção A — 4 macro perfis:** Connector / Progressor / Creator / Finisher. Mais simples para Compare e filtros.
- **Opção B — 5 perfis data-driven (recomendada):** KMeans k=5 + nomes por z-score. Melhor equilíbrio scouting vs. interpretabilidade.
- **Opção C — 6 perfis (atual):** Manter arquétipos xP rule-based já no app.
- **Opção D — 7–8 perfis:** Só para filtros avançados; baixo retorno estatístico.
