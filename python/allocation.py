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
suit_field = "tot_suit"
suit_ex_fields = [
    "Ret_SF_Ex",
    "Ind_SF_Ex",
    "Off_SF_Ex",
    "MF_SF_Ex",
    "SF_SF_Ex",
]  ## assuming this is the TOD type embellishments inside station area and areas outside TOD use values calced for Vacant

# dev_area_tbl data
dev_areas_tbl = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\scenarios\WE_Sum\WE_Sum_scenario.gdb\parcels"
dev_areas_fields = [
    "Ret_SF_Adj",
    "Ind_SF_Adj",
    "Off_SF_Adj",
    "MF_SF_Adj",
    "SF_SF_Adj",
    "Hot_SF_Adj",
]
control_tbl = (
    r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\tables\control_totals.csv"
)
control_fields = ["segment", "activity", "demand", "known", "net"]

suit_fc_seg_field = "seg_num"  # TODO: need to know what columns will hold the capacity for each activity
control_seg_attr = "segment"


def allocate(
    suit_fc,
    suit_fc_id_field,
    suit_field,
    suit_fc_seg_field,
    suit_cap_fields,
    control_tbl,
    control_fields,
):
    """

    :param suit_fc: parcel layer with parcel level change capacity values in sqft
    :param suit_fc_id_field: unique id field
    :param suit_field: suitability ranking by parcel
    :param suit_fc_seg_field: segment identifier
    :param suit_cap_fields: field containing capacity for activity by parcel
    :param control_tbl:
    :param control_fields:
    :return:
    """
    # read control totals to dictionary
    control_dict = (
        pd.read_csv(control_tbl)
        .groupby(control_seg_attr)
        .apply(lambda x: x.to_dict(orient="list"))
        .to_dict()
    )
    # set up dataframe to read values into loop for tracking count, sorted by suitability
    field_names = [suit_fc_id_field, suit_field, suit_fc_seg_field] + suit_ex_fields
    suit_df = pd.DataFrame(
        arcpy.da.TableToNumPyArray(suit_fc, field_names)
    ).sort_values(by=suit_field, ascending=False, inplace=True)
    # dev_areas_df = pd.DataFrame(arcpy.da.TableToNumPyArray(dev_areas_tbl, [suit_fc_id_field] + dev_areas_fields))
    # suit_df = pd.concat([suit_df, dev_areas_df], axis=1, join="inner")
    ind_sqft_cap, off_sqft_cap, mfr_sqft_cap, sfr_sqft_cap, hot_sqft_cap, ret_sqft_cap = suit_cap_fields
    # loop over segments and create control dictionary
    for segment, group in suit_df.groupby(suit_fc_seg_field):
        seg_controls = dict(zip(control_dict[segment]['activity'], control_dict[segment]['net']))
        segment_counter = Counter(seg_controls)
        # iterate over parcel rows
        for index, row in group.iterrows():
            parcel_count = Counter({
                'Industrial': row[ind_sqft_cap],
                'Office': row[off_sqft_cap],
                'Multifamily': row[mfr_sqft_cap],
                'Single Family': row[sfr_sqft_cap],
                'Hospitality': row[hot_sqft_cap],
                'Retail': row[ret_sqft_cap]
            })

            segment_counter.subtract(parcel_count)
            # check to see if segment counter is at 0 for all activites,
            #   move to next segment
            if all(value == 0 for value in segment_counter.values()):
                break


# if __name__ == "__main__":
