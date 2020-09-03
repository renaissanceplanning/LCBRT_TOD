"""
LC suitability
inputs:
    in_suit_fc - polygon layer to calculate suitability
    id_field - unique ID field of suitability fc
    is_do_field - field identifying Dev Op site
    do_prop_field - field identifying proportion of Dev Op site available for dev
    acres_field - field containing area in acres of each polygon
    seg_id_field - field identifying which segment a suitability polygon is in
    lu_field - field identifying land use of a suitability polygon
    pipe_field - field identifying whether a suitability polygon is in the pipeline or not
    stations - point layer identifying station locations
    station_buffers - polygon layer defining station areas (walkshed or simple buffer)
    weights - dictionary of weights for each suitability constraint
    out_gdb - output geodatabase to write suitability table and suitability feature class with tot_suit appended
    excl_lu - list of land uses to ignore in suitability analysis
    stations_wc - SQL statment to generate optional scenario suitabilities
"""
import arcpy
import numpy as np
import pandas as pd
import csv
from os import path


def miles_to_feet(miles):
    return miles * 5280


def suit_select_by_overlap(
    in_layer, select_features, overlap_type, df, id_field, search_dist=None
):
    # -- intersect layers and get parcel ids
    arcpy.SelectLayerByLocation_management(
        in_layer=in_layer,
        overlap_type=overlap_type,
        select_features=select_features,
        search_distance=search_dist,
    )
    ids = arcpy.da.TableToNumPyArray(in_table=in_layer, field_names=id_field)[id_field]
    # -- select df records by ids to assign values
    filt = np.in1d(ar1=df[id_field], ar2=ids)
    return filt


def generate_suitability(
    in_suit_fc,
    id_field,
    is_do_field,
    do_prop_field,
    acres_field,
    seg_id_field,
    lu_field,
    pipe_field,
    stations,
    station_buffers,
    weights,
    out_gdb,
    excl_lu=[],
    stations_wc=None,
):
    print "Building Suitability table..."
    # read in suitability shapes (tesselation or other (ie..parcels) to gdb
    suit_fc_name, ext = path.splitext(path.split(in_suit_fc)[1])
    suit_fc = arcpy.FeatureClassToFeatureClass_conversion(
        in_features=in_suit_fc, out_path=out_gdb, out_name=suit_fc_name,
    )
    arcpy.AddIndex_management(
        in_table=suit_fc, fields=[id_field], index_name="ID_IDX",
    )
    # Dump the table to a data frame
    fields = [
        id_field,
        is_do_field,
        do_prop_field,
        acres_field,
        seg_id_field,
        lu_field,
        pipe_field,
    ]
    df = pd.DataFrame(arcpy.da.TableToNumPyArray(suit_fc, fields))
    df[id_field] = df[id_field].astype(str)

    # Calc suit components
    df["suit_DO"] = df[is_do_field] * weights["in_DO"]
    df["suit_vac"] = np.select(
        [df[lu_field] == "Vacant/Undeveloped"], [weights["is_vacant"]], 0.0
    )
    # -- dev area
    df["base_area"] = df[acres_field] * np.select(
        [df[is_do_field] == 1], [df[do_prop_field]], 1.0
    )
    df["loss_factor"] = 0.5 + (0.4 * np.exp(-0.077 * df.base_area))
    df["dev_area"] = df.base_area * df.loss_factor
    max_devs = df[[seg_id_field, "dev_area"]].groupby(seg_id_field).max()
    # -- standardize dev area
    df["seg_max"] = df.merge(
        max_devs, how="left", left_on=seg_id_field, right_index=True
    )["dev_area_y"]
    df["dev_std"] = df.dev_area / df.seg_max
    df["suit_dev"] = df.dev_std * weights["dev_size"]

    # Add walk suit
    # -- make layers
    suit_fl = arcpy.MakeFeatureLayer_management(
        in_features=in_suit_fc, out_layer="suit_fl"
    )
    buff_fl = arcpy.MakeFeatureLayer_management(
        in_features=station_buffers, out_layer="buffers"
    )
    stations_fl = arcpy.MakeFeatureLayer_management(
        in_features=stations, out_layer="stations", where_clause=stations_wc
    )
    # -- filter polygons matching overlap and update table
    walk_filt = suit_select_by_overlap(
        in_layer=suit_fl,
        select_features=buff_fl,
        df=df,
        overlap_type="INTERSECT",
        id_field=id_field,
    )
    in_station_filt = suit_select_by_overlap(
        in_layer=suit_fl,
        select_features=stations_fl,
        df=df,
        overlap_type="WITHIN_A_DISTANCE",
        id_field=id_field,
        search_dist=miles_to_feet(0.5),
    )
    df["walk_suit"] = np.select(
        condlist=[walk_filt], choicelist=[weights["in_walkshed"]], default=0.0
    )
    df["in_station"] = np.select(
        condlist=[in_station_filt], choicelist=[weights["in_TOD"]], default=0.0
    )
    # -- clean up by deleting the layers
    arcpy.Delete_management(suit_fl)
    arcpy.Delete_management(stations_fl)
    arcpy.Delete_management(buff_fl)

    # Calc total suit
    suit_fields = ["suit_DO", "suit_vac", "suit_dev", "walk_suit", "in_station"]
    df["raw_suit"] = df[suit_fields].sum(axis=1)

    # zero out SF res/rec/cultural/transp/utilities (unless DO)
    if excl_lu:
        exclusions = pd.concat([df[lu_field] == lu for lu in excl_lu], axis=1)
        exclusions["any_excl"] = np.any(exclusions, axis=1)
        df["lu_include"] = np.select([exclusions.any_excl], [0.0], 1.0)
    else:
        df["lu_include"] = 1.0

    # zero out sites already in development pipeline
    df["pipe_include"] = np.select([df[pipe_field] == 1], [0.0], 1.0)

    # Calc total suit removing parcels deemed ineligible by LU and Pipeline dev
    # The parcel has no pipeline dev AND (is either a DO site OR a LU that could develop)
    _include_ = np.logical_and(
        df["pipe_include"] == 1,
        np.logical_or(
            df[is_do_field] == 1,
            df["lu_include"] == 1
        )
    )   
    df["full_include"] = np.select([_include_], [1.0], 0.0)
    df["tot_suit"] = df.raw_suit * df.full_include
    # df["tot_suit"] = (
    #     #df[[is_do_field, "lu_include", "pipe_include"]].max(axis=1) * df.raw_suit
        
    #     df[["lu_include", "pipe_include"]].min(axis=1) * df.raw_suit
    # )

    # dump suit table to gdb ##NOTE: this will fail on rerun as the NumPyArrayToTable cant overwrite existing tbl
    suit_tbl = path.join(out_gdb, "suitability")
    out_array = np.array(np.rec.fromrecords(df.values))
    names = df.dtypes.index.tolist()
    out_array.dtype.names = tuple(names)
    arcpy.da.NumPyArrayToTable(out_array, suit_tbl)
    print "...Suitability table generated here: {}".format(suit_tbl)

    # join suit score to suit fc
    suit_df = df[[id_field, "tot_suit"]]
    suit_arr = np.array(
        np.rec.fromrecords(suit_df.values, names=suit_df.dtypes.index.tolist())
    )
    arcpy.da.ExtendTable(
        in_table=suit_fc,
        table_match_field=id_field,
        in_array=suit_arr,
        array_match_field=id_field,
        append_only=False,
    )
    print "...'tot_suit' added to ##-{}-## layer for use in TOD tools".format(suit_fc)
    return suit_fc, suit_tbl


