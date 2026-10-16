"""Pengelola: python prepare_maps.py. Tidak ditampilkan di layar publik."""
from grid_data import get_grid,DEFAULT_CACHE
if __name__=='__main__':
    data,warning=get_grid(progress=lambda n,total:print(f'Grid {n}/{total}',flush=True))
    print('Cache:',DEFAULT_CACHE)
    print('Data:',data['meta'])
    if warning:print(warning)
