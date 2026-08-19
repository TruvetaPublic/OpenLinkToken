# ML1 model and tokenizer

This directory contains the runtime assets for ML1 inference. The model and
tokenizer are a matched pair and must be deployed together. The
`asset-manifest.json` file records the expected SHA-256 digest and size for
each asset.

## `model.onnx`

`model.onnx` is a BERT model exported as an ONNX inference graph for generating
1,024-dimensional ML1 embeddings. Its external tensor data is stored in
`model.onnx.data`; both files are required for inference.

The model does not load vocabulary files. It receives tokenized integer arrays:

- `input_ids`
- `attention_mask`
- `token_type_ids`, when present in the model inputs
- `position_ids`, when present in the model inputs

The generator extracts the embedding for the first (`[CLS]`) position and
serializes it into the ML1 signature.

## `tokenizer.json`

`tokenizer.json` is a serialized Hugging Face Tokenizers configuration. It
contains the complete tokenizer definition and vocabulary inline, including:

- BERT text normalization
- BERT pre-tokenization
- WordPiece tokenization with `##` continuation prefixes
- special-token and post-processing rules

There is no separate `vocab.txt` runtime dependency. The vocabulary embedded
in `tokenizer.json` supplies the token IDs passed to `model.onnx`.

## Runtime integration

Both implementations use the same bundled defaults:

| Setting                 | Default                                     |
| ----------------------- | ------------------------------------------- |
| Model                   | `classpath:/inferencing/ml1/model.onnx`     |
| Tokenizer               | `classpath:/inferencing/ml1/tokenizer.json` |
| Maximum sequence length | `128`                                       |
| Batch size              | `64`                                        |

The published core-ai packages do not bundle the large model files and never
download them. Place the matched files before using ML1:

- Java applications: `src/main/resources/inferencing/ml1/` in the application,
  which puts the files at `inferencing/ml1/` on the runtime classpath.
- Python applications: beside the installed
  `openlinktoken/core/ai/tokens/` package modules.
- Source checkouts: `resources/inferencing/ml1/`.

You can also configure explicit filesystem paths for the model and tokenizer.
The `model.onnx.data` file must always be beside `model.onnx`.

Standalone CLI release bundles include the three model assets and the
manifest. They use the bundled files directly.

The runtime serializes an ML1 payload to JSON, tokenizes that JSON with
`tokenizer.json`, runs the resulting arrays through `model.onnx`, and converts
the returned embedding into the ML1 signature. Python uses the `tokenizers`
and ONNX Runtime libraries; Java uses DJL's Hugging Face tokenizer and ONNX
Runtime engine.

## Compatibility and maintenance

Keep `model.onnx`, `model.onnx.data`, and `tokenizer.json` synchronized. Changing
the tokenizer can change token IDs and therefore model output; changing the
model can change the expected inputs or embedding shape. Replace the matched
assets together and run the Java/Python interoperability checks before release.
