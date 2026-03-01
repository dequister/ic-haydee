import subprocess
from pathlib import Path
import textwrap
import sys

# =========================
# CONFIGURE AQUI
# =========================
BASE_DIR = Path(r"C:\IC")
MICRO_DIR = BASE_DIR / "Microdados_ENEM"
OUT_DIR_ANO = BASE_DIR / "Dados_ENEM" / "Por_Ano"
OUT_DIR_ANALISE = BASE_DIR / "Dados_ENEM" / "Por_Analise"

ANOS = list(range(2009, 2010))  # 2010..2024

# =========================
# MAPEAMENTOS (seguindo seu Bases por analise.R)
# =========================
RENDA_VAR = {
    2009: "Q21",
    2010: "Q04",
    2011: "Q004",
    2012: "Q003",
    2013: "Q003",
    2014: "Q003",
    2015: "Q006",
    2016: "Q006",
    2017: "Q006",
    2018: "Q006",
    2019: "Q006",
    2020: "Q006",
    2021: "Q006",
    2022: "Q006",
    2023: "Q006",
    2024: "Q007",
}

RACA_VAR = {
    2009: "Q3",
    2010: "TP_COR_RACA",
    2011: "TP_COR_RACA",
    2012: "TP_COR_RACA",
    2013: "TP_COR_RACA",
    2014: "TP_COR_RACA",
    2015: "TP_COR_RACA",
    2016: "TP_COR_RACA",
    2017: "TP_COR_RACA",
    2018: "TP_COR_RACA",
    2019: "TP_COR_RACA",
    2020: "TP_COR_RACA",
    2021: "TP_COR_RACA",
    2022: "TP_COR_RACA",
    2023: "TP_COR_RACA",
    2024: "TP_COR_RACA",
}

NOTA_COLS = ["NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_CH", "NU_NOTA_CN", "NU_NOTA_REDACAO"]

# Ignorar CSVs auxiliares na escolha do "principal"
IGNORE_CSV_KEYWORDS = [
    "ITENS_PROVA",
    "itens_prova",
    "QUEST",
    "quest",
    "GABARITO",
    "gabarito",
]


def run_rscript(r_code: str):
    """Executa um trecho de R via Rscript."""
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


def pick_main_csv(dados_dir: Path) -> Path:
    """Escolhe o CSV principal (microdados) pelo maior tamanho, ignorando CSVs auxiliares."""
    csvs = list(dados_dir.glob("*.csv"))
    if not csvs:
        raise RuntimeError(f"Não encontrei nenhum CSV em {dados_dir}")

    def is_aux(csv_path: Path) -> bool:
        name = csv_path.name
        return any(k in name for k in IGNORE_CSV_KEYWORDS)

    candidates = [c for c in csvs if not is_aux(c)]
    if not candidates:
        # fallback: se só tiver "auxiliares", pega o maior mesmo
        candidates = csvs

    return max(candidates, key=lambda p: p.stat().st_size)


