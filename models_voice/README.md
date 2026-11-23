# Piper Voice Models

Place Piper ONNX voice model files here (and their matching `.onnx.json`
config files), e.g.:

```
models_voice/
├── th_TH-model.onnx
└── th_TH-model.onnx.json
```

No voice model is bundled with this repository — download one that
matches your target language and check its license before deploying it
to a public-facing community radio system (CLAUDE.md §11).

Point `PIPER_MODEL` in `.env` at the file you place here, e.g.:

```
PIPER_MODEL=models_voice/th_TH-model.onnx
```
