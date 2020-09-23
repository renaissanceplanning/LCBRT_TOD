library(tidyverse)
library(tidycensus)
library(sf)
library(tmap)
tmap_mode("view")

#housing data
housing = c(Total_Housing       = "B25001_001",	
            Total_Vacancy       = "B25004_001")

Housing <- get_acs("block group", variables = housing,
                   state = "SC", output = "wide", geometry = TRUE)

Housing <- Housing %>%
  group_by(GEOID) %>%
  summarise(GEOID   = GEOID,
            OccRate = 1 - (Total_VacancyE / Total_HousingE))
            
#files not in RDB_V3
setwd("D:/Users/IL7/Documents/Affordable_Housing")
Necessary_Files <- c("LIHTC_Units", "SBF_LRAH_04072020")

for (i in Necessary_Files) {
  filepath <- paste0(i, ".shp")
  assign(i, read_sf(filepath))
}

#current working directory
setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/source_shapefiles")
Necessary_Files <- c("Parcels", "Stations_LCRT_BRT_Recommended_andAlternative_20200814",
                     "CHATS_TAZs_FullRegion_08122020v3")

#load files
for (i in Necessary_Files) {
  filepath <- paste0(i, ".shp")
  assign(i, read_sf(filepath))
}

TAZ = CHATS_TAZs_FullRegion_08122020v3
rm(CHATS_TAZs_FullRegion_08122020v3)

#adjusting spatial reference systems

my_crs <- st_crs(Stations_LCRT_BRT_Recommended_andAlternative_20200814)

LIHTC_Units       <- st_transform(LIHTC_Units, my_crs)
SBF_LRAH_04072020 <- st_transform(SBF_LRAH_04072020, my_crs)
TAZ               <- st_transform(TAZ, my_crs)
Housing           <- st_transform(Housing, my_crs)
#TAZ Area for Later Allocation
TAZ$ORG_SqFt      <- as.numeric(st_area(TAZ))

#filter stations for appropriate scenario
Stations <- subset(Stations_LCRT_BRT_Recommended_andAlternative_20200814, 
                   Stations_LCRT_BRT_Recommended_andAlternative_20200814$WE_Fair != "NA") # only line that needs to be changed for differing scenarios
rm(Stations_LCRT_BRT_Recommended_andAlternative_20200814)

#adding in new station IDs as old ones are messy and they are needed for the loop
Stations = Stations %>% mutate(Station_ID = row_number())

#creating a vector of station IDs to loop over
Station_IDs <- Stations$Station_ID

