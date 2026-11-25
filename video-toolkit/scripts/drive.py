#!/usr/bin/env python3
"""Baixa arquivos de pastas/links públicos do Google Drive.

Uso:
  drive.py list <url_da_pasta>                 # lista id + nome dos arquivos
  drive.py get <id_ou_url_do_arquivo> <saida>  # baixa um arquivo
  drive.py getall <url_da_pasta> <pasta_saida> # baixa todos os arquivos

Observações:
- A pasta/arquivo precisa estar como "Qualquer pessoa com o link".
- O download usa drive.usercontent.google.com (o redirecionamento padrão
  do gdown para *.googleusercontent.com costuma ser bloqueado pelo proxy).
- Requer: pip install gdown (só para listar pastas).
"""
import os
import re
import subprocess
import sys


def file_id(s):
    m = re.search(r"/d/([A-Za-z0-9_-]{20,})", s) or re.search(r"id=([A-Za-z0-9_-]{20,})", s)
    return m.group(1) if m else s


def list_folder(url):
    import gdown
    files = gdown.download_folder(url, skip_download=True, quiet=True)
    return [(f.id, f.path) for f in files]


def get(fid, out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    url = f"https://drive.usercontent.google.com/download?id={file_id(fid)}&export=download&confirm=t"
    subprocess.run(["curl", "-sS", "-L", "--retry", "3", "-o", out, url], check=True)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "list":
        for fid, name in list_folder(sys.argv[2]):
            print(fid, name)
    elif cmd == "get":
        print(get(sys.argv[2], sys.argv[3]))
    elif cmd == "getall":
        for fid, name in list_folder(sys.argv[2]):
            print(get(fid, os.path.join(sys.argv[3], os.path.basename(name))))
    else:
        print(__doc__)
        sys.exit(1)
