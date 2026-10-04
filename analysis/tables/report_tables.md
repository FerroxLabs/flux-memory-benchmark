<!-- key_findings -->
On LoCoMo (all five categories, the figure in the qa summaries), the Honcho chat arm scored **85.6%**. That is above every Flux arm (flux_public 74.9%, flux_evidence 74.3%) and above full context (79.1%). On categories 1 to 4 only (the preregistered headline, n=1540) the figures are: honcho_chat 83.8%, full_context 77.6%, flux_public 70.6%, flux_evidence 70.5%, honcho_retrieval 67.7%, mem0 66.0%, letta 61.2%, closed_book 15.0%.

On LongMemEval-S (n=100): full_context 94%, flux_evidence 91%, flux_public 84%, honcho_retrieval 82%, honcho_chat 81%, letta 81%, mem0 75%, closed_book 10%.

<!-- accuracy -->
**LongMemEval-S (n=100)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty | Qa-summary accuracy % | Match |
|---|---|---|---|---|---|---|---|
| full_context | 94/100 | 94.0 | 87.5 to 97.2 | 0 | 1 | 94.00 | yes |
| flux_evidence | 91/100 | 91.0 | 83.8 to 95.2 | 0 | 1 | 91.00 | yes |
| flux_public | 84/100 | 84.0 | 75.6 to 89.9 | 0 | 1 | 84.00 | yes |
| honcho_retrieval | 82/100 | 82.0 | 73.3 to 88.3 | 0 | 1 | 82.00 | yes |
| honcho_chat | 81/100 | 81.0 | 72.2 to 87.5 | 0 | 0 | 81.00 | yes |
| letta | 81/100 | 81.0 | 72.2 to 87.5 | 0 | 2 | 81.00 | yes |
| mem0 | 75/100 | 75.0 | 65.7 to 82.5 | 0 | 1 | 75.00 | yes |
| closed_book | 10/100 | 10.0 | 5.5 to 17.4 | 0 | 0 | 10.00 | yes |

**LoCoMo categories 1-4 (n=1540, preregistered headline)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty | Qa-summary accuracy % | Match |
|---|---|---|---|---|---|---|---|
| full_context | 1195/1540 | 77.6 | 75.4 to 79.6 | 0 | 0 | n/a (subset) | - |
| flux_evidence | 1085/1540 | 70.5 | 68.1 to 72.7 | 1 | 3 | n/a (subset) | - |
| flux_public | 1088/1540 | 70.6 | 68.3 to 72.9 | 2 | 7 | n/a (subset) | - |
| honcho_retrieval | 1043/1540 | 67.7 | 65.4 to 70.0 | 0 | 3 | n/a (subset) | - |
| honcho_chat | 1291/1540 | 83.8 | 81.9 to 85.6 | 0 | 0 | n/a (subset) | - |
| letta | 942/1540 | 61.2 | 58.7 to 63.6 | 2 | 21 | n/a (subset) | - |
| mem0 | 1017/1540 | 66.0 | 63.6 to 68.4 | 0 | 7 | n/a (subset) | - |
| closed_book | 231/1540 | 15.0 | 13.3 to 16.9 | 1 | 0 | n/a (subset) | - |

**LoCoMo all five categories (n=1986, the figure in the qa summaries)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty | Qa-summary accuracy % | Match |
|---|---|---|---|---|---|---|---|
| full_context | 1570/1986 | 79.1 | 77.2 to 80.8 | 0 | 0 | 79.05 | yes |
| flux_evidence | 1476/1986 | 74.3 | 72.4 to 76.2 | 1 | 3 | 74.32 | yes |
| flux_public | 1487/1986 | 74.9 | 72.9 to 76.7 | 2 | 7 | 74.87 | yes |
| honcho_retrieval | 1466/1986 | 73.8 | 71.8 to 75.7 | 0 | 3 | 73.82 | yes |
| honcho_chat | 1700/1986 | 85.6 | 84.0 to 87.1 | 0 | 0 | 85.60 | yes |
| letta | 1344/1986 | 67.7 | 65.6 to 69.7 | 2 | 21 | 67.67 | yes |
| mem0 | 1442/1986 | 72.6 | 70.6 to 74.5 | 0 | 7 | 72.61 | yes |
| closed_book | 428/1986 | 21.6 | 19.8 to 23.4 | 1 | 0 | 21.55 | yes |

**LoCoMo category 5 adversarial (n=446)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty | Qa-summary accuracy % | Match |
|---|---|---|---|---|---|---|---|
| full_context | 375/446 | 84.1 | 80.4 to 87.2 | 0 | 0 | n/a (subset) | - |
| flux_evidence | 391/446 | 87.7 | 84.3 to 90.4 | 0 | 0 | n/a (subset) | - |
| flux_public | 399/446 | 89.5 | 86.3 to 92.0 | 0 | 0 | n/a (subset) | - |
| honcho_retrieval | 423/446 | 94.8 | 92.4 to 96.5 | 0 | 0 | n/a (subset) | - |
| honcho_chat | 409/446 | 91.7 | 88.8 to 93.9 | 0 | 0 | n/a (subset) | - |
| letta | 402/446 | 90.1 | 87.0 to 92.6 | 0 | 0 | n/a (subset) | - |
| mem0 | 425/446 | 95.3 | 92.9 to 96.9 | 0 | 0 | n/a (subset) | - |
| closed_book | 197/446 | 44.2 | 39.6 to 48.8 | 0 | 0 | n/a (subset) | - |


