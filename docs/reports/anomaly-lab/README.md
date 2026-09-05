# Published synthetic experiment evidence

These are exact JSON copies from two completed Mac lab runs. They are committed
so teammates can inspect the results without regenerating a local experiment.
They contain synthetic inputs and measured model outputs, not real operational
data, saved model objects, signatures or deployable packages.

- [Candidate report](candidate-002/training-report.json),
  [normal calibration reference](candidate-002/calibration-reference.json),
  [dataset manifest](candidate-002/dataset-manifest.json).
- [Paired calibration comparison](calibration-comparison-001/comparison-report.json),
  [comparison references](calibration-comparison-001/comparison-references.json),
  [comparison membership](calibration-comparison-001/comparison-membership.json).

Keep the JSON bytes unchanged when verifying their SHA-256 links. Reformatting
changes the digest. Source-code digests identify the code used for each run;
later code edits do not retroactively change that evidence. Model fitting used
the recorded versions and seeds; timing measurements can differ on another run.

The [training guide](../../guides/anomaly-training.md) documents reproduction commands,
normal-request results, challenge misses and limitations. New generated runs
remain ignored under `artifacts/anomaly-lab/`; update this curated evidence only
when intentionally recording another measured experiment.
