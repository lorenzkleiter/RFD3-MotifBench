#!/usr/bin/env python3
"""
convert_rfd3_outputs.py

RFD3 writes gzipped mmCIF (`<motif>_motif_<i>_model_0.cif.gz`) + a paired JSON
with per-design metadata, but Scaffold-Lab's motif_refolding.py expects `.pdb`
files named `<motif>_<sample_idx>.pdb` plus a `scaffold_info.csv` describing
motif placement per design (same format RFD1's write_scaffold_info.py
produces, derived there from output-PDB B-factors).

RFD3 has no B-factor convention, but its JSON's specification.extra.sampled_contig
gives the exact realized per-design contig directly, e.g.:

  "24,A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,A11,A12,A13,A14,A15,A16,A17,39,A18,...,A24,13"

-- plain integers are scaffold-segment lengths; runs of consecutive "A<n>"
tokens are one motif segment each (RFD3 enumerates every fixed residue
individually rather than as a range). Since our generation input collapsed
the motif onto a single chain "A", each such run is mapped back to the
ORIGINAL per-segment chain letter (from contig_specifications.csv, in
segment order) -- exactly what write_scaffold_info.py already does for RFD1.

Usage
-----
python convert_rfd3_outputs.py <scaffolds_dir> <contig_specifications.csv> <out_dir> [motif_name]

If motif_name is omitted, converts every motif subdir found in scaffolds_dir.
"""
import csv
import gzip
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from Bio.PDB import MMCIFParser, PDBIO


def parse_contig_specifications(contig_file):
    """Same convention as write_scaffold_info.py: chain letters in segment order."""
    chain_order = {}
    with open(contig_file, newline="") as f:
        for row in csv.DictReader(f):
            problem = row["problem"]
            contig = row["contig"]
            chains = [seg[0] for seg in contig.split(";") if seg and seg[0].isalpha()]
            chain_order[problem] = chains
    return chain_order


def parse_sampled_contig(sampled_contig, chains):
    """Return the "/".join(placements) string in write_scaffold_info.py's format."""
    tokens = sampled_contig.split(",")
    placements = []
    motif_index = 0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok and tok[0].isalpha():
            run_len = 0
            while i < len(tokens) and tokens[i] and tokens[i][0].isalpha():
                run_len += 1
                i += 1
            chain = chains[motif_index] if motif_index < len(chains) else "?"
            placements.append(f"{chain}:{run_len}")
            motif_index += 1
        else:
            placements.append(tok)
            i += 1
    return "/".join(placements)


def convert_one_motif(scaffolds_dir, motif_name, chains, out_dir):
    src_dir = scaffolds_dir / motif_name
    dst_dir = out_dir / motif_name
    dst_dir.mkdir(parents=True, exist_ok=True)

    parser = MMCIFParser(QUIET=True)
    io = PDBIO()
    rows = []

    cif_files = sorted(src_dir.glob(f"{motif_name}_motif_*_model_0.cif.gz"))
    if not cif_files:
        print(f"warning: no .cif.gz files found for {motif_name} in {src_dir}", file=sys.stderr)
        return

    for cif_gz in cif_files:
        m = re.match(rf"{re.escape(motif_name)}_motif_(\d+)_model_0\.cif\.gz", cif_gz.name)
        sample_idx = int(m.group(1))
        json_path = cif_gz.with_suffix("").with_suffix(".json")

        with gzip.open(cif_gz, "rt") as f_in, tempfile.NamedTemporaryFile(
            mode="w", suffix=".cif", delete=False
        ) as f_tmp:
            shutil.copyfileobj(f_in, f_tmp)
            tmp_path = f_tmp.name

        structure = parser.get_structure(motif_name, tmp_path)
        Path(tmp_path).unlink()

        out_pdb = dst_dir / f"{motif_name}_{sample_idx}.pdb"
        io.set_structure(structure)
        io.save(str(out_pdb))

        with open(json_path) as f:
            meta = json.load(f)
        sampled_contig = meta["specification"]["extra"]["sampled_contig"]
        motif_placements = parse_sampled_contig(sampled_contig, chains)
        rows.append([sample_idx, motif_placements])

    rows.sort(key=lambda r: r[0])
    with open(dst_dir / "scaffold_info.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sample_num", "motif_placements"])
        writer.writerows(rows)

    print(f"{motif_name}: converted {len(rows)} designs -> {dst_dir}")


def main():
    if len(sys.argv) not in (4, 5):
        print(f"Usage: {sys.argv[0]} <scaffolds_dir> <contig_specifications.csv> <out_dir> [motif_name]", file=sys.stderr)
        sys.exit(1)

    scaffolds_dir = Path(sys.argv[1])
    contig_file = sys.argv[2]
    out_dir = Path(sys.argv[3])
    only_motif = sys.argv[4] if len(sys.argv) == 5 else None

    chain_order = parse_contig_specifications(contig_file)

    motifs = [only_motif] if only_motif else sorted(d.name for d in scaffolds_dir.iterdir() if d.is_dir())
    for motif_name in motifs:
        chains = chain_order.get(motif_name, [])
        convert_one_motif(scaffolds_dir, motif_name, chains, out_dir)


if __name__ == "__main__":
    main()
