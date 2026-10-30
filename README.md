AI Reasoning Agent

Files
- reasoning_agent.ipynb: Python implementation, experiments, metrics, and CSV submission writer.

Requirements
- Python 3.10 or later
- Jupyter Notebook or JupyterLab
- The `datasets` package only if downloading public Hugging Face datasets

Run
1. Open reasoning_agent.ipynb and run all cells from top to bottom.
2. By default, public dataset downloads are disabled. To evaluate on public data, set LOAD_PUBLIC_DATASETS = True in the dataset section. Confirm the repository IDs and split names there match the Hugging Face dataset configurations available in your environment.
3. The notebook reports accuracy only for successfully parsed examples with recognized labels. It also reports parser coverage and inference time. The built-in synthetic examples are smoke tests, not benchmark results.

Submission CSV
Provide an evaluation CSV with an ID column, a context column, and a question/query/statement column. Then call:

generate_submission_from_csv("submission/evaluation_input.csv", "submission/submission.csv")

The output contains ID and Label columns, with labels written as True or False. The writer stops if any row is unsupported, rather than silently omitting examples or writing partial predictions. No evaluation or private test file is opened automatically.

Reasoning Scope
The engine uses first-order term unification and forward chaining over signed Horn clauses. The text parser supports a limited controlled-English subset, including simple property facts, binary relations, conjunctions, explicit negated facts, and universally quantified If/then rules. It is not a complete first-order logic parser or theorem prover. Unsupported statements are reported; absence of a derivation is labeled False according to the benchmark's binary-label convention and does not establish logical negation under open-world semantics.
