library(sf)
library(tidyverse)
library(tmap)

tmap_mode("view")

Parcels <- read_sf("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/Parcels.shp")
col_order <- names(Parcels)
Parcels$DO_Site <- NA
Parcels$PrtlDOS <- NA

Parcels$Area_AC <- as.numeric(st_area(Parcels)) / 43560

# # cols <- c("ParclID"    ,"PropID"     ,"Landuse"   , "DO_Site"    ,"PrtlDOS"    ,"DOS_AR"     ,"DOSProp"    ,"Address",   
#           "SalePri"    ,"LandVal"    ,"BldVal"    , "BldA_AC"    ,"TotVal"     ,"Area_AC"    ,"SlPrAcr"    ,"County",    
#           "NumBlds"    ,"BldLndR"    ,"seg_name"  , "seg_num"    ,"in_pipe"    ,"stn_name"   ,"stn_name_O" ,"stn_name_1",
#           "stn_name_2" ,"geometry"   ,"SDOS_AC")
# 
# # Parcels <- Parcels[cols]

Dev_Sites <- read_sf("K:/Projects/BCDCOG/Features/Files_For_RDB/Lowcountry_Webmap/LC_Opportunity_Sites.shp") 
Dev_Sites <- subset(Dev_Sites, Dev_Sites$ReviewHDR == "0" | Dev_Sites$ReviewHDR == "2")

## Dev_Sites$DOS_AR <- st_area(Dev_Sites) ## Updating the Area Measure
## Dev_Sites$DOS_AR <- as.numeric(Dev_Sites$DOS_AR) / 43560 #converting square foot to acre

DOSShape <- st_intersection(Dev_Sites, Parcels)

DOSShape$DOS_AR <- st_area(DOSShape)
DOSShape$DOS_AR <- as.numeric(DOSShape$DOS_AR) / 43560

DOSShape <- st_drop_geometry(DOSShape)

DOSShape <- DOSShape %>%
  group_by(ParclID) %>%
  summarise(DOS_AR = sum(DOS_AR))

Parcels <- left_join(Parcels[-6], DOSShape)

Parcels$DOSProp <-  Parcels$DOS_AR / Parcels$Area_AC 

Parcels$DOSProp[Parcels$DOSProp > 1] <-  1

Parcels$DO_Site[Parcels$DOSProp > 0.05] <- 1
Parcels$DO_Site[Parcels$DOSProp < 0.05] <- 0

Parcels$PrtlDOS[Parcels$DOSProp > 0.05 & Parcels$DOSProp < 0.95] <- 1
Parcels$PrtlDOS[Parcels$DO_Site == 1 & is.na(Parcels$PrtlDOS)] <- 0

Parcels$DO_Site[is.na(Parcels$DO_Site)] <- 0

Parcels <- Parcels[col_order]
setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3")
write_sf(Parcels, "Parcels_ds.shp")
