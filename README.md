# downloadgeo
A toy for downloading geo data
Just copy it over to your computer and it'll run!
## uspage
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
