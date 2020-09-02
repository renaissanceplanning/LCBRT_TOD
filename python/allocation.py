import arcpy
import pandas as pd
import numpy as np
from collections import Counter

"""
read in parcels as parcels_df
read in control totals table as control_df
for segment in segments:
    make dict of segment level activities {activity: net total list}
    get parcels in segement and sort by suit_score
    for each parcel:
        allocate to each class according to capacity numbers for Res and non-res
            get parcel capacity per activity
        update dict 
"""
# suitability polygon inputs
suit_fc = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\scenarios\WE_Sum\WE_Sum_scenario.gdb\parcels"
suit_fc_id_field = "ParclID"
suit_field = 'tot_suit'
suit_ex_fields = ["Ret_SF_Ex", "Ind_SF_Ex", "Off_SF_Ex", "MF_SF_Ex", "SF_SF_Ex", "Hot_SF_Ex"]  ## assuming this is the TOD type embellishments inside station area and areas outside TOD use values calced for Vacant

# dev_area_tbl data
dev_areas_tbl = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\scenarios\WE_Sum\WE_Sum_scenario.gdb\parcels"
dev_areas_fields = ["Ret_SF_Adj", "Ind_SF_Adj", "Off_SF_Adj", "MF_SF_Adj", "SF_SF_Adj", "Hot_SF_Adj"]
control_tbl = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\tables\control_totals.csv"
control_fields = ["segment", "activity", "demand", "known", "net"]

suit_fc_seg_field = "seg_num"  # TODO: need to know what columns will hold the capacity for each activity
control_seg_attr = "segment"


def check_count(counter):



def allocate(suit_fc, suit_fc_id_field, suit_field, suit_fc_seg_field, suit_ex_fields,
             dev_areas_tbl, dev_areas_fields,
             control_tbl, control_fields):
    """

    :param suit_fc:
    :param suit_fc_id_field:
    :param suit_field:
    :param suit_fc_seg_field:
    :param suit_ex_fields:
    :param dev_areas_tbl:
    :param dev_areas_fields:
    :param control_tbl:
    :param control_fields:
    :return:
    """
    # read control totals to dictionary
    control_dict = (pd.read_csv(control_tbl)
                    .groupby(control_seg_attr).apply(lambda x: x.to_dict(orient="list")).to_dict())
    # set up dataframe to read values into loop for tracking count
    field_names = [suit_fc_id_field, suit_field, suit_fc_seg_field] + suit_ex_fields
    suit_df = pd.DataFrame(arcpy.da.TableToNumPyArray(suit_fc, field_names))
    dev_areas_df = pd.DataFrame(arcpy.da.TableToNumPyArray(dev_areas_tbl, [suit_fc_id_field] + dev_areas_fields))
    suit_df = pd.concat([suit_df, dev_areas_df], axis=1, join="inner")

    for seg, controls in control_dict.items():
        seg_totals = dict(zip(controls['activity'], controls['net']))
        segment_counter = Counter(seg_totals)
        # loop over each parcel sorted in DESC order and update allocation for parcel
        segment_wc = """{} = {}""".format(arcpy.AddFieldDelimiters(suit_fc, suit_fc_seg_field), seg)

        with arcpy.da.SearchCursor(
                in_table=suit_fl, field_names=field_names,
                where_clause=segment_wc,
                sql_clause=(None, 'ORDER BY {} DESC'.format(suit_field))) as sc:
            for i, row in enumerate(sc):
                ''' use the collection.Counter concept to create a new counter for each parcel that captures
                    each activity --> 'Office', 'Hospitality', 'Single Family', 'Retail', 'Multifamily', 'Industrial'
                    use the new dict to subtract from the segment counter
                    ### - working idea
                    '''
                office_cap, hosp_cap, sfr_cap, retail_cap, mfr_cap, ind_cap,\
                    office_ex, hosp_ex, sfr_ex, retail_ex, mfr_ex, ind_ex = row
                parcel_count = Counter({'Office': office_cap - office_ex,
                                        'Hospitality': hosp_cap - hosp_ex,
                                        'Single Family': sfr_cap - sfr_ex,
                                        'Retail': retail_cap - retail_ex,
                                        'Multifamily': mfr_cap - mfr_ex,
                                        'Industrial': ind_cap - ind_ex})
                segment_counter.subtract(parcel_count)
                # check to see if segment counter is at 0 for all activites,
                #   move to next segment
                if all(value == 0 for value in segment_counter.values()):
                    break




if __name__ == "__main__":
