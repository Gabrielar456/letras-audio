import math
import re
import struct
import wave
import subprocess
import os
import shutil

# Semitonos de cada nota natural respecto a C
SEMITONOS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

PATRON_NOTA = re.compile(r"^([A-Ga-g])([#b]?)(\d?)$")
SILENCIOS = {"R", "r", "-", "."}

FRECUENCIA_MUESTREO = 44100
DURACION = 0.4

octava_actual = 4  # Octava por defecto


def texto_a_notas(texto):
    notas = []
    for token in re.split(r"[\s,;]+", texto.strip()):
        if not token:
            continue
        if token in SILENCIOS:
            notas.append(None)
            continue
        m = PATRON_NOTA.match(token)
        if not m:
            raise ValueError(f"Nota no válida: '{token}'.")
        letra = m.group(1).upper()
        alteracion = m.group(2)
        octava = int(m.group(3)) if m.group(3) else 4

        semitono = SEMITONOS[letra]
        if alteracion == "#":
            semitono += 1
        elif alteracion == "b":
            semitono -= 1

        midi = 12 * (octava + 1) + semitono
        notas.append({
            "letra": letra,
            "alteracion": alteracion,
            "octava": octava,
            "nombre": f"{letra}{alteracion}{octava}",
            "freq": 440 * 2 ** ((midi - 69) / 12),
        })
    return notas


def generar_muestras(nota):
    total = int(FRECUENCIA_MUESTREO * DURACION)
    if nota is None:
        return [0] * total
    muestras = []
    for i in range(total):
        t = i / FRECUENCIA_MUESTREO
        fase = (t * nota["freq"]) % 1
        onda = 4 * abs(fase - 0.5) - 1
        envolvente = min(1, i / 400) * (1 - i / total)
        muestras.append(int(onda * envolvente * 0.4 * 32767))
    return muestras


def guardar_wav(notas, archivo):
    with wave.open(archivo, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA_MUESTREO)
        for nota in notas:
            datos = generar_muestras(nota)
            w.writeframes(struct.pack("<" + "h" * len(datos), *datos))


def nota_a_ly(nota):
    if nota is None:
        return "r4"
    nombre = nota["letra"].lower()
    if nota["alteracion"] == "#":
        nombre += "is"
    elif nota["alteracion"] == "b":
        nombre += "es"
    octava = nota["octava"]
    if octava >= 3:
        marcas = "'" * (octava - 3)
    else:
        marcas = "," * (3 - octava)
    return nombre + marcas + "4"


def guardar_ly(notas, texto, archivo):
    musica = " ".join(nota_a_ly(n) for n in notas)
    letras = " ".join('"' + n["nombre"] + '"' for n in notas if n)
    titulo = texto.replace('"', "").replace("\\", "")
    contenido = (
        '\\version "2.24.0"\n'
        f'\\header {{ title = "{titulo}" tagline = ##f }}\n'
        "\\score {\n"
        f"  \\new Staff {{ \\clef treble \\tempo 4 = 150 {musica} }}\n"
    )
    if letras:
        contenido += f"  \\addlyrics {{ {letras} }}\n"
    contenido += "  \\layout { }\n  \\midi { }\n}\n"
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(contenido)


def convertir_extras(carpeta, base):
    creados = []
    faltan = []

    # Generar PDF y MIDI con LilyPond
    if shutil.which("lilypond"):
        try:
            subprocess.run(
                ["lilypond", "-o", base, base + ".ly"],
                cwd=carpeta, capture_output=True, text=True, check=False
            )
            for ext in ("pdf", "midi"):
                if os.path.exists(base + "." + ext):
                    creados.append(ext)
            if not all(os.path.exists(base + "." + ext) for ext in ("pdf", "midi")):
                faltan.append("PDF/MIDI (error de LilyPond)")
        except Exception as e:
            faltan.append("LilyPond: " + str(e))
    else:
        faltan.append("LilyPond no instalado")

    # Generar MP3 con FFmpeg a partir del WAV
    if shutil.which("ffmpeg"):
        try:
            resultado = subprocess.run(
                ["ffmpeg", "-y", "-i", base + ".wav", base + ".mp3"],
                capture_output=True, text=True, check=False
            )
            if resultado.returncode == 0 and os.path.exists(base + ".mp3"):
                creados.append("mp3")
            else:
                faltan.append("MP3 (error de FFmpeg)")
        except Exception as e:
            faltan.append("FFmpeg: " + str(e))
    else:
        faltan.append("FFmpeg no instalado")

    return creados, faltan


