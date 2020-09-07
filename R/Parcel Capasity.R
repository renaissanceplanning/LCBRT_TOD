library(sf)
library(tmap)
library(tidyverse)

#function for mode
Mode <- function(x) {
  ux <- unique(x)
  ux[which.max(tabulate(match(x, ux)))]
}

setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3")

Parcels <- read_sf("Parcels.shp")
Parcels$Sq_Feet <- st_area(Parcels)
Parcels$Sq_Feet <- as.numeric(Parcels$Sq_Feet)

Small_Parcels <- subset(Parcels, Parcels$Sq_Feet <= 12000)
Large_Parcels <- subset(Parcels, Parcels$Sq_Feet >  12000)

# parcels less than 12000 sq ft
Small_Parcels$Exp_LU <- Small_Parcels$Landuse #update to make vacant single family

Small_Parcels$Exp_LU[Small_Parcels$Exp_LU == "Vacant/Undeveloped"] <- "Single-family"
Small_Parcels$Exp_LU[is.na(Small_Parcels$Exp_LU)] <- "Single-family"


Small_Parcels$SF_Cpct <- if_else(Small_Parcels$Exp_LU == "Vacant/Undeveloped" |
                                       Small_Parcels$Exp_LU == "Multifamily" |
                                       Small_Parcels$Exp_LU == "Single-family",
                                     
                                     true  = round(Small_Parcels$Sq_Feet / 1500, digits = 0),
                                     false = 0)

# Parcels larger than 120000
# seq.int <- seq(0, nrow(Large_Parcels), 479)
# seq.gp <- cut(1:nrow(Large_Parcels), breaks=seq.int, include.lowest = TRUE)
# 
# parcel_list <- split(Large_Parcels, seq.gp)
# 
# names(parcel_list) <- paste0("chunk_", 1:length(parcel_list))
# 
# for (x in names(parcel_list)) {
#   Far_SF <- st_join(parcel_list[[x]], Parcels[c(3,12,14,22)], join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))
#   FAR_LU =
#     st_drop_geometry(Far_SF) %>%
#     group_by(ParclID) %>%
#     summarise(Exp_LU       = Mode(Landuse_org),
#               Mean_FAR      = mean(BldA_AC_org /  Area_AC),
#               Max_FAR       = Max_FAR(BldA_AC_org))
# 
#   assign(x, FAR_LU)
# }
# values <- bind_rows(mget(ls(pattern = "chunk_*")))
# Parcels <- left_join(Large_Parcels, values)
# 
# write_sf(Parcels, "K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/Parcels_EXP.shp")

#correcting land use
Large_Parcels$Exp_LU <- Large_Parcels$Landuse
Large_Parcels$Exp_FAR <- NA

Vacant_Large <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Vacant/Undeveloped" | is.na(Large_Parcels$Exp_LU))

Relevant_Parcels <- subset(Parcels, Parcels$Landuse != "Vacant/Undeveloped"    &
                                         Parcels$Landuse != "Utilities"            &
                                         Parcels$Landuse != "Transportation"       &
                                         Parcels$Landuse != "Agriculture/Forestry" &
                                         Parcels$Landuse != "Recreation/Cultural"  &
                                         !is.na(Parcels$Landuse))

EXP_LU_Join <- st_join(Vacant_Large, Relevant_Parcels [c("Landuse", "BldA_AC", "Sq_Feet", "geometry")], join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

Vacant_LUs =
  st_drop_geometry(EXP_LU_Join) %>%
    group_by(ParclID, Landuse_org) %>%
    summarise(Landuse_SqFT = sum(Sq_Feet_org)) %>%
    group_by(ParclID) %>%
    arrange(desc(Landuse_SqFT)) %>%
    summarise(Exp_LU       = first(Landuse_org))


Vacant_Large <- left_join(Vacant_Large[-27], Vacant_LUs)
Vacant_Large$Exp_LU[is.na(Vacant_Large$Exp_LU)] <- "Single-family"

Large_Parcels <- rbind(Non_Vacant_Large, Vacant_Large)

# correcting large parcel capacity

## single and multifamily

Large_Residential <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Single-family" |
                                           Large_Parcels$Exp_LU == "Multifamily")

