"""Rasterizador de triángulos en CPU: bounding boxes, baricéntricas y z-buffer.
No usa OpenGL, WebGL, shaders GPU, ray tracing ni texturas de entrada.
"""
import numpy as np
from .noise import normalize


def rasterize(vertices, faces, size=420, yaw=0., pitch=.08):
    cy, sy, cp, sp = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch)
    ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    rx = np.array([[1,0,0],[0,cp,-sp],[0,sp,cp]])
    rotation = rx @ ry
    camera = vertices @ rotation.T
    scale = size*.405
    screen = np.column_stack((camera[:,0]*scale+size/2, -camera[:,1]*scale+size/2))
    depth = np.full((size,size), -np.inf)
    positions = np.zeros((size,size,3))
    for tri in faces:
        xy = screen[tri]
        xmin, ymin = np.maximum(np.floor(xy.min(axis=0)).astype(int), 0)
        xmax, ymax = np.minimum(np.ceil(xy.max(axis=0)).astype(int), size-1)
        if xmax < xmin or ymax < ymin:
            continue
        a,b,c = xy
        denom = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denom)<1e-10:
            continue
        xx, yy = np.meshgrid(np.arange(xmin,xmax+1)+.5, np.arange(ymin,ymax+1)+.5)
        w0 = ((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/denom
        w1 = ((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/denom
        w2 = 1-w0-w1
        z = w0*camera[tri[0],2]+w1*camera[tri[1],2]+w2*camera[tri[2],2]
        target = depth[ymin:ymax+1,xmin:xmax+1]
        keep = (w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8)&(z>target)
        target[keep] = z[keep]
        p = (w0[...,None]*vertices[tri[0]]+w1[...,None]*vertices[tri[1]]+w2[...,None]*vertices[tri[2]])
        positions[ymin:ymax+1,xmin:xmax+1][keep] = p[keep]
    mask = np.isfinite(depth)
    # Normales suaves radiales, apropiadas para la esfera sin desplazar vértices.
    return {'mask':mask, 'p':normalize(positions[mask]),
            'view':np.array([0.,0.,1.]) @ rotation, 'size':size}


def compose(gbuffer, color):
    size = gbuffer['size']
    yy,xx = np.mgrid[0:size,0:size]
    radial = np.clip(1-np.sqrt((xx-size/2)**2+(yy-size/2)**2)/size,0,1)
    bg = np.zeros((size,size,3))+np.array([.009,.014,.033])
    bg += radial[...,None]*np.array([.012,.018,.030])
    bg[gbuffer['mask']] = np.clip(color,0,1)
    return np.uint8(np.clip(bg,0,1)*255+.5)
