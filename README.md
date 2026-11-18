# GoldMine SQLite Exporter

A Python command-line tool to export molecular descriptors from a GoldMine SQLite (`.sqlite`) database to CSV files, without using the GoldMine exporter.

## Requirements

- Python 3
- A GoldMine SQLite database (`.sqlite`)

No third-party Python packages are required.


## Usage

### List available dock sets

To list all dock sets available in the database:

```bash
python3 goldmine_export.py database.sqlite --listar
```

### Export all dock sets

To export all dock sets, generating one CSV file for each dock set:

```bash
python3 goldmine_export.py database.sqlite
```

### Export a specific dock set

To export only one dock set, use the `--dockset` option:

```bash
python3 goldmine_export.py database.sqlite --dockset decoys
```

### Specify the output directory

To choose where the CSV files will be saved, use the `--saida` option:

```bash
python3 goldmine_export.py database.sqlite --saida output_folder
```

If `--saida` is omitted, the CSV files are saved in the same directory as the database.
