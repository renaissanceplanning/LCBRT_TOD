library(tidyverse)
library(sf)
library(tmap)

Needed_cols <- names(read_sf("K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/temp/BCD_ProposedExistingUnderconstruction_pipelineDevelopment_points.shp"))

# New Points
setwd("K:/Projects/BCDCOG/Features/Files_For_RDB/SHP_Reprojected")

Hospitality <- read_sf("Hospitality_New.shp")
Industrial  <- read_sf("Industrial_New.shp")
MF          <- read_sf("MF_New.shp")
Office      <- read_sf("Office_New.shp")

## Extracting Necessary Columns

Hospitality_Filtered =
  Hospitality %>%
  transmute(Property_A  = Hotel_Name  ,                         
            Property_N  = Address     ,                      
            Building_S  = Status      ,                     
            RBA         = ROOMS * 500 ,                    
            City        = City        ,                   
            State       = State       ,                    
            Zip         = NA          ,                 
            County_Nam  = NA          ,                
            Year_Built  = CoStar_Yea  ,                         
            Latitude    = Latitude    ,                      
            Longitude   = Longitude   ,                        
            PropertyID  = NA          ,               
            PropertyTy  = "Hospitality New"        ,                   
            Tenancy     = NA          ,                 
            Zoning      = NA          ,                
            Property_1  = Type        ,                  
            )

Industrial_Filtered =
  Industrial %>%
  transmute(Property_A  = NAME       ,                         
            Property_N  = ARC_Addres  ,                      
            Building_S  = STATUS_1    ,                     
            RBA         = RBA         ,                    
            City        = ARC_City    ,                   
            State       = ARC_Region  ,                    
            Zip         = ARC_Postal  ,                 
            County_Nam  = ARC_Subreg  ,                
            Year_Built  = YRBUILT     ,                         
            Latitude    = Y           ,                      
            Longitude   = X           ,                        
            PropertyID  = NA          ,               
            PropertyTy  = "Industrial New"      ,                   
            Tenancy     = TENANCY     ,                 
            Zoning      = SECONDARY   ,                
            Property_1  = Type                          
            )

MF_Filtered =
  MF %>%
  transmute(Property_A  = NAME       ,                         
            Property_N  = ARC_Addres  ,                      
            Building_S  = STATUS_1    ,                     
            RBA         = RBA         ,                    
            City        = ARC_City    ,                   
            State       = ARC_Region  ,                    
            Zip         = ARC_Postal  ,                 
            County_Nam  = ARC_Subreg  ,                
            Year_Built  = YRBUILT     ,                         
            Latitude    = Y           ,                      
            Longitude   = X           ,                        
            PropertyID  = NA          ,               
            PropertyTy  = "Multi-Family New",                   
            Tenancy     = "Multi"     ,                 
            Zoning      = "Multi"   ,                
            Property_1  = TYPE_1                          
            )

Office_Filtered =
  Office %>%
  transmute(Property_A  = Property_A  ,                         
            Property_N  = Leasing_Co  ,                      
            Building_S  = Building_S  ,                     
            RBA         = RBA         ,                    
            City        = City        ,                   
            State       = State       ,                    
            Zip         = Zip         ,                 
            County_Nam  = County_Nam  ,                
            Year_Built  = Year_Built  ,                         
            Latitude    = Latitude    ,                      
            Longitude   = Longitude   ,                        
            PropertyID  = NA          ,               
            PropertyTy  = "Office New",                   
            Tenancy     = Tenancy     ,                 
            Zoning      = Secondary   ,                
            Property_1  = TYPE_1                          
  )

## adding the new spreadsheet
NEW_Devs <- openxlsx::read.xlsx("D:/Users/IL7/Documents/Lowcountry_Webmap/SBF_Dev/BCD_2020Existing_08242020.xlsx")
NEW_Devs <- st_as_sf(NEW_Devs, coords = c("Longitude", "Latitude"), crs = 4326, remove = FALSE)

