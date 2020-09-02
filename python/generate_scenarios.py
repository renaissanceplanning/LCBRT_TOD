"""
Generate a TOD scenario based on workspace details, analysis specs, standard input 
data, and derived inputs/specs:

WORKSPACE DETAILS:
  - `source_gdb`: where are the standard input data stored?
  - `scenarios_ws`: a folder where the output gdb for each scenario will be stored
  - `scenarios`: one or more strings specifying a scenario name, corresponding to a
    column name in the `stations` input dataset.

ANALYSIS SPECS:
  - Global settings:
      - `USE_NET`: If True, TOD templates will be applied for station areas defined based
         on walksheds; if False, TOD templates will be applied for station areas defined
         based on simple, non-overlapping buffers.
      - `TECH`: Station types may change based on selected tech (for LCRT always use `BRT`)

  - Use groupings (support consistent field naming and references by use category)
      - `RES`: residential use groupings
      - `NRES`: non-residential use groupings
      - `HOTEL`: hotel use groupings
      - `UNTRACKED`: other use groupings that are not tracked/forecasted for TOD templating
      - `USES`: the combined list of uses from `RES`, `NRES`, `HOTEL`, and `UNTRACKED`

  - Suitability weightings:
      - `weights`: dictionary with keys corresponding to suitability criteria and values
         defining the relative weight of each criterion.
         - `in_DO`: weight for development opportunity sites (applied to the parcel's 
           `do_prop_field` value)
         - `is_vacant`: weight for vacant parcels
         - `in_TOD`: weight for parcels that fall inside the TOD buffer area (varies by
            scenario)
         - `in_walkshed`: weight for parcels that fall inside the TOD walkshed (varies by
            scenario)
         - `dev_size`: weight for parcels based on developable area.

STANDARD INPUTS:
  - `parcels`: Parcel features
      - `id_field`: unique id for each parcel
      - `par_sqft_field`: estimated building area
      - `lu_field`: current land use
      - `par_est_fld_ref`: Dictionary with keys listing expected (relevant)
        categories in `lu_field` and values that relate each category to a use in 
        `USES`
      - `is_do_field`: is the parcel a development opportunity site? (0/1)
      - `do_prop_field`: what proportion of the parcel is a D.O. site?
      - `acres_field`: parcel area in acreage
      - `seg_id_field`: the analysis segment the parcel belongs to
      - `pipe_field`: is development in the pipeline for the parcel? (0/1)
      - `excl_lu`: List of land use categores in `lu_field` that are excluded in
         TOD templating (i.e, are assumed to have no potential for future development)
    
  - `newpipe_fc`: New and pipeline development points
      - `newpipe_par_field`: parcel associated with each point
      - `newpipe_sqft`: square footage of development
      - `newpipe_lu`: land use of the development 
      - `new_dev_fld_ref`: Dictionary with keys listing expected (relevant)
         categories in `newpipe_lu` and values that relate each category to a use in 
         `USES`
      - `pipe_fld_ref`: Dictionary with keys listing expected (relevant)
         categories in `newpipe_lu` and values that relate each category to a use in 
         `USES`
      - `new_dev_wc`: Where clause to select features from `newpipe_fc` that are new 
         developments
      - `pipe_wc`: Where clause to select features from `newpipe_fc` that are pipeline 
         developments
      
  - `stations`: Point file of all station potential locations. This feature class
     includes attribute corresponding to scenario names. Values in these attributes
     indicate the station type to be used for the named scenario. If the value for a
     given feature is "NA" for the named scenario, that station is excluded from that
     scenario. This feature class must have the fields `stn_type`, `stn_name`, and
     `stn_order` properly populated, but these are not variables in the code.
    
  - `st_type_emb_tbl`: Path to a csv table that contains station-typology embellishments.
     These include specification of activity shares by use groupings for each TOD type
     and floor-area-per-unit assumptions.
    
  - `walk_net`: The network dataset to be used when creating station area walksheds.
      - `imp_field`: The impedance attribute of `walk_net` to use when creating walkshed
         service areas.
      - `cost`: The size of the walkshed service area in the same units used for `imp_field`.
         Unit details are recorded in the network dataset's Properties dialog.

DERIVED INPUTS/SPECS:
  - `_ex_lu_fields`: a list of strings that will be added to `parcels` as an estimate
    of total existing floor area based on parcel-based floor area estimtes (``)
    and floor area estimated for recently delivered developments (`new_dev_fields`)

"""

