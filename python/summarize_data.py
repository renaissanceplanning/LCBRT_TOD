import arcpy
import pandas as pd
from os import path
import numpy as np

arcpy.env.overwriteOutput = True

# workspaces
scenario_gdb = r'K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\WE_Sum\WE_Sum_scenario.gdb'
source_gdb = r'K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\LCBRT_data.gdb'
summary_gdb = r'K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\WE_Sum\summaries.gdb'

# datasets
parcels = path.join(scenario_gdb, 'parcels')
pid = 'ParclID'
p_fields = [pid] + ['SF_SF_ExPi', 'MF_SF_ExPi', 'Ret_SF_ExPi',
                  'Ind_SF_ExPi', 'Off_SF_ExPi', 'Hot_SF_ExPi']

taz = path.join(source_gdb, 'corridor_segments_byTAZ')
tid = 'Big_TAZ'

segments = path.join(source_gdb, 'corridor_segments')
sid = 'SegmentNum'

capacities = path.join(scenario_gdb, 'capacity')
cid = pid
c_fields = [cid] + ['SF_SF_TotCap', 'MF_SF_TotCap', 'Ret_SF_TotCap',
                    'Ind_SF_TotCap', 'Off_SF_TotCap', 'Hot_SF_TotCap']

allocation = path.join(scenario_gdb, 'allocation')
aid = pid
a_fields = [aid] + ['SF_SF_alloc', 'MF_SF_alloc', 'Ret_SF_alloc',
                    'Ind_SF_alloc', 'Off_SF_alloc', 'Hot_SF_alloc','seg_num']


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
pwTAZ = arcpy.SpatialJoin_analysis(parcels, taz, path.join(summary_gdb, 'parcels_wTAZ'), match_option="INTERSECT")

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
seg_summaries.drop(tid, axis=1)
taz_summaries = joined.groupby(tid).sum()
taz_summaries.drop('seg_num', axis=1)

# write out tables
pth, gdb = path.split(summary_gdb)
taz_summaries.to_csv(path.join(pth, 'taz_summary.csv'))
seg_summaries.to_csv(path.join(pth, 'seg_summary.csv'))

seg_sum_tbl = path.join(summary_gdb, 'segment_summaries')
out_array = np.array(np.rec.fromrecords(seg_summaries.values))
names = seg_summaries.dtypes.index.tolist()
out_array.dtype.names = tuple(names)
arcpy.da.NumPyArrayToTable(out_array, seg_sum_tbl)

taz_sum_tbl = path.join(summary_gdb, 'taz_summaries')
out_array = np.array(np.rec.fromrecords(taz_summaries.values))
names = taz_summaries.dtypes.index.tolist()
out_array.dtype.names = tuple(names)
arcpy.da.NumPyArrayToTable(out_array, taz_sum_tbl)