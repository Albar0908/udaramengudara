"""Dashboard publik. Jalankan: python -m streamlit run app.py."""
from pathlib import Path
import html
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from air_data import LABELS,DataError,load_regions,aqi_category
from grid_data import get_grid,region_values,age_seconds
from raster_map import make_map,SETTINGS,VIEWS

ROOT=Path(__file__).parent
st.set_page_config(page_title='Udara Nusantara — Kualitas Udara Indonesia',page_icon='🌏',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'DM Sans',sans-serif}.block-container{max-width:1500px;padding:1.2rem 3rem 2rem}h1,h2,h3{font-family:Manrope,sans-serif!important;letter-spacing:-.8px}header[data-testid="stHeader"]{background:transparent;height:0}#MainMenu,footer{visibility:hidden}[data-testid="stSidebar"]{display:none}.brandbar{display:flex;justify-content:space-between;align-items:center;padding:8px 0 25px;border-bottom:1px solid #dfe7ed;margin-bottom:25px}.brand{display:flex;align-items:center;gap:12px;font-size:21px;font-weight:800;letter-spacing:-.8px;color:#153a4e}.brand small{display:block;color:#8097a4;font-size:8px;letter-spacing:2px;margin-top:2px;font-weight:600}.brandmark{display:grid;place-items:center;background:#173d52;border-radius:12px;width:43px;height:43px;color:#9bd8d5;font-size:25px}.topnote{font-size:10px;letter-spacing:1px;color:#6e8797}.hero{position:relative;overflow:hidden;background:linear-gradient(115deg,#123449,#204c62);padding:34px 39px;border-radius:20px;color:#fff;margin:20px 0 27px;min-height:190px}.hero:after{content:'';position:absolute;right:-35px;top:-120px;width:400px;height:400px;border:65px solid #71b9c216;border-radius:50%;pointer-events:none}.hero .eyebrow{font-size:9px;letter-spacing:2px;color:#9bced2;font-weight:700;margin-bottom:14px}.hero h1{color:#fff;font-size:37px;line-height:1.22;margin:0 0 12px;letter-spacing:-1.2px;font-weight:650;max-width:730px}.hero p{font-size:12px;line-height:1.8;color:#b9ced9;margin:0;max-width:680px}.badge{display:inline-flex;gap:7px;align-items:center;padding:5px 10px;border:1px solid #cfe1e7;background:#eef6f6;border-radius:50px;font-size:10px;color:#2a7576;letter-spacing:.2px}.badge:before{content:'';width:5px;height:5px;border-radius:50%;background:#4caba4}.section-kicker{font-size:9px;letter-spacing:1.7px;color:#6e93a2;font-weight:700;margin-top:16px}.section-title{font-size:23px;color:#193e52;margin:7px 0 6px;font-weight:700;letter-spacing:-.7px}.section-desc{font-size:12px;line-height:1.8;color:#78909f;margin:0 0 20px}.timestamp{font-size:11px;color:#547485;background:#e6eef3;padding:10px 14px;border-radius:8px;margin:8px 0 14px}.soft-card{background:white;border:1px solid #e0e8ed;border-radius:13px;padding:22px 23px;margin:0 0 14px}.soft-card .tag{font-size:8px;letter-spacing:1.8px;font-weight:700;color:#7d9ca9;margin-bottom:10px}.soft-card h3{font-size:20px;color:#1f4657;margin:0 0 10px}.soft-card p{font-size:12px;line-height:1.85;color:#8096a2;margin:0}.soft-card .big{font-size:36px;font-weight:600;color:#1c6e78;letter-spacing:-1px}.soft-card .unit{font-size:12px;color:#8ba0ac}.coming{background:linear-gradient(150deg,#eaf0f4,#f1f6f6);border-style:dashed}.coming .soon{display:inline-block;font-size:8px;color:#668795;border:1px solid #c9d9e0;border-radius:4px;padding:4px 7px;letter-spacing:1px;margin-bottom:13px}.coming h3{font-size:17px}.source-line{font-size:10px;color:#8097a2;line-height:1.8;margin-top:8px}.source-line a{color:#447c8c!important}.public-footer{margin-top:42px;padding:26px 0 4px;border-top:1px solid #dce6ed;display:flex;justify-content:space-between;align-items:center;gap:20px;font-size:10px;color:#8ca0ad}.signature{font-size:13px;color:#315d6d;font-weight:600}.signature span{font-weight:400;color:#93a7b2;font-size:11px}div[data-testid="stMetric"]{background:#fff;border:1px solid #dfe8ee;border-radius:12px;padding:20px}div[data-testid="stMetricLabel"]{font-size:11px;color:#7b93a2}div[data-testid="stMetricValue"]{font-family:Manrope,sans-serif;font-size:27px;color:#1c5669}div[data-testid="stVerticalBlockBorderWrapper"]>div{border-radius:14px!important}div[data-testid="stAlert"]{border-radius:10px;font-size:12px}div[data-testid="stPlotlyChart"]{border-radius:12px;overflow:hidden}div[data-testid="stRadio"]>div{gap:20px}div[data-testid="stRadio"] label{font-size:12px}div[data-testid="stCaptionContainer"]{font-size:10px;line-height:1.7;color:#8ba0ac}div[data-testid="stSelectbox"] label,div[data-testid="stSelectSlider"] label{font-size:11px;color:#5a7b8e}button[data-baseweb="tab"]{font-size:12px}
@media(max-width:740px){.block-container{padding:1rem 1rem 2rem}.hero{padding:27px 24px}.hero h1{font-size:29px}.topnote{display:none}.hero:after{right:-160px}.public-footer{align-items:flex-start;flex-direction:column;gap:10px}.brandbar{padding-bottom:20px}.brand{font-size:19px}}
</style>''',unsafe_allow_html=True)

@st.cache_data(ttl=3600,show_spinner=False,max_entries=2)
def public_data():
    return get_grid()

@st.cache_data(show_spinner=False,max_entries=40)
def rendered_map(meta_timestamp,index,variable,view,_bundle,focus=None):
    return make_map(_bundle,index,variable,view,focus=focus)

def stamp(t):
    return pd.Timestamp(t).tz_convert('Asia/Jakarta').strftime('%d %b %Y · %H:%M WIB')

def html_block(s):st.markdown(s,unsafe_allow_html=True)

def footer():
    html_block('''<div class="public-footer"><div>UDARA NUSANTARA<br><span style="font-size:9px">Data: <a href="https://open-meteo.com/" target="_blank">Open-Meteo</a> / <a href="https://atmosphere.copernicus.eu/" target="_blank">Copernicus CAMS</a> · Peta: OpenStreetMap</span></div><div class="signature">made by ali<span>, a nya ai</span></div></div>''')

html_block('''<div class="brandbar"><div class="brand"><div class="brandmark">≈</div><div>udara nusantara<small>INDONESIA AIR QUALITY EXPLORER</small></div></div><div class="topnote">INDONESIA & SEKITARNYA &nbsp; / &nbsp; PRAKIRAAN KUALITAS UDARA</div></div>''')
nav=st.radio('Navigasi',['Peta sebaran','Analisis wilayah','Tentang data'],horizontal=True,label_visibility='collapsed')
html_block('''<div class="hero"><div class="eyebrow">MENGENAL UDARA DI SEKITAR KITA</div><h1>Melihat udara.<br>Memahami apa yang kita hirup.</h1><p>Jelajahi prakiraan kualitas udara dan pola sebaran polutan di Indonesia. Pilih wilayah dan waktu untuk melihat perubahan yang diperkirakan model.</p></div>''')

if nav=='Tentang data':
    html_block('<div class="section-kicker">BACA DENGAN KONTEKS</div><div class="section-title">Dari model, untuk gambaran yang lebih luas.</div>')
    left,right=st.columns([1.5,1])
    with left:
        with st.container(border=True):
            st.markdown('#### Apa yang ditampilkan?')
            st.write('Dashboard menampilkan prakiraan CAMS melalui Open-Meteo. Angkanya merupakan hasil model, bukan pengukuran langsung di setiap lokasi.')
            st.write('Lapisan warna menggambarkan konsentrasi di permukaan untuk PM2.5, PM10, CO, NO₂, SO₂, dan O₃. AOD total menggambarkan aerosol dalam kolom atmosfer, dengan satuan yang berbeda.')
            st.markdown('#### Seberapa rinci petanya?')
            st.write('Model global memiliki resolusi asli sekitar 45 km. Versi dashboard ini mengambil sampel setiap 1,2° (sekitar 130 km), lalu menghaluskan tampilan lapisan warna. Penghalusan tidak menambah ketelitian atau menunjukkan kondisi per jalan.')
            st.write('Ringkasan wilayah memakai grid sampel terdekat dari kota yang dipilih. Angka tersebut bukan rata-rata seluruh provinsi. Peta mencakup laut dan wilayah sekitar Indonesia untuk memperlihatkan konteks sebaran.')
            st.markdown('#### Waktu dan warna')
            st.write('Semua waktu ditampilkan dalam WIB agar mudah dibandingkan. Waktu berlaku prakiraan berbeda dari waktu data diperoleh. Warna mengikuti skala tetap untuk setiap parameter; nilai yang melewati batas atas memakai warna paling pekat. Data kosong dibuat transparan.')
            st.write('Kategori kualitas udara memakai US AQI dari penyedia. Konsentrasi polutan dan warna lapisan konsentrasi tidak otomatis merupakan kategori kesehatan atau ISPU Indonesia.')
    with right:
        html_block('''<div class="soft-card coming"><div class="soon">SEGERA HADIR</div><h3>Prediksi kabut asap</h3><p>Lapisan khusus asap kebakaran akan ditambahkan setelah sumber prediksi yang sesuai tersedia. AOD total dan PM2.5 tidak digunakan sebagai penggantinya.</p></div>''')
        st.link_button('Sumber & dokumentasi data ↗','https://open-meteo.com/en/docs/air-quality-api',width='stretch')
        st.caption('Dashboard independen, bukan produk resmi BMKG. Data model dapat berbeda dari pengamatan stasiun.')
    footer();st.stop()

@st.fragment(run_every=3600)
def live_dashboard():
    try:
        with st.spinner('Menyiapkan peta kualitas udara…'):
            bundle,warning=public_data()
    except DataError:
        st.info('Prakiraan sedang disiapkan. Silakan kembali beberapa saat lagi.')
        footer();st.stop()
    if warning:st.warning(warning)
    regions=load_regions(ROOT/'data/lokasi_indonesia.csv')
    city=region_values(bundle,regions)
    times=pd.to_datetime(bundle['times'],utc=True)
    # Three-hour intervals match the broad native temporal detail of the global model.
    indices=sorted(set(list(range(0,len(times),3))+[len(times)-1]))
    now=pd.Timestamp.now(tz='UTC')
    past=[i for i in indices if times[i]<=now]
    default=past[-1] if past else indices[0]
    if times[-1]<now:
        st.warning('Rentang prakiraan ini sudah berlalu. Kondisi terkini belum tersedia; waktu berlaku data tetap ditampilkan.')
    html_block('<span class="badge">PRAKIRAAN MODEL · CAMS GLOBAL</span>')

    if nav=='Peta sebaran':
        html_block('<div class="section-kicker">JELAJAHI POLA SEBARAN</div><div class="section-title">Satu peta, beragam cerita tentang udara.</div><p class="section-desc">Pilih parameter dan waktu berlaku prakiraan. Klik peta untuk membaca nilai pada grid sampel terdekat.</p>')
        a,b=st.columns([1.4,1])
        variable=a.selectbox('Parameter yang ditampilkan',list(SETTINGS),index=1,format_func=lambda x:SETTINGS[x][0])
        view=b.selectbox('Fokus wilayah',list(VIEWS))
        chosen=st.select_slider('Waktu berlaku prakiraan',options=indices,value=default,format_func=lambda i:stamp(times[i]),key='map_time')
        title,unit,low,high,colors=SETTINGS[variable]
        if variable=='aerosol_optical_depth':
            st.caption('AOD total adalah aerosol seluruh kolom atmosfer. Lapisan ini bukan prediksi khusus asap kebakaran.')
        html_block(f'<div class="timestamp">{html.escape(title)} &nbsp; / &nbsp; {stamp(times[chosen])}</div>')
        mapcol,sidecol=st.columns([3.1,1],gap='large')
        with mapcol:
            content=rendered_map(bundle['meta']['fetched_at'],chosen,variable,view,bundle)
            if hasattr(st, 'iframe'):
                st.iframe(content, height=550)
            else:
                components.html(content, height=550, scrolling=False)
            st.caption('Lapisan warna: prakiraan model pada grid sampel 1,2°, dihaluskan untuk visualisasi. Bukan pengamatan per lokasi.')
        with sidecol:
            at=city[city.waktu_utc.eq(times[chosen])]
            if view!='Indonesia':at=at[at.pulau.eq(view)]
            valid=at.dropna(subset=[variable])
            html_block('<div class="soft-card"><div class="tag">MEMBACA PETA</div><h3>Warna menunjukkan pola.</h3><p>Warna lebih pekat menunjukkan nilai yang lebih tinggi. Gunakan legenda pada peta untuk membaca satuannya.</p></div>')
            if not valid.empty:
                highrow=valid.loc[valid[variable].idxmax()]
                html_block(f'''<div class="soft-card"><div class="tag">TERTINGGI DI ANTARA KOTA SAMPEL</div><div class="big">{highrow[variable]:.1f} <span class="unit">{html.escape(unit)}</span></div><p style="margin-top:8px">{html.escape(highrow.lokasi)}<br>{html.escape(highrow.wilayah)}</p></div>''')
            html_block('''<div class="soft-card coming"><div class="soon">SEGERA HADIR</div><h3>Prediksi kabut asap</h3><p>Lapisan khusus aerosol dari kebakaran hutan dan lahan.</p></div>''')
        html_block(f'<div class="source-line">Data diperoleh {stamp(pd.Timestamp(bundle["meta"]["fetched_at"]))} · Prakiraan hingga tiga hari · Sumber: Open-Meteo / Copernicus CAMS</div>')

    if nav=='Analisis wilayah':
        html_block('<div class="section-kicker">LEBIH DEKAT DENGAN WILAYAHMU</div><div class="section-title">Lihat kondisi yang diperkirakan, dari waktu ke waktu.</div><p class="section-desc">Pilih kota representatif untuk membaca tren dan membandingkannya dengan wilayah lain.</p>')
        a,b=st.columns([1.4,1])
        selected=a.selectbox('Wilayah',regions.wilayah.tolist(),index=1)
        var=b.selectbox('Parameter analisis',list(SETTINGS),format_func=lambda x:SETTINGS[x][0],key='analysis_variable')
        chosen=st.select_slider('Waktu berlaku ringkasan',options=indices,value=default,format_func=lambda i:stamp(times[i]),key='analysis_time')
        title,unit,*_=SETTINGS[var]
        row=city[city.wilayah.eq(selected)&city.waktu_utc.eq(times[chosen])].iloc[0]
        html_block(f'<div class="timestamp">{html.escape(row.lokasi)} · {html.escape(selected)} &nbsp; / &nbsp; {stamp(times[chosen])}</div>')
        metrics=st.columns(3)
        metrics[0].metric('PM2.5',f'{row.pm2_5:.1f} µg/m³' if pd.notna(row.pm2_5) else 'Data tidak tersedia')
        metrics[1].metric('US AQI',f'{row.us_aqi:.0f}' if pd.notna(row.us_aqi) else 'Data tidak tersedia')
        metrics[2].metric('Kategori US AQI',aqi_category(row.us_aqi))
        st.caption('Ringkasan memakai grid sampel terdekat dari kota, bukan rata-rata seluruh wilayah.')
        st.markdown(f'#### Sebaran {title} di sekitar {selected}')
        location=regions.loc[regions.wilayah.eq(selected)].iloc[0]
        focus=(float(location.latitude),float(location.longitude))
        region_map=rendered_map(bundle['meta']['fetched_at'],chosen,var,location.pulau,bundle,focus=focus)
        if hasattr(st, 'iframe'):
            st.iframe(region_map, height=510)
        else:
            components.html(region_map, height=510, scrolling=False)
        st.caption(f'Fokus sekitar {location.lokasi} · {stamp(times[chosen])}. Lapisan warna memakai skala yang sama dengan Peta sebaran; bukan batas administrasi provinsi.')
        if var=='aerosol_optical_depth':
            st.caption('AOD total menggambarkan aerosol kolom atmosfer, bukan prediksi khusus asap kebakaran.')
        st.markdown('#### Tren dan perbandingan wilayah')
        compare=st.multiselect('Bandingkan dengan wilayah lain',[x for x in regions.wilayah if x!=selected],default=[])
        selected_regions=[selected]+compare
        subset=city[city.wilayah.isin(selected_regions)].copy();subset['waktu_wib']=subset.waktu_utc.dt.tz_convert('Asia/Jakarta')
        fig=px.line(subset,x='waktu_wib',y=var,color='wilayah',color_discrete_sequence=['#16858d','#e4a064','#7978a8','#74ad89'],
                    labels={'waktu_wib':'Waktu berlaku (WIB)',var:f'{title} ({unit})','wilayah':'Wilayah'})
        fig.update_layout(template='plotly_white',height=360,margin={'l':10,'r':10,'t':25,'b':10},font={'family':'Arial','color':'#547485'},legend={'orientation':'h','y':1.13},paper_bgcolor='#fff',plot_bgcolor='#fff')
        fig.update_traces(line={'width':2.6},connectgaps=False)
        st.plotly_chart(fig,width='stretch')
        st.markdown('#### Perbandingan kota pada waktu yang sama')
        ranking=city[city.waktu_utc.eq(times[chosen])].copy()
        ranking['kategori_us_aqi']=ranking.us_aqi.map(aqi_category)
        ranking=ranking.sort_values(var,ascending=False)
        st.dataframe(ranking[['wilayah','lokasi',var,'kategori_us_aqi']].rename(columns={'wilayah':'Wilayah','lokasi':'Kota representatif',var:title+' ('+unit+')','kategori_us_aqi':'Kategori US AQI'}),hide_index=True,width='stretch')
        export=subset.copy();export['sumber']='Open-Meteo / Copernicus CAMS';export['diambil_utc']=bundle['meta']['fetched_at']
        st.download_button('↓ Unduh data wilayah',export.to_csv(index=False).encode('utf-8-sig'),'prakiraan_wilayah.csv','text/csv')
    footer()

live_dashboard()
