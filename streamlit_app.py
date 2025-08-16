import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageTk  # Added ImageTk here
import yt_dlp
import json
from datetime import datetime
import webbrowser

# =========================
# Constantes y Configuración
# =========================
NOMBRE_APP = "Descargador Musical Pro"
VERSION = "2.1.0"
ARCHIVO_CONFIG = "config_descargador.json"
URL_SOPORTE = "https://github.com/tu-repositorio/soporte"

# Paleta de colores profesional
COLORES = {
    "fondo": "#4a4b4d",
    "tarjeta": "#ffffff",
    "primario": "#b11313",
    "primario_oscuro": "#a82918",
    "secundario": "#34a853",
    "acento": "#ea4335",
    "texto": "#202124",
    "texto_secundario": "#f0855a",
    "borde": "#dadce0"
}

# =========================
# Funciones de Utilidad
# =========================
def crear_logo_pro(ruta_png="logo_pro.png", ruta_ico="logo_pro.ico"):
    """Crea un logo profesional con diseño moderno"""
    if os.path.exists(ruta_png) and os.path.exists(ruta_ico):
        return ruta_png, ruta_ico

    tamaño = 512
    img = Image.new("RGBA", (tamaño, tamaño), (0, 0, 0, 0))
    
    # Fondo con gradiente moderno
    gradiente = Image.new("RGBA", (tamaño, tamaño), (0,0,0,0))
    dibujar_g = ImageDraw.Draw(gradiente)
    for y in range(tamaño):
        r = int(66 + (189 - 66) * (y/tamaño))
        g = int(133 + (228 - 133) * (y/tamaño))
        b = int(244 + (255 - 244) * (y/tamaño))
        dibujar_g.line([(0, y), (tamaño, y)], fill=(r, g, b, 255))
    
    # Círculo recortado
    mascara = Image.new("L", (tamaño, tamaño), 0)
    dibujar_m = ImageDraw.Draw(mascara)
    dibujar_m.ellipse((50, 50, tamaño-50, tamaño-50), fill=255)
    gradiente.putalpha(mascara)
    img = Image.alpha_composite(img, gradiente)

    # Ícono de reproducción (triángulo moderno)
    tamaño_play = 160
    img_play = Image.new("RGBA", (tamaño, tamaño), (0,0,0,0))
    dibujar_p = ImageDraw.Draw(img_play)
    triangulo = [
        (tamaño//2 - tamaño_play//3, tamaño//2 - tamaño_play//2),
        (tamaño//2 - tamaño_play//3, tamaño//2 + tamaño_play//2),
        (tamaño//2 + tamaño_play//2, tamaño//2)
    ]
    dibujar_p.polygon(triangulo, fill=(255,255,255,220))

    # Sombra para el ícono
    sombra = img_play.filter(ImageFilter.GaussianBlur(15))
    sombra = ImageOps.colorize(sombra.split()[-1], black=(0,0,0), white=(0,0,0))
    sombra.putalpha(100)
    img = Image.alpha_composite(img, sombra)
    img = Image.alpha_composite(img, img_play)

    # Guardar archivos
    img.save(ruta_png, "PNG")
    
    # Crear ícono con múltiples tamaños
    tamaños_ico = [(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)]
    ico = img.copy()
    ico.save(ruta_ico, sizes=tamaños_ico)

    return ruta_png, ruta_ico

def cargar_configuracion():
    """Carga la configuración desde archivo"""
    valores_por_defecto = {
        "directorio_descargas": os.path.expanduser("~/Música"),
        "calidad_audio": "192",
        "modo_oscuro": False,
        "intentos_maximos": 5,
        "descargas_paralelas": 1
    }
    
    try:
        if os.path.exists(ARCHIVO_CONFIG):
            with open(ARCHIVO_CONFIG, 'r') as f:
                config = json.load(f)
                return {**valores_por_defecto, **config}
    except Exception:
        pass
    
    return valores_por_defecto

def guardar_configuracion(config):
    """Guarda la configuración en archivo"""
    try:
        with open(ARCHIVO_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass

def seleccionar_carpeta():
    """Abre el diálogo para seleccionar carpeta"""
    carpeta = filedialog.askdirectory(title="Seleccionar carpeta de descarga")
    if carpeta:
        var_carpeta.set(carpeta)

def limpiar_porcentaje(cadena_porcentaje):
    """Extrae el porcentaje de diferentes formatos de cadena"""
    if not cadena_porcentaje:
        return 0.0
    coincidencia = re.search(r'(\d+(?:\.\d+)?)\s*%', str(cadena_porcentaje))
    return float(coincidencia.group(1)) if coincidencia else 0.0

# =========================
# Lógica de Descarga
# =========================
def hook_progreso(d):
    """Callback para actualizar el progreso"""
    if d.get('status') == 'downloading':
        porcentaje = limpiar_porcentaje(d.get('_percent_str', '0%'))
        barra_progreso['value'] = porcentaje
        etiqueta_estado.config(text=f"Descargando: {porcentaje:.1f}%")
        ventana.update_idletasks()
    elif d.get('status') == 'finished':
        barra_progreso['value'] = 100
        etiqueta_estado.config(text="Procesando archivo de audio...")
        ventana.update_idletasks()

def descargar_urls():
    """Función principal de descarga con manejo de errores"""
    urls_crudas = entrada_url.get().strip()
    if not urls_crudas:
        messagebox.showwarning("Entrada requerida", "Ingresa una o más URLs de YouTube.")
        return
    
    directorio_descarga = var_carpeta.get().strip()
    if not directorio_descarga:
        messagebox.showwarning("Ubicación requerida", "Selecciona una carpeta de destino.")
        return
    
    os.makedirs(directorio_descarga, exist_ok=True)
    
    # Preparar lista de URLs (soporta separadas por coma, punto y coma o nueva línea)
    urls = [u.strip() for u in re.split(r'[,;\n]', urls_crudas) if u.strip()]
    
    # Deshabilitar UI durante la descarga
    boton_descargar.config(state="disabled")
    entrada_url.config(state="disabled")
    boton_carpeta.config(state="disabled")
    etiqueta_estado.config(text="Inicializando...")
    barra_progreso['value'] = 0
    
    # Obtener configuración de calidad
    calidad = var_calidad.get()
    
    def hilo_descarga():
        try:
            # Opciones profesionales de descarga
            opciones_ydl = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(directorio_descarga, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'retries': config['intentos_maximos'],
                'fragment_retries': 10,
                'concurrent_fragment_downloads': config['descargas_paralelas'],
                'windowsfilenames': True,
                'progress_hooks': [hook_progreso],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': calidad,
                }],
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'skip': ['dash', 'hls']
                    }
                },
                'logger': RegistradorYDL(),
            }
            
            for i, url in enumerate(urls, 1):
                barra_progreso['value'] = 0
                etiqueta_estado.config(text=f"Procesando URL {i} de {len(urls)}...")
                ventana.update_idletasks()
                
                try:
                    with yt_dlp.YoutubeDL(opciones_ydl) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info:
                            etiqueta_estado.config(text=f"Descargando: {info['title']}")
                            ventana.update_idletasks()
                            ydl.download([url])
                            
                            # Registrar descarga exitosa
                            registrar_descarga(info['title'], url, directorio_descarga)
                            
                            etiqueta_estado.config(text=f"✓ Completado {i}/{len(urls)}")
                        else:
                            etiqueta_estado.config(text=f"⚠ No se pudo obtener información del video")
                except Exception as e:
                    mensaje_error = f"Error al descargar: {url}\n\nError: {str(e)}"
                    messagebox.showerror("Error de descarga", mensaje_error)
                    etiqueta_estado.config(text=f"⚠ Error con URL {i}")
            
            etiqueta_estado.config(text="✓ Todas las descargas completadas exitosamente")
            
            # Actualizar configuración con el último directorio usado
            config['directorio_descargas'] = directorio_descarga
            guardar_configuracion(config)
            
        except Exception as e:
            messagebox.showerror("Error crítico", f"Ocurrió un error grave:\n{str(e)}")
            etiqueta_estado.config(text="⚠ Falló la descarga")
        finally:
            boton_descargar.config(state="normal")
            entrada_url.config(state="normal")
            boton_carpeta.config(state="normal")

    threading.Thread(target=hilo_descarga, daemon=True).start()