def main():
    import tkinter as tk
    carpeta = os.path.dirname(os.path.abspath(__file__))

    ventana = tk.Tk()
    ventana.title("Compositor e Índice de Partitura (Bazilio)")
    ventana.geometry("520x730")
    ventana.config(bg="#FFF0F5")  # Fondo rosa pastel muy suave
    ventana.resizable(False, False)

    # Título principal
    tk.Label(
        ventana,
        text="Compositor e Índice\nde Partitura (Bazilio)",
        font=("Helvetica", 16, "bold"),
        bg="#FFF0F5",
        fg="#D81B60",
        justify="center"
    ).pack(pady=(12, 3))

    tk.Label(
        ventana,
        text="Agrega notas musicales con letras para generar\ntu partitura e interpretarla en Bazilio.",
        font=("Helvetica", 9),
        bg="#FFF0F5",
        fg="#884466",
        justify="center"
    ).pack(pady=(0, 8))

    # Campo de texto para las notas
    entrada = tk.Entry(
        ventana,
        font=("Helvetica", 13),
        width=35,
        justify="center",
        bg="#FFFFFF",
        fg="#4A154B",
        insertbackground="#D81B60"
    )
    entrada.pack(pady=4)
    entrada.focus()

    # Campo para nombre personalizado de archivo
    frame_nombre = tk.Frame(ventana, bg="#FFF0F5")
    frame_nombre.pack(pady=4)

    tk.Label(
        frame_nombre, text="Nombre del archivo:", font=("Helvetica", 10, "bold"),
        bg="#FFF0F5", fg="#884466"
    ).pack(side=tk.LEFT, padx=5)

    input_nombre = tk.Entry(
        frame_nombre,
        font=("Helvetica", 11),
        width=20,
        justify="center",
        bg="#FFFFFF",
        fg="#888888",
        insertbackground="#D81B60"
    )
    input_nombre.insert(0, "hanoi_musical")
    input_nombre.pack(side=tk.LEFT, padx=5)

    def borrar_placeholder(event):
        if input_nombre.get() == "hanoi_musical":
            input_nombre.delete(0, tk.END)
            input_nombre.config(fg="#4A154B")

    def restaurar_placeholder(event):
        if not input_nombre.get().strip():
            input_nombre.insert(0, "hanoi_musical")
            input_nombre.config(fg="#888888")

    input_nombre.bind("<FocusIn>", borrar_placeholder)
    input_nombre.bind("<FocusOut>", restaurar_placeholder)

    # Selector de Octava
    frame_octava = tk.Frame(ventana, bg="#FFF0F5")
    frame_octava.pack(pady=4)

    tk.Label(
        frame_octava, text="Octava:", font=("Helvetica", 10, "bold"),
        bg="#FFF0F5", fg="#884466"
    ).pack(side=tk.LEFT, padx=5)

    btns_octava = {}

    def cambiar_octava(oct):
        global octava_actual
        octava_actual = oct
        for o, b in btns_octava.items():
            if o == oct:
                b.config(bg="#FF69B4", fg="#ffffff")
            else:
                b.config(bg="#FFE4E1", fg="#884466")

    for o in (3, 4, 5):
        b = tk.Button(
            frame_octava, text=str(o), font=("Helvetica", 10, "bold"),
            width=4, bg="#FF69B4" if o == 4 else "#FFE4E1", 
            fg="#ffffff" if o == 4 else "#884466",
            command=lambda o=o: cambiar_octava(o), relief="flat"
        )
        b.pack(side=tk.LEFT, padx=3)
        btns_octava[o] = b

    # Botonera de notas (C, D, E, F, G, A, B)
    frame_notas = tk.Frame(ventana, bg="#FFF0F5")
    frame_notas.pack(pady=6)

    notas_info = [
        ("C\n(Do)", "C"), ("D\n(Re)", "D"), ("E\n(Mi)", "E"), ("F\n(Fa)", "F"),
        ("G\n(Sol)", "G"), ("A\n(La)", "A"), ("B\n(Si)", "B")
    ]

    def agregar_nota(letra):
        actual = entrada.get().strip()
        nota_str = f"{letra}{octava_actual}"
        nuevo = f"{actual} {nota_str}" if actual else nota_str
        entrada.delete(0, tk.END)
        entrada.insert(0, nuevo)

    for i, (txt, ltr) in enumerate(notas_info):
        row = 0 if i < 4 else 1
        col = i if i < 4 else i - 4
        btn = tk.Button(
            frame_notas, text=txt, font=("Helvetica", 10, "bold"),
            width=7, height=2, bg="#FFB6C1", fg="#4A154B",
            activebackground="#FF69B4", activeforeground="#ffffff",
            relief="flat", command=lambda l=ltr: agregar_nota(l)
        )
        btn.grid(row=row, column=col, padx=4, pady=3)

    # Botones de Acción
    frame_acciones = tk.Frame(ventana, bg="#FFF0F5")
    frame_acciones.pack(pady=6)

    def limpiar():
        entrada.delete(0, tk.END)
        estado.config(text="")

    def exportar_bzl():
        texto = entrada.get().strip()
        if not texto:
            estado.config(text="Escribe notas primero.", fg="#D32F2F")
            return
        limpio = input_nombre.get().strip()
        if not limpio or limpio == "hanoi_musical":
            limpio = "hanoi_musical"
        if not limpio.endswith(".bzl"):
            limpio += ".bzl"
        
        ruta_bzl = os.path.join(carpeta, limpio)
        with open(ruta_bzl, "w", encoding="utf-8") as f:
            f.write(f"Hanoi |:\n    tocar {texto}\n:|\n")
        estado.config(text=f"¡Exportado con éxito a {limpio}!", fg="#2E7D32")

    tk.Button(
        frame_acciones, text="Borrar", font=("Helvetica", 10, "bold"),
        bg="#EF9A9A", fg="#B71C1C", relief="flat", width=14,
        command=limpiar
    ).grid(row=0, column=0, padx=6, pady=4)

    tk.Button(
        frame_acciones, text="Compartir .bzl", font=("Helvetica", 10, "bold"),
        bg="#CE93D8", fg="#4A148C", relief="flat", width=14,
        command=exportar_bzl
    ).grid(row=0, column=1, padx=6, pady=4)

    tk.Button(
        frame_acciones, text="Generar Todo (WAV/LY/PDF/MIDI/MP3)", font=("Helvetica", 10, "bold"),
        bg="#A5D6A7", fg="#1B5E20", relief="flat", width=30,
        command=lambda: generar_todo()
    ).grid(row=1, column=0, columnspan=2, padx=6, pady=6)

    # Estado / Vista previa
    estado = tk.Label(
        ventana, text="", font=("Courier", 9), bg="#FFF0F5", fg="#C2185B",
        wraplength=480, justify="center"
    )
    estado.pack(pady=6)

    def generar_todo():
        texto = entrada.get().strip()
        if not texto:
            estado.config(text="Error: No hay notas escritas.", fg="#D32F2F")
            return
        
        limpio = input_nombre.get().strip()
        if not limpio or limpio == "hanoi_musical":
            limpio = "hanoi_musical"
        
        # Limpiar caracteres extraños del nombre de archivo
        limpio = "".join(c for c in limpio if c.isalnum() or c in " _-").strip()
        if not limpio:
            limpio = "hanoi_musical"

        base = os.path.join(carpeta, limpio)
        try:
            notas = texto_a_notas(texto)
            guardar_wav(notas, base + ".wav")
            guardar_ly(notas, texto, base + ".ly")
            creados, faltan = convertir_extras(carpeta, base)
            
            msg = f"Archivos generados para '{limpio}':\n.wav, .ly"
            if creados:
                msg += f", {', '.join(creados)}"
            if faltan:
                msg += f"\n(Aviso: {', '.join(faltan)})"
                
            estado.config(text=msg, fg="#2E7D32")
        except Exception as e:
            estado.config(text=f"Error: {e}", fg="#D32F2F")

    ventana.mainloop()

def parsear_notas(texto):
    """Convierte 'C4 E4 G4 -' en notas. '-' es un silencio. Devuelve (notas, errores)."""
    SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    notas, errores = [], []

    for token in texto.replace(",", " ").split():
        t = token.upper()
        if t in ("-", "R"):
            notas.append(None)                      # silencio
            continue

        letra, resto = t[0], t[1:]
        if letra in SEMI and (resto == "" or (resto.isdigit() and int(resto) <= 8)):
            octava = int(resto) if resto else 4     # sin número = octava 4
            midi = 12 * (octava + 1) + SEMI[letra]
            notas.append({
                "letra": letra,
                "nombre": f"{letra}{octava}",
                "freq": 440 * 2 ** ((midi - 69) / 12),
            })
        else:
            errores.append(token)

    return notas, errores

if __name__ == "__main__":
    main()