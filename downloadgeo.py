#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# File        : downloadgeo.py
# Description : A CLI tool to batch download GEO datasets by GSE ID.
#               Supports matrix and raw file download, optional extraction,
#               and fetching GEO summary info from the web.
# Author      : ww (Wang wei)
# Created     : 2025-07-22
# Version     : 2.7
# License     : MIT
# Python Ver  : 3.7+
# Dependencies: requests, tqdm, beautifulsoup4

import os
import sys
from urllib.parse import urljoin


def print_help():
    print("""
Usage:
    downloadgeo GSEXXXXX[,GSEYYYYY,...] [--matrix | --raw] [--extract]
    downloadgeo filename.txt --file [--matrix | --raw] [--extract]

Options:
    --matrix     Only download matrix files (series_matrix.txt.gz or -GPLxxx variants)
    --raw        Only download raw files (RAW.tar, filelist.txt, etc. from suppl/)
    --extract    Automatically extract .tar and .gz files after download
    --file       Treat first argument as a .txt file containing one GEO ID per line
    --help       Show this help message
    --info       Show summary info from GEO webpage

If neither --matrix nor --raw is provided, both will be downloaded by default.

Examples:
    downloadgeo GSE76275 --info
    downloadgeo GSE76275 --extract
    downloadgeo GSE76275,GSE11909 --matrix
    downloadgeo geo_ids.txt --file --raw --extract
    """)

