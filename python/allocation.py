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


def allocate_dict(
    suit_df,
    suit_df_id_field,
    suit_field,
    suit_df_seg_field,
    suit_cap_fields,
    control_tbl,
    control_fields,
):

    # read control totals to dictionary
    control_dict = (
        pd.read_csv(control_tbl)
        .groupby(control_seg_attr)
        .apply(lambda x: x.to_dict(orient="list"))
        .to_dict()
    )
    # # set up dataframe to read values into loop for tracking count, sorted by suitability
    # field_names = [suit_fc_id_field, suit_field, suit_fc_seg_field] + suit_cap_fields
    # suit_df = pd.DataFrame(
    #     arcpy.da.TableToNumPyArray(suit_fc, field_names, null_value=0.0),
    # ).set_index(suit_fc_id_field)

    suit_df.sort_values(
        by=[suit_df_seg_field, suit_field], ascending=False, inplace=True
    )

    (
        ind_sqft_cap,
        off_sqft_cap,
        mfr_sqft_cap,
        sfr_sqft_cap,
        hot_sqft_cap,
        ret_sqft_cap,
    ) = suit_cap_fields

    filled_rows = {}
    # loop over segments and create control dictionary
    for segment, group in suit_df.groupby(suit_df_seg_field):
        print "---Segment {}---".format(segment)
        seg_controls = dict(
            zip(control_dict[segment]["activity"], control_dict[segment]["net"])
        )
        for k, v in seg_controls.items():
            print "\t{}: {}".format(k, v)
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
                alloc_att = "{}_SF_{}".format(act_key, "alloc")
                unalloc_att = "{}_SF_{}".format(act_key, "unalloc")
                segment_act_control = seg_controls[act_key]  # get segment activity control val
                parcel_act_cap = parcel_count[act_key]  # get parcel activity capacity val (ie fill_to_val)
                updated_act_control = (segment_act_control - parcel_act_cap)  # calculate updated control
                # if new control  is negative, reset activity control and parcel allocations
                dist = 0.0
                if updated_act_control < 0:
                    dist = updated_act_control * -1
                    updated_act_control += dist
                    parcel_act_cap -= (dist)
                seg_controls[
                    act_key
                ] = updated_act_control  # update activity control to reflect allocation
                new_row[alloc_att] = parcel_act_cap
                new_row[unalloc_att] = dist
                filled_rows[parcel_id] = new_row

                if all(value == 0 for value in seg_controls.values()):
                    break
        print "---End Segment {}---".format(segment)
        for k, v in seg_controls.items():
            print "\t{}: {}".format(k, v)
    filled_df = pd.DataFrame(filled_rows).T

    return filled_df


def allocate_df(
    control_df,
    control_fields,
    suit_df,
    suit_df_id,
    suit_df_cap_fields,
    suit_df_seg_field,
    suit_field,
):

    suit_df_sorted = suit_df.sort_values(
        [suit_df_seg_field, suit_field], ascending=False
    )

    # apply segment limits
    alloc_cols = []
    for cap_field, ctrl_field in zip(suit_df_cap_fields, control_fields):
        # Get field specs
        cumu_field = "{}_cumu".format(cap_field)
        alloc_field = "{}_alloc".format(ctrl_field)
        unalloc_field = "{}_unalloc".format(ctrl_field)

        # Add the unalloc columns
        control_df[alloc_field] = 0
        control_df[unalloc_field] = 0

        seg_alloc_cols = []
        # Iterate over segments
        for seg, ctrl_row in control_df.iterrows():
            ctrl = ctrl_row[ctrl_field]

            # Take a slice from recips for this seg and this cap field
            slc_fields = [suit_df_seg_field, cap_field]
            slc = suit_df_sorted[suit_df_seg_field] == seg
            suit_df_slc = suit_df_sorted[slc][slc_fields].copy()

            # TODO: make sure it isn't empty?

            # Calculate the cumulative capacity row-by-row for recips in this seg
            suit_df_slc[cumu_field] = suit_df_slc[cap_field].cumsum()

            # Include recip_slc rows with cumulative cap < ctrl
            crit = suit_df_slc[cumu_field] - suit_df_slc[cap_field] < ctrl

            # Tag rows for allocation
            suit_df_slc["__is_alloc__"] = np.select([crit], [1.0], 0.0)

            # Calculate an allocation column
            suit_df_slc[alloc_field] = suit_df_slc.__is_alloc__ * suit_df_slc[cap_field]

            # Update the cumu field
            suit_df_slc[cumu_field] *= suit_df_slc.__is_alloc__

            # Identify the last recip that could be filled
            last_recip = suit_df_slc[crit][cumu_field].argmax()
            # last_recip = recips_slc.index[last_recip]

            # Check to see if the allocated quantity exceeds the ctrl
            alloc = suit_df_slc[alloc_field].sum()
            if alloc > ctrl:
                # Revise the last recipient's total down by the difference
                diff = alloc - ctrl
                # recips_slc.iloc[last_recip][alloc_field] -= diff
                suit_df_slc.at[last_recip, alloc_field] -= diff
                unalloc = 0
                tot_alloc = ctrl
            elif alloc < ctrl:
                # All the allocation totals are retained, but some portion
                #  remains unallocated
                unalloc = ctrl - alloc
                tot_alloc = alloc
            else:
                unalloc = 0
                tot_alloc = alloc

            # Record results for this control/seg
            ctrl_row[alloc_field] = tot_alloc
            ctrl_row[unalloc_field] = unalloc
            seg_alloc_cols.append(suit_df_slc[alloc_field])

        # Combine results for all segs
        seg_alloc_col = pd.concat(seg_alloc_cols)

        # Record the result
        alloc_cols.append(seg_alloc_col)

    result = pd.concat(alloc_cols, axis=1)
    combo = pd.concat([suit_df_sorted, result], axis=1)


if __name__ == "__main__":
    # TODO: join cap table and parcels df with only necessary attributes (ParclID,segnum, XXX_SF_ChgCap...)
    # suitability polygon inputs
    # processed elements
    parcel_fc = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\scenarios\WE_Sum\WE_Sum_scenario.gdb\parcels"
    capacity_tbl = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\scenarios\WE_Sum\WE_Sum_scenario.gdb\capacity"
    id_field = "ParclID"
    seg_field = "seg_num"
    suit_field = "tot_suit"
    cap_fields = [
        "Ret_SF_ChgCap",
        "Ind_SF_ChgCap",
        "Off_SF_ChgCap",
        "MF_SF_ChgCap",
        "SF_SF_ChgCap",
        "Hot_SF_ChgCap"
    ]
    # control elements
    control_tbl = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\tables\control_totals.csv"
    control_fields = ["seg", "activity", "net"]
    control_seg_attr = "segment"

    # make df to insert
    p_flds = [id_field, seg_field, suit_field]
    cap_flds = [id_field] + cap_fields
    pdf = pd.DataFrame(
        arcpy.da.TableToNumPyArray(in_table=parcel_fc, field_names=p_flds, null_value=0.0)
    ).set_index(keys=id_field)
    capdf = pd.DataFrame(
        arcpy.da.TableToNumPyArray(in_table=capacity_tbl, field_names=cap_flds, null_value=0.0)
    ).set_index(keys=id_field)
    p_cap = pdf.join(other=capdf)
    allocate_dict(
        suit_df=p_cap,
        suit_df_id_field=id_field,
        suit_field=suit_field,
        suit_df_seg_field=seg_field,
        suit_cap_fields=cap_fields,
        control_tbl=control_tbl,
        control_fields=control_fields,
    )
