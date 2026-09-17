# Control de acceso facial con 2 Raspberry Pi Zero W

## Arquitectura

```
[Pi A: cliente]                         [Pi B: servidor]
Ultrasonico HC-SR04                     encodings.pkl
Camara (Picamera2)      --- HTTP -->    Flask + face_recognition
                                         Rele -> chapa electrica
```

1. Pi A mide distancia constantemente con el ultrasonico.
2. Si alguien se acerca, captura 6 fotos seguidas (rafaga corta).
3. Manda la rafaga completa a Pi B por HTTP (multipart).
4. Pi B revisa si hubo un parpadeo real en la secuencia (evita fotos impresas).
5. Si hay parpadeo, compara el rostro contra `encodings.pkl`.
6. Si coincide, activa el rele unos segundos.

## Paso 0 — MUY IMPORTANTE: revisa tu .pkl primero

No recuerdas cómo se generó, así que antes de tocar `pi_servidor.py` corre:

```bash
python3 inspeccionar_pkl.py encodings.pkl
```

Esto te dice si es un diccionario `{nombre: encoding}`, algo tipo
`{"encodings": [...], "names": [...]}`, o algo distinto. `pi_servidor.py`
ya intenta detectar los dos formatos más comunes automáticamente, pero
si tu caso es raro, mándame la salida de este script y ajusto la función
`cargar_encodings()`.

## Paso 1 — Cableado

**Pi A (cliente):**
- HC-SR04: VCC a 5V, GND a GND, TRIG a GPIO23, ECHO a GPIO24
  ⚠️ el pin ECHO da 5V y los GPIO de la Pi son de 3.3V — necesitas un
  divisor de voltaje (dos resistencias, ej. 1kΩ y 2kΩ) entre ECHO y el
  GPIO, si no puedes dañar el pin.
- Cámara: al puerto CSI.

**Pi B (servidor):**
- Módulo de relé: VCC/GND según el módulo, señal (IN) a GPIO17.
- El relé controla la bobina de la chapa eléctrica (revisa si es NA o NC).

## Paso 2 — Instalar dependencias

Con Pi Zero W original (ARMv6) **no compiles dlib desde cero a mano**,
te vas a quedar sin RAM. Usa los wheels precompilados de piwheels
(ya viene configurado por default en Raspberry Pi OS):

```bash
# antes que nada, aumenta el swap temporalmente (dlib usa harta RAM al instalar)
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# En Pi B (servidor):
pip install flask face_recognition scipy numpy

# En Pi A (cliente):
pip install requests picamera2 RPi.GPIO
```

Si `pip install face_recognition` se traba o tarda demasiado, instala
`dlib` por separado primero (`pip install dlib`) y revisa que esté
bajando un `.whl` y no compilando (`Building wheel for dlib...` = mala
señal en una Zero W).

## Paso 3 — Configurar IPs

En `pi_cliente.py` cambia:
```python
SERVIDOR_URL = "http://192.168.1.50:5000/verificar"
```
por la IP real de tu Pi B (`hostname -I` en la Pi B te la da).

## Paso 4 — Correr

```bash
# En Pi B primero:
python3 pi_servidor.py

# En Pi A:
python3 pi_cliente.py
```

## Sobre el rendimiento (léelo antes de frustrarte)

Con una Zero W original (un solo núcleo, 512MB RAM), cada verificación
completa puede tardar entre **5 y 20 segundos**. Es normal, no es que
algo esté roto. Formas de acelerarlo si lo ves muy lento:

- Baja `NUM_FOTOS` de 6 a 4 en `pi_cliente.py`.
- Baja la resolución de captura (ej. 480x360).
- Sube `DISTANCIA_UMBRAL_CM` para que solo dispare cuando la persona
  ya está bien cerca y de frente (mejora la detección del rostro).
- Si sigue siendo demasiado lento para tu gusto, se puede cambiar
  `face_recognition` por el reconocedor LBPH de OpenCV, que es mucho
  más ligero pero menos preciso — dime si quieres esa alternativa.

## Siguientes pasos sugeridos

- Loggear los intentos (fecha, nombre, si se concedió o no) a un CSV o SQLite.
- Agregar un LED o buzzer en Pi A para dar feedback inmediato al usuario.
- Manejar el caso de "no llegó respuesta del servidor" con un mensaje claro.
