# IBM AML sample provenance

`ibm-aml-transactions.csv` is a deterministic investigation slice of the
public IBM Transactions for Anti-Money Laundering benchmark (HI-Small).

- Dataset page: https://huggingface.co/datasets/eexzzm/IBM-Transactions-for-Anti-Money-Laundering-HI-Small-Trans
- Research context: IBM's “Realistic Synthetic Financial Transactions for
  Anti-Money Laundering Models” benchmark.
- The slice prioritizes all source-labelled laundering transactions, then adds
  ordinary transactions connected to those accounts up to 15,000 rows.
- Bank IDs are namespaced into account IDs to preserve cross-bank identity.
- Original timestamps, amounts, currencies, sender/receiver links, and payment
  formats are retained. `ibm-aml-source-labels.csv` keeps the original labels,
  but MuleTrace does not use them as detector input.

This is a public synthetic benchmark, not identifiable customer bank data.
