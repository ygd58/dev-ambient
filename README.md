# Dev x Ambient - Week 9
## Output Verification Classifier

A lightweight Python wrapper that classifies LLM outputs from Ambient GLM-5 into three categories:

- DETERMINISTIC: formulaic, always reproducible, verifiable
- PROBABILISTIC: predictions, estimates, likelihood-based
- UNVERIFIABLE: incomplete, ambiguous, unevaluatable

Outputs that mix categories are automatically rejected.

## Usage

python3 classifier.py

## Test Results Week 9

| Output | Classification | Action |
|---|---|---|
| Compound interest calculation | DETERMINISTIC | ACCEPT |
| Bitcoin price prediction | MIXED | REJECT |
| Smart contract audit complete | UNVERIFIABLE | REJECT |
| Smart contract audit incomplete | UNVERIFIABLE | REJECT |

## Key Finding

GLM-5 returned an incomplete response on the smart contract query, cutting off mid-sentence. The classifier correctly flagged it as UNVERIFIABLE and REJECT. This is exactly the behavior a production pipeline needs.

More info: ambient.xyz
