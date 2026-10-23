# Updating `sample.parquet` file

In order to keep the `sample.parquet` file up to date, you can run the following command:

```bash
 csv2parquet resources/sample.csv -o resources/sample.parquet
```

## ML-KEM / SHAKE256 sample output

The following files were generated from [sample.csv](sample.csv) using
`mlkem768-shake256`:

- [sample-mlkem768-shake256-encrypted.csv](sample-mlkem768-shake256-encrypted.csv):
  encrypted T1-T5 tokens.
- [sample-mlkem768-shake256-encrypted.metadata.json](sample-mlkem768-shake256-encrypted.metadata.json):
  processing and validation statistics.
- [sample-mlkem768-shake256.exchange.json](sample-mlkem768-shake256.exchange.json):
  the version-2 ML-KEM exchange envelope, containing encrypted secrets but no
  private key material.

ML1 inferencing was disabled to keep the example focused on the cryptographic
suite. The run processed 105 records and produced 525 token rows, including
blank tokens for invalid attributes. Recipient decryption was verified with
zero failures.

From the repository root, generate a fresh example with:

```bash
olt generate-key-pair \
  --crypto-suite mlkem768-shake256 \
  --name sample-mlkem768-shake256-recipient

olt initiate-exchange \
  --crypto-suite mlkem768-shake256 \
  --name sample-mlkem768-shake256-sender \
  --public-key ~/.openlinktoken/sample-mlkem768-shake256-recipient.public.bundle.json \
  --output resources/sample-mlkem768-shake256.exchange.json

olt package \
  -i resources/sample.csv \
  -o resources/sample-mlkem768-shake256-encrypted.csv \
  --exchange-config resources/sample-mlkem768-shake256.exchange.json \
  --private-key ~/.openlinktoken/sample-mlkem768-shake256-sender.private.bundle.json \
  --disable-inferencing
```

Private bundles remain local under `~/.openlinktoken/` and are not included in
these resources. On separate machines, transfer only the recipient's public
bundle to the sender, then the exchange file and encrypted output to the
recipient. Decrypt with the matching recipient private bundle:

```bash
olt decrypt \
  -i resources/sample-mlkem768-shake256-encrypted.csv \
  -o /tmp/sample-mlkem768-shake256-decrypted.csv \
  --exchange-config resources/sample-mlkem768-shake256.exchange.json \
  --private-key ~/.openlinktoken/sample-mlkem768-shake256-recipient.private.bundle.json
```

Decryption reveals hashed tokens, not the original person data. New random
keys, secrets, and encryption nonces produce different output on each run.
Generating new keys does not enable decryption of the existing sample output;
that requires a private bundle matching its exchange envelope.
