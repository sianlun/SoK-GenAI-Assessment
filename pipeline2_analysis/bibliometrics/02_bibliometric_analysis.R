# ============================================================
# Pipeline 2 – Phase 1: Bibliometric Analysis
# Script 02: Annual trends, venues, keyword co-occurrence,
#            thematic map — all outputs saved to outputs/
# ============================================================
# Input:  data/processed/bibliometrix_merged.rds
# Output: pipeline2_analysis/outputs/figures/*.png
#         pipeline2_analysis/outputs/tables/*.csv
# ============================================================

library(bibliometrix)
library(tidyverse)
library(here)

PROC   <- here("data", "processed")
FIGS   <- here("pipeline2_analysis", "outputs", "figures")
TABLES <- here("pipeline2_analysis", "outputs", "tables")
dir.create(FIGS,   recursive = TRUE, showWarnings = FALSE)
dir.create(TABLES, recursive = TRUE, showWarnings = FALSE)

M <- readRDS(file.path(PROC, "bibliometrix_merged.rds"))
message("Loaded ", nrow(M), " records")

# ── 1. Summary statistics ────────────────────────────────────────────────────

results <- biblioAnalysis(M, sep = ";")
sink(file.path(TABLES, "bibliometric_summary.txt"))
summary(results, k = 20, pause = FALSE)
sink()
message("✓ Summary written")

# ── 2. Annual publication growth ────────────────────────────────────────────

annual <- M %>%
  count(PY, name = "papers") %>%
  rename(year = PY) %>%
  arrange(year)

write_csv(annual, file.path(TABLES, "annual_publication_counts.csv"))

p_annual <- ggplot(annual, aes(x = year, y = papers)) +
  geom_col(fill = "#2C5F8A", width = 0.6) +
  geom_line(colour = "#E07B3A", linewidth = 1, group = 1) +
  geom_point(colour = "#E07B3A", size = 3) +
  geom_text(aes(label = papers), vjust = -0.5, size = 3.5, fontface = "bold") +
  scale_x_continuous(breaks = annual$year) +
  labs(title = "Annual Publication Count — 2022–2026",
       subtitle = "SoK: GenAI in Assessment | Engineering / STEM / CS Education",
       x = NULL, y = "Number of Papers") +
  theme_minimal(base_size = 12) +
  theme(plot.title = element_text(face = "bold"))

ggsave(file.path(FIGS, "annual_growth.png"), p_annual,
       width = 10, height = 5, dpi = 180)
message("✓ Annual growth chart saved")

# ── 3. Top publication venues ────────────────────────────────────────────────

top_venues <- as.data.frame(results$Sources) %>% head(20)
colnames(top_venues) <- c("Venue", "Papers")
write_csv(top_venues, file.path(TABLES, "top_venues.csv"))

p_venues <- ggplot(top_venues %>% head(15),
                   aes(x = reorder(Venue, Papers), y = Papers)) +
  geom_col(fill = "#2C5F8A") +
  coord_flip() +
  labs(title = "Top 15 Publication Venues",
       x = NULL, y = "Papers") +
  theme_minimal(base_size = 11) +
  theme(plot.title = element_text(face = "bold"))

ggsave(file.path(FIGS, "top_venues.png"), p_venues,
       width = 10, height = 6, dpi = 180)
message("✓ Top venues chart saved")

# ── 4. Keyword co-occurrence network ────────────────────────────────────────

tryCatch({
  NetMatrix <- biblioNetwork(M, analysis = "co-occurrences",
                             network = "keywords", sep = ";")
  png(file.path(FIGS, "keyword_cooccurrence.png"),
      width = 3000, height = 2400, res = 200)
  net_kw <- networkPlot(NetMatrix, normalize = "association",
                        weighted = TRUE, n = 60,
                        Title = "Keyword Co-occurrence Network (n = 60)",
                        type = "fruchterman", size = TRUE, edgesize = 4,
                        labelsize = 0.7, cluster = "walktrap",
                        label.cex = TRUE, remove.isolates = TRUE)
  dev.off()
  if (!is.null(net_kw$cluster_res)) {
    write_csv(net_kw$cluster_res, file.path(TABLES, "keyword_clusters.csv"))
    message("✓ Keyword co-occurrence network saved (", nrow(net_kw$cluster_res), " keywords)")
  }
}, error = function(e) {
  dev.off(); message("⚠ Keyword network skipped: ", e$message)
})

# ── 5. Thematic map ──────────────────────────────────────────────────────────

tryCatch({
  Map <- thematicMap(M, field = "DE", n = 250, minfreq = 3,
                     stemming = FALSE, size = 0.5, n.labels = 3, repel = TRUE)
  png(file.path(FIGS, "thematic_map.png"),
      width = 2400, height = 2000, res = 180)
  plot(Map$map)
  dev.off()
  write_csv(Map$words, file.path(TABLES, "thematic_map_clusters.csv"))
  message("✓ Thematic map saved")
}, error = function(e) {
  dev.off(); message("⚠ Thematic map skipped: ", e$message)
})

# ── 6. Country collaboration network ────────────────────────────────────────

tryCatch({
  if ("AU_CO" %in% colnames(M) && any(!is.na(M$AU_CO))) {
    CNet <- biblioNetwork(M, analysis = "collaboration",
                          network = "countries", sep = ";")
    png(file.path(FIGS, "country_collaboration.png"),
        width = 2400, height = 1800, res = 200)
    networkPlot(CNet, n = 30, Title = "Country Collaboration Network",
                type = "circle", size = TRUE, remove.multiple = FALSE,
                labelsize = 0.8, cluster = "none")
    dev.off()
    message("✓ Country collaboration network saved")
  } else {
    message("⚠ Country collaboration skipped: AU_CO field not available in this export")
  }
}, error = function(e) {
  dev.off(); message("⚠ Country collaboration skipped: ", e$message)
})

# ── 7. Conceptual structure ──────────────────────────────────────────────────

tryCatch({
  png(file.path(FIGS, "conceptual_structure.png"),
      width = 2400, height = 2000, res = 180)
  cs <- conceptualStructure(M, field = "DE", method = "CA",
                            minDegree = 3, clust = 5, stemming = FALSE,
                            labelsize = 12, documents = 20)
  dev.off()
  write_csv(as.data.frame(cs$km.res$cluster),
            file.path(TABLES, "conceptual_structure_clusters.csv"))
  message("✓ Conceptual structure saved")
}, error = function(e) {
  dev.off(); message("⚠ Conceptual structure skipped: ", e$message)
})

message("\n✓ Bibliometric analysis complete")
message("  Figures → ", FIGS)
message("  Tables  → ", TABLES)
