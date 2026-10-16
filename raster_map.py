"""Lapisan raster geografis dari grid; tidak menggambar heatmap dari kota."""
import base64,io,json,html
import numpy as np
from PIL import Image
import folium
from folium.raster_layers import mercator_transform
from matplotlib.colors import LinearSegmentedColormap,Normalize
from branca.element import Element, MacroElement
from jinja2 import Template
from pathlib import Path

SETTINGS={
 'us_aqi':('Kualitas udara · US AQI','indeks',0,300,['#5dceac','#d1e98e','#f4d772','#ef9b59','#d95167','#913e81']),
 'pm2_5':('PM2.5','µg/m³',0,150,['#b5e4dc','#58bea7','#c6d981','#f4d479','#ec995f','#ce6269','#803d68']),
 'pm10':('PM10','µg/m³',0,250,['#b5e4dc','#58bea7','#c6d981','#f4d479','#ec995f','#ce6269','#803d68']),
 'carbon_monoxide':('Karbon monoksida · CO','µg/m³',0,1500,['#e2eff6','#91b9d2','#5f8faf','#b983ad','#cb5675','#773352']),
 'nitrogen_dioxide':('Nitrogen dioksida · NO₂','µg/m³',0,80,['#e2eff6','#91b9d2','#5f8faf','#b983ad','#cb5675','#773352']),
 'sulphur_dioxide':('Sulfur dioksida · SO₂','µg/m³',0,60,['#e5eefa','#9cbbe0','#6384c1','#b478b0','#d65775','#793553']),
 'ozone':('Ozon · O₃','µg/m³',0,180,['#daedf0','#8bc7cb','#75abac','#d7cd8a','#e8a15e','#aa5670']),
 'aerosol_optical_depth':('Aerosol total · AOD 550 nm','tanpa satuan',0,2,['#e2edf9','#a3bfdf','#789ed0','#b381b4','#d57687','#b74462','#703653']),
}
VIEWS={'Indonesia':([-2.7,118.2],4),'Sumatra':([-0.1,101.8],5),'Jawa':([-7.2,110.3],6),'Kalimantan':([0.1,114.1],5),
 'Sulawesi':([-1.7,121.4],5),'Bali dan Nusa Tenggara':([-8.5,119],6),'Maluku':([-2,128.4],6),'Papua':([-4,136.5],5)}

def raster_rgba(values,vmin,vmax,colors,scale=16):
    """Upsample for display only; mask missing original cells, no gap filling."""
    values=np.asarray(values,dtype=np.float32)
    valid=np.isfinite(values)
    size=(values.shape[1]*scale,values.shape[0]*scale)
    raw=Image.fromarray(np.where(valid,values,0).astype('float32'))
    weights=Image.fromarray(valid.astype('float32'))
    up=np.asarray(raw.resize(size,Image.Resampling.BILINEAR))
    denominator=np.asarray(weights.resize(size,Image.Resampling.BILINEAR))
    out=np.divide(up,denominator,out=np.zeros_like(up),where=denominator>0)
    mask=np.asarray(Image.fromarray((valid*255).astype('uint8')).resize(size,Image.Resampling.NEAREST))>0
    cmap=LinearSegmentedColormap.from_list('pollutant',colors)
    rgba=(cmap(Normalize(vmin,vmax,clip=True)(out))*255).astype('uint8')
    rgba[:,:,3]=np.where(mask,255,0)
    return rgba

def bounds_for(bundle):
    step=bundle['meta']['sampling_step']
    return [[float(bundle['lats'].min()-step/2),float(bundle['lons'].min()-step/2)],
            [float(bundle['lats'].max()+step/2),float(bundle['lons'].max()+step/2)]]

