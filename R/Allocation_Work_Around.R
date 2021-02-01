# Set Up -----------------------------------------------------------------------
library(sf)
library(tmap)
tmap_mode("view")
library(tidyverse)
library(arcgisbinding)
arcgisbinding::arc.check_product()


# testing -----------------------------------------------------------------

gdb_path <- "./LCBRT_data.gdb"
in_layer <- "parcels"

Parcels <- st_read(gdb_path, in_layer) %>% 
  st_make_valid() %>% 
  st_as_sf()

update <- read_sf("./source_shapefiles/Parcels_1201_FAR.shp")

update_variables <- c("BldSqFt",
                      "SF_Cpct",  
                      "Max_FAR",  
                      "Mean_FAR", 
                      "Count_Par",
                      "EXP_Sqft")

Parcels <- Parcels[-which(colnames(Parcels) %in% update_variables)]
update  <- update[c("ParclID", update_variables)]

Parcels <- inner_join(Parcels, st_drop_geometry(update), by = "ParclID")

# saving
gdb_path <- "./LCBRT_data.gdb"
out_layer <- "parcels_bldSqft_update_1202"
arc.write(path = paste0(gdb_path, "/", out_layer), 
          data = Parcels,
          overwrite = TRUE)



