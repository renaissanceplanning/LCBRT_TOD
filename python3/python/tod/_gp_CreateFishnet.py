#create fishnet

import arcpy
from . import HandyGP


if __name__ == '__main__':
    in_features = arcpy.GetParameterAsText(0) # feature class
    where_clause = arcpy.GetParameterAsText(1) # SQL Expression, from in_features, optional
    output_fc = arcpy.GetParameterAsText(2) # feature class, output
    cell_width = arcpy.GetParameter(3) # double, optional
    cell_height = arcpy.GetParameter(4) # double, optional
    number_of_rows = arcpy.GetParameter(5) # integer, optional
    number_of_columns = arcpy.GetParameter(6) # integer, optional
    geometry_type = arcpy.GetParameterAsText(7) # string, [POLYGON, POLYLINE]
    create_label_points = arcpy.GetParameter(8) # boolean, optional
    sr = arcpy.GetParameter(9) # spatial reference

    HandyGP.createFishnet(in_features, output_fc, cell_width=cell_width,
                          cell_height=cell_height, number_of_rows=number_of_rows,
                          number_of_columns=number_of_columns,
                          geometry_type=geometry_type, where_clause=where_clause,
                          sr=sr, create_label_points=create_label_points)
    
