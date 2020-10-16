import arcpy as ap
import numpy as np
import random


def TableToTableAllocation(control_table, control_id_field, control_total_fields,
                           recipient_table, recipient_id_field, recipient_link_field,
                           recipient_capacity_fields, recipient_suitability_fields,
                           output_folder, allocation_name,
                           recipient_mix_fields=None, consumption_weights=None,
                           control_where_clause=""):
    #control table, recipient table are tables that can be read, dumped to numpy arrays via arcpy.da
    #build lists of fields for using arcpy.da methods
    control_fields = [control_id_field]
    recipient_fields = [recipient_id_field, recipient_link_field]
    #check to see if the recipient link field is a string, also recipient id
    link_is_string = ap.ListFields(recipient_table, recipient_link_field, "String")
    id_is_string = ap.ListFields(recipient_table, recipient_id_field, "String")

    #handle allocation elements, determining whether we're working with single/multiple controls, capacities, suitabilities
    single_ctrl, control_total_fields = _adaptParameters(control_total_fields)
    control_fields += control_total_fields

    single_cap, recipient_cpacity_fields = _adaptParameters(recipient_capacity_fields)
    recipient_fields += recipient_capacity_fields

    single_suit, recipient_suitability_fields = _adaptParameters(recipient_suitability_fields)
    recipient_fields += recipient_suitability_fields

    #setup default consumption weights if needed, recipient mix fields
    if consumption_weights is None: #and single_ctrl = False and single_cap = True: ????
        consumption_weights = [1 for i in control_total_fields]
    if recipient_mix_fields:
        recipient_fields += recipient_mix_fields

    #confirm paramaters are valid
    _confirmParameters(single_ctrl, control_total_fields,
                       single_cap, recipient_capacity_fields,
                       single_suit, recipient_suitability_fields,
                       recipient_mix_fields, consumption_weights)

    #create results containers
    all_allocated = []
    if link_is_string:
        alloc_dt_list = [(recipient_link_field, "|S{}".format(link_is_string[0].length))]
    else:
        alloc_dt_list = [(recipient_link_field, "<f8")]
    if id_is_string:
        alloc_dt_list.append((recipient_id_field, "|S{}".format(id_is_string[0].length)))
    else:
        alloc_dt_list.append((recipient_id_field, "<f8"))
    alloc_dt_list += [(ctf, "<i4") for ctf in control_total_fields]
    
    all_unallocated = []
    if link_is_string:
        unalloc_dt_list = [(control_id_field, "|S{}".format(link_is_string[0].length))]
    else:
        unalloc_dt_list = [(control_id_field, "<f8")]
    unalloc_dt_list += [(ctf, "<i4") for ctf in control_total_fields]

    #iterate over control rows
    control_rows = ap.da.TableToNumPyArray(control_table, control_fields, control_where_clause, skip_nulls=True)
    for control_row in control_rows:
        control_id = control_row[control_id_field]
        control_totals_dict = dict(list(zip(control_total_fields, [control_row[i] for i in control_total_fields])))
        #control_totals={'jobs':1234, 'units':3456'}, e.g.

        #create an expression to select recipients associated with the current control group
        expr = ap.AddFieldDelimiters(recipient_table, recipient_link_field)
        if link_is_string:
            expr += "= '%s'" % control_id
        else:
            expr += "= %f" % control_id

        #allocate activities to the recipient rows
        recipient_rows = ap.da.TableToNumPyArray(recipient_table, recipient_fields, expr, True)
        recipient_rows = np.array(recipient_rows, dtype=np.dtype([(cname, ctype) if ctype != '<i4' else (cname, "<f8") for cname, ctype
                                             in recipient_rows.dtype.descr]))

        #allocate activities
        this_alloc, this_unalloc = _allocateValues(control_id, control_totals_dict, control_total_fields,
                                                  recipient_rows, recipient_id_field, recipient_capacity_fields,
                                                      recipient_suitability_fields, recipient_mix_fields,
                                                  consumption_weights,
                                                  single_ctrl, single_cap, single_suit)
        all_allocated += this_alloc
        all_unallocated += this_unalloc

    alloc_array = np.array(all_allocated, dtype=np.dtype(alloc_dt_list))
    unalloc_array = np.array(all_unallocated, dtype=np.dtype(unalloc_dt_list))

    ap.da.NumPyArrayToTable(alloc_array, "{}\\{}_alloc.dbf".format(output_folder, allocation_name))
    ap.da.NumPyArrayToTable(unalloc_array, "{}\\{}_unalloc.dbf".format(output_folder, allocation_name))
        

