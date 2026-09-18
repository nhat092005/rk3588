"""Parse a rknn-toolkit2 build log (RKNN_LOG_LEVEL=3) and rank layers by
DDR/NPU cycle count to find memory-bandwidth-bound bottlenecks.

Usage: python scripts/analyze_rknn_build_log.py <log_path>
"""
import argparse
import re


def parse_layers(log_path: str) -> list[tuple[int, str, str, int, int, int, str]]:
    rows = []
    for line in open(log_path):
        m = re.match(r"D RKNN: \[[^\]]*\]\s+(.*)", line)
        if not m:
            continue
        parts = m.group(1).split()
        if len(parts) < 8 or not parts[0].isdigit():
            continue
        idx, optype, dtype, dev = parts[0], parts[1], parts[2], parts[3]
        if dev not in ("CPU", "NPU", "GPU"):
            continue
        cyc_tok = next((p for p in parts if re.fullmatch(r"\d+/\d+/\d+", p)), None)
        if not cyc_tok:
            continue
        ddr, npu, total = map(int, cyc_tok.split("/"))
        rows.append((int(idx), optype, dev, ddr, npu, total, parts[-1]))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("log_path")
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    rows = parse_layers(args.log_path)
    print(f"parsed rows: {len(rows)}")
    npu_rows = [r for r in rows if r[2] == "NPU" and r[5] > 0]
    print(f"NPU rows with total>0: {len(npu_rows)}")

    total_ddr = sum(r[3] for r in npu_rows)
    total_npu = sum(r[4] for r in npu_rows)
    print(f"\nTotal DDR cycles: {total_ddr}, Total NPU cycles: {total_npu}, "
          f"overall DDR/NPU ratio: {total_ddr / total_npu:.3f}")

    header = f'{"ID":<4}{"OpType":<16}{"DDR":>10}{"NPU":>10}{"Total":>10}{"DDR/NPU":>10}  FullName'

    print(f"\nTop {args.top} layers by absolute DDR cycles:")
    print(header)
    for idx, optype, dev, ddr, npu, total, fullname in sorted(npu_rows, key=lambda r: -r[3])[: args.top]:
        ratio = ddr / npu if npu else float("inf")
        print(f"{idx:<4}{optype:<16}{ddr:>10}{npu:>10}{total:>10}{ratio:>10.2f}  {fullname}")

    print(f"\nTop {args.top} most memory-bound layers (highest DDR/NPU ratio, npu>1000):")
    print(header)
    candidates = [r for r in npu_rows if r[4] > 1000]
    for idx, optype, dev, ddr, npu, total, fullname in sorted(candidates, key=lambda r: -(r[3] / r[4]))[: args.top]:
        ratio = ddr / npu
        print(f"{idx:<4}{optype:<16}{ddr:>10}{npu:>10}{total:>10}{ratio:>10.3f}  {fullname}")


if __name__ == "__main__":
    main()
