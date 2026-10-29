import wave

SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
IDX = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}


def _partes(nota):
    return nota["nombre"][0], int(nota["nombre"][1:])


# ---------- .ly (LilyPond) ----------
def _ly(nota):
    if nota is None:
        return "r4"
    letra, octava = _partes(nota)
    marca = "'" * (octava - 3) if octava >= 3 else "," * (3 - octava)
    return letra.lower() + marca + "4"


def guardar_ly(notas, texto, archivo):
    titulo = texto.replace('"', "").replace("\\", "")
    musica = " ".join(_ly(n) for n in notas)
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(
            '\\version "2.24.0"\n'
            f'\\header {{ title = "{titulo}" tagline = ##f }}\n'
            "\\score {\n"
            f"  \\new Staff {{ \\clef treble \\tempo 4 = 150 {musica} }}\n"
            "  \\layout { }\n  \\midi { }\n}\n"
        )


# ---------- .bzl (programa de Bazilio) ----------
def guardar_bzl(notas, nombre, archivo):
    ident = "".join(c for c in nombre if c.isalnum()) or "Musica"
    ident = ident[0].upper() + ident[1:] if ident[0].isalpha() else "M" + ident
    lineas = [f"{ident} |:"]
    lineas += [f"    <:> {n['nombre']}" for n in notas if n]   # los silencios se omiten
    lineas.append(":|")
    with open(archivo, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


# ---------- .midi (sin librerías) ----------
def _vlq(n):
    partes = [n & 0x7F]
    n >>= 7
    while n:
        partes.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(partes))


def guardar_midi(notas, archivo):
    TICKS = 480
    datos = bytearray(b"\x00\xFF\x51\x03" + (400000).to_bytes(3, "big"))  # 150 bpm
    pendiente = 0
    for n in notas:
        if n is None:
            pendiente += TICKS
            continue
        letra, octava = _partes(n)
        m = 12 * (octava + 1) + SEMI[letra]
        datos += _vlq(pendiente) + bytes([0x90, m, 90])
        datos += _vlq(TICKS) + bytes([0x80, m, 0])
        pendiente = 0
    datos += _vlq(pendiente) + b"\xFF\x2F\x00"
    cabecera = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") \
        + (1).to_bytes(2, "big") + TICKS.to_bytes(2, "big")
    with open(archivo, "wb") as f:
        f.write(cabecera + b"MTrk" + len(datos).to_bytes(4, "big") + bytes(datos))


# ---------- .mp3 (a partir del .wav) ----------
def guardar_mp3(wav, mp3):
    import lameenc
    with wave.open(wav, "rb") as w:
        pcm = w.readframes(w.getnframes())
        rate = w.getframerate()
    enc = lameenc.Encoder()
    enc.set_bit_rate(128)
    enc.set_in_sample_rate(rate)
    enc.set_channels(1)
    enc.set_quality(2)
    with open(mp3, "wb") as f:
        f.write(enc.encode(pcm) + enc.flush())


# ---------- .pdf (partitura dibujada) ----------
def guardar_pdf(notas, texto, archivo):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas

    ancho, alto = landscape(A4)
    c = canvas.Canvas(archivo, pagesize=(ancho, alto))
    espacio, margen, por_linea = 8, 50, 18
    medio = espacio / 2
    paso_x = (ancho - 2 * margen - 40) / por_linea

    def encabezado():
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(ancho / 2, alto - 40, texto)

    encabezado()
    y = alto - 150
    for inicio in range(0, len(notas), por_linea):
        if y < 80:
            c.showPage()
            encabezado()
            y = alto - 150
        c.setLineWidth(0.7)
        for i in range(5):
            c.line(margen, y + i * espacio, ancho - margen, y + i * espacio)
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(margen + 2, y + 5 * espacio + 4, "clave de sol")

        for k, n in enumerate(notas[inicio:inicio + por_linea]):
            x = margen + 40 + k * paso_x
            if n is None:                                   # silencio
                c.rect(x - 4, y + 2 * espacio - 1, 8, 3, fill=1)
                continue
            letra, octava = _partes(n)
            paso = octava * 7 + IDX[letra]                  # E4 = 30 = línea de abajo
            p = max(18, min(44, paso))                      # evita salirse de la hoja
            ny = y + (p - 30) * medio
            for q in range(28, p - 1, -2):                  # líneas adicionales abajo
                c.line(x - 9, y + (q - 30) * medio, x + 9, y + (q - 30) * medio)
            for q in range(40, p + 1, 2):                   # líneas adicionales arriba
                c.line(x - 9, y + (q - 30) * medio, x + 9, y + (q - 30) * medio)
            c.ellipse(x - 5, ny - 3.5, x + 5, ny + 3.5, fill=1)
            if p < 34:
                c.line(x + 4.5, ny, x + 4.5, ny + 26)
            else:
                c.line(x - 4.5, ny, x - 4.5, ny - 26)
            c.setFont("Helvetica", 8)
            c.drawCentredString(x, y - 64, n["nombre"])
        y -= 140
    c.save()