# if __name__ == "__main__":
#     arcpy.env.overwriteOutput = True
#
#     in_suit_fc = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\Parcels.shp"
#     stations = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\Stations_LCRT_BRT_Recommended_andAlternative_20200814.shp"
#     stations_wc = arcpy.AddFieldDelimiters(stations, "Fair_WE") + " <> 'NA'"
#     station_buffers = (
#         r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\QuarterMile_Walk_Arc.shp"
#     )
#     id_field = "ParclID"
#     is_do_field = "DO_Site"
#     do_prop_field = "DOSProp"
#     acres_field = "Area_AC"
#     seg_id_field = "seg_num"
#     lu_field = "LandUse"
#     pipe_field = "in_pipe"
#     excl_lu = ["Recreation/Cultural", "Single-family", "Transportation", "Utilities"]
#     weights = {"in_DO": 0.6,
#                "is_vacant": 0.15,
#                "in_TOD": 0.05,
#                "in_walkshed": 0.1,
#                "dev_size": 0.1}  # (IS DOS, IsVacant, InTOD, InWalkShed, size)
#     # weights = [0.60, 0.30, 0.10, 0.20]  # DO, IsVacant, dev arae, qm walk buffer IS DOS, IsVacant, InTOD, InWalkShed, size
#     out_gdb = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\testRun\temp.gdb"
#     # out_table = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\initial_suitability.dbf"
#
#     generate_suitability(
#         in_suit_fc,
#         id_field,
#         is_do_field,
#         do_prop_field,
#         acres_field,
#         seg_id_field,
#         lu_field,
#         pipe_field,
#         stations,
#         station_buffers,
#         weights,
#         out_gdb,
#         excl_lu=[],
#         stations_wc=None,
#     )
