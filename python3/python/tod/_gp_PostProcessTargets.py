import arcpy
import numpy as np
import pandas as pd
from . import TOD


dev_areas_table = arcpy.GetParameterAsText(0) #table view
id_field = arcpy.GetParameterAsText(1) # field, from dev_areas_table
station_area_field = arcpy.GetParameterAsText(2) #field, from dev_areas_table
existing_hh_field = arcpy.GetParameterAsText(3) #field, from dev_areas_table, numeric
existing_job_field = arcpy.GetParameterAsText(4) #field, from dev_areas_table, numeric
existing_hotel_field = arcpy.GetParameterAsText(5) #field, from dev_areas_table, numeric
target_hh_field = arcpy.GetParameterAsText(6) #field, from dev_areas_table, numeric
target_job_field = arcpy.GetParameterAsText(7) #field, from dev_areas_table, numeric    
target_hotel_field = arcpy.GetParameterAsText(8) #field, from dev_areas_table, numeric
where_clause = arcpy.GetParameterAsText(9) #SQL expression, from dev_areas_table
out_table = arcpy.GetParameterAsText(10) #table, output




TOD.adjustTargetsBasedOnExisting(dev_areas_table, id_field, station_area_field,
                              existing_hh_field, target_hh_field,
                              existing_job_field, target_job_field,
                              existing_hotel_field, target_hotel_field, out_table,
                              where_clause=where_clause)
