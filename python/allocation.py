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


def allocate(
    suit_fc,
    suit_fc_id_field,
    suit_field,
    suit_fc_seg_field,
    suit_cap_fields,
    control_tbl,
):
    """

    :param suit_fc: parcel layer with parcel level change capacity values in sqft
    :param suit_fc_id_field: unique id field
    :param suit_field: suitability ranking by parcel
    :param suit_fc_seg_field: segment identifier
    :param suit_cap_fields: fields containing capacity for activity by parcel
    :param filled_cap_fields: fields to hold the count of sqft allocated per parcel
    :param control_tbl: table of control totals for each activity by segment
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
    field_names = [suit_fc_id_field, suit_field, suit_fc_seg_field] + suit_cap_fields
    suit_df = pd.DataFrame(
        arcpy.da.TableToNumPyArray(suit_fc, field_names, null_value=0.0),
    ).set_index(suit_fc_id_field)
    suit_df.sort_values(by=suit_field, ascending=False, inplace=True)

    (ind_sqft_cap, off_sqft_cap,
     mfr_sqft_cap, sfr_sqft_cap,
     hot_sqft_cap, ret_sqft_cap,) = suit_cap_fields

    # create a df to hold output filled parcel capacities
    filled_rows = {}
    # loop over segments and create control dictionary
    for segment, group in suit_df.groupby(suit_fc_seg_field):
        seg_controls = dict(
            zip(control_dict[segment]["activity"], control_dict[segment]["net"])
        )
        # iterate over parcel rows
        for parcel_id, row in group.iterrows():
            new_row = {}
            parcel_count = dict(
                {
                    "Ind": row[ind_sqft_cap],
                    "Off": row[off_sqft_cap],
                    "MF": row[mfr_sqft_cap],
                    "SF": row[sfr_sqft_cap],
                    "Hot": row[hot_sqft_cap],
                    "Ret": row[ret_sqft_cap],
                }
            )
            for act_key in parcel_count.keys():
                filled_att = "{}_SF_{}".format(act_key, "filled")
                segment_act_control = seg_controls[act_key]  # get segment activity control val
                parcel_act_cap = parcel_count[act_key]  # get parcel activity capacity val (ie fill_to_val)
                updated_act_control = (segment_act_control - parcel_act_cap)  # calculate updated control
                # if new control  is negative, reset activity control and parcel allocations
                if updated_act_control < 0:
                    dist = updated_act_control * -1  # determine distance below 0
                    updated_act_control += dist  # add back to updated activity control
                    parcel_act_cap -= dist  # adjust filled activity capacity to reflect dist
                seg_controls[act_key] = updated_act_control  # update activity control to reflect allocation
                new_row[filled_att] = parcel_act_cap
                filled_rows[parcel_id] = new_row
                # # todo add check for all controls = 0 and break
                # if all(value == 0 for value in seg_controls.values()):
                #     break
    # filled_array = np.array(list(filled_rows.items()), dtype=)
    print "done"


if __name__ == "__main__":
    # suitability polygon inputs
    suit_fc = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\scenarios\WE_Sum\WE_Sum_scenario.gdb\parcels"
    suit_fc_id_field = "ParclID"
    suit_fc_seg_field = 'seg_num'
    suit_field = "tot_suit"
    suit_cap_fields = [
        "Ret_SF_Cap",
        "Ind_SF_Cap",
        "Off_SF_Cap",
        "MF_SF_Cap",
        "SF_SF_Cap",
        "Hot_SF_Cap"
    ]  ## assuming this is the TOD type embellishments inside station area and areas outside TOD use values calced for Vacant

    control_tbl = (
        r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\tables\control_totals.csv"
    )
    control_fields = ["segment", "activity", "demand", "known", "net"]

    control_seg_attr = "segment"

    allocate(suit_fc=suit_fc,
             suit_fc_id_field=suit_fc_id_field,
             suit_field=suit_field,
             suit_fc_seg_field=suit_fc_seg_field,
             suit_cap_fields=suit_cap_fields,
             control_tbl=control_tbl)