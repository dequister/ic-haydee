# haydee_pipeline.R
suppressWarnings(suppressMessages({
  library(data.table)
  library(ggplot2)
}))

# =========================
# CONFIGURE AQUI
# =========================
BASE_DIR <- "C:/IC"
DIR_ANO <- file.path(BASE_DIR, "Dados_ENEM", "Por_Ano")
DIR_ANALISE <- file.path(BASE_DIR, "Dados_ENEM", "Por_Analise")
OUT_DIR <- file.path(BASE_DIR, "Dados_ENEM", "Haydee_Automacao")
OUT_GRAF <- file.path(OUT_DIR, "graficos")

dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)
dir.create(OUT_GRAF, recursive = TRUE, showWarnings = FALSE)

ANOS <- 2009:2024

# =========================
# Helpers
# =========================
load_rdata_object <- function(path) {
  e <- new.env()
  load(path, envir = e)
  objs <- ls(e)
  if (length(objs) != 1) {
    # se tiver mais de 1, pega o maior data.frame/data.table
    dts <- objs[sapply(objs, function(nm) inherits(get(nm, envir=e), c("data.table","data.frame")))]
    if (length(dts) == 0) stop(paste("Nenhum data.frame/data.table em", path))
    sizes <- sapply(dts, function(nm) nrow(get(nm, envir=e)))
    return(as.data.table(get(dts[which.max(sizes)], envir=e)))
  }
  return(as.data.table(get(objs[1], envir = e)))
}

# padroniza labels de raça (você pode ajustar isso depois)
map_raca_label <- function(x) {
  # x pode ser character ou numeric
  # INEP geralmente:
  # 0 Não declarado, 1 Branca, 2 Preta, 3 Parda, 4 Amarela, 5 Indígena
  # mas isso pode variar; aqui tratamos o caso mais comum
  if (is.numeric(x)) x <- as.integer(x)
  if (is.character(x)) {
    # tenta converter caso seja "1", "2", etc.
    suppressWarnings({
      xi <- as.integer(x)
      if (!all(is.na(xi))) x <- xi
    })
  }

  if (is.integer(x) || is.numeric(x)) {
    return(fcase(
      x == 0, "Nao Declarado",
      x == 1, "Branca",
      x == 2, "Preta",
      x == 3, "Parda",
      x == 4, "Amarela",
      x == 5, "Indigena",
      default = paste0("Codigo_", x)
    ))
  }

  # se vier texto já, só limpa
  x <- trimws(x)
  x[x == ""] <- NA
  return(x)
}

NOTAS <- c("NU_NOTA_LC","NU_NOTA_MT","NU_NOTA_CH","NU_NOTA_CN","NU_NOTA_REDACAO")
COL_RACA <- "TP_COR_RACA"

# =========================
# 1) TABELA DE CONTAGENS (Total por ano e Analise 1 - Raça)
# =========================
contagens <- rbindlist(lapply(ANOS, function(ano) {
  f_ano <- file.path(DIR_ANO, sprintf("ENEM_%d.RData", ano))
  f_a1r <- file.path(DIR_ANALISE, sprintf("ENEM_%d_Analise1_Raca.RData", ano))

  total <- NA_integer_
  a1_raca <- NA_integer_

  if (file.exists(f_ano)) {
    dt_ano <- load_rdata_object(f_ano)
    total <- nrow(dt_ano)
  }

  if (file.exists(f_a1r)) {
    dt_a1 <- load_rdata_object(f_a1r)
    a1_raca <- nrow(dt_a1)
  }

  data.table(
    Ano = ano,
    Total_Candidatos = total,
    Total_Candidatos_Analise1_Raca = a1_raca
  )
}), fill = TRUE)

fwrite(contagens, file.path(OUT_DIR, "tabela_contagens_haydee.csv"))

# =========================
# 2) ESTUDO: opções/categorias de raça por ano (contagem por categoria)
# =========================
raca_por_ano <- rbindlist(lapply(ANOS, function(ano) {
  f_ano <- file.path(DIR_ANO, sprintf("ENEM_%d.RData", ano))
  if (!file.exists(f_ano)) return(NULL)

  dt <- load_rdata_object(f_ano)
  if (!(COL_RACA %in% names(dt))) return(data.table(Ano=ano, Categoria=NA, N=NA))

  tmp <- dt[, .(Raca = get(COL_RACA))]
  tmp[, Categoria := map_raca_label(Raca)]
  tmp[, .(N = .N), by = .(Ano = ano, Categoria)][order(Ano, Categoria)]
}), fill = TRUE)

fwrite(raca_por_ano, file.path(OUT_DIR, "raca_por_ano.csv"))

# =========================
# 3) 5 gráficos: média da nota por ano, linhas por raça
#    (usando base Analise1_Raca, que já garante notas + raça sem NA)
# =========================
calc_medias_por_ano_raca <- function(ano) {
  f_a1r <- file.path(DIR_ANALISE, sprintf("ENEM_%d_Analise1_Raca.RData", ano))
  if (!file.exists(f_a1r)) return(NULL)

  dt <- load_rdata_object(f_a1r)

  # garante colunas
  if (!(COL_RACA %in% names(dt))) return(NULL)
  miss <- setdiff(NOTAS, names(dt))
  if (length(miss) > 0) return(NULL)

  dt[, Raca_Label := map_raca_label(get(COL_RACA))]

  # calcula médias
  dt[, c("NU_NOTA_LC","NU_NOTA_MT","NU_NOTA_CH","NU_NOTA_CN","NU_NOTA_REDACAO") :=
       lapply(.SD, as.numeric), .SDcols = NOTAS]

  out <- dt[, lapply(.SD, mean, na.rm = TRUE), by = .(Ano = ano, Raca = Raca_Label), .SDcols = NOTAS]
  return(out)
}

medias <- rbindlist(lapply(ANOS, calc_medias_por_ano_raca), fill = TRUE)
fwrite(medias, file.path(OUT_DIR, "medias_por_ano_raca.csv"))

# função para plotar cada prova
plot_nota <- function(col_nota, titulo, out_png) {
  dtp <- medias[!is.na(get(col_nota)) & !is.na(Raca)]
  if (nrow(dtp) == 0) return(invisible(NULL))

  p <- ggplot(dtp, aes(x = Ano, y = get(col_nota), group = Raca, color = Raca)) +
    geom_line(linewidth = 0.8) +
    geom_point(size = 1.6) +
    labs(
      title = titulo,
      x = "Ano",
      y = "Nota média",
      color = "Raça"
    ) +
    theme_minimal(base_size = 12)

  ggsave(filename = out_png, plot = p, width = 10, height = 6, dpi = 200)
}

plot_nota("NU_NOTA_LC", "Linguagens - Nota média por raça (Análise 1)", file.path(OUT_GRAF, "media_LC_por_raca.png"))
plot_nota("NU_NOTA_MT", "Matemática - Nota média por raça (Análise 1)", file.path(OUT_GRAF, "media_MT_por_raca.png"))
plot_nota("NU_NOTA_CH", "Ciências Humanas - Nota média por raça (Análise 1)", file.path(OUT_GRAF, "media_CH_por_raca.png"))
plot_nota("NU_NOTA_CN", "Ciências Naturais - Nota média por raça (Análise 1)", file.path(OUT_GRAF, "media_CN_por_raca.png"))
plot_nota("NU_NOTA_REDACAO", "Redação - Nota média por raça (Análise 1)", file.path(OUT_GRAF, "media_REDACAO_por_raca.png"))

cat("OK - Pipeline Haydee finalizado.\n")
cat("Saídas em:", OUT_DIR, "\n")