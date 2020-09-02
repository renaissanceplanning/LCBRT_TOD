library(sf)
library(tidyverse)
library(tmap)

setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V2")

Parcel <- read_sf("Parcels.shp")

Parcel <- st_make_valid(Parcel)

## Updating the Sale Price Per Acre
Parcel$Area <- st_area(Parcel) ## Updating the Area Measure
Parcel$Area <- as.numeric(Parcel$Area) / 43560 #converting square foot to acre
Parcel$SalePerAcr <- Parcel$SalePri / Parcel$Area

## TOD_Suit <- read_sf("TOD_SUitability_Original.shp")
## rm(TOD_Suit)

Dev_Sites <- read_sf("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/LC_Opportunity_Sites.shp") 
Dev_Sites$Area <- st_area(Dev_Sites) ## Updating the Area Measure
Dev_Sites$Area <- as.numeric(Dev_Sites$Area) / 43560 #converting square foot to acre

## finds the areas where Dev_Sites overlap, calculates the areas and joins the areas to the Parcel Layer
DOSShape <- st_make_valid(Dev_Sites)
DOSShape <- st_intersection(Dev_Sites, Parcel)

DOSShape$ShareDOS <- st_area(DOSShape)
DOSShape$ShareDOS <- as.numeric(DOSShape$ShareDOS) / 43560

DOSShape <- st_drop_geometry(DOSShape)

DOSShape <- DOSShape %>%
  group_by(ParcelID) %>%
  summarise(ShareDOS = sum(ShareDOS))

Parcel <- left_join(Parcel, DOSShape)

Parcel$DO_Site <- if_else(Parcel$ShareDOS > 0, TRUE, NA)

Parcel$DO_Site[is.na(Parcel$DO_Site)] <- FALSE

Parcel$PartialDOS <- if_else(Parcel$Area == Parcel$ShareDOS, true = FALSE, false = TRUE)

col_order <- c("ParcelID",   "PropID",     "Landuse",    "ShareDOS",   "DO_Site",    
               "PartialDOS", "Address",    "SalePri",    "LandVal",    "BldVal",     
               "TotVal",     "Area",       "SalePerAcr", "County",     "Redev_Prob", 
               "OffBldCnt",  "AGES",       "MAX_AGE",    "BldLandRt",  "geometry")
Parcel <- Parcel[col_order]

setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3")
write_sf(Parcel, "Parcels.shp")

rm(list = ls())

Parcel    <- read_sf("Parcels.shp")
Buildings <- read_sf("SouthCarolina_buildings.gpkg")

Buildings_Corridor <- st_intersection(Buildings, Parcel)
Buildings_Corridor <- Buildings_Corridor["area"]
rm(Buildings)

Buildings_Corridor <- st_join(Parcel, Buildings_Corridor, join = st_contains, left = FALSE)
Buildings_Corridor <- Buildings_Corridor[c("ParcelID", "area")]
Buildings_Corridor <- st_drop_geometry(Buildings_Corridor)

Buildings_Corridor <-
  Buildings_Corridor %>%
  group_by(ParcelID) %>%
  summarise(BldArea = sum(area),
            NumBlds = n())

sum(Buildings_Corridor$area) == sum(Buildings_Corridor$BldArea)
sum(Buildings_Corridor$NumBlds)

Buildings_Corridor$BldArea <- Buildings_Corridor$BldArea / 43560

Parcel <- left_join(Parcel, Buildings_Corridor)

col_order <- c("ParcelID",   "PropID",     "Landuse",    "ShareDOS",   "DO_Site",    
               "PartialDOS", "Address",    "SalePri",    "LandVal",    "BldVal",     "BldArea",     
               "TotVal",     "Area",       "SalePerAcr", "County",     "Redev_Prob", 
               "OffBldCnt",  "NumBlds",    "AGES",       "MAX_AGE",    "BldLandRt",  "geometry")

Parcel <- Parcel[col_order]
write_sf(Parcel, "Parcels.shp")

#filtering out DO Sites and removing unnessecary columns
setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3")
Parcel    <- read_sf("Parcels.shp")

Parcel$DO_Site <- if_else(Parcel$ShareDOS < 0.1, true = 0, false = 1)

Parcel$ShareDOS[Parcel$DO_Site == 0] <- NA 

Parcel$PartialDOS[Parcel$DO_Site == 0] <- NA

Parcel$DO_Site <- replace_na(Parcel$DO_Site, 0)

Parcel$Area_MOE_Low <- Parcel$Area * 0.95
Parcel$Area_MOE_High <- Parcel$Area * 1.05

Parcel$PartialDOS[Parcel$DO_Site == 1 
                  & ((Parcel$ShareDOS >= Parcel$Area_MOE_Low) & (Parcel$ShareDOS <= Parcel$Area_MOE_High)) ] <- 0

Parcel <- subset(Parcel, select = -c(Redev_Prob, OffBldCnt, AGES, MAX_AGE, Area_MOE_Low, Area_MOE_High))
write_sf(Parcel, "Parcels.shp")

