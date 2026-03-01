import subprocess
from pathlib import Path
import textwrap
import sys

# =========================
# CONFIGURE AQUI
# =========================
BASE_DIR = Path(r"C:\IC")
MICRO_2024_DIR = BASE_DIR / "Microdados_ENEM" / "microdados_enem_2024"
DADOS_2024_DIR = MICRO_2024_DIR / "DADOS"

OUT_DIR_ANO = BASE_DIR / "Dados_ENEM" / "Por_Ano"
OUT_DIR_ANALISE = BASE_DIR / "Dados_ENEM" / "Por_Analise"

# Saídas
OUT_ANO_FILE = (OUT_DIR_ANO / "ENEM_2024.RData").as_posix()
OUT_RENDA_FILE = (OUT_DIR_ANALISE / "ENEM_2024_Analise1_Renda.RData").as_posix()
OUT_RACA_FILE = (OUT_DIR_ANALISE / "ENEM_2024_Analise1_Raca.RData").as_posix()

# Inputs (2024)
PARTICIPANTES_CSV = (DADOS_2024_DIR / "PARTICIPANTES_2024.csv")
RESULTADOS_CSV = (DADOS_2024_DIR / "RESULTADOS_2024.csv")

RENDA_VAR_2024 = "Q007"
RACA_VAR_2024 = "TP_COR_RACA"
NOTA_COLS = ["NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_CH", "NU_NOTA_CN", "NU_NOTA_REDACAO"]


def run_rscript(r_code: str):
    try:
        proc = subprocess.run(
            ["Rscript", "-e", r_code],
            check=True,
            capture_output=True,
            text=True
        )
        if proc.stdout.strip():
            print(proc.stdout)
        if proc.stderr.strip():
            print(proc.stderr)
    except FileNotFoundError:
        raise RuntimeError("Não encontrei o comando 'Rscript'. Garanta que o Rscript esteja no PATH.")
    except subprocess.CalledProcessError as e:
        print("=== ERRO ao rodar Rscript ===")
        print(e.stdout)
        print(e.stderr)
        raise