def make_map(bundle,index,variable='pm2_5',view='Indonesia',focus=None):
    title,unit,low,high,colors=SETTINGS[variable]
    values=bundle[variable][index]
    image=raster_rgba(values,low,high,colors)
    bounds=bounds_for(bundle)
    loc,zoom=VIEWS[view]
    if focus is not None:
        loc=[float(focus[0]),float(focus[1])]
        zoom=6
    m=folium.Map(location=loc,zoom_start=zoom,height='100%',tiles=None,control_scale=True,
                 min_zoom=3,max_zoom=10,prefer_canvas=True)
    # Embed the runtime locally: a CDN failure must not leave an empty iframe.
    vendor=Path(__file__).parent/'vendor'
    m.default_js=[]
    m.default_css=[]
    m.get_root().header.add_child(Element('<meta name="referrer" content="strict-origin-when-cross-origin">'))
    m.get_root().header.add_child(Element('<style>'+ (vendor/'leaflet.css').read_text() +'</style>'))
    m.get_root().header.add_child(Element('<script>'+ (vendor/'leaflet.js').read_text() +'</script>'))
    folium.TileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                     attr='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',name='Peta dasar',control=False,
                     max_zoom=19).add_to(m)
    # Data arrays go south -> north; origin lower places them correctly.
    folium.raster_layers.ImageOverlay(image,bounds=bounds,origin='lower',mercator_project=True,
                    opacity=.58,name=title,interactive=False,pixelated=False).add_to(m)
    gradient=', '.join(colors)
    legend=f'''<div class="raster-legend"><div class="legend-heading">{html.escape(title)} <span>{html.escape(unit)}</span></div>
    <div style="background:linear-gradient(to right,{gradient});height:9px;border-radius:8px;margin:9px 0 6px"></div>
    <div class="legend-numbers"><span>{low}</span><span>{high/4:g}</span><span>{high/2:g}</span><span>{high*3/4:g}</span><span>≥{high}</span></div></div>'''
    m.get_root().html.add_child(Element(legend))
    m.get_root().header.add_child(Element('''<style>html,body{font-family:Arial,sans-serif}.leaflet-container{background:#dce8ed}.leaflet-tile{filter:grayscale(1) brightness(1.04)}.raster-legend{position:absolute;bottom:32px;left:16px;z-index:999;background:rgba(255,255,255,.94);padding:13px 16px;border-radius:12px;box-shadow:0 4px 20px #173a4620;width:300px;max-width:calc(100% - 65px)}.legend-heading{font-size:12px;font-weight:700;color:#284758}.legend-heading span{float:right;font-size:10px;font-weight:400;color:#748691}.legend-numbers{display:flex;justify-content:space-between;font-size:10px;color:#647986}.leaflet-control-zoom{border:0!important;box-shadow:0 2px 12px #173a4620!important}.leaflet-control-attribution{font-size:9px!important}</style>'''))
    raw_values=[[None if not np.isfinite(v) else round(float(v),3) for v in row] for row in values]
    name=m.get_name()
    # A click reports the nearest sampled grid cell, never a fake street-level value.
    script='''const latitudes=LATITUDES,longitudes=LONGITUDES,field=VALUES,bbox=BOUNDS;
    MAP.on('click',function(e){const y=e.latlng.lat,x=e.latlng.lng;if(y<bbox[0][0]||y>bbox[1][0]||x<bbox[0][1]||x>bbox[1][1])return;
    const iy=latitudes.reduce((a,v,i)=>Math.abs(v-y)<Math.abs(latitudes[a]-y)?i:a,0);
    const ix=longitudes.reduce((a,v,i)=>Math.abs(v-x)<Math.abs(longitudes[a]-x)?i:a,0);
    const v=field[iy][ix];const val=v===null?'Data tidak tersedia':v.toLocaleString('id-ID',{maximumFractionDigits:2})+' UNIT';
    L.popup().setLatLng(e.latlng).setContent('<div style="font-family:Arial;min-width:180px"><b>TITLE</b><p style="font-size:22px;margin:9px 0">'+val+'</p><small>Prakiraan pada grid sampel terdekat<br>'+latitudes[iy].toFixed(2)+', '+longitudes[ix].toFixed(2)+'</small></div>').openOn(MAP);});'''
    for key,value in {'LATITUDES':json.dumps(bundle['lats'].tolist()),'LONGITUDES':json.dumps(bundle['lons'].tolist()),
                      'VALUES':json.dumps(raw_values),'BOUNDS':json.dumps(bounds),'MAP':name,
                      'UNIT':unit,'TITLE':title}.items():script=script.replace(key,value)
    # Map children render their script after L.map() and the data layers.
    interaction=MacroElement()
    interaction._template=Template('{% macro script(this, kwargs) %}'+script+'{% endmacro %}')
    m.add_child(interaction)
    return m.get_root().render()
