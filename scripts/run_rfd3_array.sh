#!/bin/bash
# ==============================================================================
# RFD3 SLURM Array Job -- ExpertGuess contigs (motifs 12-30)
# Uses the official expert-crafted contig recipe (example/contig_specifications.csv
# from the shared MotifBench install) instead of our own AutoContigmap contigs,
# to isolate the generative-model effect (RFD3 vs RFdiffusion1) while holding
# the contig choice fixed. One array task per motif.
# ==============================================================================

#SBATCH --job-name=ExpertGuess_RFD3
#SBATCH -c 4
#SBATCH --nodes=1
#SBATCH --reservation=AIPD
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
#SBATCH --time=10:00:00
#SBATCH --array=0-29%5
#SBATCH --output=/zfs/s01/z04/home/kleiter/Projects/MotifBench/RFD3/ExpertGuess/benchmark/logs/rfd3_%A_%a.out

BASE_DIR="/zfs/s01/z04/home/kleiter/Projects/MotifBench/RFD3/ExpertGuess/benchmark"
INPUTS_DIR="${BASE_DIR}/inputs"
SCAFFOLD_DIR="$(dirname "${BASE_DIR}")/scaffolds"
CKPT_PATH="/work/kleiter/checkpoints/rfd3_latest.ckpt"

N_BATCHES=${N_BATCHES:-100}
DIFFUSION_BATCH_SIZE=1

MOTIFS=(01_1LDB 02_1ITU 03_2CGA 04_5WN9 05_5ZE9 06_6E6R 07_6E6R 08_7AD5 09_7CG5 10_7WRK 11_3TQB 12_4JHW 13_4JHW 14_5IUS 15_7A8S 16_7BNY 17_7DGW 18_7MQQ 19_7MQQ 20_7UWL 21_1B73 22_1BCF 23_1MPY 24_1QY3 25_2RKX 26_3B5V 27_4XOJ 28_5YUI 29_6CPA 30_7UWL)
motif_name="${MOTIFS[$SLURM_ARRAY_TASK_ID]}"

INPUT_JSON="${INPUTS_DIR}/${motif_name}.json"
OUTPUT_DIR="${SCAFFOLD_DIR}/${motif_name}"
mkdir -p "${OUTPUT_DIR}"

echo "========================================"
echo " RFD3 Array Task Starting"
echo " $(date)"
echo "========================================"
echo " Array task : ${SLURM_ARRAY_TASK_ID}"
echo " Motif      : ${motif_name}"
echo " Input JSON : ${INPUT_JSON}"
echo " Output dir : ${OUTPUT_DIR}"
echo " N_BATCHES  : ${N_BATCHES}"
echo "========================================"

if [[ ! -f "${INPUT_JSON}" ]]; then
    echo "ERROR: Input JSON not found: ${INPUT_JSON}"
    exit 1
fi

conda run -n rfd3 rfd3 design \
    out_dir="${OUTPUT_DIR}" \
    inputs="${INPUT_JSON}" \
    prevalidate_inputs=True \
    n_batches="${N_BATCHES}" \
    diffusion_batch_size="${DIFFUSION_BATCH_SIZE}" \
    ckpt_path="${CKPT_PATH}"

EXIT_CODE=$?

echo "========================================"
if [[ ${EXIT_CODE} -eq 0 ]]; then
    echo " Task finished successfully — $(date)"
else
    echo " Task FAILED with exit code ${EXIT_CODE} — $(date)"
fi
echo "========================================"

exit ${EXIT_CODE}
