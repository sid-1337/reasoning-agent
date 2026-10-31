# Classical Logic Reasoning Agent

## Project Overview

This project predicts whether a query follows from a knowledge base of facts and rules. It uses symbolic inference; a generative model does not make the final True/False decision.

The implementation is deliberately split into data handling, language/formula parsing, and inference so the reasoning core can be inspected independently.

## Project Map

| Path | Purpose |
| --- | --- |
| `submission/reasoning_agent.ipynb` | Dataset loading, parsing, experiments, metrics, traces, and submission CSV generation. |
| `submission/logic_engine.py` | Core representation, unification, and forward chaining. |
| `submission/folio_horn_adapter.py` | Strict adapter for the supported Horn subset of FOLIO's formal formulas. |

## Run the Notebook

Requirements: Python 3.10 or later, Jupyter, and network access to Hugging Face for dataset downloads. The notebook installs the `datasets` package in its active kernel. FOLIO access also requires accepting the dataset's access terms and authenticating with Hugging Face.

1. Open `submission/reasoning_agent.ipynb`.
2. Run the cells from top to bottom. Public dataset loading is enabled in the current notebook configuration.
3. Review the printed schema, coverage, accuracy, inference time, and reasoning trace outputs.

The notebook uses RuleTaker's `test` split, two CounterBench JSON files, and FOLIO's `validation` split. It does not open private evaluation data automatically.

## Reasoning Method

Facts are represented as signed atoms and rules as Horn clauses. The inference engine unifies rule variables with known facts and applies forward chaining until it reaches a fixed point. FOLIO records are first attempted through their formal logic fields; unsupported formulas fall back to the limited controlled-English parser.

This is not a complete first-order theorem prover. Existential conjunctions and Horn implications are supported in the FOL adapter; disjunction, exclusive-or, nested quantifiers, and other unsupported formulas are reported rather than guessed.

## Latest Public-Data Run

Results below are from the latest recorded notebook run. Inference time includes parsing and reasoning for each loaded split; timing is environment-dependent.

| Dataset and split | Rows | Supported | Coverage | Accuracy on supported labeled rows | Time |
| --- | ---: | ---: | ---: | ---: | ---: |
| RuleTaker `test` | 250 | 250 | 100.00% | 97.60% | 0.238 s |
| CounterBench | 1,200 | 0 | 0.00% | Not measured | 0.181 s |
| FOLIO `validation` | 203 | 55 | 27.09% | 83.33% | 0.072 s |

Coverage and accuracy are different. FOLIO accuracy is only for the supported subset with a recognized True/False label; it is not overall FOLIO accuracy. CounterBench uses intervention and counterfactual semantics that this Horn reasoner does not implement, so it currently reports no accuracy for that dataset.

## Generate a Submission CSV

Prepare an input CSV with an ID column, a context column, and a query column. Accepted names include `ID` or `id`, `context` or `premises`, and `question`, `query`, or `statement`. In the notebook, call:

```python
generate_submission_from_csv(
	"submission/evaluation_input.csv",
	"submission/submission.csv",
)
```

The output columns are `ID` and `Label`, with labels written as `True` or `False`. Generation stops if an input row is unsupported, rather than silently writing an incomplete file. The submission CSV is not created until this function is explicitly called.

## Dataset-Backed Export Included in This Repo

This repository also includes a concrete export at `submission/submission.csv` that was generated from the actual public datasets loaded in the notebook (`RuleTaker`, `CounterBench`, and `FOLIO`). It is not synthetic or fabricated data. The file stores the original records alongside the model's prediction for each example.

Current export schema:

```csv
dataset,id,context,question,answer,predicted_answer,status
RuleTaker,0,"Facts:\nLiam volunteers...","The book volunteers.","False","False","ok"
```

`answer` preserves the original dataset label, `predicted_answer` records the reasoner output, and `status` records whether the row was supported by the parser/reasoner. The current export contains all loaded public rows: 250 RuleTaker + 1,200 CounterBench + 203 FOLIO = 1,653 rows.

This export is useful for inspection and debugging because it lets you compare the source text, the gold answer, and the actual predicted answer side by side. If you need the benchmark-ready submission format with only `ID,Label`, use the `generate_submission_from_csv(...)` helper above on a CSV that contains eligible rows.

## Interpreting False

The benchmark uses binary labels, so a query that is not derived is returned as `False`. Under open-world logic, failure to derive a query is not proof of its negation. The report should distinguish this benchmark convention from classical entailment of a negative statement.
