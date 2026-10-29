import io
import os
import tempfile
import zipfile

import streamlit as st
from letras import parsear_notas, guardar_wav
from exportar import guardar_ly, guardar_bzl, guardar_midi, guardar_mp3, guardar_pdf

ORDEN = ["bzl", "ly", "pdf", "midi", "wav", "mp3"]
MIMES = {"bzl": "text/plain", "ly": "text/plain", "pdf": "application/pdf",
         "midi": "audio/midi", "wav": "audio/wav", "mp3": "audio/mpeg"}

st.title("Notas a Audio")

texto = st.text_input("Escribe las notas separadas por espacio", placeholder="C4 E4 G4 C5")
nombre = st.text_input("Nombre de los archivos", value="notas")
st.caption("Notas de A a G con octava 0-8 (ej. C4). Sin número = octava 4. Usa - para un silencio.")

if st.button("Generar todo") and texto:
    notas, errores = parsear_notas(texto)

    if errores:
        st.error("Notas no válidas: " + ", ".join(errores))
    elif not notas:
        st.warning("No hay notas que tocar.")
    else:
        limpio = "".join(c for c in nombre if c.isalnum() or c in " _-").strip() or "notas"
        carpeta = tempfile.mkdtemp()
        base = os.path.join(carpeta, limpio)

        guardar_wav(notas, base + ".wav")
        generadores = {
            "bzl": lambda: guardar_bzl(notas, limpio, base + ".bzl"),
            "ly": lambda: guardar_ly(notas, texto, base + ".ly"),
            "pdf": lambda: guardar_pdf(notas, texto, base + ".pdf"),
            "midi": lambda: guardar_midi(notas, base + ".midi"),
            "mp3": lambda: guardar_mp3(base + ".wav", base + ".mp3"),
        }
        fallos = []
        for ext, fn in generadores.items():
            try:
                fn()
            except Exception as e:
                fallos.append(f"{ext}: {e}")

        st.write("  ".join(n["nombre"] if n else "·" for n in notas))
        st.audio(base + ".wav")

        existentes = [e for e in ORDEN if os.path.exists(f"{base}.{e}")]

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            for e in existentes:
                z.write(f"{base}.{e}", f"{limpio}.{e}")
        st.download_button("Descargar todo (.zip)", buffer.getvalue(),
                           file_name=f"{limpio}.zip", mime="application/zip",
                           on_click="ignore")

        for e in existentes:
            with open(f"{base}.{e}", "rb") as f:
                st.download_button(f"Descargar .{e}", f.read(),
                                   file_name=f"{limpio}.{e}", mime=MIMES[e],
                                   on_click="ignore")

        if fallos:
            st.warning("No se generó: " + " | ".join(fallos))