def _allocateValues(control_id, control_totals, control_total_fields,
                    recipient_rows, recipient_id_field, recipient_capacity_fields,
                        recipient_suitability_fields, recipient_mix_fields,
                    consumption_weights,
                    single_ctrl, single_cap, single_suit):
    allocated_dict = {} #{recipient_id: {activity: value}}
    unallocated_dict = dict(control_totals) #copy of control totals dictionary

    #check total capacity and total suitability
    total_cap = sum([sum(recipient_rows[field])
                     for field in recipient_capacity_fields])
    total_suit = sum([sum(recipient_rows[field])
                          for field in recipient_suitability_fields])
    count=-1
    chex=0

    while sum(control_totals.values()) > 0: #loop until all control totals have been allocated
        count +=1
        if total_suit == 0 or total_cap < 1:
            #no suitable recipients or no remaining capacity
            print("suitability or capacity exhausted for control area ({})".format(control_id))
            unallocated = _makeUnallocatedRow(control_id, unallocated_dict, control_total_fields)
            allocated = _makeAllocatedRows(control_id, allocated_dict, control_total_fields)            
            return allocated, unallocated

        #determine which field to allocate based on allocation parameters
        if single_ctrl:
            activity = list(control_totals.keys())[0]
            allocation_idx = 0
        else:
            if single_suit:
                activity = "_unknown"
                allocation_idx = None
            else:
                #randomly choose an activity to allocate
                activity_choice_array = np.array(list(zip(list(control_totals.keys()), list(control_totals.values()))),
                                                 dtype=np.dtype([("activity", "|S255"), ("control_value", "<f8")]))
                activity_row = _selectRandomRowFromArray(activity_choice_array,["control_value"])
                activity = activity_row['activity']
                allocation_idx = control_total_fields.index(activity)

        #get valid recipient rows | CAPACITY
        if single_ctrl or single_suit:
            #fetch recipient rows where any capacity field is greater than 1
            valid_cap_rows = _fetchValidRecipients(recipient_rows, [recipient_capacity_fields[i] for i in range(len(control_total_fields))
                                                                   if control_total_fields[i] in list(control_totals.keys())], 1, True)
        elif single_cap:
            #fetch recipient rows where the capacity field is greater than 1
            valid_cap_rows = _fetchValidRecipients(recipient_rows, recipient_capacity_fields, 1, True)
        else:
            #fetch recipient rows that have capacity for the activity being allocated
            valid_cap_rows = _fetchValidRecipients(recipient_rows, [recipient_capacity_fields[allocation_idx]], 1, True)

        #get value recipient rows | SUITABILITY
        if single_ctrl or single_suit:
            #criteria fields will be the suitability fields
            score_fields = recipient_suitability_fields            
        else:
            #criteria fields will be based on the suitability for the activity being allocated
            score_fields = [recipient_suitability_fields[allocation_idx]]
        valid_rows = _fetchValidRecipients(valid_cap_rows, score_fields, 0)

        #select a row for allocation
        if len(valid_rows) == 0:
            #if there are no rows to allocate to, report allocation progress and unallocated remnant
            if single_ctrl or single_suit:
                if activity != '_unknown':
                    unallocated_dict[activity] = control_totals[activity]
                print("suitability or capacity exhausted for control area ({})".format(control_id))
                unallocated = _makeUnallocatedRow(control_id, unallocated_dict, control_total_fields)
                allocated = _makeAllocatedRows(control_id, allocated_dict, control_total_fields)
                return allocated, unallocated
            else:
                unallocated_dict[activity] = control_totals[activity]
                del control_totals[activity]
                continue
        else:
            allocation_row = _selectRandomRowFromArray(valid_rows, score_fields)
            
        #get allocation row
        recipient_id = allocation_row[recipient_id_field]
        allocation_row_idx = np.where(recipient_rows[recipient_id_field] == recipient_id)[0][0]
        #if activity has not been determined yet, randomly choose activity now
        if activity == '_unknown':
            mix_indices = [control_total_fields.index(field) for field in control_total_fields if field in list(control_totals.keys())]
            dtype = np.dtype([("activity", '|S255'), ('mix_value','<f8')])
            #capacity check
            if single_cap:
                search_rows = [(control_total_fields[i], allocation_row[recipient_mix_fields[i]]) for i in mix_indices]
            else:
                chex +=1
                search_rows = [(control_total_fields[i], allocation_row[recipient_mix_fields[i]]) for i in mix_indices
                                if allocation_row[recipient_capacity_fields[i]] >=1
                                   and allocation_row[recipient_mix_fields[i]]>0]
                if not search_rows:
                    for recipient_capacity_field in recipient_capacity_fields:
                        recipient_rows[allocation_row_idx][recipient_capacity_field] = 0
                    continue
            activity_row = _selectRandomRowFromArray(np.array(search_rows, dtype=dtype),["mix_value"])
            activity = activity_row['activity']                
            allocation_idx = control_total_fields.index(activity)

        #allocate activity, update control totals and unallocated dict
        activity_dict = allocated_dict.get(recipient_id, {})
        activity_sum = activity_dict.get(activity, 0) + 1 #######increment?
        activity_dict[activity] = activity_sum
        allocated_dict[recipient_id] = activity_dict
        control_totals[activity] -= 1 ########increment?
        if control_totals[activity] <= 0:
            del control_totals[activity]
        unallocated_dict[activity] -= 1 #######increment?

        #update capacity
        if single_ctrl:
            if single_cap:
                #there's only one capacity field that needs to be reduced
                recipient_rows[allocation_row_idx][recipient_capacity_fields[0]] -=1
            else:
                #there are multiple capacity fields for a single control, randomly reduce one of them by the increment (1)
                search_rows = list(zip(recipient_capacity_fields, [allocation_row[field] if allocation_row[field] >=1 else 0 #######>=increment?
                                                                for field in recipient_capacity_fields]))
                reduction_field = _selectRandomRowFromArray(np.array(search_rows, dtype=np.dtype([("cap_field", "|S255"), ("cap_calue", '<f8')])),
                                                                    ['cap_value'])['cap_field']
                recipient_rows[allocation_row_idx][reduction_field] -= 1 ########increment?
        else:
            if single_cap:
                #diminish total capacity based on the activity's consumption weight
                consumption_weight = consumption_weights[allocation_idx]
                diminish_qty = 1 * consumption_weight #######increment * consumption weight?
                recipient_rows[allocation_row_idx][recipient_capacity_fields[0]] -= diminish_qty
            else:
                #reduce the capacity for the activity being allocated by the increment (1)
                recipient_rows[allocation_row_idx][recipient_capacity_fields[allocation_idx]] -=1 ##### increment
                #reduce capacities for each activity by the diminish_qty (increment * consumption weight)
                for i in range(len(control_total_fields)):
                    if i != allocation_idx:
                        consumption_weight = consumption_weights[allocation_idx]/float(consumption_weights[i])
                        diminish_qty = 1 * consumption_weight #######increment * consumption weight
                        recipient_rows[allocation_row_idx][recipient_capacity_fields[i]] -= diminish_qty

    #when the loop is finished and all control totals have been allocated
    print("allocation complete for control area ({})".format(control_id))
    unallocated = _makeUnallocatedRow(control_id, unallocated_dict, control_total_fields)
    allocated = _makeAllocatedRows(control_id, allocated_dict, control_total_fields)
    return allocated, unallocated   


