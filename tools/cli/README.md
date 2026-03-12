# CLI Matrix Harness Commands

`tools/cli/run_cli_matrix.sh` runs the OpenToken CLI from the current worktree
with a temporary workspace. The script exports:

- `HOME=<WORKSPACE>/home`
- `PYTHONPATH=<WORKTREE>/lib/python/opentoken-cli/src/main:<WORKTREE>/lib/python/opentoken/src/main`
- `NO_COLOR=1`

The command lines below are the exact CLI invocations that the script executes.
`<WORKSPACE>` is the temporary directory that the script creates at runtime.

## Default command order

1. `python -m opentoken_cli.main --no-update-check --help`
2. `python -m opentoken_cli.main --no-update-check help`
3. `python -m opentoken_cli.main --no-update-check help package`
4. `python -m opentoken_cli.main --no-update-check tokenize --help`
5. `python -m opentoken_cli.main --no-update-check tokenize -i <WORKSPACE>/inputs/people.csv -t csv -o <WORKSPACE>/outputs/tokenized-demo.csv --demo-mode`
6. `python -m opentoken_cli.main --no-update-check generate-key-pair --help`
7. `python -m opentoken_cli.main --no-update-check generate-key-pair --name recipient --force`
8. `python -m opentoken_cli.main --no-update-check generate-key-pair --name recipient-p384 --curve P-384 --force`
9. `python -m opentoken_cli.main --no-update-check generate-key-pair --name recipient-p521 --curve P-521 --force`
10. `python -m opentoken_cli.main --no-update-check initiate-exchange --help`
11. `python -m opentoken_cli.main --no-update-check initiate-exchange --name sender-local --public-key <WORKSPACE>/home/.opentoken/recipient.public.pem --output <WORKSPACE>/outputs/local.exchange.json --hashingsecret LocalHarnessHashingSecret --force`
12. `python -m opentoken_cli.main --no-update-check tokenize -i <WORKSPACE>/inputs/people.csv -t csv -o <WORKSPACE>/outputs/tokenized-hash.csv --exchange-config <WORKSPACE>/outputs/local.exchange.json --private-key <WORKSPACE>/home/.opentoken/sender-local.private.pem`
13. `python -m opentoken_cli.main --no-update-check encrypt --help`
14. `python -m opentoken_cli.main --no-update-check encrypt -i <WORKSPACE>/outputs/tokenized-hash.csv -t csv -o <WORKSPACE>/outputs/encrypted.csv --exchange-config <WORKSPACE>/outputs/local.exchange.json --private-key <WORKSPACE>/home/.opentoken/sender-local.private.pem`
15. `python -m opentoken_cli.main --no-update-check decrypt --help`
16. `python -m opentoken_cli.main --no-update-check decrypt -i <WORKSPACE>/outputs/encrypted.csv -t csv -o <WORKSPACE>/outputs/decrypted.csv --exchange-config <WORKSPACE>/outputs/local.exchange.json --private-key <WORKSPACE>/home/.opentoken/sender-local.private.pem`
17. `python -m opentoken_cli.main --no-update-check package --help`
18. `python -m opentoken_cli.main --no-update-check package -i <WORKSPACE>/inputs/people.csv -t csv -o <WORKSPACE>/outputs/packaged.csv --exchange-config <WORKSPACE>/outputs/local.exchange.json --private-key <WORKSPACE>/home/.opentoken/sender-local.private.pem`
19. `python -m opentoken_cli.main --no-update-check update --help`

## Optional command

If you pass `--include-live-update`, the script appends:

20. `python -m opentoken_cli.main --no-update-check update --dry-run --yes`

## Execution behavior

- By default, the script waits for confirmation before advancing to the next command.
- Pass `--auto-continue` to run straight through without prompting.
- Pass `--dry-run` to print the command sequence without executing it.
