# Set Up -----------------------------------------------------------------------
library(sf)
library(tmap)
tmap_mode("view")
library(tidyverse)
setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/source_shapefiles")
# function ---------------------------------------------------------------------
Mode <- function(x) {
  ux <- unique(x)
  ux[which.max(tabulate(match(x, ux)))]
}

Add_FAR = function(Calc_PAR, All_PAR, LU_EXM = NA){
  LU_PAR = subset(Calc_PAR, Calc_PAR$Exp_LU == LU_EXM)
  
  EXP_LU_Join <- st_join(LU_PAR, 
                         subset(All_PAR[c("Exp_LU", "BldSqFt",
                                          "Sq_Feet", "geometry")], 
                                All_PAR$Exp_LU == LU_EXM), 
                         join = st_is_within_distance, 
                         dist = 1000, 
                         suffix = c("", "_org"),
                         left = TRUE)
  
  cat("join done \n")
  
  FAR_LU =
    st_drop_geometry(EXP_LU_Join) %>% 
    group_by(ParclID) %>%
    summarise(Mean_FAR      = mean(BldSqFt_org / Sq_Feet_org, na.rm = TRUE),
              Max_FAR       = max(BldSqFt_org  / Sq_Feet_org, na.rm = TRUE),
              Count_Par     = n()
    )
  
  return(FAR_LU)
}

Add_Far_Use_All = function(Calc_PAR, All_PAR){
  
  EXP_LU_Join = st_join(Calc_PAR, 
                        All_PAR[c("Exp_LU", "BldSqFt",
                                  "Sq_Feet", "geometry")],
                        join = st_is_within_distance, 
                        dist = 1000, 
                        suffix = c("", "_org"),
                        left = TRUE)
  
  cat("join done \n")
  
  FAR_LU =
    st_drop_geometry(EXP_LU_Join) %>% 
    group_by(ParclID) %>%
    summarise(Mean_FAR      = mean(BldSqFt_org / Sq_Feet_org, na.rm = TRUE),
              Max_FAR       = max(BldSqFt_org  / Sq_Feet_org, na.rm = TRUE),
              Count_Par     = n()
    )
}
# Calculations -----------------------------------------------------------------
## Read in and Subset Data
Parcels <- read_sf("Parcels_1201.shp")
FAR_Parcels = subset(Parcels, Parcels$Exp_LU != "Single-family")
SF          = subset(Parcels, Parcels$Exp_LU == "Single-family")

## Single Family, Updating Single Family Capacity
## Single Family Capacity == Sq_Feet / 1500
SF$SF_Cpct  = round(SF$Sq_Feet / 1500, digits = 0)
SF$Max_FAR  = NA
SF$Mean_FAR = NA
SF$Count_Par= NA

## Mean and Max FAR by Landuse
FAR_Parcels$SF_Cpct = NA

LUs = unique(FAR_Parcels$Exp_LU)

for(LU in LUs){
  FARS = Add_FAR(FAR_Parcels, Parcels, LU)
  assign(paste(LU, "FARs", sep = "_"), FARS)
  cat("done with ", LU, "\n")
}

FARs = bind_rows(mget(ls(pattern = "*_FARs")))

Redo = subset(FARs, FARs$Count_Par == 1)
FARs = subset(FARs, FARs$Count_Par != 1)

Iso_Parcels = subset(FAR_Parcels,
                     FAR_Parcels$ParclID %in% Redo$ParclID)

LUs = unique(Iso_Parcels$Exp_LU)
ISO_FARS = Add_Far_Use_All(Iso_Parcels, Parcels)

FARS_Add = rbind(ISO_FARS, FARs)
rm(list = ls(pattern = "*_FARs"))
rm(FARs, FARS, ISO_FARS, Redo, Iso_Parcels)

FAR_Parcels = 
  inner_join(FAR_Parcels[-which(names(FAR_Parcels) 
                                %in% c("Mean_FAR", "Max_FAR"))],
             FARS_Add)
rm(FARS_Add)
Parcels = rbind(FAR_Parcels, SF)

# Writing Out ------------------------------------------------------------------
Parcels$EXP_Sqft = Parcels$Sq_Feet * Parcels$Mean_FAR
write_sf(Parcels, "Parcels_1201_FAR.shp")