def _adaptParameters(input_param):
    """adapt input parameters to organize fields into a list format and have the allocation flag the status of single/multiple
        control totals, capacity fields, or suitability fields"""
    single=True
    if type(input_param) is list:
        if len(input_param) > 1:
            single = False
    else:
        input_param = [input_param]
    return single, input_param


def _confirmParameters(single_ctrl, control_total_fields,
                       single_cap, recipient_capacity_fields,
                       single_suit, recipient_suitability_fields,
                       recipient_mix_fields, consumption_weights):
    """confirm that the parameters passed to TableToTableAllocation match in number and will allow the tool to function as expected"""
    #if single_ctrl=True, everything else is fine, raise no errors
    if not single_ctrl:
        #confirm capacity inputs
        if not single_cap:
            #multiple control totals with multiple capacities must have equal number of fields
            if len(recipient_capacity_fields) != len(control_total_fields):
                raise ValueError("Input Error 0000: unequal number of fields defining control totals and recipient capacities")
        else:
            #mult. ctrls using single cap. must have consumption weights equal in number to ctrl fields
            if len(consumption_weights) != len(control_total_fields):
                raise ValueError("Input Error 0001: unequal number of fields defining activities to allocate and consumption weights")

        #confirm suitability inputs
        if not single_suit:
            #mult. ctrls using mult. suits must have equal number of fields
            if len(recipient_suitability_fields) != len(control_total_fields):                        
                raise ValueError("Input Error 0002: unequal number of fields defining suitability scores and recipient control totals/capacities")
        else:
            #mult. ctrls using single suit must have mix fields equal in number to ctrl fields
            if not type(recipient_mix_fields) is list or len(recipient_mix_fields) != len(control_total_fields):
                raise ValueError("Input Error 0003: argument is not a list or unequal number of fields defining mix values and recipient control totals/capacities")


