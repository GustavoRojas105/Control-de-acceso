#!/usr/bin/env python3
"""
Cliente - Raspberry Pi Zero W (con sensor ultrasonico HC-SR04 y camara)

Detecta presencia con el ultrasonico, captura una rafaga corta de fotos
(para poder validar parpadeo despues) y las manda al servidor de
reconocimiento facial por HTTP.
"""

import time
import io
import requests
from picamera2 import Picamera2

# ---------- CONFIGURACION ----------
NUM_FOTOS = 6                   # fotos en la rafaga (necesarias para ver el parpadeo)
INTERVALO_FOTOS = 0.25          # segundos entre foto y foto
SERVIDOR_URL = "http://192.168.0.176:5000/verificar"  # <-- CAMBIA la IP de tu Pi servidor
COOLDOWN_SEG = 3                # tiempo minimo entre intentos, evita doble disparo por accidente

# ---------- SETUP ----------
camera = Picamera2()
# Resolucion baja a proposito: menos datos que mandar y menos trabajo
# para el servidor, que ya tiene bastante con el reconocimiento.
config = camera.create_still_configuration(main={"size": (640, 480)})
camera.configure(config)
camera.start()
time.sleep(2)  # deja estabilizar el sensor de la camara


def capturar_rafaga():
    """Captura NUM_FOTOS fotos seguidas y las regresa como lista de bytes JPEG."""
    fotos = []
    for _ in range(NUM_FOTOS):
        stream = io.BytesIO()
        camera.capture_file(stream, format="jpeg")
        stream.seek(0)
        fotos.append(stream.read())
        time.sleep(INTERVALO_FOTOS)
    return fotos


def enviar_rafaga(fotos):
    archivos = [
        (f"foto_{i}", (f"foto_{i}.jpg", contenido, "image/jpeg"))
        for i, contenido in enumerate(fotos)
    ]
    try:
        # timeout generoso: el servidor puede tardar varios segundos
        resp = requests.post(SERVIDOR_URL, files=archivos, timeout=45)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"Error al contactar al servidor: {e}")
        return None


def main():
    print("Sistema de acceso iniciado.")
    print("Presiona ENTER para capturar y verificar (Ctrl+C para salir).")
    ultimo_intento = 0
    while True:
        input(">> Enter para disparar la captura... ")
        ahora = time.time()

        if (ahora - ultimo_intento) < COOLDOWN_SEG:
            print("Espera un momento antes de intentar de nuevo.")
            continue

        ultimo_intento = ahora
        print("Capturando rafaga...")
        fotos = capturar_rafaga()
        resultado = enviar_rafaga(fotos)

        if resultado is None:
            print("No se pudo verificar (error de red).")
        elif resultado.get("acceso"):
            print(f"ACCESO CONCEDIDO a {resultado.get('nombre')}")
        else:
            print(f"Acceso denegado: {resultado.get('razon')}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
