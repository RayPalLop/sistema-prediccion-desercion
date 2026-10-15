import os
import sys
import time
import psycopg2
import httpx
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Configurar salida de terminal en UTF-8 para Windows
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Intentar habilitar el almacén de certificados de Windows si truststore está presente
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

# 1. CONFIGURACIÓN DE CONEXIÓN A BASE DE DATOS
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "innotech_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "Ube"), 
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# 2. CONFIGURACIÓN DEL CLIENTE GROQ
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

def get_groq_client():
    """Inicializa el cliente de Groq con tolerancia a entornos SSL en Windows."""
    try:
        client = Groq(api_key=GROQ_API_KEY, timeout=30.0, max_retries=2)
        # Verificación rápida
        client.models.list()
        return client
    except Exception:
        # Respaldo sin verificación SSL para evitar fallos por certificados locales o antivirus
        http_client = httpx.Client(verify=False, timeout=30.0)
        return Groq(api_key=GROQ_API_KEY, http_client=http_client, timeout=30.0, max_retries=2)

def procesar_analisis_ia():
    try:
        client = get_groq_client()
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 3. LEER DATOS DESDE LA VISTA PRIMERO
        cur.execute("""
            SELECT id_estudiante, nombre_completo, promedio_notas, asistencia, 
                   nivel_socioeconomico, cuotas_vencidas 
            FROM v_riesgo_estudiantes
        """)
        estudiantes = cur.fetchall()

        if not estudiantes:
            print("No hay estudiantes con datos para analizar.", flush=True)
            cur.close()
            conn.close()
            return

        # --- LIMPIEZA DE TABLA ALERTA ---
        print("\nLimpiando dashboard y registros previos...", flush=True)
        cur.execute("TRUNCATE TABLE alerta_desercion RESTART IDENTITY CASCADE;")
        conn.commit() 

        print(f"\n--- Iniciando Análisis de {len(estudiantes)} estudiantes con modelo {GROQ_MODEL} ---\n", flush=True)

        for est in estudiantes:
            id_est, nombre, promedio, asist, socio, deudas = est
            
            # Sanitización de datos para evitar errores con valores nulos
            prom_val = float(promedio) if promedio is not None else 0.0
            asist_val = float(asist) if asist is not None else 0.0
            socio_val = str(socio) if socio else "No especificado"
            deudas_val = int(deudas) if deudas is not None else 0
            
            # LÓGICA DE RIESGO
            if (prom_val < 5) or (prom_val < 7 and deudas_val > 0) or (asist_val < 70):
                nivel = "Alto"
                color = "#dc3545" # Rojo
            elif (prom_val < 8) or (deudas_val > 0) or (asist_val < 85):
                nivel = "Medio"
                color = "#ffc107" # Amarillo
            else:
                nivel = "Bajo"
                color = "#28a745" # Verde

            # PROMPT REFINADO
            prompt = f"""
            Como experto en retención estudiantil, analiza este perfil:
            - Estudiante: {nombre}
            - Promedio: {prom_val:.2f}
            - Asistencia: {asist_val:.1f}%
            - Nivel Socioeconómico: {socio_val}
            - Cuotas Vencidas: {deudas_val}
            
            Genera un diagnóstico técnico y una estrategia de intervención pedagógica o administrativa.
            Sé directo y profesional (máximo 300 caracteres).
            """

            respuesta = None
            try:
                completion = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": "Eres un analista de datos educativos especializado en predicción de deserción."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6,
                    max_tokens=250
                )
                respuesta = completion.choices[0].message.content.strip()

            except Exception as api_err:
                print(f"[AVISO] Error con la API para {nombre}: {api_err}. Reintentando...", flush=True)
                time.sleep(3)
                try:
                    completion = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": "Eres un analista de datos educativos especializado en predicción de deserción."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.6,
                        max_tokens=250
                    )
                    respuesta = completion.choices[0].message.content.strip()
                except Exception as retry_err:
                    print(f"[AVISO] Reintento fallido para {nombre}: {retry_err}. Usando diagnóstico estándar.", flush=True)
                    if nivel == "Alto":
                        respuesta = f"Riesgo Alto. Promedio ({prom_val:.1f}), Asistencia ({asist_val:.0f}%), Deudas ({deudas_val}). Requiere tutoría urgente y plan de regularización."
                    elif nivel == "Medio":
                        respuesta = f"Riesgo Medio. Presenta indicadores en observación (Asistencia: {asist_val:.0f}%, Promedio: {prom_val:.1f}). Se sugiere seguimiento periódico."
                    else:
                        respuesta = f"Riesgo Bajo. Estudiante con rendimiento y asistencia favorables. Mantener monitoreo preventivo regular."

            # GUARDAR EN BASE DE DATOS
            query_insert = """
                INSERT INTO alerta_desercion (id_estudiante, nivel_riesgo, color_semaforo, causa_ia)
                VALUES (%s, %s, %s, %s)
            """
            cur.execute(query_insert, (id_est, nivel, color, respuesta))
            print(f"[OK] Analisis guardado para {nombre} [Riesgo: {nivel}]", flush=True)

            # Pequeña pausa para respetar cuotas de la API
            time.sleep(0.5)

        conn.commit()
        cur.close()
        conn.close()
        print("\n--- ¡Motor de IA actualizado y ejecutado con éxito! ---", flush=True)

    except Exception as e:
        print(f"\n[ERROR GENERAL]: {e}", flush=True)

if __name__ == "__main__":
    procesar_analisis_ia()