<!-- paired -->
**LongMemEval-S (n=100).** Difference = Flux arm minus the other arm, percentage points (positive favours Flux). Bootstrap: 10,000 resamples, seed 20261003.

| Flux arm | Other arm | Diff pts | Item bootstrap 95% | Flux only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| flux_public | full_context | -10.0 | -16.0 to -5.0 | 0 | 10 | 0.001953 | 0.01172 |
| flux_public | flux_evidence | -7.0 | -14.0 to -1.0 | 2 | 9 | 0.06543 | 0.3271 |
| flux_public | honcho_retrieval | +2.0 | -5.0 to +9.0 | 8 | 6 | 0.7905 | 1 |
| flux_public | honcho_chat | +3.0 | -5.0 to +11.0 | 10 | 7 | 0.6291 | 1 |
| flux_public | letta | +3.0 | -3.0 to +10.0 | 7 | 4 | 0.5488 | 1 |
| flux_public | mem0 | +9.0 | +0.0 to +18.0 | 16 | 7 | 0.09314 | 0.3726 |
| flux_public | closed_book | +74.0 | +65.0 to +83.0 | 75 | 1 | 2.038e-21 | 1.427e-20 |
| flux_evidence | full_context | -3.0 | -8.0 to +2.0 | 2 | 5 | 0.4531 | 0.4531 |
| flux_evidence | flux_public | +7.0 | +1.0 to +14.0 | 9 | 2 | 0.06543 | 0.1309 |
| flux_evidence | honcho_retrieval | +9.0 | +2.0 to +16.0 | 11 | 2 | 0.02246 | 0.1064 |
| flux_evidence | honcho_chat | +10.0 | +2.0 to +19.0 | 14 | 4 | 0.03088 | 0.1064 |
| flux_evidence | letta | +10.0 | +3.0 to +18.0 | 13 | 3 | 0.02127 | 0.1064 |
| flux_evidence | mem0 | +16.0 | +8.0 to +25.0 | 19 | 3 | 0.0008554 | 0.005133 |
| flux_evidence | closed_book | +81.0 | +72.0 to +89.0 | 82 | 1 | 1.737e-23 | 1.216e-22 |

**LoCoMo categories 1-4 (n=1540, preregistered headline).** Difference = Flux arm minus the other arm, percentage points (positive favours Flux). Bootstrap: 10,000 resamples, seed 20261003.

| Flux arm | Other arm | Diff pts | Item bootstrap 95% | Conversation-clustered 95% | Flux only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|---|
| flux_public | full_context | -6.9 | -8.9 to -5.1 | -7.9 to -5.9 | 62 | 169 | 1.209e-12 | 4.835e-12 |
| flux_public | flux_evidence | +0.2 | -1.2 to +1.6 | -1.2 to +1.3 | 66 | 63 | 0.8603 | 0.8603 |
| flux_public | honcho_retrieval | +2.9 | +0.3 to +5.6 | +1.0 to +4.8 | 242 | 197 | 0.03561 | 0.07122 |
| flux_public | honcho_chat | -13.2 | -15.5 to -10.8 | -15.5 to -11.0 | 81 | 284 | 1.504e-27 | 9.021e-27 |
| flux_public | letta | +9.5 | +7.3 to +11.6 | +7.0 to +12.0 | 223 | 77 | 1.256e-17 | 6.282e-17 |
| flux_public | mem0 | +4.6 | +2.5 to +6.8 | +3.0 to +6.2 | 180 | 109 | 3.519e-05 | 0.0001056 |
| flux_public | closed_book | +55.6 | +53.0 to +58.4 | +52.7 to +58.9 | 894 | 37 | 2.871e-214 | 2.01e-213 |
| flux_evidence | full_context | -7.1 | -9.1 to -5.3 | -8.2 to -5.8 | 61 | 171 | 2.945e-13 | 1.178e-12 |
| flux_evidence | flux_public | -0.2 | -1.6 to +1.2 | -1.3 to +1.2 | 63 | 66 | 0.8603 | 0.8603 |
| flux_evidence | honcho_retrieval | +2.7 | +0.1 to +5.4 | +0.6 to +4.8 | 238 | 196 | 0.04894 | 0.09787 |
| flux_evidence | honcho_chat | -13.4 | -15.7 to -11.1 | -15.2 to -11.4 | 75 | 281 | 3.82e-29 | 2.292e-28 |
| flux_evidence | letta | +9.3 | +7.1 to +11.4 | +7.3 to +11.7 | 215 | 72 | 1.057e-17 | 5.283e-17 |
| flux_evidence | mem0 | +4.4 | +2.3 to +6.6 | +2.9 to +5.9 | 178 | 110 | 7.339e-05 | 0.0002202 |
| flux_evidence | closed_book | +55.5 | +52.7 to +58.2 | +52.5 to +58.4 | 886 | 32 | 1.333e-217 | 9.331e-217 |

