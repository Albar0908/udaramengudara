"""Klien data tanpa framework: dapat dipakai dari Colab dan Streamlit."""
from __future__ import annotations
import io
import json
import math
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import pandas as pd

OM_URL = 'https://air-quality-api.open-meteo.com/v1/air-quality'
OA_URL = 'https://api.openaq.org/v3/'
VARIABLES = ['pm2_5','pm10','carbon_monoxide','nitrogen_dioxide','sulphur_dioxide','ozone','us_aqi','aerosol_optical_depth']
LABELS = {'pm2_5':'PM2.5','pm10':'PM10','carbon_monoxide':'CO','nitrogen_dioxide':'NO₂','sulphur_dioxide':'SO₂','ozone':'O₃','us_aqi':'US AQI','aerosol_optical_depth':'AOD total 550 nm'}
class DataError(RuntimeError):
    pass

def get_json(url, params=None, key=None):
    if params:
        url += '?' + urlencode(params)
    headers={'User-Agent':'UdaraIndonesia-Analysis/1.0','Accept':'application/json'}
    if key:
        headers['X-API-Key']=key
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers=headers),timeout=35) as response:
                data=json.load(response)
            if isinstance(data,dict) and data.get('error'):
                raise DataError(str(data.get('reason','Layanan mengembalikan kesalahan.')))
            return data
        except HTTPError as exc:
            if exc.code in (429,500,502,503,504) and attempt < 2:
                time.sleep(2**attempt)
                continue
            message={401:'API key OpenAQ tidak valid.',403:'Akses ditolak oleh sumber data/jaringan.',429:'Kuota API tercapai; tunggu sebelum mencoba kembali.'}.get(exc.code,f'Layanan data mengembalikan HTTP {exc.code}.')
            raise DataError(message) from None
        except (URLError,TimeoutError) as exc:
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            raise DataError('Koneksi ke sumber data gagal. Periksa internet dan coba kembali.') from None
        except (ValueError,TypeError):
            raise DataError('Respons sumber data bukan JSON yang dapat dibaca.') from None


def load_regions(path):
    frame=pd.read_csv(path)
    required={'wilayah','lokasi','pulau','latitude','longitude'}
    if not required.issubset(frame.columns):
        raise DataError('CSV lokasi perlu kolom: '+', '.join(sorted(required)))
    if frame.empty or len(frame)>250:
        raise DataError('Isi 1–250 lokasi. Gunakan titik representatif, bukan klaim rata-rata seluruh wilayah.')
    for col in ('latitude','longitude'):
        frame[col]=pd.to_numeric(frame[col],errors='coerce')
    if frame[list(required)].isna().any().any() or not frame.latitude.between(-11.5,6.5).all() or not frame.longitude.between(94,142).all():
        raise DataError('Nama dan koordinat wajib terisi, dengan koordinat dalam cakupan Indonesia.')
    if frame.wilayah.duplicated().any():
        raise DataError('Kolom wilayah harus unik; beri label berbeda untuk titik tambahan.')
    return frame.reset_index(drop=True)


def normalize_forecast(payload, regions, fetched_at=None):
    items=payload if isinstance(payload,list) else [payload]
    if len(items)!=len(regions):
        raise DataError('Jumlah hasil API berbeda dari jumlah lokasi yang diminta.')
    retrieved=fetched_at or datetime.now(timezone.utc).isoformat()
    frames=[]
    for (_, region),item in zip(regions.iterrows(),items):
        if item.get('error'):
            raise DataError(str(item.get('reason')))
        hourly=item.get('hourly',{})
        if not hourly.get('time'):
            raise DataError('Respons tidak memiliki deret waktu per jam.')
        df=pd.DataFrame(hourly).rename(columns={'time':'waktu_utc'})
        df['waktu_utc']=pd.to_datetime(df['waktu_utc'],utc=True,errors='raise')
        for var in VARIABLES:
            if var not in df:
                df[var]=float('nan')
            df[var]=pd.to_numeric(df[var],errors='coerce')
            df.loc[df[var]<0,var]=float('nan')
        # The response coordinates are the model grid point selected by the API.
        for col in ('wilayah','lokasi','pulau','latitude','longitude'):
            df[col]=region[col]
        df['grid_latitude']=item.get('latitude')
        df['grid_longitude']=item.get('longitude')
        df['jenis_data']='model CAMS via Open-Meteo'
        df['diambil_utc']=retrieved
        frames.append(df)
    result=pd.concat(frames,ignore_index=True)
    return result.sort_values(['wilayah','waktu_utc']).reset_index(drop=True)


def fetch_forecast(regions,days=3):
    if not 1<=days<=5:
        raise DataError('Rentang prediksi harus 1–5 hari.')
    frames=[]
    for start in range(0,len(regions),20):
        chunk=regions.iloc[start:start+20]
        payload=get_json(OM_URL,{
            'latitude':','.join(map(str,chunk.latitude)),
            'longitude':','.join(map(str,chunk.longitude)),
            'hourly':','.join(VARIABLES),
            'forecast_days':days,'past_days':1,'timezone':'GMT','domains':'cams_global',
        })
        frames.append(normalize_forecast(payload,chunk))
    return pd.concat(frames,ignore_index=True)


def snapshot_at(frame,when):
    """Satu jam valid yang sama untuk semua titik, tanpa mengganti data hilang."""
    timestamp=pd.Timestamp(when)
    timestamp=timestamp.tz_localize('UTC') if timestamp.tzinfo is None else timestamp.tz_convert('UTC')
    return frame.loc[frame.waktu_utc.eq(timestamp)].copy()