for (i in Station_IDs) {
  station <- subset(Stations, Stations$Station_ID == i)
  
  buff <- paste0("buffer_for_st_", i)
  assign(buff, st_buffer(station, dist = 2640)) 
  
  clip_parcs <- paste0("cliped_par_for_st_", i)
  assign(clip_parcs, st_intersection(st_make_valid(get(buff)), 
                                     st_make_valid(Parcels)))
  
  station$total_area <- as.numeric(st_area(st_union(get(clip_parcs))))

  #land use areas
  station$single_family            <- if (nrow(get(clip_parcs) %>% 
                                               filter(Landuse == "Single-family")) != 0) {
    
    as.numeric(st_area(st_union(get(clip_parcs) %>%
                                  filter(Landuse == "Single-family"))))
    
  } else {0}
  
  
  station$Multifamily              <- if (nrow(get(clip_parcs) %>% 
                                               filter(Landuse == "Multifamily")) != 0) {
    
    as.numeric(st_area(st_union(get(clip_parcs) %>%
                                  filter(Landuse == "Multifamily"))))
    
  } else {0}
  
  
  station$Commercial_Retail        <- if (nrow(get(clip_parcs) %>% 
                                               filter(Landuse == "Commercial/Retail")) != 0) {
    
    as.numeric(st_area(st_union((get(clip_parcs) %>%
                                   filter(Landuse == "Commercial/Retail")))))
    
  } else {0}
  
  
  station$Utilities                <- if (nrow(get(clip_parcs) %>% 
                                               filter(Landuse == "Utilities")) != 0){
    
    as.numeric(st_area(st_union(get(clip_parcs) %>%
                                  filter(Landuse == "Utilities"))))
    
  } else {0}
  
  
  
  station$Industrial_Manufacturing <- if (nrow(get(clip_parcs) %>% 
                                               filter(Landuse == "Industrial/Manufacturing")) != 0){
    
    as.numeric(st_area(st_union(get(clip_parcs) %>%
                                  filter(Landuse == "Industrial/Manufacturing"))))
    
  } else {0}
  
  
  
  station$Institutional            <- if (nrow(get(clip_parcs) %>% 
                                               filter(Landuse == "Institutional")) != 0){
    
    as.numeric(st_area(st_union(get(clip_parcs) %>%
                                  filter(Landuse == "Institutional"))))
    
  } else {0}
  
  
  
  station$Transportation           <- if (nrow(get(clip_parcs) %>% 
                                               filter(Landuse == "Transportation")) != 0){
    
    as.numeric(st_area(st_union(get(clip_parcs) %>%
                                  filter(Landuse == "Transportation"))))
    
  } else {0}
  
  
  
  station$Office                  <- if (nrow(get(clip_parcs) %>% 
                                              filter(Landuse == "Office")) != 0) {
    
    as.numeric(st_area(st_union(get(clip_parcs) %>%
                                  filter(Landuse == "Office"))))
    
  } else {0}
  
  
  
  station$Recreation_Cultural     <- if (nrow(get(clip_parcs) %>% 
                                              filter(Landuse == "Recreation/Cultural")) != 0){
    
    as.numeric(st_area(st_union(get(clip_parcs) %>%
                                  filter(Landuse == "Recreation/Cultural"))))
    
  } else {0}

  station$Vacant_Undeveloped      <- if (nrow(get(clip_parcs) %>% 
                                              filter(Landuse == "Vacant/Undeveloped")) != 0){
    
    as.numeric(st_area(st_union((get(clip_parcs) %>%
                                   filter(Landuse == "Vacant/Undeveloped")))))
    
  } else {0}
  
  #development sites
  
  station$dev_Opp_acres <- if (nrow(get(clip_parcs) %>% 
                                   filter(DO_Site == 1)) != 0){
    
    sum(st_drop_geometry(get(clip_parcs)) %>% filter(DO_Site == 1) %>% select(DOS_AR))
    
  } else {0}
  
  station$dev_vac_acres <- if (nrow(get(clip_parcs) %>% 
                                   filter(DO_Site == 1) %>% 
                                   filter(Landuse == "Vacant/Undeveloped")) != 0){
    
    sum(st_drop_geometry(get(clip_parcs) %>% 
                           filter(DO_Site == 1) %>% 
                           filter(Landuse == "Vacant/Undeveloped") %>% 
                           select(DOS_AR)))
    
  } else {0}
  
  station$pot_redev_acres <- station$dev_Opp_acres - station$dev_vac_acres
  
  #converting area to units
    #adding the other layer
  
  station$other <- sum(station$Utilities, station$Transportation,
                       station$Institutional, station$Recreation_Cultural)
  
    #converting units
  station$SF_Units  <- station$single_family / 1800
  station$MF_Units  <- station$Multifamily   / 1400
  station$Ind_Units <- station$Industrial_Manufacturing / 1000
  station$Off_Units <- station$Office / 600
  station$Ret_Units <- station$Commercial_Retail / 700
  station$Oth_Units <- station$other / 800
  
    #summarizing
  station$Res_Units <- sum(station$SF_Units, station$MF_Units)
  station$Job_Units <- sum(station$Ind_Units, station$MF_Units,
                           station$Ret_Units, station$Oth_Units)
  
  station$JH_ratio <- station$Job_Units / station$Res_Units
  
  station$Job_Density <- station$Job_Units / 502.4
  station$DU_Density  <- station$Res_Units / 502.4
  
  station$FAR <- (sum(st_drop_geometry(get(clip_parcs)) %>% 
                        select(BldSqFt), na.rm = TRUE) 
                  / as.numeric(st_area(st_union(get(clip_parcs)))))
  
  #occupied units
  vacancy <- paste0("vacancy_st_", i)
  assign(vacancy, st_intersection(Housing, get(buff)) )
  
  station$occupied_units <- mean(unlist(st_drop_geometry(get(vacancy) %>% select(OccRate)))) * station$Res_Units
  
  #calculating population using Person Per HH pulled from TAZ data
  tazs <- paste0("taz_st_", i)
  assign(tazs, st_intersection(get(buff), TAZ))
  
  assign(tazs, 
         get(tazs) %>% mutate(Buff_SqFt   = as.numeric(st_area(get(tazs)))) %>%
                       mutate(POP_in_Buff = round(TOTPOP15 * (Buff_SqFt / ORG_SqFt)
                                                  , digits = 0),
                              HH_in_Buff  = round(HH15 * (Buff_SqFt / ORG_SqFt),
                                                  digits = 0)))
  
  station$person_per_hh <- (sum(st_drop_geometry(get(tazs) %>% 
                                                  select(POP_in_Buff))) 
                            / sum(st_drop_geometry(get(tazs) %>% 
                                                     select(HH_in_Buff))))

  #population is occupied housing units times persons per hh
  station$population <- station$person_per_hh * station$occupied_units
  
  af_hos_1 <- paste0("af_hos_1_st_", i)
  assign(af_hos_1, st_intersection(get(buff), LIHTC_Units))
  
  af_hos_2 <- paste0("af_hos_2_st_", i)
  assign(af_hos_2, st_intersection(get(buff), SBF_LRAH_04072020))
  
  if (nrow(get(af_hos_1)) == 0 & nrow(get(af_hos_2)) == 0){
    
    station$affordable_units_1 <- 0
    station$affordable_units_2 <- 0
    
    station$affordable_units_total <- station$affordable_units_1 + station$affordable_units_2
    station_output <- paste0("Station_", i)  
    assign(station_output, station)
    
  } else if (nrow(get(af_hos_1)) != 0 & nrow(get(af_hos_2)) == 0){
    
    station$affordable_units_1 <- sum(st_drop_geometry(get(af_hos_1) %>% select(Total_Low_)))
    station$affordable_units_2 <- 0
    
    station$affordable_units_total <- station$affordable_units_1 + station$affordable_units_2
    station_output <- paste0("Station_", i)  
    assign(station_output, station)
  } else if (nrow(get(af_hos_1)) == 0 & nrow(get(af_hos_2)) != 0){
    
    station$affordable_units_1 <- 0
    station$affordable_units_2 <- sum(st_drop_geometry(get(af_hos_2) %>% select(LI_Units)))
    
    station$affordable_units_total <- station$affordable_units_1 + station$affordable_units_2
    station_output <- paste0("Station_", i)  
    assign(station_output, station)
  } else{
    station$affordable_units_1 <- sum(st_drop_geometry(get(af_hos_1) %>% select(Total_Low_)))
    
    station$affordable_units_2 <- sum(st_drop_geometry(get(af_hos_2) %>% select(LI_Units)))
    
    station$affordable_units_total <- station$affordable_units_1 + station$affordable_units_2
    station_output <- paste0("Station_", i)  
    assign(station_output, station)
  }
  
}