# %% IMPORTS
import arcpy
from suitability import generate_suitability
from walksheds import generate_walksheds
from existing_sqft import sqFtByLu
from os import path
from tod.TOD import createTODTemplatesGDB, applyTODTemplates, adjustTargetsBasedOnExisting2
from tod.HandyGP import extendTableDf
import pandas as pd
import numpy as np

# %% WORKSPACES AND SCENARIO NAMES.
source_gdb = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\LCBRT_data.gdb"
scenarios_ws = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\scenarios_LAB"
scenarios = ['WE_Sum', 'WE_Fair']
arcpy.env.overwriteOutput = True

# %% GLOBAL SETTINGS/SPECS
USE_NET = False
TECH = "BRT"

# Use groupings
RES = ["SF", "MF"]
NRES = ["Ret", "Ind", "Off"]
HOTEL = ["Hot"]
UNTRACKED = ["Oth"]
USES = RES + NRES + HOTEL

# Suitability weightings
weights = {
    "in_DO": 0.6,
    "is_vacant": 0.15,
    "in_TOD": 0.05,
    "in_walkshed": 0.1,
    "dev_size": 0.1
}


# %% HELPER FUNCTIONS AND CLASSES
class LicenseError(Exception):
    pass


def genFieldList(suffix, include_untracked=True):
    """
    Generates a list of fields based on use groupings with the form:
    `{UseGroup}_SF_{suffix}`, recording the square footage (SF) for each
    use grouping for a time frame indicated by the suffix.
    """
    global USES, UNTRACKED
    if include_untracked:
        return ["{}_SF_{}".format(use, suffix) for use in USES]
    else:
        return ["{}_SF_{}".format(use, suffix) for use in USES if use not in UNTRACKED]


def makeFieldRefDict(in_dict, suffix):
    """
    Generates a dictionary of field references the map category labels to output
    fields based on use type (checked against USES in the analysis).
    """
    global USES
    out_dict = {}
    for k in in_dict:
        v = in_dict[k]
        if v not in USES:
            raise ValueError("Invalid use grouping specified for key '{}'".format(k))
        out_dict[k] = "{}_SF_{}".format(v, suffix)
    return out_dict


# %% INPUT DATA SETS
# Parcels
parcels = "parcels"
id_field = "ParclID"
lu_field = "LandUse"
par_est_fld_ref = {
    "Commercial/Retail": "Ret",
    "Industrial/Manufacturing": "Ind",
    "Institutional": "Off",
    "Multifamily": "MF",
    "Office": "Off",
    "Single-family": "SF",
    "Hospitality": "Hot"
}  # lu_field_ref
par_sqft_field = "BldSqFt"
is_do_field = "DO_Site"
do_prop_field = "DOSProp"
acres_field = "Area_AC"
seg_id_field = "seg_num"
pipe_field = "in_pipe"
excl_lu = ["Recreation/Cultural", "Single-family", "Transportation", "Utilities"]

# New/pipeline features
newpipe_fc = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\SBF_New_Pipe_Merged_Parcel_SJ.shp"  # TODO: add to source_gdb?
newpipe_par_field = "ParclID"
newpipe_sqft = "RBA"
newpipe_lu = "PropertyTy"
new_dev_fld_ref = {
    "Flex New": "Ind",
    "Hospitality New": "Hot",
    "Industrial New": "Ind",
    "Multi-Family New": "MF",
    "Office New": "Off",
    "Retail (Power Center) New": "Ret",
    "Retail New": "Ret",
    "Student New": "Oth"
}
pipe_fld_ref = {
    "Flex Pipeline": "Ind",
    "Health Care Pipeline": "Oth",
    "Hospitality Pipeline": "Hot",
    "Industrial Pipeline": "Ind",
    "Multi-Family Pipeline": "MF",
    "Office Pipeline": "Off",
    "Retail Pipeline": "Ret",
    "Specialty Pipeline": "Oth",
    "Student Pipeline": "Oth"
}
new_dev_wc = arcpy.AddFieldDelimiters(newpipe_fc, newpipe_lu) + "LIKE '%New'"
pipe_wc = arcpy.AddFieldDelimiters(newpipe_fc, newpipe_lu) + "LIKE '%Pipeline'"

# Stations
stations = "stations_LCRT_BRT_scenarios_20200814"
st_type_emb_tbl = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\tables\tod_type_shares.csv"

