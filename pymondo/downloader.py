from pathlib import Path
import requests


def download(download_dir: Path=Path('/usr/local/share/pymondo'), overwrite: bool=False):
    if not download_dir.exists():
        download_dir.mkdir()
    url_list = [
        'http://purl.obolibrary.org/obo/mondo.json',
        'http://purl.obolibrary.org/obo/mondo.owl',
        'http://purl.obolibrary.org/obo/mondo.obo',
    ]
    for url in url_list:
        fname = url.split('/')[-1]
        fp = download_dir / fname
        if fp.exists() and not overwrite:
            continue

        print('downloading {}'.format(fname))
        res = requests.get(url)
        with fp.open(mode='wb') as f:
            f.write(res.content)
