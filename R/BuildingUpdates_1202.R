# Set Up ------------------------------------------------------------------

library(tidyverse)
library(sf)
library(tmap)
library(arcgisbinding)
arcgisbinding::arc.check_product()
tmap_mode("view")

# Updated Floor Logic -----------------------------------------------------
## Changed from the 12-01 script to include the historic peninsula
building_path <- paste0("./source_shapefiles/building_data/",
                        "buildings_update_newFloorLogic_110220.shp")

buildings <- st_read(dsn = building_path) %>% 
  st_make_valid()

segment_path <- paste0("./source_shapefiles/corridor_marketsegments.shp")
segment <- read_sf(segment_path)

buildings <- st_join(buildings, segment,
                join = st_within)

selection_index <- 
  which(((buildings$Landuse == "Commercial/Retail") | 
             ((buildings$Landuse == "Industrial/Manufacturing"))) &
         (buildings$flrs_est > 1))
buildings[selection_index,]

buildings$flrs_est[selection_index] <- 1
buildings[selection_index,]

buildings$flrAr_sqft <- buildings$flrs_est * buildings$Shape_Area
buildings[selection_index,]

building_out <- paste0("./source_shapefiles/building_data/",
                        "buildings_update_1202.shp")

write_sf(buildings, building_out)
# Adding Buildings to Parcels ---------------------------------------------

gdb_path <- "./LCBRT_data.gdb"
in_layer <- "parcels"

parcels <- st_read(gdb_path, in_layer) %>% 
  st_make_valid()

bld_area <- st_intersection(parcels[c("ParclID")], buildings)
bld_area$Shape_Area <- st_area(bld_area) %>% as.numeric()

bld_area <- bld_area %>% 
  st_drop_geometry() %>% 
  mutate(flrAr_sqft = Shape_Area * flrs_est) %>% 
  group_by(ParclID) %>% 
  summarise(BldSqFt =  sum(flrAr_sqft))

final_parcels <- parcels[-which(colnames(parcels) == "BldSqFt")] %>% 
  left_join(bld_area)

# final_parcels %>% mutate(FAR = BldSqFt / Sq_Feet) %>% 
#   tm_shape() + tm_polygons(col = "FAR", lwd = 0.1,
#                            breaks = c(0, 0.2, 0.4, 0.6, 0.8, 1, 1.5, 2, 10))

final_parcels$BldA_AC <- final_parcels$BldSqFt / 43560

col_order <- colnames(parcels)
final_parcels <- final_parcels[col_order]

out_layer <- "parcels_bldSqft_update_1202"
arc.write(path = paste0(gdb_path, "/", out_layer), data = final_parcels)