# Network
walk_net = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\temp\LCBRT_data.gdb\network\walk_network_ND"
imp_field = "Length"
cost = "1320"

# %% DERIVED INPUTS/SPECS
par_est_fields = genFieldList("Par")  # par_fields, par_fields_u
new_dev_fields = genFieldList("New")  # new_dev_fields, new_dev_fields_u
ex_lu_fields = genFieldList("Ex")  # ex_lu_fields, ex_lu_fields_u
pipe_fields = genFieldList("Pipe")  # pipe_fields, pipe_fields_u
# out_gdb = r"D:\Users\DE7\Documents\temp\TOD_TestRun\TOD_TEST_CR.gdb"


# %% PROCESS
try:
    if arcpy.CheckExtension("Network") == "Available":
        arcpy.CheckOutExtension("Network")
    else:
        raise LicenseError

    # Setup working environments for each scenario
    arcpy.env.workspace = source_gdb
    scenarios_sr = arcpy.Describe(parcels).spatialReference

    # Run each scenario
    for scenario in scenarios:
        # Create the scenario workspace folder if needed
        print "---Scenario: {}---".format(scenario)
        scen_ws = path.join(scenarios_ws, scenario)
        scen_gdb = path.join(scen_ws, "{}_scenario.gdb".format(scenario))
        if not arcpy.Exists(scen_ws):
            arcpy.CreateFolder_management(out_folder_path=scenarios_ws, out_name=scenario)

        # Drop scenario gdb for a clean run
        #  (NumPyArrayToTable cannot overwrite existing tables)
        if arcpy.Exists(scen_gdb):
            print "Deleting existing scenario db for new run..."
            arcpy.Delete_management(scen_gdb)

        # Creat the scenario gdb
        print "Creating scenario gdb..."
        scen_gdb = createTODTemplatesGDB(in_folder=scen_ws,
                                         gdb_name="{}_scenario.gdb".format(scenario),
                                         sr=scenarios_sr)

        # Check if sqft embellishments have been added already
        #  (most of this is currently superfluous since we drop and recreate the gdb
        #   with each run)
        print "Extending station types table with embellishments..."
        st_type_tbl = path.join(scen_gdb, 'station_area_types')
        if arcpy.Exists(st_type_tbl):
            flds = [f.name for f in arcpy.ListFields(st_type_tbl)]
            if not any('shr' in f for f in flds):
                type_emb = pd.read_csv(st_type_emb_tbl)
                type_emb_arr = np.array(np.rec.fromrecords(recList=type_emb.values,
                                                           names=type_emb.dtypes.index.tolist()))
                # Add embellishsments
                arcpy.da.ExtendTable(in_table=st_type_tbl,
                                     table_match_field='stn_type',
                                     in_array=type_emb_arr,
                                     array_match_field="stn_type")

        # Import scenario stations into the new GDB
        print "Pushing scenario stations to gdb..."
        stations_wc = arcpy.AddFieldDelimiters(stations, scenario) + " <> 'NA'"
        stations_fl = arcpy.MakeFeatureLayer_management(in_features=stations,
                                                        out_layer='stat_scenario',
                                                        where_clause=stations_wc)

        # Assume stations source has the template fields already populated (stn_type, stn_name, stn_order)
        arcpy.Append_management(inputs=stations_fl,
                                target=path.join(scen_gdb, 'stations'),
                                schema_type='NO_TEST')
        ''' TODO: modify TOD.py to generate customized tables 
            (ie _todTemplatesFromConfig() ...insert csv as templates for stn_types and gradients)
            existing strategy is to modify the defaults to fit LCRT needs
        '''
        # Build walkshed for suitability calculations
        print "Generating walksheds..."
        walk_shed = generate_walksheds(stations=stations,
                                       walk_net=walk_net,
                                       imp_field=imp_field,
                                       cost=cost,
                                       out_gdb=scen_gdb,
                                       stations_wc=None)

        # generate suitability table and tack on the tot_suit to parcel data
        print "Evaluating suitability..."
        suit_fc, suit_table = generate_suitability(in_suit_fc=parcels,
                                                   id_field=id_field,
                                                   is_do_field=is_do_field,
                                                   do_prop_field=do_prop_field,
                                                   acres_field=acres_field,
                                                   seg_id_field=seg_id_field,
                                                   lu_field=lu_field,
                                                   pipe_field=pipe_field,
                                                   stations=stations_fl,
                                                   station_buffers=walk_shed,
                                                   weights=weights,
                                                   out_gdb=scen_gdb,
                                                   excl_lu=excl_lu,
                                                   stations_wc=None)

        # Estimate existing, pipeline development
        #  -- Parcel-based estimates
        print "Appending existing activity data to parcel features based on parcel attributes"
        _par_est_fld_ref = makeFieldRefDict(par_est_fld_ref, "Par")
        sqFtByLu(in_fc=suit_fc,
                 sqft_field=par_sqft_field,
                 lu_field=lu_field,
                 lu_field_ref=_par_est_fld_ref,
                 where_clause=None)

        # -- From New Dev features
        print "...Estimating new activity"
        newpipe = arcpy.FeatureClassToFeatureClass_conversion(newpipe_fc, scen_gdb, "newpipe")
        _new_dev_fld_ref = makeFieldRefDict(new_dev_fld_ref, "New")
        sqFtByLu(in_fc=newpipe,
                 sqft_field=newpipe_sqft,
                 lu_field=newpipe_lu,
                 lu_field_ref=_new_dev_fld_ref,
                 where_clause=new_dev_wc)

        # -- Pipeline dev
        print "...Estimating pipeline development"
        _pipe_fld_ref = makeFieldRefDict(pipe_fld_ref, "Pipe")
        sqFtByLu(in_fc=newpipe,
                 sqft_field=newpipe_sqft,
                 lu_field=newpipe_lu,
                 lu_field_ref=_pipe_fld_ref,
                 where_clause=pipe_wc)

        # -- Sum to parcels
        print "...Summarizing new and pipeline data to parcel level"
        # new_dev_fields_u = sorted({f for f in new_dev_fields})
        # pipe_fields_u = sorted({f for f in pipe_fields})
        newpipe_fields = [newpipe_par_field] + new_dev_fields + pipe_fields
        newpipe_df = pd.DataFrame(arcpy.da.TableToNumPyArray(newpipe, newpipe_fields))
        newpipe_sum = newpipe_df.groupby(newpipe_par_field).sum()
        # -- Extend table
        print "...Adding new and pipeline data to parcels"
        extendTableDf(in_table=suit_fc, table_match_field=id_field,
                      df=newpipe_sum, df_match_field=newpipe_par_field,
                      append_only=False, null_value=0.0)

        # -- Calculate fields
        print "...Calculating existing (parcel-based + new development)"
        for ex_lu_field in ex_lu_fields:
            par_field = ex_lu_field.replace("Ex", "Par")
            new_dev_field = ex_lu_field.replace("Ex", "New")
            arcpy.AddField_management(suit_fc, ex_lu_field, "LONG")
            with arcpy.da.UpdateCursor(suit_fc, [par_field, new_dev_field, ex_lu_field]) as c:
                for r in c:
                    par_val, new_dev_val, ex_lu_val = r
                    if new_dev_val:
                        r[-1] = new_dev_val
                    else:
                        r[-1] = par_val
                    c.updateRow(r)

        print "...Calculating existing + pipeline"
        expi_fields = []
        for ex_lu_field in ex_lu_fields:
            pipe_field = ex_lu_field.replace("Ex", "Pipe")
            expi_field = ex_lu_field.replace("Ex", "ExPi")
            expi_fields.append(expi_field)
            arcpy.AddField_management(suit_fc, expi_field, "LONG")
            with arcpy.da.UpdateCursor(suit_fc, [ex_lu_field, pipe_field, expi_field]) as c:
                for r in c:
                    ex_val, pipe_val, expi_val = r
                    r[-1] = ex_val + pipe_val
                    c.updateRow(r)

        # apply TOD templates
        if USE_NET:
            # Net-based run:
            applyTODTemplates(in_gdb=scen_gdb, fishnet_fc=suit_fc, fishnet_id=id_field, technology_name=TECH,
                              fishnet_suitability_field='tot_suit', fishnet_where_clause="", network_dataset=walk_net,
                              impedance_attribute='Length', restrictions=None, preset_stations_field=None,
                              weight_by_area=True, share_threshold=0.5)
            dev_area_tbl = path.join(scen_gdb, 'dev_area_activities_net_suit')
        else:
            # Simple buffer-based run:
            applyTODTemplates(in_gdb=scen_gdb, fishnet_fc=suit_fc, fishnet_id=id_field, technology_name=TECH,
                              fishnet_suitability_field='tot_suit', fishnet_where_clause="",
                              preset_stations_field=None, weight_by_area=True, share_threshold=0.5)
            dev_area_tbl = path.join(scen_gdb, 'dev_area_activities_suit')

        # Adjust dev_area_activities_net_suit  activity values to SQFT
        # -- Add fields
        tgt_sf_field_dict = {
            "SF_SF_Tgt": ("RES", "shr_sfr", "sfr_sqft"),
            "MF_SF_Tgt": ("RES", "shr_mfr", "mfr_sqft"),
            "Ind_SF_Tgt": ("JOB", "shr_ind", "ind_sqft"),
            "Ret_SF_Tgt": ("JOB", "shr_ret", "ret_sqft"),
            "Off_SF_Tgt": ("JOB", "shr_off", "off_sqft"),
            "Hot_SF_Tgt": ("HOTEL", "shr_hot", "hot_sqft")
        }
        tgt_sf_fields = sorted(tgt_sf_field_dict.keys())
        for tgt_sf_field in tgt_sf_fields:
            arcpy.AddField_management(dev_area_tbl, tgt_sf_field, "LONG")
            arcpy.CalculateField_management(dev_area_tbl, tgt_sf_field, 0)
        # -- Dump reference tables
        stations_df = pd.DataFrame(arcpy.da.TableToNumPyArray(stations, ["stn_name", "stn_type"]))
        stn_type_fields = ["stn_type"] + [fld for k in tgt_sf_fields for fld in tgt_sf_field_dict[k][-2:]]
        stn_types_df = pd.DataFrame(arcpy.da.TableToNumPyArray(in_table=st_type_tbl, field_names=stn_type_fields))
        # -- Tack on existing + pipeline square footage fields to the dev_area_tbl
        append_fields = [id_field, "stn_name"] + expi_fields
        parcels_df = pd.DataFrame(
            arcpy.da.TableToNumPyArray(
                in_table=suit_fc, field_names=append_fields, null_value=0.0
            )
        )
        extendTableDf(in_table=dev_area_tbl, table_match_field=id_field,
                      df=parcels_df, df_match_field=id_field, append_only=False)

        # -- Update dev_area_tbl
        print "converting targets to square footage by land use"
        tgt_act_fields = list({tgt_sf_field_dict[k][0] for k in tgt_sf_fields})
        dev_area_fields = [id_field] + tgt_sf_fields + tgt_act_fields
        with arcpy.da.UpdateCursor(dev_area_tbl, dev_area_fields) as c:
            for r in c:
                parcel_id = r[0]
                stn_name = parcels_df[parcels_df[id_field] == parcel_id]["stn_name"].values[0]
                stn_type = stations_df[stations_df["stn_name"] == stn_name]["stn_type"].values[0] + ' - ' + TECH
                stn_type_data = stn_types_df[stn_types_df["stn_type"] == stn_type]
                for tgt_sf_field in tgt_sf_fields:
                    tgt_act_field, share_field, sqft_field = tgt_sf_field_dict[tgt_sf_field]
                    tgt_idx = dev_area_fields.index(tgt_act_field)
                    update_idx = dev_area_fields.index(tgt_sf_field)
                    tgt_val = r[tgt_idx]
                    if tgt_val > 0:
                        share = stn_type_data[share_field].values[0]
                        sqft = stn_type_data[sqft_field].values[0]
                        estimate = tgt_val * share * sqft
                        r[update_idx] = estimate
                        c.updateRow(r)

        adj_tgt_tbl = dev_area_tbl + "_adj"
        out_fields = [f.replace("Tgt", "Adj") for f in tgt_sf_fields]
        expi_refs = [f.replace("Tgt", "ExPi") for f in tgt_sf_fields]
        adjustTargetsBasedOnExisting2(dev_areas_table=dev_area_tbl, id_field=id_field,
                                      station_area_field="stn_name", existing_fields=expi_refs,
                                      target_fields=tgt_sf_fields, out_fields=out_fields, out_table=adj_tgt_tbl,
                                      where_clause=None)

        # TODO:  Blend TOD results with baseline parcel expected LU, mean FAR


except LicenseError:
    arcpy.AddWarning("Network Analyst not available to genreate walksheds")
except Exception as e:
    arcpy.AddMessage(e)
