#!/usr/bin/env python3
"""
Export descriptors from a GoldMine (.sqlite) database to CSV,
without using the GoldMine exporter.

Usage:
    python3 goldmine_export.py database.sqlite
    python3 goldmine_export.py database.sqlite --saida output_folder
    python3 goldmine_export.py database.sqlite --dockset decoys
    python3 goldmine_export.py database.sqlite --listar

Generates one CSV per dock set: <database_name>_<dockset>.csv
Missing values are left blank (read as NaN by pandas).
Uses only the Python standard library (sqlite3, csv, argparse).
"""
import argparse
import csv
import sqlite3
import sys
from pathlib import Path


def conectar(caminho):
    caminho = Path(caminho).resolve()
    if not caminho.is_file():
        sys.exit(f"ERROR: file not found: {caminho}")
    # Open in read-only mode so the GoldMine database is never modified.
    return sqlite3.connect(f"{caminho.as_uri()}?mode=ro", uri=True)


def tabelas_existentes(con):
    return {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def dock_sets(con):
    """Dock sets are dock_info rows without 'silver_for' (main tables).
    Child tables (energies, etc.) refer to their dock set in silver_for."""
    principais, filhas = [], {}
    for nome, pai in con.execute(
            "SELECT table_name, silver_for FROM dock_info ORDER BY rowid"):
        if pai:
            filhas.setdefault(pai, []).append(nome)
        else:
            principais.append(nome)
    return principais, filhas


def colunas_validas(con, tabelas):
    """Descriptors marked as valid (valid=1) in gm_column_data,
    in the order registered by GoldMine. Excludes MOL_ID and raw text
    fields (STRUCTURE, Score.Contributions, etc.), which have valid=0."""
    marcadores = ",".join("?" * len(tabelas))
    linhas = con.execute(
        f"SELECT table_name, column_name FROM gm_column_data "
        f"WHERE valid=1 AND table_name IN ({marcadores}) ORDER BY rowid",
        tabelas).fetchall()
    vistos, saida = set(), []
    for tab, col in linhas:
        if col.upper() == "MOL_ID" or col in vistos:
            continue
        vistos.add(col)
        saida.append((tab, col))
    return saida


def nome_mol_id(con, tabela):
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{tabela}")')]
    for c in cols:
        if c.upper() == "MOL_ID":
            return c
    sys.exit(f"ERROR: table '{tabela}' has no MOL_ID column")


def exportar_dockset(con, ds, filhas, pasta_saida, prefixo):
    existentes = tabelas_existentes(con)
    tabelas = [ds] + [t for t in filhas.get(ds, []) if t in existentes]
    faltando = [t for t in filhas.get(ds, []) if t not in existentes]
    if faltando:
        print(f"  WARNING: {len(faltando)} table(s) listed in dock_info "
              f"do not exist in the database: {faltando}")

    descritores = colunas_validas(con, tabelas)
    if not descritores:
        print(f"  WARNING: no valid descriptors for '{ds}'; skipping.")
        return

    # MOL_IDs from the main dock set define the rows.
    mid = nome_mol_id(con, ds)
    mol_ids = [r[0] for r in con.execute(
        f'SELECT "{mid}" FROM "{ds}" ORDER BY "{mid}"')]
    if len(mol_ids) != len(set(mol_ids)):
        sys.exit(f"ERROR: duplicate MOL_ID in table '{ds}'")

    # Read each table separately (avoids SQLite's JOIN limit).
    dados = {mol: {} for mol in mol_ids}
    por_tabela = {}
    for tab, col in descritores:
        por_tabela.setdefault(tab, []).append(col)
    for tab, cols in por_tabela.items():
        mid_t = nome_mol_id(con, tab)
        sel = ", ".join(f'"{c}"' for c in cols)
        for linha in con.execute(f'SELECT "{mid_t}", {sel} FROM "{tab}"'):
            mol = linha[0]
            if mol not in dados:
                print(f"  WARNING: MOL_ID {mol} in '{tab}' does not exist in '{ds}'")
                continue
            for c, v in zip(cols, linha[1:]):
                dados[mol][c] = v

    nomes = [c for _, c in descritores]
    cabecalho = ["Entry", "Index", "MOL_ID"] + nomes
    arquivo = pasta_saida / f"{prefixo}_{ds}.csv"
    with open(arquivo, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        for mol in mol_ids:
            reg = dados[mol]
            nome = reg.get("NAME", "")
            entry = f"{ds}|{nome}|{mol}"   # Same format as the GoldMine export.
            w.writerow([entry, mol + 1, mol] +
                       ["" if reg.get(c) is None else reg.get(c) for c in nomes])

    # Checks.
    n_res = sum(1 for c in nomes if c.startswith("energies_residues."))
    vazias = [c for c in nomes if all(dados[m].get(c) is None for m in mol_ids)]
    print(f"  {len(mol_ids)} ligands x {len(nomes)} descriptors "
          f"({n_res} per residue), {len(tabelas)} table(s) read")
    if vazias:
        print(f"  WARNING: {len(vazias)} completely empty column(s): {vazias}")
    print(f"  saved to: {arquivo}")


def main():
    ap = argparse.ArgumentParser(
        description="Export descriptors from a GoldMine (.sqlite) database to CSV.")
    ap.add_argument("banco", help="GoldMine .sqlite file")
    ap.add_argument("--saida", default=None,
                    help="output folder (default: same directory as the database)")
    ap.add_argument("--dockset", default=None,
                    help="export only this dock set (default: all)")
    ap.add_argument("--listar", action="store_true",
                    help="only list the database's dock sets and exit")
    args = ap.parse_args()

    con = conectar(args.banco)
    if "dock_info" not in tabelas_existentes(con):
        sys.exit("ERROR: table 'dock_info' not found. "
                 "Is this a GoldMine database?")

    principais, filhas = dock_sets(con)
    print(f"Database: {args.banco}")
    print("Dock sets: " + ", ".join(
        f"{d} ({len(filhas.get(d, []))} child tables)" for d in principais))
    if args.listar:
        return

    alvo = principais
    if args.dockset:
        if args.dockset not in principais:
            sys.exit(f"ERROR: dock set '{args.dockset}' does not exist. "
                     f"Available: {principais}")
        alvo = [args.dockset]

    pasta = Path(args.saida) if args.saida else Path(args.banco).resolve().parent
    pasta.mkdir(parents=True, exist_ok=True)
    prefixo = Path(args.banco).stem

    for ds in alvo:
        print(f"\n[{ds}]")
        exportar_dockset(con, ds, filhas, pasta, prefixo)
    con.close()


if __name__ == "__main__":
    main()
