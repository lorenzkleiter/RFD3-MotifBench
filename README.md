# General Information
All 30 [MotifBench](https://github.com/blt2114/MotifBench)
benchmark problems, were generated with [**RFD3**](https://www.biorxiv.org/content/10.1101/2025.09.18.676967v1) (RosettaFold Diffusion 3) on a cluster of the Technical University of Munich (TUM).

## Method

- **Model:** RFD3, checkpoint `rfd3_latest.ckpt` (dated 2026-06-03).
- **Contigs:** MotifBench's reference contigmaps were translated 1 to 1 to the RFD3 style.
  (`scripts/contig_specifications.csv` in this repo, copied from
  MotifBench's `example/contig_specifications.csv`). In other words, the same
  segment placement and gap ranges used to generate the
  reference backbones were used.
- **Generation settings:** `n_batches=100`, `diffusion_batch_size=1` per problem,
  `prevalidate_inputs=True` and `is_non_loopy: True`.
- **UNK → GLY relabeling (generation input only):** MotifBench marks "redesign
  positions" (structurally required, sequence left open) as `UNK` residues with
  backbone-only atoms. Feeding `UNK` straight into RFD3 crashes its
  non-standard-residue atomization pathway, since `UNK` isn't in RFD3's
  `STANDARD_AA` allowlist, unlike `GLY`, which has the same backbone-only
  geometry. To get around this, we copied the motifs, relabeled `UNK` to `GLY`
  and marked those exact positions via RFD3's `select_unfixed_sequence` field.
  Meanwhile the evaluation reads from the original, `UNK`-labeled reference PDBs.
  Everything else was left to the RFD3 defaults.

## Scripts

- `scripts/write_rfd3_input_jsons.py`: builds one RFD3 input JSON per problem
  from `contig_specifications.csv`, handling the `UNK`/`GLY` relabeling and the
  multi-chain `select_unfixed_sequence` construction described above.
- `scripts/run_rfd3_array.sh`: SLURM array launcher, one task per problem,
  calling RFD3's CLI (`rfd3 design ...`) with the generated JSON.
- `scripts/convert_rfd3_outputs.py`: converts RFD3's native output format
  (gzipped mmCIF plus per-design JSON metadata) into the `.pdb` and
  `scaffold_info.csv` format MotifBench's evaluation pipeline
  (`Scaffold-Lab/motif_refolding.py`) expects. It works out each design's
  realized motif placement from the JSON's `specification.extra.sampled_contig`
  field, since RFD3 randomizes gap lengths per sample the same way
  RFdiffusion(1) does.
- `scripts/contig_specifications.csv`: the referemce contigs used, copied
  from MotifBench's `example/` directory.

Evaluation itself used MotifBench's own unmodified `scripts/evaluate_bbs.sh`
pipeline (ProteinMPNN self-consistency, ESMFold, Foldseek clustering). No
evaluation-side code was changed.

## Results

Produced by MotifBench's `scripts/summarize_results.sh` (our local MotifBench
checkout didn't have a script called `collect_summaries.sh` specifically;
`summarize_results.sh` is what produces both `summary_by_problem.csv` and the
group/overall summary below, including the official bootstrap MotifBench
score):

| Group | Number Solved | Mean Num_Solutions | Mean Novelty | Mean Success Rate |
|---|---|---|---|---|
| 1 (01–10) | 8/10 | 12.60 | 0.29 | 21.40% |
| 2 (11–20) | 8/10 | 2.30 | 0.29 | 13.80% |
| 3 (21–30) | 9/10 | 6.10 | 0.31 | 30.20% |
| **Overall** | 25/30 | 7.00 | 0.30 | 21.80% |

**MotifBench score: 36.04**

Full per-problem numbers: [`results/summary_by_problem.csv`](results/summary_by_problem.csv).
Group/overall numbers: [`results/overall_summary.csv`](results/overall_summary.csv).

## Compute resources

Backbone generation (RFD3 inference only, not evaluation) for all 30 problems
times 100 backbones each (3000 backbones total) took:

- **Total GPU time:** 36,520 s, about **10.14 GPU-hours**
- **Per backbone:** about **12.2 seconds** (36,520 s / 3000 backbones)
- **Hardware:** a mix of NVIDIA RTX 5090 (14 of the 30 per-problem generation
  jobs, roughly 3.53 GPU-hours) and NVIDIA RTX PRO 6000 Blackwell Server
  Edition (16 of the 30 jobs, roughly 6.62 GPU-hours), on a university
  cluster. Each per-problem job used 1 MIG partition, 4 CPU cores, and 16 GB RAM.

## Data availability

Submitted scaffold set, full evaluation results, and summary results:
`<Zenodo DOI to be added>`

## Contact

Lorenz Kleiter, lorenz.kleiter@tum.de