#labeling areal units
setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3")
Parcel    <- read_sf("Parcels.shp")

col_names <- c("ParcelID", "PropID", "Landuse",    "ShareDOS_AC", "DO_Site", "PartialDOS", "Address", "SalePri",   
               "LandVal",  "BldVal", "BldArea_AC", "TotVal",      "Area_AC", "SalePerAcr", "County",  "NumBlds",   
               "BldLandRt",  "geometry")

colnames(Parcel) <- col_names

write_sf(Parcel, "Parcels.shp")

#deleting odd parcels
setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3")
Parcel    <- read_sf("Parcels.shp")

Parcel <- subset(Parcel, Parcel$ParclID != 27258)
Parcel <- subset(Parcel, Parcel$ParclID != "WATER")
Parcel <- subset(Parcel, Parcel$ParclID != "SCDOT")
Parcel <- subset(Parcel, Parcel$ParclID != "ROW")
Parcel <- subset(Parcel, Parcel$ParclID != "RAIL")
Parcel <- subset(Parcel, Parcel$ParclID != "HPR")
Parcel <- subset(Parcel, Parcel$ParclID != "BL")

write_sf(Parcel, "Parcels.shp")


## updating parcel after HDR DOS Review, also using centroids to adjust for shapefile problems
Parcels <- read_sf("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/Parcels.shp")
Parcels$DO_Site <- NA
Parcels$PrtlDOS <- NA
Parcels$SDOS_AC <- NA

cols <- c("ParclID"    ,"PropID"     ,"Landuse"   , "DO_Site"    ,"PrtlDOS"    ,"DOS_AR"     ,"DOSProp"    ,"Address",   
          "SalePri"    ,"LandVal"    ,"BldVal"    , "BldA_AC"    ,"TotVal"     ,"Area_AC"    ,"SlPrAcr"    ,"County",    
          "NumBlds"    ,"BldLndR"    ,"seg_name"  , "seg_num"    ,"in_pipe"    ,"stn_name"   ,"stn_name_O" ,"stn_name_1",
          "stn_name_2" ,"geometry"   ,"SDOS_AC")

Parcels <- Parcels[cols]

Dev_Sites <- read_sf("K:/Projects/BCDCOG/Features/Files_For_RDB/Lowcountry_Webmap/LC_Opportunity_Sites.shp") 
Dev_Sites <- subset(Dev_Sites, Dev_Sites$ReviewHDR == "0" | Dev_Sites$ReviewHDR == "2")

## Dev_Sites$DOS_AR <- st_area(Dev_Sites) ## Updating the Area Measure
## Dev_Sites$DOS_AR <- as.numeric(Dev_Sites$DOS_AR) / 43560 #converting square foot to acre

Dev_Sites <- st_make_valid(Dev_Sites)
DOSShape <- st_intersection(Dev_Sites, Parcels)

DOSShape$DOS_AR <- st_area(DOSShape)
DOSShape$DOS_AR <- as.numeric(DOSShape$DOS_AR) / 43560

DOSShape <- st_drop_geometry(DOSShape)

DOSShape <- DOSShape %>%
  group_by(ParclID) %>%
  summarise(DOS_AR = sum(DOS_AR))

Parcels <- left_join(Parcels, DOSShape)

Parcels$DO_Site <- if_else(Parcels$DOS_AR > 0, true = 1, false = 0)
Parcels$DO_Site <- if_else(Parcels$DOS_AR < 0.1, true = 0, false = 1)
Parcels$DO_Site <- replace_na(Parcels$DO_Site, 0)

Parcels$PrtlDOS <- if_else(round(Parcels$DOS_AR, 3) == round(Parcels$Area_AC, 3), true = 0, false = 1)
Parcels$DOSProp <-  Parcels$DOS_AR / Parcels$Area_AC 

Parcels$DOSProp[Parcels$DO_Site == 0] <- NA 
Parcels$PrtlDOS[Parcels$DO_Site == 0] <- NA

Parcels$DOSProp[Parcels$DO_Site == 0] <- NA
Parcels$DOSProp[Parcels$PrtlDOS == 0] <- 1


col_order <- c("ParclID"    ,"PropID"     ,"Landuse"   , "DO_Site"    ,"PrtlDOS"    ,"DOS_AR"     ,"DOSProp"    ,"Address",   
               "SalePri"    ,"LandVal"    ,"BldVal"    , "BldA_AC"    ,"TotVal"     ,"Area_AC"    ,"SlPrAcr"    ,"County",    
               "NumBlds"    ,"BldLndR"    ,"seg_name"  , "seg_num"    ,"in_pipe"    ,"stn_name"   ,"stn_name_O" ,"stn_name_1",
               "stn_name_2" ,"geometry"   ,"SDOS_AC")

Parcels <- Parcels[col_order]
setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3")
write_sf(Parcels, "Parcels.shp")