class RegistradorYDL:
    """Registrador personalizado para yt-dlp"""
    def debug(self, msg):
        pass  # Ignorar mensajes de depuración
    
    def warning(self, msg):
        if "URL could be a direct video link" not in msg:  # Ignorar advertencia común
            print(f"Advertencia: {msg}")
    
    def error(self, msg):
        print(f"Error: {msg}")

def registrar_descarga(titulo, url, directorio):
    """Registra descargas exitosas para historial"""
    entrada_registro = {
        "fecha": datetime.now().isoformat(),
        "titulo": titulo,
        "url": url,
        "directorio": directorio
    }
    
    archivo_registro = os.path.join(os.path.dirname(ARCHIVO_CONFIG), "historial_descargas.json")
    try:
        historial = []
        if os.path.exists(archivo_registro):
            with open(archivo_registro, 'r') as f:
                historial = json.load(f)
        
        historial.append(entrada_registro)
        
        with open(archivo_registro, 'w') as f:
            json.dump(historial, f, indent=2)
    except Exception:
        pass

# =========================
# Ventana de Configuración
# =========================
def mostrar_configuracion():
    """Diálogo profesional de configuración"""
    ventana_config = tk.Toplevel(ventana)
    ventana_config.title("Configuración")
    ventana_config.geometry("500x400")
    ventana_config.resizable(False, False)
    ventana_config.configure(bg=COLORES['fondo'])
    
    # Encabezado
    encabezado = tk.Frame(ventana_config, bg=COLORES['primario'], height=60)
    encabezado.pack(fill="x")
    tk.Label(encabezado, text="Configuración", font=("Helvetica", 16, "bold"), 
            bg=COLORES['primario'], fg="white").pack(pady=15, padx=20, anchor="w")
    
    # Contenido principal
    contenido = tk.Frame(ventana_config, bg=COLORES['fondo'], padx=20, pady=20)
    contenido.pack(fill="both", expand=True)
    
    # Calidad de Audio
    tk.Label(contenido, text="Calidad de Audio (kbps):", bg=COLORES['fondo'], 
             fg=COLORES['texto'], font=("Helvetica", 10)).grid(row=0, column=0, sticky="w", pady=5)
    opciones_calidad = ["128", "192", "256", "320"]
    menu_calidad = ttk.Combobox(contenido, values=opciones_calidad, textvariable=var_calidad, width=8)
    menu_calidad.grid(row=0, column=1, sticky="w", padx=10, pady=5)
    
    # Intentos Máximos
    tk.Label(contenido, text="Intentos Máximos:", bg=COLORES['fondo'], 
             fg=COLORES['texto'], font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", pady=5)
    spinner_intentos = tk.Spinbox(contenido, from_=1, to=10, textvariable=var_intentos, width=5)
    spinner_intentos.grid(row=1, column=1, sticky="w", padx=10, pady=5)
    
    # Descargas Paralelas
    tk.Label(contenido, text="Descargas Paralelas:", bg=COLORES['fondo'], 
             fg=COLORES['texto'], font=("Helvetica", 10)).grid(row=2, column=0, sticky="w", pady=5)
    spinner_paralelas = tk.Spinbox(contenido, from_=1, to=4, textvariable=var_paralelas, width=5)
    spinner_paralelas.grid(row=2, column=1, sticky="w", padx=10, pady=5)
    
    # Modo Oscuro
    check_modo_oscuro = tk.Checkbutton(
        contenido, text="Activar Modo Oscuro", variable=var_modo_oscuro,
        bg=COLORES['fondo'], fg=COLORES['texto'], selectcolor=COLORES['fondo'],
        activebackground=COLORES['fondo'], activeforeground=COLORES['texto'],
        font=("Helvetica", 10), command=cambiar_modo_oscuro
    )
    check_modo_oscuro.grid(row=3, column=0, columnspan=2, sticky="w", pady=10)
    
    # Botón Guardar
    marco_guardar = tk.Frame(contenido, bg=COLORES['fondo'])
    marco_guardar.grid(row=4, column=0, columnspan=2, pady=20)
    tk.Button(
        marco_guardar, text="Guardar Configuración", command=lambda: guardar_config_y_cerrar(ventana_config),
        bg=COLORES['primario'], fg="white", activebackground=COLORES['primario_oscuro'],
        font=("Helvetica", 10, "bold"), padx=20, pady=5
    ).pack()

def guardar_config_y_cerrar(ventana_config):
    """Guarda la configuración y cierra la ventana"""
    config.update({
        'calidad_audio': var_calidad.get(),
        'intentos_maximos': var_intentos.get(),
        'descargas_paralelas': var_paralelas.get(),
        'modo_oscuro': var_modo_oscuro.get()
    })
    guardar_configuracion(config)
    ventana_config.destroy()

def cambiar_modo_oscuro():
    """Alterna entre modo claro y oscuro"""
    if var_modo_oscuro.get():
        COLORES.update({
            "fondo": "#121212",
            "tarjeta": "#1e1e1e",
            "texto": "#e1e1e1",
            "texto_secundario": "#a0a0a0",
            "borde": "#333333"
        })
    else:
        COLORES.update({
            "fondo": "#f8f9fa",
            "tarjeta": "#ffffff",
            "texto": "#202124",
            "texto_secundario": "#5f6368",
            "borde": "#dadce0"
        })
    aplicar_tema()

def aplicar_tema():
    """Aplica el tema de colores actual a todos los widgets"""
    ventana.configure(bg=COLORES['fondo'])
    marco_encabezado.configure(bg=COLORES['primario'])
    etiqueta_titulo.configure(bg=COLORES['primario'], fg="white")
    marco_tarjeta.configure(bg=COLORES['tarjeta'])
    
    for widget in marco_tarjeta.winfo_children():
        if isinstance(widget, (tk.Label, tk.Frame)):
            widget.configure(bg=COLORES['tarjeta'])
    
    etiqueta_url.configure(fg=COLORES['texto'])
    etiqueta_carpeta.configure(fg=COLORES['texto'])
    etiqueta_estado.configure(fg=COLORES['texto'])
    
    entrada_url.configure(
        bg=COLORES['tarjeta'], fg=COLORES['texto'],
        highlightbackground=COLORES['borde'],
        highlightcolor=COLORES['primario']
    )
    entrada_carpeta.configure(
        bg=COLORES['tarjeta'], fg=COLORES['texto'],
        highlightbackground=COLORES['borde'],
        highlightcolor=COLORES['primario']
    )
    
    estilo.configure("TProgressbar",
        troughcolor=COLORES['fondo'],
        background=COLORES['primario'],
        bordercolor=COLORES['borde'],
        lightcolor=COLORES['primario'],
        darkcolor=COLORES['primario_oscuro']
    )

# =========================
# Ventana Acerca De
# =========================
def mostrar_acerca_de():
    """Diálogo profesional Acerca De"""
    ventana_acerca = tk.Toplevel(ventana)
    ventana_acerca.title(f"Acerca de {NOMBRE_APP}")
    ventana_acerca.geometry("400x300")
    ventana_acerca.resizable(False, False)
    ventana_acerca.configure(bg=COLORES['fondo'])
    
    # Encabezado
    encabezado = tk.Frame(ventana_acerca, bg=COLORES['primario'], height=60)
    encabezado.pack(fill="x")
    tk.Label(encabezado, text=f"Acerca de {NOMBRE_APP}", font=("Helvetica", 16, "bold"), 
            bg=COLORES['primario'], fg="white").pack(pady=15, padx=20, anchor="w")
    
    # Contenido
    contenido = tk.Frame(ventana_acerca, bg=COLORES['fondo'], padx=20, pady=20)
    contenido.pack(fill="both", expand=True)
    
    # Logo y versión
    logo_pequeno = ImageTk.PhotoImage(imagen_logo.resize((64,64), Image.LANCZOS))
    etiqueta_logo = tk.Label(contenido, image=logo_pequeno, bg=COLORES['fondo'])
    etiqueta_logo.image = logo_pequeno
    etiqueta_logo.pack(pady=10)
    
    tk.Label(contenido, text=f"{NOMBRE_APP} v{VERSION}", 
             font=("Helvetica", 12, "bold"), bg=COLORES['fondo'], fg=COLORES['texto']).pack()
    
    tk.Label(contenido, text="Descargador profesional de música de YouTube", 
             font=("Helvetica", 10), bg=COLORES['fondo'], fg=COLORES['texto_secundario']).pack(pady=5)
    
    # Enlace de soporte
    enlace_soporte = tk.Label(
        contenido, text="Soporte Técnico", font=("Helvetica", 10, "underline"), 
        fg=COLORES['primario'], bg=COLORES['fondo'], cursor="hand2")
    enlace_soporte.pack(pady=10)
    enlace_soporte.bind("<Button-1>", lambda e: webbrowser.open(URL_SOPORTE))
    
    # Copyright
    tk.Label(contenido, text=f"© 2023 {NOMBRE_APP}. Todos los derechos reservados.", 
             font=("Helvetica", 8), bg=COLORES['fondo'], fg=COLORES['texto_secundario']).pack(side="bottom", pady=10)

# =========================
# Ventana Principal
# =========================
# Inicializar configuración
config = cargar_configuracion()

# Crear ventana principal
ventana = tk.Tk()
ventana.title(f"{NOMBRE_APP} v{VERSION}")
ventana.geometry("720x520")
ventana.minsize(600, 450)

# Crear logo profesional
ruta_logo_png, ruta_logo_ico = crear_logo_pro()
try:
    ventana.iconbitmap(ruta_logo_ico)
except:
    pass

# Cargar imagen del logo
imagen_logo = Image.open(ruta_logo_png)

# Crear estilo
estilo = ttk.Style()
estilo.theme_use('clam')

# Variables
var_carpeta = tk.StringVar(value=config['directorio_descargas'])
var_calidad = tk.StringVar(value=config['calidad_audio'])
var_intentos = tk.IntVar(value=config['intentos_maximos'])
var_paralelas = tk.IntVar(value=config['descargas_paralelas'])
var_modo_oscuro = tk.BooleanVar(value=config['modo_oscuro'])

# Encabezado
marco_encabezado = tk.Frame(ventana, bg=COLORES['primario'], height=80)
marco_encabezado.pack(fill="x")

etiqueta_titulo = tk.Label(
    marco_encabezado,
    text=NOMBRE_APP,
    font=("Helvetica", 20, "bold"),
    fg="white",
    bg=COLORES['primario']
)
etiqueta_titulo.pack(side="left", padx=20, pady=10)

# Barra de menú
barra_menu = tk.Menu(ventana)
ventana.config(menu=barra_menu)

# Menú Archivo
menu_archivo = tk.Menu(barra_menu, tearoff=0)
barra_menu.add_cascade(label="Archivo", menu=menu_archivo)
menu_archivo.add_command(label="Configuración...", command=mostrar_configuracion)
menu_archivo.add_separator()
menu_archivo.add_command(label="Salir", command=ventana.quit)

# Menú Ayuda
menu_ayuda = tk.Menu(barra_menu, tearoff=0)
barra_menu.add_cascade(label="Ayuda", menu=menu_ayuda)
menu_ayuda.add_command(label="Acerca de...", command=mostrar_acerca_de)

# Tarjeta principal
marco_tarjeta = tk.Frame(ventana, bg=COLORES['tarjeta'], padx=20, pady=20)
marco_tarjeta.pack(fill="both", expand=True, padx=20, pady=10)

# Entrada URL
etiqueta_url = tk.Label(
    marco_tarjeta,
    text="URL(s) de YouTube:",
    font=("Helvetica", 11, "bold"),
    bg=COLORES['tarjeta'],
    fg=COLORES['texto']
)
etiqueta_url.grid(row=0, column=0, sticky="w", pady=(0, 5))

entrada_url = tk.Entry(
    marco_tarjeta,
    width=60,
    font=("Helvetica", 11),
    bg=COLORES['tarjeta'],
    fg=COLORES['texto'],
    highlightthickness=1
)
entrada_url.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15), ipady=4)

