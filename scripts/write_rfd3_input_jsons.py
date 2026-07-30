#!/usr/bin/env python3
"""
write_rfd3_input_jsons.py (RFD3 + ExpertGuess contigs)

Same purpose as RFD3/AutoContigmap's script of the same name, but using the
official expert-crafted contig recipe (example/contig_specifications.csv from
the shared MotifBench install -- the exact contigs used to generate the
"ExpertGuess" reference RFdiffusion(v1) scaffolds) instead of our own
auto-computed AutoContigmap contigs. This isolates the generative-model effect
(RFD3 vs RFdiffusion1) while holding the contig recipe fixed.

Key difference from AutoContigmap's version: the expert contigs reference the
ORIGINAL multi-chain motif structure (e.g. 22_1BCF has segments on chains
A/B/C/D) rather than the RFD1-specific single-chain-collapsed motif_pdbs --
so motif_pdbs/ here is copied from motif_pdbs_raw (pre-collapse, multi-chain),
and UNK->GLY relabeling / select_unfixed_sequence detection must scan ALL
chains, not just "A".

Usage
-----
python write_rfd3_input_jsons.py contig_specifications.csv motif_pdbs/ motif_pdbs_gly/ inputs/
"""
import csv
import json
import sys
from pathlib import Path

from Bio.PDB import PDBParser


def relabel_unk_to_gly(in_pdb, out_pdb):
    """Rewrites in_pdb with UNK->GLY (all chains). Returns {chain: [unk_res_ids]}."""
    with open(in_pdb) as f:
        lines = f.readlines()

    unk_by_chain = {}
    out_lines = []
    for line in lines:
        if line.startswith(("ATOM", "HETATM", "TER")) and line[17:20] == "UNK":
            if line.startswith(("ATOM", "HETATM")):
                chain = line[21]
                resnum = int(line[22:26])
                unk_by_chain.setdefault(chain, set()).add(resnum)
            line = line[:17] + "GLY" + line[20:]
        out_lines.append(line)

    with open(out_pdb, "w") as f:
        f.writelines(out_lines)

    return {c: sorted(ids) for c, ids in unk_by_chain.items()}


def collapse_to_ranges(chain, res_ids):
    if not res_ids:
        return []
    ranges = []
    start = prev = res_ids[0]
    for n in res_ids[1:]:
        if n == prev + 1:
            prev = n
        else:
            ranges.append((start, prev))
            start = prev = n
    ranges.append((start, prev))
    return [f"{chain}{a}" if a == b else f"{chain}{a}-{b}" for a, b in ranges]


def main():
    if len(sys.argv) != 5:
        print(f"Usage: {sys.argv[0]} contig_specifications.csv motif_pdbs/ motif_pdbs_gly/ inputs/", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    motif_pdb_dir = Path(sys.argv[2])
    gly_pdb_dir = Path(sys.argv[3])
    out_dir = Path(sys.argv[4])
    gly_pdb_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        problem = row["problem"]
        length = row["length"]
        contig = row["contig"].replace(";", ",")
        in_pdb = motif_pdb_dir / f"{problem}.pdb"
        out_pdb = gly_pdb_dir / f"{problem}.pdb"

        unk_by_chain = relabel_unk_to_gly(in_pdb, out_pdb)
        unfixed_seq_ranges = []
        for chain in sorted(unk_by_chain):
            unfixed_seq_ranges.extend(collapse_to_ranges(chain, unk_by_chain[chain]))

        motif_spec = {
            "dialect": 2,
            "input": str(out_pdb.resolve()),
            "contig": contig,
            "length": str(length),
            "is_non_loopy": True,
        }
        if unfixed_seq_ranges:
            motif_spec["select_unfixed_sequence"] = ",".join(unfixed_seq_ranges)

        payload = {"motif": motif_spec}

        out_path = out_dir / f"{problem}.json"
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"wrote {out_path} (unfixed_seq={unfixed_seq_ranges or None})")


if __name__ == "__main__":
    main()
