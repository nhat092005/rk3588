"""Parsers of real RKNN-Toolkit2 2.3.2 eval_perf output. Run: make test-parsers"""
from pathlib import Path

from ai.core.rknn.benchmark import LAYERS_TIME_RE, parse_frequencies, parse_layers, parse_summary_time_us

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def main() -> None:
    summary = (FIXTURES / "eval_perf_2.3.2_summary.txt").read_text()
    assert parse_summary_time_us(summary) == 17219
    assert parse_frequencies(summary) == {"CPU": [1800000, 2256000, 2304000], "NPU": [1000000000], "DDR": [2112000000]}

    layers_text = (FIXTURES / "eval_perf_2.3.2_layers.txt").read_text()
    rows = parse_layers(layers_text)
    assert float(LAYERS_TIME_RE.search(layers_text).group(1)) == 20663
    assert rows[0]["op"] == "InputOperator" and rows[1] == {
        "id": 2, "op": "ConvExSwish", "dtype": "UINT8", "target": "NPU",
        "ddr_cycles": 121323, "npu_cycles": 921600, "total_cycles": 921600,
        "time_us": 1861, "name": "Conv:/model/model.0/conv/Conv",
    }
    # every layer row parsed: per-layer times add up to the reported per-frame total
    assert sum(r["time_us"] for r in rows) == 20663, sum(r["time_us"] for r in rows)
    assert any(r["op"] == "Transpose" and r["target"] == "CPU" for r in rows)
    print(f"PARSERS OK ({len(rows)} layers)")


if __name__ == "__main__":
    main()