def aqi_category(value):
    if pd.isna(value) or value < 0:
        return 'Tidak ada data'
    for limit,label in [(50,'Baik'),(100,'Sedang'),(150,'Tidak sehat bagi kelompok sensitif'),(200,'Tidak sehat'),(300,'Sangat tidak sehat')]:
        if value<=limit:
            return label
    return 'Berbahaya'


def openaq_locations(key):
    if not key:
        raise DataError('Isi OPENAQ_API_KEY untuk data pengamatan stasiun.')
    records=[]
    for page in range(1,101):
        data=get_json(OA_URL+'locations',{'iso':'ID','parameters_id':2,'limit':1000,'page':page},key)
        batch=data.get('results',[])
        for item in batch:
            sensor=next((s for s in item.get('sensors',[]) if s.get('parameter',{}).get('name')=='pm25' and s['parameter'].get('units') in ['µg/m³','μg/m³']),None)
            if not sensor:
                continue
            coords=item.get('coordinates') or {}
            licenses=item.get('licenses') or []
            records.append({'id':item['id'],'stasiun':item['name'],'locality':item.get('locality') or '',
                'latitude':coords.get('latitude'),'longitude':coords.get('longitude'),
                'sensor_id':sensor['id'],'terakhir_lokasi_utc':(item.get('datetimeLast') or {}).get('utc'),
                'provider':(item.get('provider') or {}).get('name',''),
                'lisensi':'; '.join(l.get('name','') for l in licenses),
                'atribusi':'; '.join((l.get('attribution') or {}).get('name') or '' for l in licenses),
                'metadata_json':json.dumps(item,ensure_ascii=False)})
        if len(batch)<1000:
            columns=['id','stasiun','locality','latitude','longitude','sensor_id','terakhir_lokasi_utc','provider','lisensi','atribusi','metadata_json']
            return pd.DataFrame(records,columns=columns)
    raise DataError('Pagination OpenAQ melebihi batas; pengambilan dihentikan agar hasil tidak terpotong diam-diam.')


def openaq_detail(key,location_id,sensor_id,days=7):
    from datetime import timedelta
    end=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    latest=get_json(OA_URL+f'locations/{int(location_id)}/latest',{'limit':1000},key)
    candidates=[r for r in latest.get('results',[]) if r.get('sensorsId')==int(sensor_id)]
    point=max(candidates,key=lambda r:(r.get('datetime') or {}).get('utc',''),default=None)
    # Seven days of hourly aggregates fit in one 1,000-record page.
    raw=get_json(OA_URL+f'sensors/{int(sensor_id)}/hours',{'datetime_from':(end-timedelta(days=days)).isoformat(),'datetime_to':end.isoformat(),'limit':1000},key)
    rows=[]
    for r in raw.get('results',[]):
        value=r.get('value')
        when=((r.get('period') or {}).get('datetimeTo') or {}).get('utc')
        if when and isinstance(value,(int,float)) and math.isfinite(value) and value>=0:
            rows.append({'waktu_utc':when,'pm25':value,'coverage':(r.get('coverage') or {}).get('percentCoverage')})
    frame=pd.DataFrame(rows,columns=['waktu_utc','pm25','coverage'])
    frame['waktu_utc']=pd.to_datetime(frame.waktu_utc,utc=True)
    return point,frame.sort_values('waktu_utc')


def validate_smoke(frame):
    """Accept source-provided biomass-burning AOD forecasts; never infer smoke from total AOD."""
    required={'waktu_utc','latitude','longitude','bbaod550','sumber','inisialisasi_utc'}
    if not required.issubset(frame.columns):
        raise DataError('Kolom kabut asap wajib: '+', '.join(sorted(required)))
    if frame.empty or len(frame)>100000:
        raise DataError('CSV kabut asap harus berisi 1–100.000 baris.')
    frame=frame.copy()
    for c in ('waktu_utc','inisialisasi_utc'):
        # Explicit time zone required: UTC ISO-8601, e.g. ...Z or ...+00:00.
        strings=frame[c].astype(str)
        if not strings.str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$',regex=True).all():
            raise DataError(c+' harus menyertakan zona waktu, contoh 2026-10-16T00:00:00Z.')
        frame[c]=pd.to_datetime(frame[c],utc=True,errors='coerce')
    for c in ('latitude','longitude','bbaod550'):
        frame[c]=pd.to_numeric(frame[c],errors='coerce')
    if frame[list(required)].isna().any().any():
        raise DataError('Terdapat nilai kosong atau format data tidak valid.')
    if not frame.latitude.between(-11.5,6.5).all() or not frame.longitude.between(94,142).all():
        raise DataError('Koordinat kabut asap berada di luar cakupan Indonesia.')
    if not frame.bbaod550.map(math.isfinite).all() or (frame.bbaod550<0).any():
        raise DataError('bbaod550 harus angka hingga dan tidak negatif.')
    if not frame.sumber.astype(str).str.strip().ne('').all():
        raise DataError('Sumber data harus diisi.')
    if (frame.waktu_utc<frame.inisialisasi_utc).any():
        raise DataError('Waktu valid prediksi tidak boleh sebelum waktu inisialisasi model.')
    if frame.duplicated(['latitude','longitude','waktu_utc','inisialisasi_utc']).any():
        raise DataError('CSV memiliki titik-waktu duplikat dalam satu inisialisasi model.')
    return frame.sort_values(['inisialisasi_utc','waktu_utc','latitude','longitude'])