NEW_Devs_Filtered =
  NEW_Devs %>%
  transmute(Property_A  = Property.Address  ,                         
            Property_N  = Property.Name  ,                      
            Building_S  = Building.Status  ,                     
            RBA         = RBA         ,                    
            City        = City        ,                   
            State       = State       ,                    
            Zip         = Zip         ,                 
            County_Nam  = County.Name  ,                
            Year_Built  = Year.Built  ,                         
            Latitude    = Latitude    ,                      
            Longitude   = Longitude   ,                        
            PropertyID  = NA          ,               
            PropertyTy  = paste(PropertyType, "New", sep = " "),                   
            Tenancy     = Tenancy     ,                 
            Zoning      = Zoning   ,                
            Property_1  = Secondary.Type                         
  )

## adding the retail
Retail <- read_sf("D:/Users/IL7/Documents/Lowcountry_Webmap/SBF_Dev/BCD_RetailNew/BCD_RetailNew.shp")


Retail_Filtered =
  Retail %>%
  transmute(Property_A  = Property_A  ,                         
            Property_N  = Property_N  ,                      
            Building_S  = Building_S  ,                     
            RBA         = RBA         ,                    
            City        = City        ,                   
            State       = State       ,                    
            Zip         = Zip         ,                 
            County_Nam  = County_Nam  ,                
            Year_Built  = Year_Built  ,                         
            Latitude    = Latitude    ,                      
            Longitude   = Longitude   ,                        
            PropertyID  = NA          ,               
            PropertyTy  = "Retail New",                   
            Tenancy     = NA     ,                 
            Zoning      = "Commercial"   ,                
            Property_1  = NA                         
  )

my_crs <- st_crs(MF_Filtered)

Retail_Filtered <- st_transform(Retail_Filtered, my_crs)
NEW_Devs_Filtered <- st_transform(NEW_Devs_Filtered, my_crs)

New_Points <- rbind(Hospitality_Filtered, Industrial_Filtered, MF_Filtered, NEW_Devs_Filtered, Office_Filtered, Retail_Filtered)

## adding the pipeline data
Pipeline <- read_sf("D:/Users/IL7/Documents/Lowcountry_Webmap/SBF_Dev/BCD_ProposedUnderConstruction08032020_Costar/BCD_ProposedUnderConstruction08032020_Costar.shp")

Pipeline_Filtered =
  Pipeline %>%
  transmute(Property_A  = PropAddres  ,                         
            Property_N  = PropName  ,                      
            Building_S  = BldngStat  ,                     
            RBA         = RBA         ,                    
            City        = City        ,                   
            State       = State       ,                    
            Zip         = Zip         ,                 
            County_Nam  = County      ,                
            Year_Built  = Year_Built  ,                         
            Latitude    = Latitude    ,                      
            Longitude   = Longitude   ,                        
            PropertyID  = PropertyID  ,               
            PropertyTy  = PropertyTy  ,                   
            Tenancy     = Tenancy     ,                 
            Zoning      = Zoning      ,                
            Property_1  = NA                         
  )

Pipeline_Filtered <- st_transform(Pipeline_Filtered, my_crs)

Pipeline_Filtered$PropertyTy[Pipeline_Filtered$PropertyTy == "Retail (Neighborhood Center)"] <- "Retail"
Pipeline_Filtered$PropertyTy[Pipeline_Filtered$PropertyTy == "Retail (Community Center)"] <- "Retail"
Pipeline_Filtered$PropertyTy[Pipeline_Filtered$PropertyTy == "Retail (Strip Center)"] <- "Retail"

Pipeline_Filtered$PropertyTy <- paste(Pipeline_Filtered$PropertyTy, "Pipeline", sep = " ")
unique(Pipeline_Filtered$PropertyTy)

Pipeline_Filtered$Time_Frame <- "Pipeline"
New_Points$Time_Frame <- "New"

SBF_New_Pipe_Merged <- rbind(Pipeline_Filtered, New_Points)

write_sf(SBF_New_Pipe_Merged, "K:/Projects/BCDCOG/Features/Files_For_RDB/RDB_V3/SBF_New_Pipe_Merged.shp")