def show_geo_info(geo_id):
    import requests
    from bs4 import BeautifulSoup

    url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={geo_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"\n❌ Failed to fetch info: HTTP {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.find_all("tr", valign="top")
        print(f"\n📄 GEO Information for {geo_id}")
        print("=" * 70)

        found = False
        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 2:
                key = tds[0].get_text(strip=True)
                val_td = tds[1]

                if val_td.find("table"):
                    val = " | ".join(cell.get_text(strip=True) for cell in val_td.find_all("td"))
                else:
                    val = val_td.get_text(separator=" ", strip=True)

                if key and val:
                    print(f"\n🔹 {key}\n{val}")
                    found = True

        if not found:
            print("⚠️ No structured GEO description fields found.")

        print("=" * 70)

    except Exception as e:
        print(f"⚠️ Error fetching info: {e}")

def get_geo_prefix(geo_id):
    geo_number = int(geo_id[3:])
    if geo_number < 1000:
        return "GSEnnn"
    else:
        return f"GSE{geo_id[3:-3]}nnn"

def download_file_list(url, keyword=None):
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200 or not resp.text:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a')
        files = [
            link.get('href') for link in links
            if link.get('href') and not link.get('href').endswith('/')
            and not link.get('href').startswith("http")
        ]
        if keyword:
            files = [f for f in files if keyword in f]
        return files
    except Exception as e:
        print(f"⚠️ requests error: {e}")
        return None

def extract_file(filepath):
    import gzip
    import shutil
    import subprocess

    if filepath.endswith(".gz") and not filepath.endswith(".tar.gz"):
        output_file = filepath[:-3]
        if os.path.exists(output_file):
            print(f"✅ Skipping extract: {output_file} exists")
            return
        print(f"📦 Extracting .gz: {os.path.basename(filepath)}")
        try:
            with gzip.open(filepath, 'rb') as f_in, open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        except Exception as e:
            print(f"❌ Failed to extract {filepath}: {e}")
    elif filepath.endswith(".tar"):
        print(f"📦 Extracting .tar: {os.path.basename(filepath)}")
        try:
            subprocess.run(["tar", "-xf", filepath], check=True)
        except subprocess.CalledProcessError:
            print(f"❌ Failed to extract {filepath}")

def download_files_with_requests(base_url, files, outdir=".", extract=False):
    import requests

    os.makedirs(outdir, exist_ok=True)
    for fname in files:
        file_url = urljoin(base_url, fname)
        out_path = os.path.join(outdir, fname)

        if os.path.exists(out_path):
            print(f"✅ Skipping existing file: {fname}")
        else:
            print(f"⬇️ Downloading (requests): {fname}")
            try:
                with requests.get(file_url, stream=True, timeout=30) as r:
                    if r.status_code == 200:
                        with open(out_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                    else:
                        print(f"❌ Failed to download {fname}, status code: {r.status_code}")
            except Exception as e:
                print(f"❌ Error downloading {fname}: {e}")

        if extract:
            extract_file(out_path)

def fallback_with_wget(url, outdir, accept="*", extract=False):
    import subprocess

    print(f"🔁 Falling back to wget for: {url}")
    subprocess.run([
        "wget", "-r", "-np", "-nH", "--cut-dirs=5", "-P", outdir,
        "--accept", accept, "-nc", url
    ])
    if extract:
        for root, _, files in os.walk(outdir):
            for fname in files:
                if fname.endswith(".tar") or fname.endswith(".gz"):
                    extract_file(os.path.join(root, fname))

def fallback_download_matrix(geo_id, geo_prefix, outdir, extract=False):
    import subprocess

    fallback_url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{geo_prefix}/{geo_id}/matrix/{geo_id}_series_matrix.txt.gz"
    out_path = os.path.join(outdir, f"{geo_id}_series_matrix.txt.gz")
    if os.path.exists(out_path):
        print(f"✅ Matrix already exists: {out_path}")
    else:
        print(f"🔁 Fallback direct download of matrix: {fallback_url}")
        subprocess.run(["wget", "-nc", "-O", out_path, fallback_url])
    if extract:
        extract_file(out_path)

def download_geo(geo_id, download_raw=True, download_matrix=True, extract=False):
    geo_id = geo_id.strip().upper()
    if not geo_id.startswith("GSE") or not geo_id[3:].isdigit():
        print(f"❌ Invalid GEO ID: {geo_id}")
        return

    geo_prefix = get_geo_prefix(geo_id)
    main_url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{geo_prefix}/{geo_id}/"
    suppl_url = main_url + "suppl/"
    matrix_url = main_url + "matrix/"
    os.makedirs(geo_id, exist_ok=True)

    if download_raw:
        print(f"\n📁 [{geo_id}] Checking supplementary files at: {suppl_url}")
        suppl_files = download_file_list(suppl_url)
        if suppl_files:
            download_files_with_requests(suppl_url, suppl_files, outdir=geo_id, extract=extract)
        else:
            fallback_with_wget(suppl_url, outdir=geo_id, accept="*", extract=extract)

    if download_matrix:
        print(f"\n📁 [{geo_id}] Checking matrix file(s) at: {matrix_url}")
        matrix_files = download_file_list(matrix_url, keyword="series_matrix")
        if matrix_files:
            download_files_with_requests(matrix_url, matrix_files, outdir=geo_id, extract=extract)
        else:
            fallback_download_matrix(geo_id, geo_prefix, geo_id, extract=extract)

    print(f"✅ [{geo_id}] Download complete.")

def parse_geo_list_from_file(filename):
    geo_list = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                geo_list.append(line)
    return geo_list

if __name__ == "__main__":
    if len(sys.argv) < 2 or "--help" in sys.argv:
        print_help()
        sys.exit(0)

    is_file_mode = "--file" in sys.argv
    extract = "--extract" in sys.argv
    download_raw = "--raw" in sys.argv or ("--matrix" not in sys.argv and "--raw" not in sys.argv)
    download_matrix = "--matrix" in sys.argv or ("--matrix" not in sys.argv and "--raw" not in sys.argv)

    if is_file_mode:
        txt_file = sys.argv[1]
        if not os.path.exists(txt_file):
            print(f"❌ File not found: {txt_file}")
            sys.exit(1)
        geo_list = parse_geo_list_from_file(txt_file)
    else:
        geo_input = sys.argv[1]
        geo_list = [g.strip() for g in geo_input.split(",") if g.strip()]
    from tqdm import tqdm
    geo_iter = tqdm(geo_list, desc="Processing GEOs") if len(geo_list) > 1 else geo_list

    if "--info" in sys.argv:
        for geo_id in geo_list:
            show_geo_info(geo_id)
        sys.exit(0)

    for geo_id in geo_iter:
        download_geo(geo_id, download_raw=download_raw, download_matrix=download_matrix, extract=extract)
    print('Thank you for using downloadgeo, developed by ww!')