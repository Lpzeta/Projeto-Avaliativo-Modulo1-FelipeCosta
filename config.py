"""Configurações do projeto. Lê as credenciais do arquivo .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Banco de dados (vem do .env)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "viagens")

# Banco de manutenção, usado só para criar o DB_NAME
DB_ADMIN = "postgres"

# Download dos dados
DRIVE_FILE_ID = "1pQjKacyHdIsyteknQbwKGM5_4hL5V4RV"

# Pastas e arquivos
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ZIP_PATH = DATA_DIR / "viagens.zip"

# Leitura dos CSVs (conforme o documento)
CSV_SEP = ";"
CSV_ENCODING = "latin-1"
CHUNK_SIZE = 10_000

# CSV de origem -> tabela Raw de destino
ARQUIVOS_RAW = {
    "2025_Viagem.csv": "raw_viagem",
    "2025_Pagamento.csv": "raw_pagamento",
    "2025_Passagem.csv": "raw_passagem",
    "2025_Trecho.csv": "raw_trecho",
}