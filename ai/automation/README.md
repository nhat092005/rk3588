# automation/

Official execution pipeline for training, evaluation, and baseline RKNN export.

## Usage

```bash
python -m ai.automation.run ai/automation/configs/<config_name>.yaml
python -m ai.automation.export_npu <run_id>
```

## Structure

- `configs/`: Experiment configurations (model, dataset, hyperparameters, seed).
- `runs/<run_id>/`: Execution outputs (`config.yaml`, `metrics.csv`, `weights/`, `plots/`, `npu_benchmark.json`).
- `leaderboards/<dataset>.csv`: Tracked evaluation results, partitioned by dataset.
- `export_npu.py`: Exports a finished run to RKNN format using native baseline settings.