**LoCoMo all five categories (n=1986, the figure in the qa summaries).** Difference = Flux arm minus the other arm, percentage points (positive favours Flux). Bootstrap: 10,000 resamples, seed 20261003.

| Flux arm | Other arm | Diff pts | Item bootstrap 95% | Conversation-clustered 95% | Flux only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|---|
| flux_public | full_context | -4.2 | -5.8 to -2.5 | -4.9 to -3.5 | 98 | 181 | 7.646e-07 | 3.058e-06 |
| flux_public | flux_evidence | +0.6 | -0.7 to +1.8 | -0.4 to +1.4 | 85 | 74 | 0.4278 | 0.7216 |
| flux_public | honcho_retrieval | +1.1 | -1.1 to +3.2 | -0.6 to +2.8 | 250 | 229 | 0.3608 | 0.7216 |
| flux_public | honcho_chat | -10.7 | -12.6 to -8.8 | -12.5 to -9.0 | 98 | 311 | 6.5e-27 | 3.9e-26 |
| flux_public | letta | +7.2 | +5.4 to +9.0 | +5.4 to +9.2 | 240 | 97 | 3.975e-15 | 1.988e-14 |
| flux_public | mem0 | +2.3 | +0.5 to +4.0 | +0.8 to +3.7 | 185 | 140 | 0.01453 | 0.0436 |
| flux_public | closed_book | +53.3 | +51.0 to +55.7 | +51.3 to +55.9 | 1112 | 53 | 9.661e-259 | 6.763e-258 |
| flux_evidence | full_context | -4.7 | -6.3 to -3.2 | -5.5 to -4.0 | 88 | 182 | 1.088e-08 | 4.35e-08 |
| flux_evidence | flux_public | -0.6 | -1.8 to +0.7 | -1.4 to +0.4 | 74 | 85 | 0.4278 | 0.8557 |
| flux_evidence | honcho_retrieval | +0.5 | -1.6 to +2.7 | -1.2 to +2.3 | 242 | 232 | 0.6794 | 0.8557 |
| flux_evidence | honcho_chat | -11.3 | -13.2 to -9.4 | -13.0 to -9.7 | 88 | 312 | 1.766e-30 | 1.059e-29 |
| flux_evidence | letta | +6.6 | +4.9 to +8.4 | +5.0 to +8.7 | 230 | 98 | 2.242e-13 | 1.121e-12 |
| flux_evidence | mem0 | +1.7 | -0.1 to +3.5 | +0.5 to +2.9 | 181 | 147 | 0.06827 | 0.2048 |
| flux_evidence | closed_book | +52.8 | +50.4 to +55.1 | +50.7 to +55.3 | 1098 | 50 | 6.062e-258 | 4.243e-257 |

**LoCoMo category 5 adversarial (n=446).** Difference = Flux arm minus the other arm, percentage points (positive favours Flux). Bootstrap: 10,000 resamples, seed 20261003.

| Flux arm | Other arm | Diff pts | Item bootstrap 95% | Conversation-clustered 95% | Flux only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|---|
| flux_public | full_context | +5.4 | +2.5 to +8.5 | +2.2 to +7.9 | 36 | 12 | 0.0007173 | 0.002869 |
| flux_public | flux_evidence | +1.8 | -0.4 to +4.3 | -0.7 to +4.1 | 19 | 11 | 0.2005 | 0.5225 |
| flux_public | honcho_retrieval | -5.4 | -8.1 to -2.7 | -8.2 to -2.3 | 8 | 32 | 0.0001822 | 0.0009108 |
| flux_public | honcho_chat | -2.2 | -5.2 to +0.7 | -5.4 to +1.6 | 17 | 27 | 0.1742 | 0.5225 |
| flux_public | letta | -0.7 | -3.4 to +2.0 | -2.6 to +1.3 | 17 | 20 | 0.7428 | 0.7428 |
| flux_public | mem0 | -5.8 | -8.3 to -3.4 | -8.7 to -3.4 | 5 | 31 | 1.291e-05 | 7.748e-05 |
| flux_public | closed_book | +45.3 | +40.1 to +50.4 | +37.3 to +52.6 | 218 | 16 | 1.786e-46 | 1.25e-45 |
| flux_evidence | full_context | +3.6 | +0.9 to +6.3 | +1.5 to +5.3 | 27 | 11 | 0.01385 | 0.04156 |
| flux_evidence | flux_public | -1.8 | -4.3 to +0.4 | -4.1 to +0.7 | 11 | 19 | 0.2005 | 0.2346 |
| flux_evidence | honcho_retrieval | -7.2 | -9.9 to -4.7 | -9.2 to -5.1 | 4 | 36 | 1.857e-07 | 9.285e-07 |
| flux_evidence | honcho_chat | -4.0 | -7.0 to -1.1 | -7.0 to -1.0 | 13 | 31 | 0.00956 | 0.03824 |
| flux_evidence | letta | -2.5 | -5.2 to +0.2 | -3.9 to -1.0 | 15 | 26 | 0.1173 | 0.2346 |
| flux_evidence | mem0 | -7.6 | -10.3 to -4.9 | -9.6 to -5.8 | 3 | 37 | 1.947e-08 | 1.168e-07 |
| flux_evidence | closed_book | +43.5 | +38.3 to +48.9 | +36.3 to +50.3 | 212 | 18 | 3.24e-43 | 2.268e-42 |