# Selección de Carpeta
etiqueta_carpeta = tk.Label(
    marco_tarjeta,
    text="Carpeta de Descarga:",
    font=("Helvetica", 11, "bold"),
    bg=COLORES['tarjeta'],
    fg=COLORES['texto']
)
etiqueta_carpeta.grid(row=2, column=0, sticky="w", pady=(0, 5))

entrada_carpeta = tk.Entry(
    marco_tarjeta,
    textvariable=var_carpeta,
    width=50,
    font=("Helvetica", 10),
    bg=COLORES['tarjeta'],
    fg=COLORES['texto'],
    highlightthickness=1
)
entrada_carpeta.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 15), ipady=3)

boton_carpeta = tk.Button(
    marco_tarjeta,
    text="Examinar...",
    command=seleccionar_carpeta,
    bg=COLORES['primario'],
    fg="white",
    activebackground=COLORES['primario_oscuro'],
    font=("Helvetica", 10, "bold"),
    relief="flat",
    padx=12,
    pady=4
)
boton_carpeta.grid(row=3, column=1, sticky="e", pady=(0, 15))

# Barra de Progreso
barra_progreso = ttk.Progressbar(
    marco_tarjeta,
    orient="horizontal",
    length=600,
    mode="determinate",
    style="TProgressbar"
)
barra_progreso.grid(row=4, column=0, columnspan=2, pady=(10, 5), sticky="ew")

