# ============================================================
# Pipeline 2 – Phase 1c: Apply OpenAlex affiliation enrichment
# ============================================================
# Reads the CSV produced by 01b_enrich_affiliations.py and
# merges the enriched C1 / AU_CO fields back into the merged RDS,
# then re-runs the affiliation-derived fields (AU_UN, AU_CO).
#
# Input:  data/processed/bibliometrix_merged.rds
#         data/processed/affiliations_enriched.csv
# Output: data/processed/bibliometrix_merged.rds  (updated in place)
# ============================================================

library(bibliometrix)
library(tidyverse)
library(here)

PROC <- here("data", "processed")

# ── 1. Load ──────────────────────────────────────────────────────────────────

message("Loading merged RDS …")
M <- readRDS(file.path(PROC, "bibliometrix_merged.rds"))
message("  ", nrow(M), " records")

enrich_path <- file.path(PROC, "affiliations_enriched.csv")
if (!file.exists(enrich_path)) {
  stop("Run 01b_enrich_affiliations.py first to generate ", enrich_path)
}
enrich <- read_csv(enrich_path, show_col_types = FALSE) %>%
  filter(found == TRUE, nchar(C1_enriched) > 0)
message("  ", nrow(enrich), " enrichment records with affiliation data")

# ── 2. Patch C1 and AU_CO for IEEE/ACM/ERIC records ─────────────────────────

# Only overwrite if the existing C1 is blank.
# Works with partial enrichment CSV — applies whatever rows are available.
message("  Enrichment rows available: ", nrow(enrich),
        " (of ", sum(M$DB_SOURCE == "IEEE_ACM_ERIC", na.rm=TRUE), " IEEE/ACM/ERIC records)")

# Match by DOI (DI field)
enrich_lookup <- enrich %>%
  mutate(DI_norm = tolower(trimws(gsub("https?://doi\\.org/", "", DI)))) %>%
  select(DI_norm, C1_enriched, AU_CO_enriched)

M$DI_norm <- tolower(trimws(gsub("https?://doi\\.org/", "", M$DI)))

# Ensure C1 and AU_CO columns exist (may be absent if no affiliation data was loaded)
if (!"C1"    %in% names(M)) M$C1    <- NA_character_
if (!"AU_CO" %in% names(M)) M$AU_CO <- NA_character_

before_c1  <- sum(!is.na(M$C1)    & trimws(M$C1)    != "", na.rm = TRUE)
before_co  <- sum(!is.na(M$AU_CO) & trimws(M$AU_CO) != "", na.rm = TRUE)

M <- M %>%
  left_join(enrich_lookup, by = "DI_norm") %>%
  mutate(
    C1    = case_when(
      DB_SOURCE == "IEEE_ACM_ERIC" & (is.na(C1) | trimws(C1) == "") & !is.na(C1_enriched) ~ C1_enriched,
      TRUE ~ C1
    ),
    AU_CO = case_when(
      DB_SOURCE == "IEEE_ACM_ERIC" & (is.na(AU_CO) | trimws(AU_CO) == "") & !is.na(AU_CO_enriched) ~ AU_CO_enriched,
      TRUE ~ AU_CO
    )
  ) %>%
  select(-C1_enriched, -AU_CO_enriched, -DI_norm)

after_c1  <- sum(!is.na(M$C1) & trimws(M$C1) != "", na.rm = TRUE)
after_co  <- sum(!is.na(M$AU_CO) & trimws(M$AU_CO) != "", na.rm = TRUE)

message("  C1 (affiliation) coverage: ", before_c1, " → ", after_c1,
        " (+", after_c1 - before_c1, ")")
message("  AU_CO (country) coverage:  ", before_co, " → ", after_co,
        " (+", after_co - before_co, ")")

# ── 3. Rebuild AU_UN from enriched C1 ────────────────────────────────────────

message("Rebuilding AU_UN from enriched C1 …")
M <- tryCatch(
  metaTagExtraction(M, Field = "AU_UN"),
  error = function(e) { message("  AU_UN rebuild skipped: ", e$message); M }
)

# ── 4. Save ──────────────────────────────────────────────────────────────────

saveRDS(M, file.path(PROC, "bibliometrix_merged.rds"))
message("Saved → data/processed/bibliometrix_merged.rds")
message("\nRe-run 02_bibliometric_analysis.R to regenerate figures with country data.")
