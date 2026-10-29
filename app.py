import streamlit as st
from letras import parsear_notas, guardar_wav

st.title("Notas a Audio")

texto = st.text_input("Escribe las notas separadas por espacio", placeholder="C4 E4 G4 C5")
nombre = st.text_input("Nombre del audio", value="notas")
st.caption("Notas de A a G con octava 0-8 (ej. C4). Sin número = octava 4. Usa - para un silencio.")

if st.button("Generar audio") and texto:
    notas, errores = parsear_notas(texto)

    if errores:
        st.error("Notas no válidas: " + ", ".join(errores))
    elif not notas:
        st.warning("No hay notas que tocar.")
    else:
        limpio = "".join(c for c in nombre if c.isalnum() or c in " _-").strip() or "notas"
        archivo = f"{limpio}.wav"

        st.write("  ".join(n["nombre"] if n else "·" for n in notas))
        guardar_wav(notas, archivo)
        st.audio(archivo)

        with open(archivo, "rb") as f:
            st.download_button("Descargar audio", f, file_name=archivo, mime="audio/wav")