# Etiqueta de Estado
etiqueta_estado = tk.Label(
    marco_tarjeta,
    text="Listo para descargar",
    font=("Helvetica", 10),
    bg=COLORES['tarjeta'],
    fg=COLORES['texto']
)
etiqueta_estado.grid(row=5, column=0, columnspan=2, pady=(0, 20), sticky="w")

# Botón de Descarga
boton_descargar = tk.Button(
    marco_tarjeta,
    text="DESCARGAR MÚSICA",
    command=descargar_urls,
    bg=COLORES['primario'],
    fg="white",
    activebackground=COLORES['primario_oscuro'],
    font=("Helvetica", 12, "bold"),
    relief="flat",
    padx=20,
    pady=10
)
boton_descargar.grid(row=6, column=0, columnspan=2, pady=(10, 0))

# Pie de página
marco_pie = tk.Frame(ventana, bg=COLORES['fondo'], height=30)
marco_pie.pack(fill="x", side="bottom", pady=(0, 5))

etiqueta_pie = tk.Label(
    marco_pie,
    text=f"© 2023 {NOMBRE_APP} | Solo para uso personal",
    font=("Helvetica", 8),
    bg=COLORES['fondo'],
    fg=COLORES['texto_secundario']
)
etiqueta_pie.pack()

# Aplicar tema inicial
aplicar_tema()

# Iniciar bucle principal
ventana.mainloop()