#!/usr/bin/env python3
"""
Servidor - Raspberry Pi Zero W (la que tiene encodings.pkl)

Recibe una rafaga de fotos, valida que hubo un parpadeo real (para que
no sirva engañarlo con una foto impresa o de pantalla), compara el
rostro contra encodings.pkl y, si coincide, activa el rele de la
chapa electrica.
"""

import pickle
import time
import numpy as np
import face_recognition
from flask import Flask, request, jsonify
from scipy.spatial import distance as dist
import RPi.GPIO as GPIO

# ---------- CONFIGURACION ----------
PKL_PATH = "encodings.pkl"
RELE_PIN = 17
TOLERANCIA_ROSTRO = 0.5       # mas bajo = mas estricto (0.6 es el default de face_recognition)
EAR_UMBRAL = 0.21             # por debajo de esto se considera "ojo cerrado"
TIEMPO_RELE_SEG = 4

app = Flask(__name__)

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELE_PIN, GPIO.OUT)
GPIO.output(RELE_PIN, GPIO.LOW)


def cargar_encodings():
    """
    Soporta los dos formatos mas comunes generados por scripts de
    face_recognition:
      - {"encodings": [...], "names": [...]}
      - {"nombre": encoding_o_lista_de_encodings, ...}

    Si tu pkl tiene otra forma, corre primero inspeccionar_pkl.py
    y ajusta esta funcion segun lo que veas.
    """
    with open(PKL_PATH, "rb") as f:
        datos = pickle.load(f)

    nombres = []
    encodings = []

    if isinstance(datos, dict) and "encodings" in datos and "names" in datos:
        encodings = list(datos["encodings"])
        nombres = list(datos["names"])
    elif isinstance(datos, dict) and "embeddings" in datos and "nombres" in datos:
        encodings = [np.array(e) for e in datos["embeddings"]]
        nombres = list(datos["nombres"])
    elif isinstance(datos, dict):
        for nombre, valor in datos.items():
            # ¿es una lista de varios encodings de la misma persona?
            if isinstance(valor, (list, tuple)) and len(valor) and hasattr(valor[0], "__len__"):
                for enc in valor:
                    encodings.append(np.array(enc))
                    nombres.append(nombre)
            else:
                encodings.append(np.array(valor))
                nombres.append(nombre)
    else:
        raise ValueError(
            "Formato de encodings.pkl no reconocido automaticamente. "
            "Corre inspeccionar_pkl.py y ajusta cargar_encodings()."
        )

    return nombres, encodings


NOMBRES_CONOCIDOS, ENCODINGS_CONOCIDOS = cargar_encodings()
print(f"Cargados {len(ENCODINGS_CONOCIDOS)} rostros conocidos: {set(NOMBRES_CONOCIDOS)}")


def calcular_ear(ojo):
    """Eye Aspect Ratio: baja cuando el ojo se cierra."""
    a = dist.euclidean(ojo[1], ojo[5])
    b = dist.euclidean(ojo[2], ojo[4])
    c = dist.euclidean(ojo[0], ojo[3])
    return (a + b) / (2.0 * c)


def hubo_parpadeo(lista_imagenes):
    """Revisa la secuencia y regresa True si el EAR baja del umbral y luego se recupera."""
    ears = []
    for img in lista_imagenes:
        # model="large" = 68 puntos, necesario para tener los 6 puntos por ojo del EAR
        landmarks = face_recognition.face_landmarks(img, model="large")
        if not landmarks:
            continue
        puntos = landmarks[0]
        if "left_eye" not in puntos or "right_eye" not in puntos:
            continue
        ear_izq = calcular_ear(puntos["left_eye"])
        ear_der = calcular_ear(puntos["right_eye"])
        ears.append((ear_izq + ear_der) / 2.0)

    if len(ears) < 3:
        return False

    return min(ears) < EAR_UMBRAL and max(ears) > EAR_UMBRAL


def reconocer_rostro(lista_imagenes):
    """Busca el primer frame con un rostro claro y lo compara contra los conocidos."""
    for img in lista_imagenes:
        ubicaciones = face_recognition.face_locations(img, model="hog")  # hog = mucho mas rapido que cnn en CPU
        if not ubicaciones:
            continue
        encs = face_recognition.face_encodings(img, ubicaciones, num_jitters=0)
        if not encs:
            continue

        distancias = face_recognition.face_distance(ENCODINGS_CONOCIDOS, encs[0])
        idx = int(np.argmin(distancias))
        if distancias[idx] <= TOLERANCIA_ROSTRO:
            return NOMBRES_CONOCIDOS[idx]
    return None


def activar_rele():
    GPIO.output(RELE_PIN, GPIO.HIGH)
    time.sleep(TIEMPO_RELE_SEG)
    GPIO.output(RELE_PIN, GPIO.LOW)


@app.route("/verificar", methods=["POST"])
def verificar():
    archivos = sorted(request.files.values(), key=lambda f: f.filename)
    if not archivos:
        return jsonify({"acceso": False, "razon": "no llegaron fotos"}), 400

    imagenes = [face_recognition.load_image_file(a) for a in archivos]

    if not hubo_parpadeo(imagenes):
        return jsonify({"acceso": False, "razon": "no se detecto parpadeo (posible foto/spoof)"})

    nombre = reconocer_rostro(imagenes)
    if nombre is None:
        return jsonify({"acceso": False, "razon": "rostro no reconocido"})

    activar_rele()
    return jsonify({"acceso": True, "nombre": nombre})


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000)
    finally:
        GPIO.cleanup()
