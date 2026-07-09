# ============================================================
# Pipeline 2 – Phase 1: Bibliometric Analysis
# Script 01: Load BIB files and build merged bibliometrix dataset
# ============================================================
# Requirements:
#   install.packages(c("bibliometrix", "tidyverse", "here"))
#
# Input:  data/raw/*.bib
# Output: data/processed/bibliometrix_merged.rds
# ============================================================

library(bibliometrix)
library(tidyverse)
library(here)

RAW   <- here("data", "raw")
PROC  <- here("data", "processed")

# ── 1. Load each database export ────────────────────────────────────────────

bib_files <- list(
  ieee    = file.path(RAW, "ieee_combined_278.bib"),
  acm     = file.path(RAW, "acm_1113.bib"),
  scopus  = file.path(RAW, "scopus_1001.bib"),
  wos     = file.path(RAW, "wos_305.bib"),
  eric    = file.path(RAW, "eric_69.bib")
)

dfs <- lapply(names(bib_files), function(db) {
  message("Loading: ", db)
  df <- convert2df(bib_files[[db]],
                   dbsource = ifelse(db %in% c("ieee","acm"), "isi", db),
                   format   = "bibtex")
  df$DB_SOURCE <- toupper(db)
  df
})

# ── 2. Merge and deduplicate ─────────────────────────────────────────────────

merged <- mergeDbSources(dfs[[1]], dfs[[2]], dfs[[3]], dfs[[4]], dfs[[5]],
                         remove.duplicated = TRUE)
message("Records after merge + dedup: ", nrow(merged))

# ── 3. Filter to 2022–2026 ───────────────────────────────────────────────────

merged <- merged %>% filter(PY >= 2022, PY <= 2026)
message("Records in 2022–2026 window: ", nrow(merged))

# ── 4. Save ──────────────────────────────────────────────────────────────────

saveRDS(merged, file.path(PROC, "bibliometrix_merged.rds"))
message("Saved → data/processed/bibliometrix_merged.rds")
