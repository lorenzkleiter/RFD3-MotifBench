# RFD3 MotifBench benchmark (ExpertGuess contig recipe)

Motif-scaffolding backbones for all 30 [MotifBench](https://github.com/blt2114/MotifBench)
benchmark problems, generated with **RFD3** (RosettaFold Diffusion 3). We used the
exact same expert-crafted contig recipe that MotifBench's own official "ExpertGuess"
reference scaffolds were generated with (`example/contig_specifications.csv` in the
MotifBench repository). Keeping the contig/placement strategy fixed and only swapping
out the generative model gives a direct, apples-to-apples comparison against the
officially published RFdiffusion(1) reference results.

## Method

- **Model:** RFD3, checkpoint `rfd3_latest.ckpt`.
- **Contig recipe:** MotifBench's official expert-crafted contigs
  (`scripts/contig_specifications.csv` in this repo, copied verbatim from
  MotifBench's `example/contig_specifications.csv`). In other words, the same
  segment placement and gap ranges used to generate the published ExpertGuess
  reference backbones, just run through RFD3 instead of RFdiffusion(1).
- **Generation settings:** `n_batches=100`, `diffusion_batch_size=1` per problem
  (100 backbones per problem, matching the standard MotifBench design budget),
  `prevalidate_inputs=True`, everything else left at RFD3's defaults.
- **UNK → GLY relabeling (generation input only):** MotifBench marks "redesign
  positions" (structurally required, sequence left open) as `UNK` residues with
  backbone-only atoms. Feeding `UNK` straight into RFD3 crashes its
  non-standard-residue atomization pathway, since `UNK` isn't in RFD3's
  `STANDARD_AA` allowlist, unlike `GLY`, which has the same backbone-only
  geometry. To get around this, we relabel `UNK` to `GLY` in the structure fed
  to RFD3 only, and mark those exact positions via RFD3's
  `select_unfixed_sequence` field so it still designs a real identity there
  instead of treating "GLY" as the fixed answer. Evaluation reads from the
  original, untouched `UNK`-labeled reference PDBs, so none of this affects
  scoring or redesign-position detection.
- **Multi-chain motifs:** a handful of problems (e.g. `22_1BCF`, `25_2RKX`)
  place motif segments across multiple original chains. `select_unfixed_sequence`
  and the `UNK` to `GLY` relabeling are computed per chain, not just for chain A.

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
- `scripts/contig_specifications.csv`: the expert contig recipe used, copied
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
  cluster. Each per-problem job used 1 GPU, 4 CPU cores, and 16 GB RAM.

Self-consistency evaluation compute (ProteinMPNN, ESMFold, Foldseek) is
separate and isn't included in the numbers above.

## Data availability

Submitted scaffold set, full evaluation results, and summary results:
`<Zenodo DOI to be added>`

## Contact

Lorenz Kleiter, lorenz.kleiter@tum.de