def build_r_code_for_year(ano: int, pasta_ano: Path) -> str:
    dados_dir = pasta_ano / "DADOS"
    if not dados_dir.exists():
        raise RuntimeError(f"Não achei a pasta DADOS em: {dados_dir}")

    out_ano_file = (OUT_DIR_ANO / f"ENEM_{ano}.RData").as_posix()
    out_renda_file = (OUT_DIR_ANALISE / f"ENEM_{ano}_Analise1_Renda.RData").as_posix()
    out_raca_file = (OUT_DIR_ANALISE / f"ENEM_{ano}_Analise1_Raca.RData").as_posix()

    renda_var = RENDA_VAR[ano]
    raca_var = RACA_VAR[ano]

    # 2024: PARTICIPANTES + RESULTADOS
    if ano == 2024:
        part = dados_dir / "PARTICIPANTES_2024.csv"
        res = dados_dir / "RESULTADOS_2024.csv"
        if not part.exists() or not res.exists():
            raise RuntimeError(f"2024: não achei PARTICIPANTES_2024.csv e/ou RESULTADOS_2024.csv em {dados_dir}")

        part_r = part.as_posix()
        res_r = res.as_posix()

        load_block = f"""
            suppressWarnings(suppressMessages(library(data.table)))

            PARTICIPANTES_2024 <- fread("{part_r}", sep=";", encoding="Latin-1", showProgress=FALSE)
            RESULTADOS_2024    <- fread("{res_r}",  sep=";", encoding="Latin-1", showProgress=FALSE)

            # Merge seguro por NU_INSCRICAO (se existir)
            if (!("NU_INSCRICAO" %in% names(PARTICIPANTES_2024)) || !("NU_INSCRICAO" %in% names(RESULTADOS_2024))) {{
                stop("2024: Não encontrei a coluna NU_INSCRICAO em PARTICIPANTES_2024 ou RESULTADOS_2024 para fazer merge.")
            }}

            setkey(PARTICIPANTES_2024, NU_INSCRICAO)
            setkey(RESULTADOS_2024, NU_INSCRICAO)

            ENEM_{ano} <- merge(PARTICIPANTES_2024, RESULTADOS_2024, by="NU_INSCRICAO", all=FALSE)
        """
    else:
        main_csv = pick_main_csv(dados_dir)
        main_csv_r = main_csv.as_posix()

        load_block = f"""
            suppressWarnings(suppressMessages(library(data.table)))

            ENEM_{ano} <- fread("{main_csv_r}", sep=";", encoding="Latin-1", showProgress=FALSE)
        """

    nota_checks = " &\n            ".join([f'not_missing(dados${c})' for c in NOTA_COLS])

    analysis_block = f"""
        not_missing <- function(x) {{
            if (is.character(x)) return(!is.na(x) & x != "NA" & x != "")
            return(!is.na(x))
        }}

        dados <- ENEM_{ano}

        # ===== Renda =====
        needed_renda <- c("{renda_var}", {", ".join([f'"{c}"' for c in NOTA_COLS])})
        missing_cols_renda <- setdiff(needed_renda, names(dados))
        if (length(missing_cols_renda) > 0) {{
            stop(paste0("Ano {ano}: colunas ausentes para renda: ", paste(missing_cols_renda, collapse=", ")))
        }}

        idx_renda <- which(
            {nota_checks} &
            not_missing(dados${renda_var})
        )
        ENEM_{ano}_Analise1_Renda <- dados[idx_renda, c("{renda_var}", {", ".join([f'"{c}"' for c in NOTA_COLS])}), with=FALSE]

        # ===== Raça =====
        needed_raca <- c("{raca_var}", {", ".join([f'"{c}"' for c in NOTA_COLS])})
        missing_cols_raca <- setdiff(needed_raca, names(dados))
        if (length(missing_cols_raca) > 0) {{
            stop(paste0("Ano {ano}: colunas ausentes para raça: ", paste(missing_cols_raca, collapse=", ")))
        }}

        idx_raca <- which(
            {nota_checks} &
            not_missing(dados${raca_var})
        )
        ENEM_{ano}_Analise1_Raca <- dados[idx_raca, c("{raca_var}", {", ".join([f'"{c}"' for c in NOTA_COLS])}), with=FALSE]
    """

    r_code = f"""
        {load_block}

        # Salva base anual
        save(ENEM_{ano}, file="{out_ano_file}")

        # Gera bases por análise
        {analysis_block}

        save(ENEM_{ano}_Analise1_Renda, file="{out_renda_file}")
        save(ENEM_{ano}_Analise1_Raca,  file="{out_raca_file}")

        cat("OK - Ano {ano} finalizado.\\n")
    """

    return textwrap.dedent(r_code).strip()


def main():
    OUT_DIR_ANO.mkdir(parents=True, exist_ok=True)
    OUT_DIR_ANALISE.mkdir(parents=True, exist_ok=True)

    for ano in ANOS:
        pasta_ano = MICRO_DIR / f"microdados_enem_{ano}"
        if not pasta_ano.exists():
            print(f"[PULOU] Não achei a pasta do ano {ano}: {pasta_ano}")
            continue

        print(f"\n=== Processando {ano} ===")
        r_code = build_r_code_for_year(ano, pasta_ano)
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