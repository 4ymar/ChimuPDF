from PySide6.QtGui import QImage, QPixmap


def pixmap_de_pagina(documento, indice, zoom, dpr=1.0):
    """Pixmap de la página. Con dpr > 1 se dibuja con más píxeles para verse nítido en pantallas escaladas."""
    datos, ancho, alto, stride = documento.renderizar(indice, zoom * dpr)
    imagen = QImage(datos, ancho, alto, stride, QImage.Format.Format_RGB888).copy()
    pixmap = QPixmap.fromImage(imagen)
    pixmap.setDevicePixelRatio(dpr)
    return pixmap
