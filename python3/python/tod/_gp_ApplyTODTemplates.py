import arcpy
from . import TOD

if __name__ == "__main__":
    in_gdb = arcpy.GetParameterAsText(0)  # workspace, local database
    fishnet_fc = arcpy.GetParameterAsText(1)  # feature class, polygons
    fishnet_id = arcpy.GetParameterAsText(
        2
    )  # field, from fishnet, auto search for CELL_ID
    fishnet_suitability_field = arcpy.GetParameterAsText(
        3
    )  # field, from fishnet, numeric
    fishnet_where_clause = arcpy.GetParameterAsText(
        4
    )  # expression, from fishnet, optional
    technology_name = arcpy.GetParameterAsText(5)  # string, from technologies table
    sr = arcpy.GetParameterAsText(6)  # spatial reference, optional
    network_dataset = arcpy.GetParameterAsText(7)  # network dataset, optional
    impedance_attribute = arcpy.GetParameterAsText(
        8
    )  # string, from network_dataset, optional
    restrictions = arcpy.GetParameterAsText(
        9
    )  # string, multivalue, form network_dataset, optional
    preset_station_areas = arcpy.GetParameter(10)  # boolean, optional
    preset_field = arcpy.GetParameterAsText(11)  # field, from fishnet_fc
    weight_by_area = arcpy.GetParameter(12)  # boolean
    share_threshold = arcpy.GetParameter(13)  # double

    if network_dataset:
        if not impedance_attribute:
            raise ValueError(
                "an impedance attribute must be specified when using a network dataset"
            )
        else:
            impedance_attribute = impedance_attribute.split(",")[0]
    restrictions = restrictions.split(";")
    if not restrictions:
        restrictions = None

    if not preset_station_areas:
        preset_field = None

    if not fishnet_where_clause:
        fishnet_where_clause = ""

    TOD.applyTODTemplates(
        in_gdb,
        fishnet_fc,
        fishnet_id,
        technology_name,
        fishnet_suitability_field=fishnet_suitability_field,
        fishnet_where_clause=fishnet_where_clause,
        sr=sr,
        network_dataset=network_dataset,
        impedance_attribute=impedance_attribute,
        restrictions=restrictions,
        preset_stations_field=preset_field,
        weight_by_area=weight_by_area,
        share_threshold=share_threshold,
    )
