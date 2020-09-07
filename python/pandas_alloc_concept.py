# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 19:48:44 2020

@author: AK7
"""
# %% IMPORTS
import pandas as pd
import numpy as np

#%% CONTROLS
controls = pd.DataFrame(
    {
     "Segment": [1,2,3],
     "Res": [5, 7, 1],
     "Com": [10, 12, 9],
     "Ind": [3, 2, 8]
    }
    ).set_index("Segment")

recips = pd.DataFrame(
    {
     "ParclID": [1000, 10001, 1002, 1003, 
                 2000, 20001, 
                 3000, 30001, 3002],
     "Seg": [1, 1, 1, 1, 
             2, 2, 
             3, 3, 3],
     "Suit": [0.01, 0.5, 0.9, 0.7, 
              1.0, 0.2, 
              0.8, 0.2, 0.6],
     "ResCap": [10, 0, 4, 2, 
                0, 20, 
                0, 0, 0],
     "ComCap": [5, 10, 0, 0, 
                10, 4, 
                8, 0, 0],
     "IndCap": [4, 0, 0, 0, 
                1, 1, 
                3, 4, 4]
     }
    ).set_index("ParclID")
    
# %% Accumulate capacity
ctrl_fields = ["Res", "Com", "Ind"]
cap_fields = ["ResCap", "ComCap", "IndCap"]


recips_sorted = recips.sort_values(["Seg", "Suit"], ascending=False)

# for cap_field in cap_fields:
#     cumu_field = "{}_cumu".format(cap_field)
#     recips_sorted[cumu_field] = recips_sorted[cap_field].cumsum()
    
# %% Apply segment limits

alloc_cols = []

for cap_field, ctrl_field in zip(cap_fields, ctrl_fields):
    # Get field specs
    #cap_field = cap_fields[ctrl_i]
    cumu_field = "{}_cumu".format(cap_field)
    alloc_field = "{}_alloc".format(ctrl_field)
    unalloc_field = "{}_unalloc".format(ctrl_field)
    
    # Add the unalloc columns
    controls[alloc_field] = 0
    controls[unalloc_field] = 0
    
    seg_alloc_cols = []
    # Iterate over segments
    for seg, ctrl_row in controls.iterrows():
        ctrl = ctrl_row[ctrl_field]
        
        # Take a slice from recips for this seg and this cap field
        slc_fields = ["Seg", cap_field]
        slc = recips_sorted["Seg"] == seg
        recips_slc = recips_sorted[slc][slc_fields].copy()
       
        #TODO: make sure it isn't empty?
       
        # Calculate the cumulative capacity row-by-row for recips in this seg
        recips_slc[cumu_field] = recips_slc[cap_field].cumsum()
               
        # Include recip_slc rows with cumulative cap < ctrl       
        crit = recips_slc[cumu_field] - recips_slc[cap_field] < ctrl
        
        # Tag rows for allocation
        recips_slc["__is_alloc__"] = np.select([crit], [1.0], 0.0)
        
        # Calculate an allocation column
        recips_slc[alloc_field] = recips_slc.__is_alloc__ * recips_slc[cap_field]
        
        # Update the cumu field
        recips_slc[cumu_field] *= recips_slc.__is_alloc__
        
        # Identify the last recip that could be filled
        last_recip = recips_slc[crit][cumu_field].argmax()
        #last_recip = recips_slc.index[last_recip]
        
        # Check to see if the allocated quantity exceeds the ctrl
        alloc = recips_slc[alloc_field].sum()
        if alloc > ctrl:
            # Revise the last recipient's total down by the difference
            diff = alloc - ctrl
            #recips_slc.iloc[last_recip][alloc_field] -= diff
            recips_slc.at[last_recip, alloc_field] -= diff
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
        seg_alloc_cols.append(recips_slc[alloc_field])
    
    # Combine results for all segs
    seg_alloc_col = pd.concat(seg_alloc_cols)
    
    # Record the result
    alloc_cols.append(seg_alloc_col)
    
result = pd.concat(alloc_cols, axis=1)
        
# %%
combo = pd.concat([recips_sorted, result], axis=1)

        
        
        
        
        
        
        
        
        
        
        
    