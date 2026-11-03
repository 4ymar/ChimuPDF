"""Crea chimupdf.ico a partir de chimupdf/recursos/chimupdf.png."""
from PIL import Image

origen = Image.open("chimupdf/recursos/chimupdf.png").convert("RGBA")
origen.save(
    "chimupdf.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("Creado chimupdf.ico")