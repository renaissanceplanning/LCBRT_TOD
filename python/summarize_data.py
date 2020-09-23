import arcpy
import pandas as pd
from os import path
import numpy as np

arcpy.env.overwriteOutput = True

# Use groupings
RES = ["SF", "MF"]
NRES = ["Ret", "Ind", "Off"]
HOTEL = ["Hot"]
UNTRACKED = ["Oth"]
USES = RES + NRES + HOTEL + UNTRACKED

# share values
shares = {"SF": 1800, "MF": 1200, "Ret": 500, "Ind": 800, "Off": 400, "Hot": 500}


# support function
def genFieldList(suffix, measure="SF", include_untracked=True):
    """
    Generates a list of fields based on use groupings with the form:
    `{UseGroup}_SF_{suffix}`, recording the square footage (SF) for each
    use grouping for a time frame indicated by the suffix.
    """
    global USES, UNTRACKED
    if include_untracked:
        return ["{}_{}_{}".format(use, measure, suffix) for use in USES]
    else:
        return [
            "{}_{}_{}".format(use, measure, suffix)
            for use in USES
            if use not in UNTRACKED
        ]


# workspaces
scenario_gdb = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\WE_Fair\WE_Fair_scenario.gdb"
source_gdb = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\LCBRT_data.gdb"
summary_wkspc = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\WE_Fair"

# field lists
expi_flds = genFieldList(suffix="ExPi", include_untracked=False)
totcap_flds = genFieldList(suffix="TotCap", include_untracked=False)
alloc_flds = genFieldList(suffix="alloc", include_untracked=False)
buildout_flds = genFieldList(suffix="2040", include_untracked=False)

# datasets
parcels = path.join(scenario_gdb, "parcels")
pid = "ParclID"
p_fields = [pid, "seg_num"] + expi_flds + totcap_flds + alloc_flds

taz = path.join(source_gdb, "corridor_segments_byTAZ")
tid = "Big_TAZ"

segments = path.join(source_gdb, "corridor_segments")
sid = "SegmentNum"


# pth, gdb = path.split(summary_gdb)
# if arcpy.Exists(summary_gdb):
#     arcpy.Delete_management(in_data=summary_gdb)
#
# arcpy.CreateFileGDB_management(out_folder_path=path, out_name=gdb)

def generate_summaries(suit_fc, suit_id, suit_fields, taz_fc, taz_id, seg_id)
    # setup field lists
    expi_flds = genFieldList(suffix="ExPi", include_untracked=False)
    totcap_flds = genFieldList(suffix="TotCap", include_untracked=False)
    alloc_flds = genFieldList(suffix="alloc", include_untracked=False)
    buildout_flds = genFieldList(suffix="2040", include_untracked=False)
    
    pwTAZ = arcpy.SpatialJoin_analysis(
        suti_fc, taz_fc, "in_memory\parcels_wTAZ", match_option="INTERSECT"
    )

    p_df = pd.DataFrame(
        arcpy.da.TableToNumPyArray(
            in_table=pwTAZ, field_names=suit_fields + [taz_id], null_value=0.0
        )
    ).set_index(suit_id)

    seg_summaries = p_df.groupby(seg_id).sum()
    seg_summaries.drop(tid, axis=1, inplace=True)
    for expi_fld, alloc_fld, buildout_fld in zip(expi_flds, alloc_flds, buildout_flds):
        seg_summaries[buildout_fld] = seg_summaries[expi_fld] + seg_summaries[alloc_fld]

    seg_summaries["RES"] = (seg_summaries[buildout_flds[0]] / shares["SF"]) + (
        seg_summaries[buildout_flds[1]] / shares["MF"]
    )
    seg_summaries["JOBS"] = (
        (seg_summaries[buildout_flds[2]] / shares["Ret"])
        + (seg_summaries[buildout_flds[3]] / shares["Ind"])
        + (seg_summaries[buildout_flds[4]] / shares["Off"])
        + (seg_summaries[buildout_flds[5]] / shares["Hot"])
    )

    taz_summaries = p_df.groupby(tid).sum()
    taz_summaries.drop("seg_num", axis=1, inplace=True)
    for expi_fld, alloc_fld, buildout_fld in zip(expi_flds, alloc_flds, buildout_flds):
        taz_summaries[buildout_fld] = taz_summaries[expi_fld] + taz_summaries[alloc_fld]
    taz_summaries["RES"] = (taz_summaries[buildout_flds[0]] / shares["SF"]) + (
        taz_summaries[buildout_flds[1]] / shares["MF"]
    )
    taz_summaries["JOBS"] = (
        (taz_summaries[buildout_flds[2]] / shares["Ret"])
        + (taz_summaries[buildout_flds[3]] / shares["Ind"])
        + (taz_summaries[buildout_flds[4]] / shares["Off"])
    )  # + (taz_summaries[buildout_flds[5]] / shares['Hot'])


    # write out tables
    taz_summaries.to_csv(path.join(summary_wkspc, "taz_summary.csv"))
    seg_summaries.to_csv(path.join(summary_wkspc, "seg_summary.csv"))

# seg_sum_tbl = path.join(summary_gdb, 'segment_summaries')
# out_array = np.array(np.rec.fromrecords(seg_summaries.values))
# names = seg_summaries.dtypes.index.tolist()
# out_array.dtype.names = tuple(names)
# arcpy.da.NumPyArrayToTable(out_array, seg_sum_tbl)
#
# taz_sum_tbl = path.join(summary_gdb, 'taz_summaries')
# out_array = np.array(np.rec.fromrecords(taz_summaries.values))
# names = taz_summaries.dtypes.index.tolist()
# out_array.dtype.names = tuple(names)
# arcpy.da.NumPyArrayToTable(out_array, taz_sum_tbl)