def build_r_code_2024(part_csv: Path, res_csv: Path) -> str:
    if not part_csv.exists():
        raise RuntimeError(f"Não encontrei: {part_csv}")
    if not res_csv.exists():
        raise RuntimeError(f"Não encontrei: {res_csv}")

    part_r = part_csv.as_posix()
    res_r = res_csv.as_posix()

    # tenta achar uma chave comum (se existir em alguma variação)
    key_candidates = [
        "NU_INSCRICAO",
        "NU_SEQUENCIAL",
        "NU_INSCRICAO_PARTICIPANTE",
        "INSCRICAO",
        "CO_INSCRICAO",
        "ID_INSCRICAO",
    ]

    nota_cols_r = ", ".join([f'"{c}"' for c in NOTA_COLS])

    r_code = f"""
suppressWarnings(suppressMessages(library(data.table)))

PARTICIPANTES_2024 <- fread("{part_r}", sep="auto", encoding="Latin-1", integer64="character", showProgress=FALSE)
RESULTADOS_2024    <- fread("{res_r}",  sep="auto", encoding="Latin-1", integer64="character", showProgress=FALSE)

# Normaliza nomes
fix_names <- function(dt) {{
  n <- names(dt)
  n <- gsub("^\\\\ufeff", "", n)
  n <- trimws(n)
  setnames(dt, n)
}}
fix_names(PARTICIPANTES_2024)
fix_names(RESULTADOS_2024)

# Tenta achar chave comum
candidatos <- c({", ".join([f'"{c}"' for c in key_candidates])})
key <- candidatos[candidatos %in% names(PARTICIPANTES_2024) & candidatos %in% names(RESULTADOS_2024)]

if (length(key) > 0) {{
  key <- key[1]
  cat("Chave encontrada para merge:", key, "\\n")
  setkeyv(PARTICIPANTES_2024, key)
  setkeyv(RESULTADOS_2024, key)
  ENEM_2024 <- merge(PARTICIPANTES_2024, RESULTADOS_2024, by=key, all=FALSE)
}} else {{
  # Sem chave comum: fallback por posição (cbind)
  cat("AVISO: sem chave comum para merge. Fazendo cbind por posição (ordem das linhas).\\n")
  cat("N linhas PARTICIPANTES:", nrow(PARTICIPANTES_2024), " | RESULTADOS:", nrow(RESULTADOS_2024), "\\n")

  if (nrow(PARTICIPANTES_2024) != nrow(RESULTADOS_2024)) {{
    stop("2024: PARTICIPANTES e RESULTADOS têm quantidades diferentes de linhas. Não é seguro fazer cbind.")
  }}

  # evita duplicar colunas iguais nos dois (ex: NU_ANO, UF_PROVA, etc.)
  dup <- intersect(names(PARTICIPANTES_2024), names(RESULTADOS_2024))
  dup <- setdiff(dup, character(0))
  if (length(dup) > 0) {{
    RESULTADOS_2024 <- RESULTADOS_2024[, setdiff(names(RESULTADOS_2024), dup), with=FALSE]
  }}

  ENEM_2024 <- cbind(PARTICIPANTES_2024, RESULTADOS_2024)
}}

# Salva base anual
save(ENEM_2024, file="{OUT_ANO_FILE}")

# Função utilitária
not_missing <- function(x) {{
  if (is.character(x)) return(!is.na(x) & x != "NA" & x != "")
  return(!is.na(x))
}}

dados <- ENEM_2024

# ===== Renda =====
needed_renda <- c("{RENDA_VAR_2024}", {nota_cols_r})
missing_cols_renda <- setdiff(needed_renda, names(dados))
if (length(missing_cols_renda) > 0) {{
  stop(paste0("Ano 2024: colunas ausentes para renda: ", paste(missing_cols_renda, collapse=", ")))
}}

idx_renda <- which(
  not_missing(dados$NU_NOTA_LC) &
  not_missing(dados$NU_NOTA_MT) &
  not_missing(dados$NU_NOTA_CH) &
  not_missing(dados$NU_NOTA_CN) &
  not_missing(dados$NU_NOTA_REDACAO) &
  not_missing(dados${RENDA_VAR_2024})
)

ENEM_2024_Analise1_Renda <- dados[idx_renda, c("{RENDA_VAR_2024}", {nota_cols_r}), with=FALSE]
save(ENEM_2024_Analise1_Renda, file="{OUT_RENDA_FILE}")

# ===== Raça =====
needed_raca <- c("{RACA_VAR_2024}", {nota_cols_r})
missing_cols_raca <- setdiff(needed_raca, names(dados))
if (length(missing_cols_raca) > 0) {{
  stop(paste0("Ano 2024: colunas ausentes para raça: ", paste(missing_cols_raca, collapse=", ")))
}}

idx_raca <- which(
  not_missing(dados$NU_NOTA_LC) &
  not_missing(dados$NU_NOTA_MT) &
  not_missing(dados$NU_NOTA_CH) &
  not_missing(dados$NU_NOTA_CN) &
  not_missing(dados$NU_NOTA_REDACAO) &
  not_missing(dados${RACA_VAR_2024})
)

ENEM_2024_Analise1_Raca <- dados[idx_raca, c("{RACA_VAR_2024}", {nota_cols_r}), with=FALSE]
save(ENEM_2024_Analise1_Raca, file="{OUT_RACA_FILE}")

cat("OK - 2024 finalizado.\\n")
"""

    return textwrap.dedent(r_code).strip()


def main():
    OUT_DIR_ANO.mkdir(parents=True, exist_ok=True)
    OUT_DIR_ANALISE.mkdir(parents=True, exist_ok=True)

    r_code = build_r_code_2024(PARTICIPANTES_CSV, RESULTADOS_CSV)
    run_rscript(r_code)

    print("\nFinalizado! Verifique:")
    print(f"- {OUT_DIR_ANO}")
    print(f"- {OUT_DIR_ANALISE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\nERRO:", e)
        sys.exit(1)