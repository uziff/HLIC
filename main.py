import os
import subprocess
from contextlib import nullcontext

import requests
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configurazione
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"  # O "mistral"
TEMP_FILE = "temp_program.py"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/run', methods=['POST'])
def run_code():
    data = request.json
    pseudocode = data.get('code', '')

    if not pseudocode:
        return jsonify({'output': 'Nessun codice inserito.'})

    try:
        # 1. TRADUZIONE (COMPILAZIONE) VIA OLLAMA
        # Chiediamo all'AI di agire come un transpiler rigoroso
        prompt = f"""
        Sei un compilatore esperto. Il tuo compito è tradurre il seguente pseudocodice italiano in codice Python 3 valido ed eseguibile.

        REGOLE:
        1. Restituisci SOLO il codice Python.
        2. NON includere markdown (niente ```python o ```).
        3. NON includere spiegazioni o commenti, solo codice puro.
        4. Assicurati di gestire le stampe (print) correttamente.

        PSEUDOCODICE:
        {pseudocode}
        """

        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(OLLAMA_API_URL, json=payload)
        response_json = response.json()
        python_code = response_json.get('response', '').strip()

        # Pulizia extra nel caso l'LLM disobbedisca e metta i backticks
        if python_code.startswith("```"):
            python_code = python_code.replace("```python", "").replace("```", "")

        # Salviamo il codice generato (utile per debug)
        with open(TEMP_FILE, "w") as f:
            f.write(python_code)

        # 2. ESECUZIONE
        # Eseguiamo il file python generato
        process = subprocess.run(
            ['python3', TEMP_FILE],
            capture_output=True,
            text=True,
            timeout=2  # Timeout di sicurezza
        )
        output = process.stdout
        if process.stderr:
            output += f"\n[ERRORE DI RUNTIME]:\n{process.stderr}"

        return jsonify({'output': output, 'compiled_code': python_code})

    except requests.exceptions.ConnectionError:
        return jsonify({'output': "Errore: Assicurati che Ollama sia in esecuzione (comando: 'ollama serve')."})
    except Exception as e:
        return jsonify({'output': f"Errore di sistema: {str(e)}"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5642)