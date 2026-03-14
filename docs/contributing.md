# Contributing

## Add a model

Update `data/config.json`:

1. Add the model key under `models`
2. Define display name, category, and required metrics
3. Add any threshold overrides if needed

## Add hardware

Update `data/config.json` under `hardware` with a stable hardware key and display name.

## Add a metric

1. Add it to the relevant model's `required` or `optional` list
2. Update ingestion and report generation if it needs special handling
3. Add tests before implementation changes
