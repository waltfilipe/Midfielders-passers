# Player similarity — alt metrics + heatmap

Pool: **251** eligible midfielders.

## Métricas alternativas (k-NN em z-scores)

| Key | Label |
|---|---|
| `long_pass_share_pct` | % passes longos |
| `progressive_pass_rate` | % passes progressivos / passe |
| `impact_v2_per_pass` | Impact v2 / passe |
| `xpv_per_pass` | xPV / passe |
| `xpv_per_game` | xPV / jogo |
| `xpass_coe_pct` | COE |
| `xpass_long_coe_pct` | COE long passes |

**Heatmap:** cosseno entre grelhas 8×6 de origem dos passes.

**Híbrido:** 65% métricas alternativas + 35% heatmap.

## Joshua Kimmich (FC Bayern München) · €35.00M
- % passes longos 13.80 · % passes progressivos / passe 9.83 · Impact v2 / passe 3.30 · xPV / passe 0.38 · xPV / jogo 32.00 · COE +6.2pp · COE long passes +6.7pp

### 7 pilares (referência anterior)

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 99.0 | Pedri | FC Barcelona | €150.00M | 0.8309 |
| 98.2 | Manuel Locatelli | Juventus | €25.00M | 0.832 |
| 96.7 | Luka Modrić | AC Milan | €3.50M | 0.8316 |
| 95.9 | Vitinha | Paris Saint-Germain | €140.00M | 0.8319 |
| 95.0 | Angelo Stiller | VfB Stuttgart | €45.00M | 0.8156 |
| 93.7 | Aleix García | Bayer 04 Leverkusen | €20.00M | 0.8319 |
| 93.5 | Fabián Ruiz | Paris Saint-Germain | €30.00M | 0.8137 |
| 92.4 | Rodri | Manchester City | €55.00M | 0.8211 |

### Métricas alternativas

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 82.0 | Pedri | FC Barcelona | €150.00M | 0.8309 |
| 82.0 | Vitinha | Paris Saint-Germain | €140.00M | 0.8319 |
| 81.1 | Aleix García | Bayer 04 Leverkusen | €20.00M | 0.8319 |
| 76.2 | Rodri | Manchester City | €55.00M | 0.8211 |
| 71.8 | Aleksandar Pavlović | FC Bayern München | €90.00M | 0.8269 |
| 70.2 | Fabián Ruiz | Paris Saint-Germain | €30.00M | 0.8137 |
| 70.1 | Angelo Stiller | VfB Stuttgart | €45.00M | 0.8156 |
| 67.8 | Luka Modrić | AC Milan | €3.50M | 0.8316 |

### Heatmap (origem dos passes)

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 97.0 | Martín Zubimendi | Arsenal | €75.00M | 0.7071 |
| 97.0 | Youssouf Fofana | AC Milan | €23.00M | 0.5761 |
| 96.6 | Adam Wharton | Crystal Palace | €70.00M | 0.7024 |
| 96.5 | Marten de Roon | Atalanta | €3.20M | 0.7803 |
| 95.8 | Mamadou Sangare | RC Lens | €40.00M | 0.7187 |
| 95.3 | Hakan Çalhanoğlu | Inter | €16.00M | 0.7962 |
| 95.2 | Iván Martín | Girona FC | €5.00M | 0.662 |
| 95.2 | Niccolò Pisilli | AS Roma | €30.00M | 0.6313 |

### Híbrido (65% métricas + 35% heatmap)

Inclui jogadores que combinam estilo de taxas **e** zona de ação.

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 84.1 | Vitinha | Paris Saint-Germain | €140.00M | 0.8319 |
| 83.3 | Aleix García | Bayer 04 Leverkusen | €20.00M | 0.8319 |
| 82.7 | Pedri | FC Barcelona | €150.00M | 0.8309 |
| 80.6 | Rodri | Manchester City | €55.00M | 0.8211 |
| 76.9 | Aleksandar Pavlović | FC Bayern München | €90.00M | 0.8269 |
| 75.5 | Frenkie de Jong | FC Barcelona | €35.00M | 0.8241 |
| 75.0 | Hakan Çalhanoğlu | Inter | €16.00M | 0.7962 |
| 74.8 | Angelo Stiller | VfB Stuttgart | €45.00M | 0.8156 |


## Bruno Fernandes (Manchester United) · €35.00M
- % passes longos 16.50 · % passes progressivos / passe 15.03 · Impact v2 / passe 4.71 · xPV / passe 0.41 · xPV / jogo 19.04 · COE +1.0pp · COE long passes +9.5pp

### 7 pilares (referência anterior)

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 93.1 | Nicolò Barella | Inter | €50.00M | 0.7836 |
| 90.8 | Bruno Guimarães | Newcastle United | €70.00M | 0.7909 |
| 90.5 | Granit Xhaka | Sunderland | €8.00M | 0.7608 |
| 90.0 | Dominik Szoboszlai | Liverpool FC | €100.00M | 0.795 |
| 89.4 | Angelo Stiller | VfB Stuttgart | €45.00M | 0.8156 |
| 88.9 | Nadiem Amiri | 1. FSV Mainz 05 | €17.00M | 0.7561 |
| 88.4 | Branco Van den Boomen | Angers | €2.50M | 0.7746 |
| 88.2 | Pablo Fornals | Real Betis | €8.00M | 0.7782 |

