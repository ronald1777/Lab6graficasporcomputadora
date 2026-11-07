"""Tres fragment shaders. Entrada: coordenada/normal local, vista, luz y tiempo.
Todos los colores, regiones, nubes, manchas y tormentas son matemáticos.
"""
import numpy as np
from .noise import noise, fbm, smoothstep, normalize, mix

PARAMS = {
    'star': {'granule_scale':38., 'turbulence':.65, 'speed':.32, 'spot_threshold':.65},
    'rock': {'continent_scale':2.5, 'sea_level':.49, 'cloud_coverage':.52,
             'cloud_speed':.13, 'bump_strength':.045, 'cloud_height':.055,
             'specular_power':75., 'city_strength':1.0},
    'gas': {'band_frequency':22., 'vortex_strength':3.8, 'vortex_radius':.48,
            'flow_speed':.14, 'warp':.26},
}
NAMES = {'star':'HELIOS · estrella de ámbar', 'rock':'NERIDA · océanos y tierras de jade',
         'gas':'ZEFIRO · gigante de bandas turquesa'}


def star_shader(p, view, light, time, params=None):
    s = params or PARAMS['star']
    t = time*s['speed']
    # Advección del campo y dominio deformado: el material cambia con malla fija.
    q = p*4 + np.array([t,0,-t*.6])
    warp = np.stack([noise(q+11),noise(q+37),noise(q+71)],axis=-1)-.5
    granules = fbm(p*s['granule_scale'] + warp*s['turbulence']*8 + t, 3)
    cracks = smoothstep(.30,.62,granules)
    spots = smoothstep(s['spot_threshold'],s['spot_threshold']+.13,fbm(q*1.1,3))
    color = mix([.70,.085,.008],[1.,.79,.19],cracks)
    color = mix(color,[.19,.012,.018],spots*.85)
    # Oscurecimiento del limbo, sin depender de luz externa (superficie emisiva).
    facing = np.maximum(p@view,0)
    return color*(.64+.36*np.sqrt(facing))[:,None]


def terrain(p, s):
    q = p*s['continent_scale'] + np.array([3.1,4.7,1.3])
    warp = np.stack([noise(q+5),noise(q+17),noise(q+29)],axis=-1)-.5
    return fbm(q+warp*.8,5)


def cloud_mask(p, time, s):
    # Rotación SOLO de coordenadas del ruido; la geometría permanece intacta.
    a = time*s['cloud_speed']
    q = np.stack([p[:,0]*np.cos(a)+p[:,2]*np.sin(a),p[:,1],
                  -p[:,0]*np.sin(a)+p[:,2]*np.cos(a)],axis=-1)
    w = fbm(q*3.4+19,3)
    density = fbm(q*8 + w[:,None]*1.8+7,4)
    threshold = .76-.43*s['cloud_coverage']
    return smoothstep(threshold-.055,threshold+.055,density)*.90


def bump_normal(p, height, s):
    # Gradiente central del campo de altura; proyectado al plano tangente.
    eps = .003
    gradients = []
    for axis in np.eye(3):
        gradients.append((terrain(normalize(p+axis*eps),s)-terrain(normalize(p-axis*eps),s))/(2*eps))
    grad = np.stack(gradients,axis=-1)
    grad -= np.sum(grad*p,axis=-1)[:,None]*p
    land = smoothstep(s['sea_level']-.015,s['sea_level']+.035,height)
    return normalize(p-s['bump_strength']*grad*land[:,None])


