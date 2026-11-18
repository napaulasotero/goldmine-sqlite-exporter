# GoldMine SQLite Exporter

A Python command-line tool to export molecular descriptors from a GoldMine SQLite (`.sqlite`) database to CSV files, without using the GoldMine exporter.

## Requirements

- Python 3
- A GoldMine SQLite database (`.sqlite`)

No third-party Python packages are required.

## Usage

List the dock sets in a database:

```bash
python3 goldmine_export.py database.sqlite --listar