def _makeUnallocatedRow(control_id, unallocated_dict, control_total_fields):    
    print("\tUNALLOCATED:")
    out_row =[control_id]
    for field in control_total_fields:
        print("\t\t{}: {}".format(field, unallocated_dict[field]))
        out_row.append(unallocated_dict[field])
    return [tuple(out_row)]


def _makeAllocatedRows(control_id, allocated_dict, control_total_fields):
    print("\tALLOCATED:")
    sub_dicts = list(allocated_dict.values())
    for field in control_total_fields:
        print("\t\t{}: {}".format(field, sum([sub_dict.get(field,0) for sub_dict in sub_dicts])))
    return [tuple([str(control_id), str(recipient_id)] + [allocated_dict[recipient_id].get(field, 0) for field in control_total_fields])
            for recipient_id in list(allocated_dict.keys())]

    
def _selectRandomRowFromArray(array, score_fields):
    if len(array) == 0:
        raise ValueError("Empty array %s" % (score_fields))
    total_score = float(sum([np.sum(array[score_field]) for score_field in score_fields]))
    weights = [sum(row[score_field] for score_field in score_fields)/total_score for row in array]
    return np.random.choice(array, p=weights)

    
def _fetchValidRecipients(recipient_rows, criteria_fields, criterion, inclusive=False):
    if inclusive:
        return np.take(recipient_rows,
                       sorted({idx for field in criteria_fields
                               for idx in np.where(recipient_rows[field] >= criterion)[0]}))
    else:
        return np.take(recipient_rows,
                       sorted({idx for field in criteria_fields
                               for idx in np.where(recipient_rows[field] > criterion)[0]}))








            
