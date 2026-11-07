"""Esfera auxiliar y lector OBJ. La geometría se carga una vez para los 3 shaders."""
from pathlib import Path
import numpy as np


def create_sphere(path, segments=64, rings=32):
    # Solo se utiliza para crear el recurso de respaldo, nunca para animarlo.
    vertices = [(0., 1., 0.)]
    for j in range(1, rings):
        phi = np.pi * j / rings
        for i in range(segments):
            theta = 2*np.pi*i/segments
            vertices.append((np.sin(phi)*np.sin(theta), np.cos(phi), np.sin(phi)*np.cos(theta)))
    vertices.append((0., -1., 0.))
    faces = []
    for i in range(segments):
        faces.append((0, 1+i, 1+(i+1)%segments))
    for j in range(rings-2):
        a, b = 1+j*segments, 1+(j+1)*segments
        for i in range(segments):
            k = (i+1)%segments
            faces.extend([(a+i,b+i,a+k), (a+k,b+i,b+k)])
    bottom = len(vertices)-1
    start = 1+(rings-2)*segments
    for i in range(segments):
        faces.append((start+i, bottom, start+(i+1)%segments))
    with Path(path).open('w', encoding='utf-8') as f:
        f.write('# Esfera de respaldo; sustituir por la proporcionada en clase.\n')
        for v in vertices:
            f.write('v %.9f %.9f %.9f\n' % v)
        for face in faces:
            f.write('f %d %d %d\n' % tuple(i+1 for i in face))


def load_obj(path):
    vertices, faces = [], []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append([float(v) for v in fields[1:4]])
        elif fields[0] == 'f':
            ids = [int(v.split('/')[0]) for v in fields[1:]]
            ids = [i-1 if i>0 else len(vertices)+i for i in ids]
            faces.extend((ids[0], ids[k], ids[k+1]) for k in range(1, len(ids)-1))
    vertices = np.asarray(vertices, dtype=float)
    faces = np.asarray(faces, dtype=int)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(faces):
        raise ValueError('El OBJ debe incluir vértices v y caras f.')
    # Se exige una esfera centrada y de radio 1: no se cambia ningún vértice.
    if not np.allclose(np.linalg.norm(vertices, axis=1), 1, atol=.03):
        raise ValueError('Este adaptador necesita una esfera centrada de radio 1. Ajusta la cámara/adaptador para el recurso de clase.')
    return vertices, faces
