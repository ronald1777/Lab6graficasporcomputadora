#!/usr/bin/env python3
"""Ejecutar desde cualquier directorio: python main.py --help."""
import argparse
from pathlib import Path
import time as clock
import numpy as np
from PIL import Image, ImageDraw
from src.mesh import load_obj
from src.renderer import rasterize, compose
from src.shaders import SHADERS, NAMES, PARAMS
from src.noise import normalize

ROOT = Path(__file__).resolve().parent


def light_direction(angle=-.85):
    return normalize(np.array([np.sin(angle),.28,np.cos(angle)]))


def render(g, body, time=0., light_angle=-.85):
    colors = SHADERS[body](g['p'],g['view'],light_direction(light_angle),time)
    return Image.fromarray(compose(g,colors))


def caption(image, text):
    image = image.copy()
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,0,image.width,27),fill=(4,8,18))
    draw.text((10,8),text,fill=(215,231,240))
    return image


def evidence(vertices, faces, size, directory):
    directory.mkdir(parents=True,exist_ok=True)
    g = rasterize(vertices,faces,size)
    captures = []
    for body in SHADERS:
        frame = render(g,body,1.8)
        frame.save(directory/f'{body}.png')
        captures.append(frame)
        frames = [caption(render(g,body,t),f'{body.upper()} | t={t:.1f} s | CPU')
                  for t in np.linspace(0,6,16,endpoint=False)]
        # Rebobinado explícito para no ocultar el salto temporal al repetir.
        frames = frames+frames[-2:0:-1]
        frames[0].save(directory/f'{body}_animacion.gif',save_all=True,
                       append_images=frames[1:],duration=140,loop=0)
        print(f'Evidencia {body} guardada',flush=True)
    frames = []
    for angle in np.linspace(-2.1,2.1,21):
        frames.append(caption(render(g,'rock',1.8,angle),f'NERIDA | luz={angle:.2f} rad | tiempo fijo'))
    frames += frames[-2:0:-1]
    frames[0].save(directory/'rock_luz.gif',save_all=True,append_images=frames[1:],duration=170,loop=0)
    # Comparación controlada del bump: misma cámara, luz y tiempo.
    original = PARAMS['rock']['bump_strength']
    PARAMS['rock']['bump_strength'] = 0.
    flat = render(g,'rock',1.8,-1.15)
    PARAMS['rock']['bump_strength'] = original
    bumped = render(g,'rock',1.8,-1.15)
    pair = Image.new('RGB',(size*2,size))
    pair.paste(caption(flat,'BUMP = 0.000'),(0,0))
    pair.paste(caption(bumped,f'BUMP = {original:.3f}'),(size,0))
    pair.save(directory/'rock_bump.png')
    sheet = Image.new('RGB',(size*3,size+45),(4,8,18))
    draw = ImageDraw.Draw(sheet)
    for i,(body,img) in enumerate(zip(SHADERS,captures)):
        sheet.paste(img,(i*size,0))
        draw.text((i*size+15,size+15),NAMES[body],fill=(216,230,239))
    sheet.save(directory/'galeria.png')


def interactive(vertices, faces, size, body):
    try:
        import tkinter as tk
        from PIL import ImageTk
        window = tk.Tk()
    except (ImportError, Exception) as e:
        raise SystemExit(f'No se pudo abrir la ventana: {e}\nUsa --render salida.png o instala Tk (ver README).')
    window.title('Laboratorio · shaders procedurales en CPU')
    window.configure(bg='#080e1c')
    label = tk.Label(window,bg='#080e1c')
    label.pack()
    info = tk.Label(window,fg='#d6e5ed',bg='#080e1c',justify='left',font=('Courier',10))
    info.pack(padx=12,pady=10)
    state = {'body':body,'yaw':0.,'light':-.85,'t':0.,'paused':False,'g':rasterize(vertices,faces,size),'last':clock.monotonic()}
    def key(event):
        k = event.keysym.lower()
        if k in ('1','2','3'):
            state['body'] = ('star','rock','gas')[int(k)-1]
        elif k == 'space': state['paused'] = not state['paused']
        elif k in ('left','right'):
            state['yaw'] += -.18 if k=='left' else .18
            state['g'] = rasterize(vertices,faces,size,state['yaw'])
        elif k in ('up','down'): state['light'] += .18 if k=='up' else -.18
        elif k == 'c': PARAMS['rock']['cloud_coverage'] = (PARAMS['rock']['cloud_coverage']+.2)%1.01
        elif k == 'b': PARAMS['rock']['bump_strength'] = 0. if PARAMS['rock']['bump_strength'] else .045
        elif k == 's':
            path = ROOT/'captura.png'
            render(state['g'],state['body'],state['t'],state['light']).save(path)
            print(f'Captura: {path}')
        elif k == 'r':
            state.update(yaw=0.,light=-.85,t=0.,paused=False)
            state['g'] = rasterize(vertices,faces,size)
        elif k == 'escape': window.destroy()
    window.bind('<Key>',key)
    def tick():
        now = clock.monotonic()
        if not state['paused']: state['t'] += min(now-state['last'],.5)
        state['last'] = now
        frame = render(state['g'],state['body'],state['t'],state['light'])
        photo = ImageTk.PhotoImage(frame)
        label.configure(image=photo)
        label.image = photo
        info.configure(text=f"{NAMES[state['body']]}\nt={state['t']:.1f}s  luz={state['light']:.2f}  nube={PARAMS['rock']['cloud_coverage']:.2f}\n1/2/3: cuerpo | Espacio: pausa | Esc: salir\nIzq/Der: camara | Arriba/Abajo: luz\nC: cobertura | B: bump | S: captura | R: reiniciar vista")
        window.after(30,tick)
    tick()
    window.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body',choices=SHADERS,default='rock')
    parser.add_argument('--size',type=int,default=360)
    parser.add_argument('--obj',type=Path,default=ROOT/'assets/sphere.obj')
    parser.add_argument('--time',type=float,default=1.8)
    parser.add_argument('--yaw',type=float,default=0.)
    parser.add_argument('--light',type=float,default=-.85)
    parser.add_argument('--render',type=Path,help='Exporta PNG sin abrir ventana')
    parser.add_argument('--evidence',action='store_true',help='Regenera capturas y GIF en evidencias/')
    args = parser.parse_args()
    if not 64<=args.size<=1600:
        parser.error('--size debe estar entre 64 y 1600')
    vertices,faces = load_obj(args.obj)
    if args.evidence: evidence(vertices,faces,args.size,ROOT/'evidencias')
    elif args.render:
        args.render.parent.mkdir(parents=True,exist_ok=True)
        render(rasterize(vertices,faces,args.size,args.yaw),args.body,args.time,args.light).save(args.render)
        print(args.render.resolve())
    else: interactive(vertices,faces,args.size,args.body)

if __name__=='__main__': main()
