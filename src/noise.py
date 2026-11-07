"""Ruido de valor 3D reproducible; no usa imágenes ni archivos de texturas."""
import numpy as np


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def hash3(x, y, z):
    return np.mod(np.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453, 1)


def noise(p):
    cell = np.floor(p)
    f = p - cell
    u = f * f * (3 - 2 * f)
    value = np.zeros(p.shape[:-1])
    for x in (0, 1):
        for y in (0, 1):
            for z in (0, 1):
                w = ((u[..., 0] if x else 1-u[..., 0]) *
                     (u[..., 1] if y else 1-u[..., 1]) *
                     (u[..., 2] if z else 1-u[..., 2]))
                value += w * hash3(cell[..., 0]+x, cell[..., 1]+y, cell[..., 2]+z)
    return value


def fbm(p, octaves=4):
    result = np.zeros(p.shape[:-1])
    amplitude, total = .5, 0.
    for _ in range(octaves):
        result += amplitude * noise(p)
        total += amplitude
        p = p * 2.03 + np.array([17.1, 9.2, 3.7])
        amplitude *= .5
    return result / total


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-10)


def mix(a, b, t):
    return np.asarray(a) * (1-t[..., None]) + np.asarray(b) * t[..., None]
