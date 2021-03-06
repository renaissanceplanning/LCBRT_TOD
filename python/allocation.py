import arcpy
import pandas as pd
import numpy as np
from collections import OrderedDict

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
        suit_id_field,
        suit_field,
        suit_df_seg_field,
        suit_cap_fields,
        control_dict,
):
    # sort data by segment and suitability descending
    suit_df.sort_values(
        by=[suit_df_seg_field, suit_field], ascending=False, inplace=True
    )

    (
        sfr_sqft_cap,
        mfr_sqft_cap,
        ret_sqft_cap,
        ind_sqft_cap,
        off_sqft_cap,
        hot_sqft_cap,
    ) = suit_cap_fields

    filled_rows = {}
    # loop over segments and create control dictionary
    for segment, group in suit_df.groupby(suit_df_seg_field):
        seg_controls = control_dict[segment]
        print("Calculating allocation for segment --> {}".format(segment))
        print ("...segment controls start: {}".format(seg_controls))
        # iterate over parcel rows
        count = 0
        for parcel_id, row in group.iterrows():
            new_row = {suit_df_seg_field: segment}
            parcel_count = OrderedDict(
                {
                    "SF": row[sfr_sqft_cap],
                    "MF": row[mfr_sqft_cap],
                    "Ret": row[ret_sqft_cap],
                    "Ind": row[ind_sqft_cap],
                    "Off": row[off_sqft_cap],
                    "Hot": row[hot_sqft_cap],
                }
            )
            for act_key in parcel_count.keys():
                alloc_att = "{}_SF_{}".format(act_key, "alloc")
                # get segment activity control val, if control is 0 set lu allocation to 0
                segment_act_control = int(seg_controls[act_key])
                if segment_act_control == 0:
                    new_row[alloc_att] = 0
                    continue
                # get parcel activity capacity val (ie fill_to_val), if parcel_cap is 0 set alloc to 0
                parcel_act_ccap = int(parcel_count[act_key])
                if parcel_act_ccap == 0:
                    new_row[alloc_att] = 0
                    continue
                # calculate updated control
                updated_act_control = int(segment_act_control - parcel_act_ccap)
                # if new control  is negative,
                #   reset activity control and parcel allocations
                if updated_act_control < 0:
                    dist = updated_act_control * -1
                    updated_act_control += dist
                    parcel_act_ccap -= dist
                seg_controls[act_key] = updated_act_control  # update activity control to reflect allocation
                new_row[alloc_att] = parcel_act_ccap  # add

            # add new row to filled dict
            filled_rows[parcel_id] = new_row
        print ("...segment controls end: {}".format(seg_controls))

    filled_df = (
        pd.DataFrame(filled_rows)
            .T.reset_index()
            .rename(columns={"index": suit_id_field})
            .drop(suit_df_seg_field, axis=1)
    )
    return filled_df


def allocate_df(
        control_df,
        control_fields,
        suit_df,
        suit_df_cap_fields,
        suit_df_seg_field,
        suit_field,
):
    """

    :param control_df: df of activity controls {rows are segments, columns are activities;  seg set to idx}
    :param control_fields: field names identifying activities
    :param suit_df: features used to allocation activity
    :param suit_df_id: unique id field
    :param suit_df_cap_fields: capacity fields of suitability features
    :param suit_df_seg_field: field identifying the segment of a feature
    :param suit_field: suitabiility field
    :return: pandas dataframe unique id, allocated units and unallocated units by activity.
    """

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
            if not len(suit_df_slc[crit][cumu_field]) == 0:
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
    # TODO: sort out why result is 3x bigger than suit_df_sorted
    combo = pd.concat([suit_df_sorted, result], axis=1)
    return combo


if __name__ == "__main__":
    # suitability polygon inputs
    # processed elements
    parcel_fc = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\WE_Sum\WE_Sum_scenario.gdb\parcels"
    id_field = "ParclID"
    seg_field = "seg_num"
    suit_field = "tot_suit"
    cap_fields = ["SF_SF_ChgCap", "MF_SF_ChgCap", "Ret_SF_ChgCap",
                  "Ind_SF_ChgCap", "Off_SF_ChgCap", "Hot_SF_ChgCap", ]

    # control elements
    control_tbl = (r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\tables\control_totals.csv")
    control_fields = ["Ind", "Ret", "MF", "SF", "Off", "Hot"]
    control_seg_attr = "segment"
    demand_phase = "group"
    ctl_df = pd.read_csv(control_tbl, usecols=control_fields + [control_seg_attr, demand_phase]).set_index(control_seg_attr)
    ctl_df = ctl_df[ctl_df[demand_phase] == "net"].drop(demand_phase, axis=1)
    ctl_dict = ctl_df.T.to_dict()

    # make df to insert
    p_flds = [id_field, seg_field, suit_field] + cap_fields
    cap_flds = [id_field] + cap_fields
    pdf = pd.DataFrame(arcpy.da.TableToNumPyArray(
            in_table=parcel_fc, field_names=p_flds, null_value=0.0)).set_index(keys=id_field)

    allocation_dict = allocate_dict(
        suit_df=pdf,
        suit_id_field=id_field,
        suit_field=suit_field,
        suit_df_seg_field=seg_field,
        suit_cap_fields=cap_fields,
        control_dict=ctl_dict,
    )
    out_array = np.array(np.rec.fromrecords(allocation_dict.values))
    names = allocation_dict.dtypes.index.tolist()
    out_array.dtype.names = tuple(names)
    arcpy.da.NumPyArrayToTable(
        out_array,
        r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\tables\allocation.csv",
    )
    print(allocation_dict.head())