<!-- categories -->
**LoCoMo, per category** (correct/n, accuracy %; Wilson 95% in brackets)

| Arm | cat1-multi-hop (n=282) | cat2-temporal (n=321) | cat3-open-domain (n=96) | cat4-single-hop (n=841) | cat5-adversarial (n=446) |
|---|---|---|---|---|---|
| full_context | 197/282 69.9 [64-75] | 156/321 48.6 [43-54] | 63/96 65.6 [56-74] | 779/841 92.6 [91-94] | 375/446 84.1 [80-87] |
| flux_evidence | 153/282 54.3 [48-60] | 141/321 43.9 [39-49] | 53/96 55.2 [45-65] | 738/841 87.8 [85-90] | 391/446 87.7 [84-90] |
| flux_public | 149/282 52.8 [47-59] | 146/321 45.5 [40-51] | 56/96 58.3 [48-68] | 737/841 87.6 [85-90] | 399/446 89.5 [86-92] |
| honcho_retrieval | 117/282 41.5 [36-47] | 247/321 76.9 [72-81] | 48/96 50.0 [40-60] | 631/841 75.0 [72-78] | 423/446 94.8 [92-96] |
| honcho_chat | 203/282 72.0 [66-77] | 276/321 86.0 [82-89] | 59/96 61.5 [52-71] | 753/841 89.5 [87-91] | 409/446 91.7 [89-94] |
| letta | 133/282 47.2 [41-53] | 109/321 34.0 [29-39] | 55/96 57.3 [47-67] | 645/841 76.7 [74-79] | 402/446 90.1 [87-93] |
| mem0 | 172/282 61.0 [55-66] | 49/321 15.3 [12-20] | 55/96 57.3 [47-67] | 741/841 88.1 [86-90] | 425/446 95.3 [93-97] |
| closed_book | 27/282 9.6 [7-14] | 14/321 4.4 [3-7] | 27/96 28.1 [20-38] | 163/841 19.4 [17-22] | 197/446 44.2 [40-49] |

**LongMemEval-S, per question type** (correct/n, accuracy %; types have 6 to 27 questions, so intervals are wide and are omitted)

| Arm | knowledge-update (n=15) | multi-session (n=27) | single-session-assistant (n=11) | single-session-preference (n=6) | single-session-user (n=14) | temporal-reasoning (n=27) |
|---|---|---|---|---|---|---|
| full_context | 13/15 87 | 24/27 89 | 11/11 100 | 6/6 100 | 14/14 100 | 26/27 96 |
| flux_evidence | 14/15 93 | 22/27 81 | 11/11 100 | 5/6 83 | 14/14 100 | 25/27 93 |
| flux_public | 10/15 67 | 18/27 67 | 11/11 100 | 6/6 100 | 14/14 100 | 25/27 93 |
| honcho_retrieval | 14/15 93 | 16/27 59 | 10/11 91 | 6/6 100 | 13/14 93 | 23/27 85 |
| honcho_chat | 12/15 80 | 15/27 56 | 11/11 100 | 6/6 100 | 14/14 100 | 23/27 85 |
| letta | 12/15 80 | 14/27 52 | 11/11 100 | 6/6 100 | 12/14 86 | 26/27 96 |
| mem0 | 13/15 87 | 19/27 70 | 10/11 91 | 4/6 67 | 14/14 100 | 15/27 56 |
| closed_book | 0/15 0 | 3/27 11 | 4/11 36 | 0/6 0 | 2/14 14 | 1/27 4 |

<!-- cost -->
**LongMemEval-S** (USD; reader and judge from the qa summaries; ingestion, extraction and query from `results-public/ledger.jsonl`)

| Arm | Reader | Judge | Ingest / extraction | Memory-system LLM at query | Ledger total for the arm |
|---|---|---|---|---|---|
| full_context | 1.7534 | 0.0088 | 0.0000 | 0 | 1.7622 |
| flux_evidence | 0.1405 | 0.0090 | 1.4436 | 0 | 1.5931 |
| flux_public | 0.0731 | 0.0087 | 0.0000 | 0 | 0.0817 |
| honcho_retrieval | 0.0789 | 0.0091 | 8.7740 | 0.0991 (retrieval and dialectic combined) | 8.9612 |
| honcho_chat | 0.0590 | 0.0095 | 0.0000 (shared ingest with honcho_retrieval; see below) | 0 | 0.0685 |
| letta | 0.1233 | 0.0085 | 0.0000 | 0 | 0.1317 |
| mem0 | 0.1250 | 0.0092 | 4.1571 | 0 | 4.2913 |
| closed_book | 0.0570 | 0.0086 | 0.0000 | 0 | 0.0655 |

