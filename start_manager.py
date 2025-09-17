# start_manager.py
import subprocess
import sys
import atexit
import time
import webbrowser
import os
from pathlib import Path

# --- Controllo Prerequisiti Essenziali ---
MIN_PYTHON_VERSION = (3, 8)
if sys.version_info < MIN_PYTHON_VERSION:
    current_version = ".".join(map(str, sys.version_info[:3]))
    required_version = ".".join(map(str, MIN_PYTHON_VERSION))
    print(f"❌ ERRORE: Versione di Python non compatibile.")
    print(f"   Trovata versione: {current_version}")
    print(f"   Versione richiesta: >= {required_version}")
    print(f"   Per favore, installa una versione aggiornata di Python da https://www.python.org/downloads/")
    input("\nPremi INVIO per uscire.")
    sys.exit(1)

try:
    import psutil
    import requests
except ImportError:
    print("Installazione di librerie essenziali (psutil, requests)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil", "requests"])
    import psutil
    import requests

# --- Configurazione dei percorsi ---
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "webapp" / "backend"
FRONTEND_DIR = ROOT_DIR / "webapp" / "frontend"
VENV_DIR = ROOT_DIR / "venv"
BACKEND_PORT = 5050
FRONTEND_PORT = 5173
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"

processes = []

def cleanup():
    print("\n🧹 Eseguo la pulizia e chiudo i server...")
    for p in processes:
        try:
            parent = psutil.Process(p.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            p.wait(timeout=5)
        except (psutil.NoSuchProcess, subprocess.TimeoutExpired):
            pass
    print("✅ Pulizia completata.")

def kill_process_on_port(port):
    """Trova e termina qualsiasi processo in ascolto su una porta specifica."""
    # Itera sui processi chiedendo solo le informazioni base
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Per ogni processo, ORA chiamiamo la funzione connections()
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"🛑 Trovato processo '{proc.info['name']}' (PID: {proc.info['pid']}) sulla porta {port}. Lo chiudo...")
                    proc.terminate()
                    proc.wait(timeout=5)
                    return # Esci dopo aver trovato e terminato il processo
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # È normale che un processo scompaia durante l'iterazione, quindi ignoriamo l'errore
            continue

def run_command(command, cwd, name, use_shell=False):
    print(f"🚀 Avvio di {name}...")
    is_windows = sys.platform == 'win32'
    proc = subprocess.Popen(command, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, shell=is_windows)
    processes.append(proc)
    print(f"✅ {name} avviato con PID: {proc.pid}")
    return proc

def wait_for_server(url, timeout=45):
    print(f"⏳ In attesa che il server frontend sia pronto su {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url, timeout=2)
            print(f"🌍 Server su {url} è online!")
            return True
        except requests.ConnectionError:
            time.sleep(1)
    print(f"❌ Timeout: il server su {url} non ha risposto.")
    return False

if __name__ == "__main__":
    atexit.register(cleanup)

    print("--- ⚙️  Fase 1: Preparazione dell'ambiente ---")
    
    if not VENV_DIR.exists():
        print(f"Ambiente virtuale non trovato. Creazione in '{VENV_DIR}'...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
            print("✅ Ambiente virtuale creato con successo.")
        except subprocess.CalledProcessError as e:
            print(f"❌ ERRORE: Impossibile creare l'ambiente virtuale. Dettagli: {e}")
            input("\nPremi INVIO per uscire.")
            sys.exit(1)

    kill_process_on_port(BACKEND_PORT)
    kill_process_on_port(FRONTEND_PORT)

    print("\n--- 📦 Fase 2: Installazione delle dipendenze ---")
    print("Controllo dipendenze Python...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=ROOT_DIR)
    print("Controllo dipendenze Node.js...")
    subprocess.check_call(["npm", "install"], cwd=FRONTEND_DIR, shell=sys.platform == 'win32')
    
    print("\n--- 🚀 Fase 3: Avvio dei server ---")
    run_command(["python", "backend_unified.py"], cwd=BACKEND_DIR, name="Backend Flask")
    run_command(["npm", "run", "dev"], cwd=FRONTEND_DIR, name="Frontend React")
    
    print("\n--- 🖥️  Fase 4: Avvio dell'interfaccia ---")
    if wait_for_server(FRONTEND_URL):
        webbrowser.open(FRONTEND_URL)
    else:
        print("Impossibile avviare il frontend. Controlla i log per errori.")
        sys.exit(1)

    print("\n✅ Il Translation Manager è in esecuzione. Lascia questa finestra aperta.")
    print("   Premi INVIO qui per chiudere tutto.")
    try:
        input()
    except KeyboardInterrupt:
        pass