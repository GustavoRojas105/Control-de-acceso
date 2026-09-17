#!/usr/bin/env python3
"""
Corre esto primero (puede ser en tu compu, no hace falta que sea en la Pi)
para saber exactamente que forma tiene tu encodings.pkl y asi confirmar
que pi_servidor.py lo esta leyendo bien.

Uso:
    python3 inspeccionar_pkl.py ruta/a/tu/archivo.pkl
"""

import pickle
import sys

ruta = sys.argv[1] if len(sys.argv) > 1 else "encodings.pkl"

with open(ruta, "rb") as f:
    datos = pickle.load(f)

print(f"Tipo del objeto principal: {type(datos)}")

if isinstance(datos, dict):
    llaves = list(datos.keys())
    print(f"Numero de llaves: {len(llaves)}")
    print(f"Primeras llaves: {llaves[:10]}")
    primera = llaves[0]
    valor = datos[primera]
    print(f"\nEjemplo -> llave: {primera!r}")
    print(f"Tipo del valor: {type(valor)}")
    if hasattr(valor, "__len__"):
        print(f"Longitud del valor: {len(valor)}")
        if len(valor) and hasattr(valor[0], "__len__"):
            print(f"Parece una LISTA de encodings. Longitud del primer encoding: {len(valor[0])}")
        else:
            print("Parece ser UN SOLO encoding (numero flotante por posicion).")

elif isinstance(datos, (list, tuple)):
    print(f"Longitud de la lista: {len(datos)}")
    if len(datos):
        print(f"Tipo del primer elemento: {type(datos[0])}")
        print(f"Primer elemento (recortado): {str(datos[0])[:300]}")
else:
    print(f"Contenido crudo (primeros 500 caracteres):\n{str(datos)[:500]}")