**LoCoMo** (USD; reader and judge from the qa summaries; ingestion, extraction and query from `results-public/ledger.jsonl`)

| Arm | Reader | Judge | Ingest / extraction | Memory-system LLM at query | Ledger total for the arm |
|---|---|---|---|---|---|
| full_context | 1.1233 | 0.2767 | 0.0000 | 0 | 1.4000 |
| flux_evidence | 1.6506 | 0.2762 | 0.1714 | 0 | 2.0981 |
| flux_public | 1.7859 | 0.2744 | 0.0000 | 0 | 2.0603 |
| honcho_retrieval | 1.1933 | 0.2763 | 0.1480 | 1.6840 (retrieval and dialectic combined) | 3.3016 |
| honcho_chat | 0.5299 | 0.2759 | 0.0000 (shared ingest with honcho_retrieval; see below) | 0 | 0.8058 |
| letta | 2.3148 | 0.2734 | 0.0000 | 0 | 2.5882 |
| mem0 | 1.2917 | 0.2715 | 0.1657 | 0 | 1.7290 |
| closed_book | 3.1634 | 0.2668 | 0.0000 | 0 | 3.4302 |

Total spend in the ledger: **$34.3685** (progress.log final line: 34.3685).
Honcho: ingestion for both Honcho arms was done once and is booked under `honcho_retrieval`; the query-time LLM spend (the dialectic calls) is booked under `honcho_retrieval` too, because both arms ran in the same process (`--arms ctx,chat`). Honcho retrieval (`peer.context` with a search query) makes no chat-model call as far as the driver shows, so this query spend is attributed below to the dialectic (chat) arm; that attribution is an inference from the driver code, not a separate measurement. The Honcho proxy log that would separate the two was not copied.

<!-- ingest -->
| Bench | Arm | Units | Items posted | Items dropped | Mean ingest s per unit | Mean ingest LLM USD per unit |
|---|---|---|---|---|---|---|
| lme | flux_public | 100 | 49083 | 0 | 72.5 | 0.0000 |
| lme | flux_evidence | 100 | 49083 | 0 | 2.2 | 0.0000 |
| lme | mem0 | 100 | 4753 | 0 | 151.4 | 0.0416 |
| lme | letta | 100 | 49081 | 1 | 631.8 | 0.0000 |
| lme | honcho_retrieval | 100 | 49080 | 1 | 95.1 | 0.0877 |
| locomo | flux_public | 10 | 5882 | 0 | 9.9 | 0.0000 |
| locomo | flux_evidence | 10 | 5882 | 0 | 0.0 | 0.0000 |
| locomo | mem0 | 10 | 272 | 0 | 79.7 | 0.0166 |
| locomo | letta | 10 | 5882 | 0 | 599.0 | 0.0000 |
| locomo | honcho_retrieval | 10 | 5882 | 0 | 30.3 | 0.0148 |

Flux evidence ingest figures reuse cached embeddings from flux_public (seconds are not comparable); its extraction cost is in the cost table. Items are turns for Flux and Honcho, sessions for mem0, passages for Letta.

<!-- honcho_month -->
| Corpus | Ledger ingest USD | Turns posted | USD per turn | Ledger query USD | Questions | USD per query | Retrieval arm: 600 x USD/turn | Chat arm: 600 x USD/turn + 100 x USD/query |
|---|---|---|---|---|---|---|---|---|
| LongMemEval-S | 8.7740 | 49079 | 0.0001788 | 0.0991 | 100 | 0.000991 | $0.1073 | $0.2064 |
| LoCoMo | 0.1480 | 5882 | 0.0000252 | 1.6840 | 1986 | 0.000848 | $0.0151 | $0.0999 |

