library(sf)
library(tidyverse)
library(tmap)

tmap_mode("view")

Parcels_Path    = paste0("K:/Projects/BCDCOG/Features/Files_For_RDB/",
                         "RDB_V3/source_shapefiles/Parcels.shp")
Parcels         = read_sf(Parcels_Path)
   
col_order       = names(Parcels)
Parcels$DO_Site = NA
Parcels$PrtlDOS = NA

Parcels$Area_AC = as.numeric(st_area(Parcels)) / 43560

Dev_Site_Path   = paste0("K:/Projects/BCDCOG/Features/Files_For_RDB/",
                         "RDB_V3/source_shapefiles/",
                         "Dev_Opp_Sites_1006.shp")

# Dev_Sites = read_sf(Dev_Site_Path) 
# Dev_Sites = st_transform(Dev_Sites, st_crs(Parcels))
# 
# Pipeline  = subset(Dev_Sites, Dev_Sites$KNWN_DEV == 1)
# Pipeline  = st_centroid(Pipeline)

Pipe_Path = paste0("K:/Projects/BCDCOG/Features/Files_For_RDB/",
                   "RDB_V3/source_shapefiles/",
                   "Dev_Opp_KnwnDev_Points.shp")
#
# write_sf(Pipeline, Pipe_Path)

Dev_Sites = subset(Dev_Sites, 
                   Dev_Sites$OP_SITE  != 0 &
                   Dev_Sites$In_Plan  == 0 &
                   Dev_Sites$KNWN_DEV != 1 &
                   Dev_Sites$FLU      != "Parking")

DOSShape  = st_intersection(Dev_Sites, Parcels)

DOSShape$DOS_AR <- st_area(DOSShape)
DOSShape$DOS_AR <- as.numeric(DOSShape$DOS_AR) / 43560

DOSShape = st_drop_geometry(DOSShape)

#Creating SBF_FLU
Vacant_LUs =
  DOSShape %>%
  group_by(ParclID, FLU) %>%
  summarise(Landuse_SqFT = sum(AREA_SF)) %>%
  group_by(ParclID) %>%
  arrange(desc(Landuse_SqFT)) %>%
  summarise(SBF_FLU       = first(FLU))

DOSShape = DOSShape %>%
             group_by(ParclID) %>%
             summarise(DOS_AR = sum(DOS_AR))

DOS_AR_Columns = which(colnames(Parcels) == "DOS_AR")

Parcels  = left_join(Parcels[-DOS_AR_Columns], DOSShape)
Parcels  = left_join(Parcels, Vacant_LUs)

Parcels$DOSProp =  Parcels$DOS_AR / Parcels$Area_AC 

Parcels$DOSProp[Parcels$DOSProp > 1] =  1

Parcels$DO_Site[Parcels$DOSProp > 0.05] = 1
Parcels$DO_Site[Parcels$DOSProp < 0.05] = 0

Parcels$PrtlDOS[Parcels$DOSProp > 0.05 & Parcels$DOSProp < 0.95] = 1
Parcels$PrtlDOS[Parcels$DO_Site == 1   & is.na(Parcels$PrtlDOS)] = 0

Parcels$DO_Site[is.na(Parcels$DO_Site)] = 0

new_col_order = c(col_order[-29], "SPF_FLU", col_order[29])

Parcels <- Parcels[col_order]

Parcels$SBF_FLU[Parcels$SBF_FLU == "Affordable"] = "Multifamily"
Parcels$SBF_FLU[Parcels$SBF_FLU == "MFH"] = "Multifamily"
Parcels$SBF_FLU[Parcels$SBF_FLU == "SFH"] = "Single-family"
Parcels$SBF_FLU[Parcels$SBF_FLU == "Townhome"] = "Multifamily"

Parcels$SBF_FLU[is.na(Parcels$SBF_FLU)] = "Unassigned"

Mask = (Parcels$DO_Site == 1 & Parcels$SBF_FLU != "Unassigned")

Parcels$Exp_LU[Mask] = Parcels$SBF_FLU[Mask]


setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/source_shapefiles")
write_sf(Parcels, "Parcels.shp")
