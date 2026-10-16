"""Prakiraan grid reguler dan cache bersama; bukan interpolasi 38 kota."""
from pathlib import Path
import json, os, tempfile, time
from datetime import datetime,timezone,timedelta
from contextlib import contextmanager
import numpy as np
import pandas as pd
from air_data import get_json, DataError, OM_URL, VARIABLES
DEFAULT_CACHE=Path(__file__).parent/'cache'/'forecast_grid.npz'
MAX_AGE=6*3600
STEP=1.2

def coordinates(step=STEP):
    if step not in (0.4,0.8,1.2,1.6):raise DataError('Grid harus kelipatan resolusi model 0.4 derajat.')
    return np.round(np.arange(-11.6,6.40001,step),4),np.round(np.arange(94.4,142.40001,step),4)

def fetch_grid(step=STEP,progress=None):
    lats,lons=coordinates(step)
    points=[(float(y),float(x)) for y in lats for x in lons]
    start=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    end=start+timedelta(hours=71)
    times=None;arrays=None;grid_lats=[];grid_lons=[]
    for begin in range(0,len(points),30):
        batch=points[begin:begin+30]
        # At most ~440 coordinate-calls/min even with instantaneous HTTP.
        if begin:time.sleep(4.1)
        payload=get_json(OM_URL,{'latitude':','.join(str(y) for y,x in batch),'longitude':','.join(str(x) for y,x in batch),
            'hourly':','.join(VARIABLES),'domains':'cams_global','timezone':'GMT',
            'start_hour':start.strftime('%Y-%m-%dT%H:%M'),'end_hour':end.strftime('%Y-%m-%dT%H:%M'),'cell_selection':'nearest'})
        items=payload if isinstance(payload,list) else [payload]
        if len(items)!=len(batch):raise DataError('Respons grid tidak lengkap; cache lama dipertahankan.')
        for offset,item in enumerate(items):
            hourly=item.get('hourly',{}); current_times=hourly.get('time')
            if not current_times:raise DataError('Prakiraan grid tidak memiliki waktu valid.')
            if times is None:
                times=np.array(current_times,dtype='U25')
                arrays={v:np.full((len(times),len(points)),np.nan,dtype=np.float32) for v in VARIABLES}
            if list(times)!=current_times:raise DataError('Jam valid antar-grid berbeda.')
            grid_lats.append(item.get('latitude',float('nan')));grid_lons.append(item.get('longitude',float('nan')))
            for v in VARIABLES:
                values=np.array([np.nan if z is None else z for z in hourly.get(v,[np.nan]*len(times))],dtype=np.float32)
                if values.shape!=(len(times),):raise DataError('Panjang data grid tidak sesuai waktu valid.')
                values[(~np.isfinite(values))|(values<0)]=np.nan
                arrays[v][:,begin+offset]=values
        if progress:progress(min(begin+len(batch),len(points)),len(points))
    meta={'fetched_at':datetime.now(timezone.utc).isoformat(),'sampling_step':step,'source':'Open-Meteo / Copernicus CAMS global',
          'requested_points':len(points),'model_native_resolution_degrees':0.4,'kind':'forecast','schema_version':1}
    return {'times':times,'lats':lats,'lons':lons,'grid_lats':np.array(grid_lats),'grid_lons':np.array(grid_lons),'meta':meta,
            **{v:a.reshape(len(times),len(lats),len(lons)) for v,a in arrays.items()}}

def save_grid(bundle,path=DEFAULT_CACHE):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.npz',delete=False) as handle:temporary=Path(handle.name)
    try:
        np.savez_compressed(temporary,metadata=json.dumps(bundle['meta']),**{k:v for k,v in bundle.items() if k!='meta'})
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)

def read_grid(path=DEFAULT_CACHE):
    with np.load(path,allow_pickle=False) as raw:
        result={k:raw[k].copy() for k in raw.files if k!='metadata'}
        result['meta']=json.loads(str(raw['metadata']))
    if result['meta'].get('schema_version')!=1:raise DataError('Versi cache grid tidak dikenali.')
    for v in VARIABLES:
        if result[v].shape!=(len(result['times']),len(result['lats']),len(result['lons'])):raise DataError('Ukuran cache grid tidak konsisten.')
    return result

def age_seconds(bundle):
    return (datetime.now(timezone.utc)-datetime.fromisoformat(bundle['meta']['fetched_at'])).total_seconds()

@contextmanager
def collection_lock(path=DEFAULT_CACHE):
    lock=Path(str(path)+'.lock');lock.parent.mkdir(parents=True,exist_ok=True)
    if lock.exists() and time.time()-lock.stat().st_mtime>1200:lock.unlink(missing_ok=True)
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise DataError('Pembaruan data sedang berlangsung.') from None
    try:os.close(fd);yield
    finally:lock.unlink(missing_ok=True)

def get_grid(path=DEFAULT_CACHE,progress=None):
    old=None
    try:old=read_grid(path)
    except (OSError,ValueError,KeyError,DataError):pass
    if old is not None and age_seconds(old)<MAX_AGE:return old,None
    try:
        with collection_lock(path):
            try:
                current=read_grid(path)
                if age_seconds(current)<MAX_AGE:return current,None
            except (OSError,ValueError,KeyError,DataError):pass
            new=fetch_grid(progress=progress);save_grid(new,path);return new,None
    except (DataError,OSError,ValueError):
        if old is not None:return old,'Pembaruan tertunda. Menampilkan prakiraan terakhir yang tersedia.'
        raise DataError('Peta belum dapat dimuat. Silakan coba kembali beberapa saat lagi.') from None

def region_values(bundle,regions):
    rows=[];times=pd.to_datetime(bundle['times'],utc=True)
    for _,r in regions.iterrows():
        iy=int(np.abs(bundle['lats']-r.latitude).argmin());ix=int(np.abs(bundle['lons']-r.longitude).argmin())
        for i,t in enumerate(times):
            row={'wilayah':r.wilayah,'lokasi':r.lokasi,'pulau':r.pulau,'waktu_utc':t,
                 'sample_latitude':float(bundle['lats'][iy]),'sample_longitude':float(bundle['lons'][ix])}
            for v in VARIABLES:row[v]=float(bundle[v][i,iy,ix])
            rows.append(row)
    return pd.DataFrame(rows)