Large_Residential$SF_Cpct <-  round(Large_Residential$Sq_Feet / 1500)

Large_Residential <- Large_Residential[-which(names(Large_Residential) ==  "Exp_FAR")]
Large_Residential$Mean_FAR <- NA
Large_Residential$Max_FAR  <- NA

## office
Large_Office <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Office")

EXP_LU_Join <- st_join(Large_Office, subset(Parcels[c("Landuse", "BldA_AC", "geometry")], Parcels$Landuse == "Office"), 
                       join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

FAR_LU =
 st_drop_geometry(EXP_LU_Join) %>% 
 group_by(ParclID) %>%
 summarise(Mean_FAR      = mean(BldA_AC_org /  Area_AC),
           Max_FAR       = max(BldA_AC_org /  Area_AC)
          )

Large_Office <- left_join(Large_Office[-which(names(Large_Office) ==  "Exp_FAR")], FAR_LU)

## retail
Large_retail <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Commercial/Retail")

EXP_LU_Join <- st_join(Large_retail, subset(Parcels[c("Landuse", "BldA_AC", "geometry")], Parcels$Landuse == "Commercial/Retail"), 
                       join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

FAR_LU =
  st_drop_geometry(EXP_LU_Join) %>% 
  group_by(ParclID) %>%
  summarise(Mean_FAR      = mean(BldA_AC_org /  Area_AC),
            Max_FAR       = max(BldA_AC_org /  Area_AC)
  )

Large_retail <- left_join(Large_retail[-which(names(Large_retail) ==  "Exp_FAR")], FAR_LU)

## Institutional
Large_institutional <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Institutional")

EXP_LU_Join <- st_join(Large_institutional, subset(Parcels[c("Landuse", "BldA_AC", "geometry")], Parcels$Landuse == "Institutional"), 
                       join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

FAR_LU =
  st_drop_geometry(EXP_LU_Join) %>% 
  group_by(ParclID) %>%
  summarise(Mean_FAR      = mean(BldA_AC_org /  Area_AC),
            Max_FAR       = max(BldA_AC_org /  Area_AC)
  )

Large_institutional <- left_join(Large_institutional[-which(names(Large_institutional) ==  "Exp_FAR")], FAR_LU)

## industrial
Large_industrial <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Industrial/Manufacturing")

EXP_LU_Join <- st_join(Large_industrial, subset(Parcels[c("Landuse", "BldA_AC", "geometry")], Parcels$Landuse == "Industrial/Manufacturing"), 
                       join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

FAR_LU =
  st_drop_geometry(EXP_LU_Join) %>% 
  group_by(ParclID) %>%
  summarise(Mean_FAR      = mean(BldA_AC_org /  Area_AC),
            Max_FAR       = max(BldA_AC_org /  Area_AC)
  )

Large_industrial <- left_join(Large_industrial[-which(names(Large_industrial) ==  "Exp_FAR")], FAR_LU)

## non relevant

Large_non_rel <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Recreation/Cultural" |
                          Large_Parcels$Exp_LU == "Agriculture/Forestry" |
                          Large_Parcels$Exp_LU == "Utilities" |
                          Large_Parcels$Exp_LU == "Transportation")

Large_non_rel <- Large_non_rel[-which(names(Large_non_rel) ==  "Exp_FAR")]
Large_non_rel$Mean_FAR <- NA
Large_non_rel$Max_FAR <- NA

Small_Parcels <- Small_Parcels[-which(names(Small_Parcels) ==  "Exp_FAR")]
Small_Parcels$Mean_FAR <- NA
Small_Parcels$Max_FAR <- NA


Large_Parcels <- rbind(Large_industrial, Large_Office, Large_Residential, Large_retail, Large_institutional, Large_non_rel)

Parcels <- rbind(Small_Parcels, Large_Parcels)

Parcels$SF_Cpct[Parcels$Exp_LU == "Single-family"] <- round(Parcels$Sq_Feet[Parcels$Exp_LU == "Single-family"] / 1500, digits = 0)
Parcels$SF_Cpct[Parcels$Exp_LU == "Multifamily"] <- round(Parcels$Sq_Feet[Parcels$Exp_LU == "Multifamily"] / 1500, digits = 0)

Parcels$SF_Cpct[Parcels$Exp_LU != "Multifamily" & Parcels$Exp_LU != "Single-family"] <- NA

write_sf(Parcels, "Parcels_EXP.shp")

## updates on 8/28 to add building height and recalculate, will be unnesseasry in updates
Parcels <- read_sf("Parcels.shp")
Parcels$Sq_Feet <- as.numeric(st_area(Parcels))
Buildings <- read_sf("buildings_with_floors.shp")

Buildings_Corridor <- st_join(st_centroid(Buildings), Parcels[-which(names(Parcels) == "BldSqFt")], join = st_within, left = FALSE)

Buildings_Corridor$fl_est[Buildings_Corridor$Landuse == "Commercial/Retail" & Buildings_Corridor$fl_est > 2] <- 2
Buildings_Corridor$fl_est[Buildings_Corridor$Landuse == "Industrial/Manufacturing" & Buildings_Corridor$fl_est > 2] <- 2

Buildings_Corridor$fl_ar_sq <- Buildings_Corridor$fl_est * Buildings_Corridor$Shape_Area

Buildings_Corridor <- st_drop_geometry(Buildings_Corridor)

Buildings_Areas <-
  Buildings_Corridor %>%
    group_by(ParclID) %>%
    summarise(BldSqFt = sum(fl_ar_sq))

Parcels <- left_join(Parcels[-which(names(Parcels) == "BldSqFt")], Buildings_Areas)

Parcels$BldA_AC <- Parcels$BldSqFt / 43560

Small_Parcels <- subset(Parcels, Parcels$Sq_Feet <= 12000)
Large_Parcels <- subset(Parcels, Parcels$Sq_Feet >  12000)

# correcting large parcel capacity
## single and multifamily
Large_Residential <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Single-family" |
                              Large_Parcels$Exp_LU == "Multifamily")

Large_Residential$SF_Cpct <-  round(Large_Residential$Sq_Feet / 1500)

Large_Residential <- Large_Residential[-which(names(Large_Residential) %in% c("Mean_FAR", "Max_FAR"))]
                                      
Large_Residential$Mean_FAR <- NA
Large_Residential$Max_FAR  <- NA

## office
Large_Office <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Office")

EXP_LU_Join <- st_join(Large_Office, subset(Parcels[c("Landuse", "BldA_AC", "Area_AC", "geometry")], Parcels$Landuse == "Office"), 
                       join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

FAR_LU =
  st_drop_geometry(EXP_LU_Join) %>% 
  group_by(ParclID) %>%
  summarise(Mean_FAR      = mean(BldA_AC_org /  Area_AC_org, na.rm = TRUE),
            Max_FAR       = max(BldA_AC_org /  Area_AC_org, na.rm = TRUE)
  )

Large_Office <- left_join(Large_Office[-which(names(Large_Office) %in% c("Mean_FAR", "Max_FAR"))], FAR_LU)

## retail
Large_retail <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Commercial/Retail")

EXP_LU_Join <- st_join(Large_retail, subset(Parcels[c("Landuse", "BldA_AC", "Area_AC", "geometry")], Parcels$Landuse == "Commercial/Retail"), 
                       join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

FAR_LU =
  st_drop_geometry(EXP_LU_Join) %>% 
  group_by(ParclID) %>%
  summarise(Mean_FAR      = mean(BldA_AC_org /  Area_AC_org, na.rm = TRUE),
            Max_FAR       = max(BldA_AC_org /  Area_AC_org, na.rm = TRUE)
  )

Large_retail <- left_join(Large_retail[-which(names(Large_retail) %in% c("Mean_FAR", "Max_FAR"))], FAR_LU)

## Institutional
Large_institutional <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Institutional")

EXP_LU_Join <- st_join(Large_institutional, subset(Parcels[c("Landuse", "BldA_AC", "Area_AC", "geometry")], Parcels$Landuse == "Institutional"), 
                       join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

FAR_LU =
  st_drop_geometry(EXP_LU_Join) %>% 
  group_by(ParclID) %>%
  summarise(Mean_FAR      = mean(BldA_AC_org /  Area_AC_org, na.rm = TRUE),
            Max_FAR       = max(BldA_AC_org /  Area_AC_org, na.rm = TRUE)
  )

Large_institutional <- left_join(Large_institutional[-which(names(Large_institutional) %in% c("Mean_FAR", "Max_FAR"))], FAR_LU)

## industrial
Large_industrial <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Industrial/Manufacturing")

EXP_LU_Join <- st_join(Large_industrial, subset(Parcels[c("Landuse", "BldA_AC", "Area_AC", "geometry")], Parcels$Landuse == "Industrial/Manufacturing"), 
                       join = st_is_within_distance, dist = 1000, suffix = c("", "_org"))

FAR_LU =
  st_drop_geometry(EXP_LU_Join) %>% 
  group_by(ParclID) %>%
  summarise(Mean_FAR      = mean(BldA_AC_org /  Area_AC_org, na.rm = TRUE),
            Max_FAR       = max(BldA_AC_org /  Area_AC_org, na.rm = TRUE)
  )

Large_industrial <- left_join(Large_industrial[-which(names(Large_industrial) %in% c("Mean_FAR", "Max_FAR"))], FAR_LU)

## non relevant

Large_non_rel <- subset(Large_Parcels, Large_Parcels$Exp_LU == "Recreation/Cultural" |
                          Large_Parcels$Exp_LU == "Agriculture/Forestry" |
                          Large_Parcels$Exp_LU == "Utilities" |
                          Large_Parcels$Exp_LU == "Transportation")

Large_non_rel <- Large_non_rel[-which(names(Large_non_rel) %in% c("Mean_FAR", "Max_FAR"))]
Large_non_rel$Mean_FAR <- NA
Large_non_rel$Max_FAR <- NA

Small_Parcels <- Small_Parcels[-which(names(Small_Parcels) %in% c("Mean_FAR", "Max_FAR"))]
Small_Parcels$Mean_FAR <- NA
Small_Parcels$Max_FAR <- NA


Large_Parcels <- rbind(Large_industrial, Large_Office, Large_Residential, Large_retail, Large_institutional, Large_non_rel)

## adding values for edge cases with no comparable

FAR_Values <-
  st_drop_geometry(Large_Parcels[c("seg_nam", "Exp_LU", "Mean_FAR", "Max_FAR")]) %>%
    group_by(seg_nam, Exp_LU) %>%
    summarise(Mean_FAR = mean(Mean_FAR, na.rm = TRUE),
              Max_FAR  = max(Max_FAR,   na.rm = TRUE))

NA_Large_Par <- subset(Large_Parcels, Large_Parcels$Max_FAR == "-Inf")

NA_Large_Par <- left_join(NA_Large_Par[-which(names(NA_Large_Par) %in% c("Mean_FAR", "Max_FAR"))], FAR_Values)

non_na_large_par <-   subset(Large_Parcels, !Large_Parcels$ParclID %in% unique(NA_Large_Par$ParclID))

Large_Parcels <- rbind(NA_Large_Par, non_na_large_par)

Parcels <- rbind(Small_Parcels, Large_Parcels)
write_sf(Parcels, "Parcels.shp")

# adding expected floor area
Parcels <- read_sf("Parcels.shp")

Parcels$EXP_Sqft <- Parcels3$Sq_Feet * Parcels3$Mean_FAR

write_sf(Parcels, "Parcels.shp")
write_sf(Parcels,"K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/Backup/Parcels_Back_Up.shp")





 