### Métricas alternativas

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 83.2 | Nadiem Amiri | 1. FSV Mainz 05 | €17.00M | 0.7561 |
| 75.1 | Mathias Jensen | Brentford | €10.00M | 0.7018 |
| 74.7 | Luka Modrić | AC Milan | €3.50M | 0.8316 |
| 73.5 | Granit Xhaka | Sunderland | €8.00M | 0.7608 |
| 73.1 | Adam Wharton | Crystal Palace | €70.00M | 0.7024 |
| 71.9 | Nicolò Barella | Inter | €50.00M | 0.7836 |
| 71.6 | Bruno Guimarães | Newcastle United | €70.00M | 0.7909 |
| 71.5 | Branco Van den Boomen | Angers | €2.50M | 0.7746 |

### Heatmap (origem dos passes)

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 97.2 | Hakon Arnar Haraldsson | Lille | €25.00M | 0.651 |
| 96.9 | Tijjani Reijnders | Manchester City | €50.00M | 0.5932 |
| 96.7 | Denis Suárez | Deportivo Alavés | €1.00M | 0.6002 |
| 96.3 | Nadiem Amiri | 1. FSV Mainz 05 | €17.00M | 0.7561 |
| 96.1 | Benjamin André | Lille | €3.00M | 0.6984 |
| 96.1 | João Neves | Paris Saint-Germain | €140.00M | 0.7387 |
| 95.9 | Phil Foden | Manchester City | €70.00M | 0.639 |
| 95.7 | Sergi Darder | Mallorca | €3.00M | 0.6447 |

### Híbrido (65% métricas + 35% heatmap)

Inclui jogadores que combinam estilo de taxas **e** zona de ação.

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 87.8 | Nadiem Amiri | 1. FSV Mainz 05 | €17.00M | 0.7561 |
| 81.9 | Mathias Jensen | Brentford | €10.00M | 0.7018 |
| 80.2 | Luka Modrić | AC Milan | €3.50M | 0.8316 |
| 79.4 | Granit Xhaka | Sunderland | €8.00M | 0.7608 |
| 78.8 | Moi Gómez | Osasuna | €1.50M | 0.7438 |
| 78.0 | Bruno Guimarães | Newcastle United | €70.00M | 0.7909 |
| 77.9 | Arda Güler | Real Madrid | €90.00M | 0.762 |
| 77.0 | Branco Van den Boomen | Angers | €2.50M | 0.7746 |


## João Neves (Paris Saint-Germain) · €140.00M
- % passes longos 11.40 · % passes progressivos / passe 4.43 · Impact v2 / passe 2.84 · xPV / passe 0.32 · xPV / jogo 14.40 · COE +3.1pp · COE long passes +2.0pp

### 7 pilares (referência anterior)

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 87.4 | Mateus Fernandes | West Ham United | €50.00M | 0.7311 |
| 85.7 | Reece James | Chelsea | €60.00M | 0.708 |
| 85.2 | Stanislav Lobotka | SSC Napoli | €10.00M | 0.7766 |
| 84.8 | Samir El Mourabet | RC Strasbourg | €22.00M | 0.6956 |
| 83.5 | Bernardo Silva | Manchester City | €22.00M | 0.7492 |
| 82.8 | Lucas Da Cunha | Como | €20.00M | 0.7657 |
| 82.2 | Michel Aebischer | Pisa | €4.00M | 0.6887 |
| 81.7 | James Garner | Everton | €45.00M | 0.7367 |

### Métricas alternativas

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 83.7 | Marc Roca | Real Betis | €4.00M | 0.6476 |
| 83.1 | Sergi Altimira | Real Betis | €20.00M | 0.6341 |
| 82.0 | Phil Foden | Manchester City | €70.00M | 0.639 |
| 81.2 | Samir El Mourabet | RC Strasbourg | €22.00M | 0.6956 |
| 80.4 | Iván Martín | Girona FC | €5.00M | 0.662 |
| 79.3 | Fran Beltrán | Girona FC | €4.00M | 0.7155 |
| 79.0 | Bernardo Silva | Manchester City | €22.00M | 0.7492 |
| 78.9 | Ellyes Skhiri | Eintracht Frankfurt | €5.00M | 0.6361 |

### Heatmap (origem dos passes)

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 97.1 | Pablo Fornals | Real Betis | €8.00M | 0.7782 |
| 96.7 | Ayyoub Bouaddi | Lille | €80.00M | 0.5627 |
| 96.6 | Denis Suárez | Deportivo Alavés | €1.00M | 0.6002 |
| 96.6 | Johann Lepenant | Nantes | €7.00M | 0.5331 |
| 96.4 | Joel Chima Fujita | FC St. Pauli | €10.00M | 0.5098 |
| 96.4 | Pascal Groß | Brighton & Hove Albion | €2.50M | 0.7484 |
| 96.1 | Bruno Fernandes | Manchester United | €35.00M | 0.8008 |
| 96.1 | Mateus Fernandes | West Ham United | €50.00M | 0.7311 |

### Híbrido (65% métricas + 35% heatmap)

Inclui jogadores que combinam estilo de taxas **e** zona de ação.

| Sim % | Player | Team | MV | xP pass |
|---:|---|---|---:|---:|
| 85.9 | Phil Foden | Manchester City | €70.00M | 0.639 |
| 85.7 | Sergi Altimira | Real Betis | €20.00M | 0.6341 |
| 84.6 | Marc Roca | Real Betis | €4.00M | 0.6476 |
| 84.4 | Bernardo Silva | Manchester City | €22.00M | 0.7492 |
| 83.7 | Iván Martín | Girona FC | €5.00M | 0.662 |
| 82.3 | Fran Beltrán | Girona FC | €4.00M | 0.7155 |
| 82.3 | Stanislav Lobotka | SSC Napoli | €10.00M | 0.7766 |
| 81.5 | Lucas Da Cunha | Como | €20.00M | 0.7657 |