def rock_shader(p, view, light, time, params=None):
    s = params or PARAMS['rock']
    h = terrain(p,s)
    land = smoothstep(s['sea_level']-.012,s['sea_level']+.018,h)
    shallow = smoothstep(s['sea_level']-.13,s['sea_level'],h)
    ocean = mix([.012,.040,.14],[.02,.29,.38],shallow)
    dryness = fbm(p*5+42,3)
    ground = mix([.055,.24,.16],[.63,.44,.22],smoothstep(.43,.64,dryness))
    peaks = smoothstep(.64,.75,h)
    ice = smoothstep(.76,.95,np.abs(p[:,1]))
    ground = mix(ground,[.80,.85,.79],np.maximum(peaks,ice))
    base = mix(ocean,ground,land)
    n = bump_normal(p,h,s)
    ndl = np.maximum(n@light,0)
    geometric_ndl = p@light
    # Intersección del rayo hacia la luz con una envolvente esférica de nubes.
    # No se añade malla: solo se evalúa el mismo campo en el punto proyectado.
    radius = 1+s['cloud_height']
    ray_distance = -geometric_ndl+np.sqrt(geometric_ndl**2+radius**2-1)
    cloud_hit = normalize(p+ray_distance[:,None]*light)
    shadow = cloud_mask(cloud_hit,time,s)*smoothstep(.03,.24,geometric_ndl)
    lighting = .075+.925*ndl*(1-.60*shadow)
    color = base*lighting[:,None]
    # Agua brillante y suelo mate; el brillo responde al vector mitad.
    half = normalize(view+light)
    spec = np.maximum(n@half,0)**s['specular_power']
    color += spec[:,None]*(1-land)[:,None]*np.maximum(geometric_ndl,0)[:,None]*np.array([.80,.92,1.])
    # Agrupaciones de luces en tierra, filtradas por la noche y cerca de costas.
    city = smoothstep(.66,.77,noise(p*115))
    clusters = smoothstep(.55,.64,fbm(p*18+8,3))
    coastal = land*(1-smoothstep(s['sea_level']+.04,s['sea_level']+.13,h))
    night = 1-smoothstep(-.22,.06,geometric_ndl)
    color += (city*clusters*coastal*night*s['city_strength'])[:,None]*np.array([1.,.57,.13])
    clouds = cloud_mask(p,time,s)
    cloud_light = .10+.90*np.maximum(geometric_ndl,0)
    color = mix(color,np.array([.88,.94,1.])*cloud_light[:,None],clouds)
    # Bruma de limbo calculada en el mismo fragmento, sin otra esfera.
    rim = (1-np.maximum(p@view,0))**4
    color += (rim*(.10+.25*np.maximum(geometric_ndl,0)))[:,None]*np.array([.10,.36,.60])
    return color


def gas_coordinates(p, time, s):
    longitude = np.arctan2(p[:,0],p[:,2])
    latitude = np.arcsin(np.clip(p[:,1],-1,1))
    # Vórtice localizado: rotar el dominio dentro de una envolvente gaussiana.
    dx = (longitude-.18+np.pi)%(2*np.pi)-np.pi
    dy = latitude+.19
    r2 = dx*dx+(dy*1.35)**2
    angle = s['vortex_strength']*np.exp(-r2/(s['vortex_radius']**2))
    x = dx*np.cos(angle)-dy*np.sin(angle)
    y = dx*np.sin(angle)+dy*np.cos(angle)
    lon,lat = longitude+(x-dx), latitude+(y-dy)
    # Volver a 3D elimina costuras de ruido en el meridiano.
    q = np.stack([np.cos(lat)*np.sin(lon),np.sin(lat),np.cos(lat)*np.cos(lon)],axis=-1)
    q[:,0] += time*s['flow_speed']
    return lat,q,r2


def gas_shader(p, view, light, time, params=None):
    s = params or PARAMS['gas']
    lat,q,r2 = gas_coordinates(p,time,s)
    turbulence = fbm(q*7+np.array([time*.07,3.,1.]),4)-.5
    bands = .5+.5*np.sin(lat*s['band_frequency']+s['warp']*turbulence*18)
    color = mix([.025,.16,.23],[.25,.73,.66],smoothstep(.12,.88,bands))
    fine = fbm(q*36+2,3)
    color *= (.77+.34*fine)[:,None]
    # La tinta cálida sigue la misma coordenada torcida que curva las bandas.
    tint = np.exp(-r2/.15)*(.35+.65*bands)*.70
    color = mix(color,[.91,.57,.28],tint)
    diffuse = .18+.82*np.maximum(p@light,0)
    return color*diffuse[:,None]

SHADERS = {'star':star_shader,'rock':rock_shader,'gas':gas_shader}
