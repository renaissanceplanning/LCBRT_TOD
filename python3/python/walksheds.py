import arcpy
from os import path


def generate_walksheds(stations, walk_net, imp_field, cost, out_gdb,
                       stations_wc=None):
    print('building walksheds for suitability and TOD analysis')
    # Create the network problem
    sa_layer = arcpy.MakeServiceAreaLayer_na(
        in_network_dataset=walk_net, out_network_analysis_layer="service_area",
        impedance_attribute=imp_field, travel_from_to="TRAVEL_FROM",
        default_break_values=cost, polygon_type="SIMPLE_POLYS",
        merge="NO_OVERLAP", nesting_type="DISKS", line_type="NO_LINES")

    # Add locations
    stations_fl = arcpy.MakeFeatureLayer_management(
        in_features=stations, where_clause=stations_wc)

    arcpy.AddLocations_na(in_network_analysis_layer="service_area",
                          sub_layer="Facilities", in_table=stations_fl,
                          field_mappings="Name Name #",
                          search_tolerance="5000 feet", )

    # Solve the problem
    arcpy.Solve_na(in_network_analysis_layer="service_area")

    # Export the result
    arcpy.FeatureClassToFeatureClass_conversion(
        in_features="service_area\\polygons",
        out_path=out_gdb,
        out_name='walksheds')

    # Cleanup
    arcpy.Delete_management(sa_layer)
    arcpy.Delete_management(stations_fl)
    print("...walksheds created here: {}".format(path.join(out_gdb, 'walksheds')))
    return path.join(out_gdb, 'walksheds')


def create_gdb(folder, gdb_name):
    if gdb_name[-4:] != ".gdb":
        gdb_name = gdb_name + ".gdb"
    gdb_path = path.join(folder, gdb_name)
    if not arcpy.Exists(gdb_path):
        arcpy.CreateFileGDB_management(folder, gdb_name)
    return gdb_path


if __name__ == "__main__":
    stations = r"C:\Users\V_RPG\OneDrive - Renaissance Planning Group\SHARE\LCBRT_DATA\LCBRT_data.gdb\stations_LCRT_BRT_scenarios_20200814"
    walk_net = r"C:\Users\V_RPG\OneDrive - Renaissance Planning Group\SHARE\LCBRT_DATA\LCBRT_data.gdb\network\walk_network_ND"
    imp_field = "Length"
    cost = "1320"
    stations_wc = arcpy.AddFieldDelimiters(stations, "Fair_WE") + " <> 'NA'"
    out_ws = r"C:\Users\V_RPG\OneDrive - Renaissance Planning Group\SHARE\LCBRT_DATA\temp\scenarios\Fair_WE"
    out_gdb = r"D:\Users\DE7\Documents\temp\TOD_TestRun\TOD_TEST_CR.gdb"
    # out_file = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\Fair_WE\walksheds.shp"

    generate_walksheds(stations, walk_net, imp_field, cost, out_gdb,
                       stations_wc=None)