<!-- reason -->
**Accuracy** (reference arms are the main run's numbers, repeated here for comparison only)

**LongMemEval-S (n=100)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty |
|---|---|---|---|---|---|
| flux_reason | 80/100 | 80.0 | 71.1 to 86.7 | 0 | 0 |
| flux_evidence | 91/100 | 91.0 | 83.8 to 95.2 | 0 | 1 |
| flux_public | 84/100 | 84.0 | 75.6 to 89.9 | 0 | 1 |
| honcho_chat | 81/100 | 81.0 | 72.2 to 87.5 | 0 | 0 |

**LoCoMo categories 1-4 (n=1540, preregistered headline)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty |
|---|---|---|---|---|---|
| flux_reason | 1129/1540 | 73.3 | 71.0 to 75.5 | 0 | 1 |
| flux_evidence | 1085/1540 | 70.5 | 68.1 to 72.7 | 1 | 3 |
| flux_public | 1088/1540 | 70.6 | 68.3 to 72.9 | 2 | 7 |
| honcho_chat | 1291/1540 | 83.8 | 81.9 to 85.6 | 0 | 0 |

**LoCoMo category 5 adversarial (n=446)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty |
|---|---|---|---|---|---|
| flux_reason | 426/446 | 95.5 | 93.2 to 97.1 | 0 | 0 |
| flux_evidence | 391/446 | 87.7 | 84.3 to 90.4 | 0 | 0 |
| flux_public | 399/446 | 89.5 | 86.3 to 92.0 | 0 | 0 |
| honcho_chat | 409/446 | 91.7 | 88.8 to 93.9 | 0 | 0 |

**Paired differences.** Difference = flux_reason minus the other arm, percentage points (positive favours flux_reason), on identical items. Bootstrap: 10,000 resamples, seed 20261003. Holm is applied across these 3 comparisons within each item set; these tests stand on their own and are not part of the main report's Holm family.

**LongMemEval-S (n=100)**

| Other arm | Diff pts | Item bootstrap 95% | flux_reason only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|
| flux_evidence | -11.0 | -17.0 to -5.0 | 0 | 11 | 0.0009766 | 0.00293 |
| flux_public | -4.0 | -11.0 to +3.0 | 5 | 9 | 0.424 | 0.8479 |
| honcho_chat | -1.0 | -9.0 to +8.0 | 9 | 10 | 1 | 1 |

**LoCoMo categories 1-4 (n=1540, preregistered headline)**

| Other arm | Diff pts | Item bootstrap 95% | Conversation-clustered 95% | flux_reason only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| flux_evidence | +2.9 | +0.6 to +5.1 | -0.2 to +6.2 | 176 | 132 | 0.01415 | 0.0283 |
| flux_public | +2.7 | +0.4 to +4.9 | -0.6 to +6.2 | 182 | 141 | 0.02588 | 0.0283 |
| honcho_chat | -10.5 | -12.7 to -8.4 | -12.5 to -8.3 | 70 | 232 | 1.953e-21 | 5.86e-21 |

**LoCoMo category 5 adversarial (n=446)**

| Other arm | Diff pts | Item bootstrap 95% | Conversation-clustered 95% | flux_reason only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| flux_evidence | +7.8 | +5.2 to +10.8 | +5.8 to +9.5 | 40 | 5 | 7.878e-08 | 2.364e-07 |
| flux_public | +6.1 | +3.4 to +9.0 | +2.9 to +8.4 | 34 | 7 | 2.532e-05 | 5.064e-05 |
| honcho_chat | +3.8 | +1.3 to +6.3 | +1.9 to +5.8 | 24 | 7 | 0.003327 | 0.003327 |

**LoCoMo, per category** (correct/n, accuracy %)

| Arm | cat1-multi-hop (n=282) | cat2-temporal (n=321) | cat3-open-domain (n=96) | cat4-single-hop (n=841) | cat5-adversarial (n=446) |
|---|---|---|---|---|---|
| flux_reason | 158/282 56.0 | 232/321 72.3 | 38/96 39.6 | 701/841 83.4 | 426/446 95.5 |
| flux_evidence | 153/282 54.3 | 141/321 43.9 | 53/96 55.2 | 738/841 87.8 | 391/446 87.7 |
| flux_public | 149/282 52.8 | 146/321 45.5 | 56/96 58.3 | 737/841 87.6 | 399/446 89.5 |
| honcho_chat | 203/282 72.0 | 276/321 86.0 | 59/96 61.5 | 753/841 89.5 | 409/446 91.7 |

**LongMemEval-S, per question type** (correct/n, accuracy %; cells of 6 to 27 questions, not tested)

| Arm | knowledge-update (n=15) | multi-session (n=27) | single-session-assistant (n=11) | single-session-preference (n=6) | single-session-user (n=14) | temporal-reasoning (n=27) |
|---|---|---|---|---|---|---|
| flux_reason | 12/15 80 | 17/27 63 | 10/11 91 | 4/6 67 | 14/14 100 | 23/27 85 |
| flux_evidence | 14/15 93 | 22/27 81 | 11/11 100 | 5/6 83 | 14/14 100 | 25/27 93 |
| flux_public | 10/15 67 | 18/27 67 | 11/11 100 | 6/6 100 | 14/14 100 | 25/27 93 |
| honcho_chat | 12/15 80 | 15/27 56 | 11/11 100 | 6/6 100 | 14/14 100 | 23/27 85 |

**Verdict against the preregistered threshold** (within 5.0 points of honcho_chat on LoCoMo categories 1 to 4, that is at least 1214 of 1540 correct): flux_reason scored 1129/1540 (73.3%), honcho_chat 1291/1540 (83.8%), flux_evidence 1085/1540 (70.5%). Gap to honcho_chat: -10.5 points; share of the honcho_chat minus flux_evidence gap closed: 21%. Verdict: **does not close most of the gap**.

**Cost and failures** (USD; pass 1 = the reasoning call, pass 2 = reader plus judge, both from the arm's own summaries)

| Bench | Pass 1 | Pass 2 reader | Pass 2 judge | Arm total | Pass-1 failures | Empty notes | Rows scored as error | Empty reader answers |
|---|---|---|---|---|---|---|---|---|
| LongMemEval-S | 0.0726 | 0.0421 | 0.0090 | 0.1237 | 0 | 0 | 0 | 0 |
| LoCoMo | 0.7715 | 0.5370 | 0.2757 | 1.5842 | 0 | 0 | 0 | 1 |

Arm total 1.7079 USD from the summaries; ledger lines for the arm (`results-public/ledger-flux_reason.jsonl`) sum to 1.7079 USD against the arm's cap of 10 USD. The qa summaries record prompt_sha256 `cb2ed8ffeaf930b7...` (LongMemEval) and `f0ce4540d38d093a...` (LoCoMo), equal to the honcho_chat arm's: yes.

<!-- temporal -->
**Accuracy** (reference arms are earlier numbers, repeated here for comparison only; this arm is in-sample, see the caution above)

**LongMemEval-S (n=100)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty |
|---|---|---|---|---|---|
| flux_temporal | 84/100 | 84.0 | 75.6 to 89.9 | 0 | 1 |
| flux_evidence | 91/100 | 91.0 | 83.8 to 95.2 | 0 | 1 |
| flux_public | 84/100 | 84.0 | 75.6 to 89.9 | 0 | 1 |
| flux_reason | 80/100 | 80.0 | 71.1 to 86.7 | 0 | 0 |
| honcho_chat | 81/100 | 81.0 | 72.2 to 87.5 | 0 | 0 |

**LoCoMo categories 1-4 (n=1540, preregistered headline)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty |
|---|---|---|---|---|---|
| flux_temporal | 1160/1540 | 75.3 | 73.1 to 77.4 | 1 | 2 |
| flux_evidence | 1085/1540 | 70.5 | 68.1 to 72.7 | 1 | 3 |
| flux_public | 1088/1540 | 70.6 | 68.3 to 72.9 | 2 | 7 |
| flux_reason | 1129/1540 | 73.3 | 71.0 to 75.5 | 0 | 1 |
| honcho_chat | 1291/1540 | 83.8 | 81.9 to 85.6 | 0 | 0 |

**LoCoMo category 5 adversarial (n=446)**

| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty |
|---|---|---|---|---|---|
| flux_temporal | 394/446 | 88.3 | 85.0 to 91.0 | 0 | 0 |
| flux_evidence | 391/446 | 87.7 | 84.3 to 90.4 | 0 | 0 |
| flux_public | 399/446 | 89.5 | 86.3 to 92.0 | 0 | 0 |
| flux_reason | 426/446 | 95.5 | 93.2 to 97.1 | 0 | 0 |
| honcho_chat | 409/446 | 91.7 | 88.8 to 93.9 | 0 | 0 |

**Paired differences.** Difference = flux_temporal minus the other arm, percentage points (positive favours flux_temporal), on identical items. Bootstrap: 10,000 resamples, seed 20261003. Holm is applied across these 4 comparisons within each item set; these tests stand on their own and are not part of the main report's Holm family. flux_temporal is a composition of stored flux_reason and flux_evidence results, so it overlaps both by construction.

**LongMemEval-S (n=100)**

| Other arm | Diff pts | Item bootstrap 95% | flux_temporal only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|
| flux_evidence | -7.0 | -12.0 to -3.0 | 0 | 7 | 0.01562 | 0.0625 |
| flux_public | +0.0 | -7.0 to +7.0 | 6 | 6 | 1 | 1 |
| flux_reason | +4.0 | +1.0 to +8.0 | 4 | 0 | 0.125 | 0.375 |
| honcho_chat | +3.0 | -5.0 to +11.0 | 10 | 7 | 0.6291 | 1 |

**LoCoMo categories 1-4 (n=1540, preregistered headline)**

| Other arm | Diff pts | Item bootstrap 95% | Conversation-clustered 95% | flux_temporal only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| flux_evidence | +4.9 | +3.2 to +6.5 | +2.6 to +7.4 | 121 | 46 | 5.735e-09 | 1.721e-08 |
| flux_public | +4.7 | +2.7 to +6.6 | +2.3 to +7.2 | 156 | 84 | 3.914e-06 | 7.827e-06 |
| flux_reason | +2.0 | +0.5 to +3.5 | +0.6 to +3.3 | 86 | 55 | 0.01126 | 0.01126 |
| honcho_chat | -8.5 | -10.6 to -6.4 | -10.2 to -6.4 | 76 | 207 | 3.47e-15 | 1.388e-14 |

**LoCoMo category 5 adversarial (n=446)**

| Other arm | Diff pts | Item bootstrap 95% | Conversation-clustered 95% | flux_temporal only right | Other only right | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| flux_evidence | +0.7 | +0.0 to +1.6 | +0.0 to +1.6 | 3 | 0 | 0.25 | 0.5 |
| flux_public | -1.1 | -3.6 to +1.3 | -3.6 to +1.3 | 13 | 18 | 0.4731 | 0.5 |
| flux_reason | -7.2 | -9.9 to -4.5 | -8.6 to -5.4 | 5 | 37 | 4.434e-07 | 1.773e-06 |
| honcho_chat | -3.4 | -6.1 to -0.7 | -5.8 to -0.7 | 13 | 28 | 0.02753 | 0.0826 |

**LoCoMo, per category** (correct/n, accuracy %)

| Arm | cat1-multi-hop (n=282) | cat2-temporal (n=321) | cat3-open-domain (n=96) | cat4-single-hop (n=841) | cat5-adversarial (n=446) |
|---|---|---|---|---|---|
| flux_temporal | 151/282 53.5 | 233/321 72.6 | 50/96 52.1 | 726/841 86.3 | 394/446 88.3 |
| flux_evidence | 153/282 54.3 | 141/321 43.9 | 53/96 55.2 | 738/841 87.8 | 391/446 87.7 |
| flux_public | 149/282 52.8 | 146/321 45.5 | 56/96 58.3 | 737/841 87.6 | 399/446 89.5 |
| flux_reason | 158/282 56.0 | 232/321 72.3 | 38/96 39.6 | 701/841 83.4 | 426/446 95.5 |
| honcho_chat | 203/282 72.0 | 276/321 86.0 | 59/96 61.5 | 753/841 89.5 | 409/446 91.7 |

**LongMemEval-S, per question type** (correct/n, accuracy %; cells of 6 to 27 questions, not tested)

| Arm | knowledge-update (n=15) | multi-session (n=27) | single-session-assistant (n=11) | single-session-preference (n=6) | single-session-user (n=14) | temporal-reasoning (n=27) |
|---|---|---|---|---|---|---|
| flux_temporal | 13/15 87 | 18/27 67 | 11/11 100 | 5/6 83 | 14/14 100 | 23/27 85 |
| flux_evidence | 14/15 93 | 22/27 81 | 11/11 100 | 5/6 83 | 14/14 100 | 25/27 93 |
| flux_public | 10/15 67 | 18/27 67 | 11/11 100 | 6/6 100 | 14/14 100 | 25/27 93 |
| flux_reason | 12/15 80 | 17/27 63 | 10/11 91 | 4/6 67 | 14/14 100 | 23/27 85 |
| honcho_chat | 12/15 80 | 15/27 56 | 11/11 100 | 6/6 100 | 14/14 100 | 23/27 85 |

**Router readouts** (reported only, no bar; the category and type labels were never shown to the router and are used here after the run)

| Item set | Routed TEMPORAL | Share | Truth label | True positives | Precision % | Recall % | Unparseable | Failed calls |
|---|---|---|---|---|---|---|---|---|
| LongMemEval-S (n=100) | 51/100 | 51.0% | type temporal-reasoning (n=27) | 27 | 52.9 | 100.0 | 0 | 0 |
| LoCoMo categories 1-4 | 513/1540 | 33.3% | category 2 (n=321) | 320 | 62.4 | 99.7 | 0 | 0 |
| LoCoMo all five categories | 585/1986 | 29.5% | category 2 (n=321) | 320 | 54.7 | 99.7 | 0 | 0 |

**Verdict against the preregistered bars** (all against flux_evidence; exploratory, in-sample: a PASS only justifies an out-of-sample confirmation)

| Bar | Requirement | Observed | Result |
|---|---|---|---|
| (i) LoCoMo categories 1-4 | diff at least +4.0 pts and the conversation-clustered 95% interval excludes zero | +4.9 pts, clustered +2.6 to +7.4 | **PASS** |
| (ii) LongMemEval-S | diff at least -2.0 pts | -7.0 pts | **FAIL** |
| (iii) LoCoMo categories 1, 3, 4 | none falls by more than 2.0 pts | cat1 -0.7, cat3 -3.1, cat4 -1.4 pts | **FAIL** |
| Overall | all three | | **FAIL** |

Gap to honcho_chat on LoCoMo categories 1-4: -8.5 points (flux_temporal minus honcho_chat; conversation-clustered -10.2 to -6.4).

**Cost** (USD; router calls are the only new spend; the chosen path's reader, judge and, for the flux_reason path, pass-1 costs are the stored ones; shared ingest, extraction and retrieval are not counted)

| Bench | Router | Chosen paths (stored calls) | Arm total | Router failures | Items on the flux_reason path |
|---|---|---|---|---|---|
| LongMemEval-S | 0.0024 | 0.1440 | 0.1464 | 0 | 51 |
| LoCoMo | 0.0451 | 1.8129 | 1.8580 | 0 | 585 |

Ledger lines for the arm (`results-public/ledger-flux_temporal.jsonl`) sum to 0.0475 USD against the arm's cap of 3 USD.
