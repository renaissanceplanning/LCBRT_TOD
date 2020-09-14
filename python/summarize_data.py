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
shares = {"SF": 1800,
          "MF": 1200,
          "Ret": 500,
          "Ind": 800,
          "Off": 400,
          "Hot": 500}


# support function
def genFieldList(suffix, measure='SF', include_untracked=True):
    """
    Generates a list of fields based on use groupings with the form:
    `{UseGroup}_SF_{suffix}`, recording the square footage (SF) for each
    use grouping for a time frame indicated by the suffix.
    """
    global USES, UNTRACKED
    if include_untracked:
        return ["{}_{}_{}".format(use, measure, suffix) for use in USES]
    else:
        return ["{}_{}_{}".format(use, measure, suffix) for use in USES if use not in UNTRACKED]


# workspaces
scenario_gdb = r'K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\WE_Sum\WE_Sum_scenario.gdb'
source_gdb = r'K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\LCBRT_data.gdb'
summary_wkspc = r'K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\WE_Sum'

# datasets
parcels = path.join(scenario_gdb, 'parcels')
pid = 'ParclID'
expi_flds = genFieldList(suffix='ExPi', include_untracked=False)
p_fields = [pid] + expi_flds

taz = path.join(source_gdb, 'corridor_segments_byTAZ')
tid = 'Big_TAZ'

segments = path.join(source_gdb, 'corridor_segments')
sid = 'SegmentNum'

capacities = path.join(scenario_gdb, 'capacity')
cid = pid
totcap_flds = genFieldList(suffix='TotCap', include_untracked=False)
c_fields = [cid] + totcap_flds

allocation = path.join(scenario_gdb, 'allocation')
aid = pid
alloc_flds = genFieldList(suffix='alloc', include_untracked=False)
a_fields = [aid, 'seg_num'] + alloc_flds

buildout_flds = genFieldList(suffix="2040", include_untracked=False)
'''
work to do:
1) sj parcels to TAZ to get TAZID with parcel
2) join cap and allocation to parcels
3) summarize by Segment
4) summariZe by TAZ
'''
# pth, gdb = path.split(summary_gdb)
# if arcpy.Exists(summary_gdb):
#     arcpy.Delete_management(in_data=summary_gdb)
#
# arcpy.CreateFileGDB_management(out_folder_path=path, out_name=gdb)

p_fl = arcpy.MakeFeatureLayer_management(in_features=parcels, out_layer='parcels_fl')
pwTAZ = arcpy.SpatialJoin_analysis(parcels, taz, 'in_memory\parcels_wTAZ', match_option="INTERSECT")

p_df = pd.DataFrame(
    arcpy.da.TableToNumPyArray(
        in_table=pwTAZ, field_names=p_fields + [tid], null_value=0.0)).set_index(pid)
cap_df = pd.DataFrame(
    arcpy.da.TableToNumPyArray(
        in_table=capacities, field_names=c_fields, null_value=0.0)).set_index(cid)
alloc_df = pd.DataFrame(
    arcpy.da.TableToNumPyArray(
        in_table=allocation, field_names=a_fields, null_value=0.0)).set_index(aid)

# join all tables together and summarize
joined = (p_df.join(cap_df)).join(alloc_df)
seg_summaries = joined.groupby('seg_num').sum()
seg_summaries.drop(tid, axis=1, inplace=True)
for expi_fld, alloc_fld, buildout_fld in zip(expi_flds, alloc_flds, buildout_flds):
    seg_summaries[buildout_fld] = seg_summaries[expi_fld] + seg_summaries[alloc_fld]

seg_summaries['RES'] = (seg_summaries[buildout_flds[0]] / shares['SF']) + (seg_summaries[buildout_flds[1]] / shares['MF'])
seg_summaries['JOBS'] = (seg_summaries[buildout_flds[2]] / shares['Ret']) + (seg_summaries[buildout_flds[3]] / shares['Ind']) + (seg_summaries[buildout_flds[4]] / shares['Off']) + (seg_summaries[buildout_flds[5]] / shares['Hot'])

taz_summaries = joined.groupby(tid).sum()
taz_summaries.drop('seg_num', axis=1, inplace=True)
for expi_fld, alloc_fld, buildout_fld in zip(expi_flds, alloc_flds, buildout_flds):
    taz_summaries[buildout_fld] = taz_summaries[expi_fld] + taz_summaries[alloc_fld]
taz_summaries['RES'] = (taz_summaries[buildout_flds[0]] / shares['SF']) + (taz_summaries[buildout_flds[1]] / shares['MF'])
taz_summaries['JOBS'] = (taz_summaries[buildout_flds[2]] / shares['Ret']) + (taz_summaries[buildout_flds[3]] / shares['Ind']) + (taz_summaries[buildout_flds[4]] / shares['Off']) + (taz_summaries[buildout_flds[5]] / shares['Hot'])


# write out tables
taz_summaries.to_csv(path.join(summary_wkspc, 'taz_summary.csv'))
seg_summaries.to_csv(path.join(summary_wkspc, 'seg_summary.csv'))

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
