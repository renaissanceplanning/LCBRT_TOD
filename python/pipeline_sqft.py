import arcpy

# List of LU categories found in parcel data
lu_cats = [
    "Flex Pipeline",
    "Health Care Pipeline",
    "Hospitality Pipeline",
    "Industrial Pipeline",
    "Multi-Family Pipeline",
    "Office Pipeline",
    "Retail Pipeline",
    "Specialty Pipeline",
    "Student Pipeline"
    ]

# List of fields to which square footage (SF) will be assigned
#  - corresponds to lu_cats for dict creation below
lu_fields = [
    "Ind_SF_Pipe",
    "Oth_SF_Pipe",
    "Hot_SF_Pipe",
    "Ind_SF_Pipe",
    "MF_SF_Pipe",
    "Off_SF_Pipe",
    "Ret_SF_Pipe",
    "Oth_SF_Pipe",
    "Oth_SF_Pipe"
    ]
lu_field_ref = dict(zip(lu_cats, lu_fields))

pipeline_fc = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\SBF_New_Pipe_Merged.shp"
pipeline_wc = arcpy.AddFieldDelimiters(pipeline_fc, "PropertyTy") + "LIKE '%Pipeline'"
pipeline_fl = arcpy.MakeFeatureLayer_management(pipeline_fc, "pipe", pipeline_wc)


def sqFtByLu(in_fc, sqft_field, lu_field, lu_field_ref, where_clause=None):
    """
    in_fc: String (path to feature class)
        Feature class 
    sqft_field: String
        Field in `in_fc` that contains building square footage
    lu_field: String
        Field in `in_fc` that contains land use information
    lu_field_ref: Dict
        Dictionary of land use categories (expected values from `lu_field`)
        as keys and output field names as values. Any observed square footage
        in a given category will be recorded in the field list implied by
        the dictionary values. These fields will be added to `in_fc` if
        they do not already exist.
    """
    # Add lu fields if needed
    update_fields = sorted({v for v in lu_field_ref.values()})
    for update_field in update_fields:
        # Check if the field exists
        try:
            f = arcpy.ListFields(in_fc, update_field)[0]
            # Reset field value to zero
            arcpy.CalculateField_management(in_fc, update_field, 0)
        except IndexError:
            # Add the field
            arcpy.AddField_management(in_fc, update_field, "LONG")
    # Update field values using a cursor
    all_fields = update_fields + [lu_field, sqft_field]
    with arcpy.da.UpdateCursor(in_fc, all_fields) as c:
        for r in c:
            bldg_area = r[-1]
            lu = r[-2]
            update_field = lu_field_ref.get(lu, "")
            if update_field:
                update_idx = update_fields.index(update_field)
                r[update_idx] = bldg_area
                c.updateRow(r)
                

    
            