for (i in Station_IDs) {
  this_station <- paste0("Station_", i)
  assign(this_station, st_drop_geometry(get(this_station)))
}

for_rbind <- ls(pattern = "Station_[1-9]", all.names = FALSE)

station_areas_data <- bind_rows(mget(for_rbind))
View(station_areas_data)

#converting to acres 
station_areas_data$total_area_acres <- station_areas_data$total_area / 43560

station_areas_data$single_family_acres            <- station_areas_data$single_family / 43560
station_areas_data$Multifamily_acres              <- station_areas_data$Multifamily / 43560
station_areas_data$Commercial_Retail_acres        <- station_areas_data$Commercial_Retail / 43560
station_areas_data$Utilities_acres                <- station_areas_data$Utilities / 43560
station_areas_data$Industrial_Manufacturing_acres <- station_areas_data$Industrial_Manufacturing / 43560
station_areas_data$Institutional_acres            <- station_areas_data$Institutional / 43560
station_areas_data$Transportation_acres           <- station_areas_data$Transportation / 43560
station_areas_data$Office_acres                   <- station_areas_data$Office / 43560
station_areas_data$Agriculture_Forestry_acres     <- station_areas_data$Agriculture_Forestry / 43560
station_areas_data$Recreation_Cultural_acres      <- station_areas_data$Recreation_Cultural / 43560
station_areas_data$Vacant_Undeveloped_acres       <- station_areas_data$Vacant_Undeveloped / 43560

setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/Files_for_Kristen")
write.csv(station_areas_data, "Station_Area_Summaries_v2.csv" )
