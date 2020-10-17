"""
#TODO: clean up all data inputs for an authoritative source gdb
#TODO: handle segment-level control totals and document vars here
#TODO: report FAR, units per acre, lu mix by station area, segment (this might be just as easily done in a dashboard)
#TODO: station area typology spreadsheet ingestion tool (might be a separate tool?)

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
      - `SHARE_THRESHOLD`: The proportion of a parcel feature that needs to overlap a 
         TOD station area polygon to be considered "within" the station area.

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
      - `par_bld_sqft_field`: estimated building area
      - 'par_sqft_field': estimate FAR
      - `lu_field`: current land use
      - `par_est_fld_ref`: Dictionary with keys listing expected (relevant)
        categories in `lu_field` and values that relate each category to a use in 
        `USES`
      - `is_do_field`: is the parcel a development opportunity site? (0/1)
      - `do_prop_field`: what proportion of the parcel is a D.O. site?
      - `acres_field`: parcel area in acreage
      - `seg_id_field`: the analysis segment the parcel belongs to
      - `in_pipe_field`: is development in the pipeline for the parcel? (0/1)
      - `excl_lu`: List of land use categores in `lu_field` that are excluded in
         TOD templating (i.e, are assumed to have no potential for future development)
      - `basecap_sqft`: the estimated baseline capacity square footage for parcel
         development potential outside TOD areas.
      - `basecap_lu`: the expected land use for parcel develoment potential outside
         TOD areas. Values are expected to be found in `par_est_fld_ref`.
    
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
    
  - `walk_net`: The network dataset to be used when creating station area walksheds and
     defining TOD station areas (if `USE_NET` is True).
      - `imp_field`: The impedance attribute of `walk_net` to use when creating walkshed
         service areas.
      - `cost`: The size of the walkshed service area in the same units used for 
         `imp_field`. Unit details are recorded in the network dataset's Properties 
         dialog.
      - `restrictions`: Restriction attributes in `walk_net` to honor when defining 
         station areas. To ignore restrictions, set this variable to `None`.

DERIVED INPUTS/SPECS:
  - `par_est_fields`: a list of fields that will be added to `parcels` as an estimate
    of total existing floor area based on parcel attributes alone.
  - `new_dev_fields`: a list of fields that will be added to `parcels` as an estimate
    of recently-delivered floor area.
  - `ex_lu_fields`: a list of fields that will be added to `parcels` as an estimate
    of total existing floor area based on parcel-based floor area estimtes 
    (`par_est_fields`) and floor area estimated for recently delivered developments 
    (`new_dev_fields`)
  - `pipe_fields`: a list of fields that will be added to `parcels` as an estimate
    of commited floor area in the pipeline.


The key steps in the scenario generation process are outlined below:
  - Create the output scenario workspace
  - Iterate over scenarios
      - Delete existing gdb if present
      - Create a fresh analysis gdb
      - Add station type embellishments from csv
      - Import stations from source gdb to scenario gdb, applying selection
      - Generate station walksheds
      - Evaluate parcel suitability for this scenario
      - Add existing (parcel based, new dev) and pipeline floor area estimates to 
        scenario parcels
      - Apply TOD templates for basic parcel build-out target setting
      - Convert parcel activity targets to floor area targets
         - Fetch station associated with each parcel
         - Fetch station type for this scenario
         - Proportion RES, JOB, HOTEL target into sub-uses based on use groupings
            TODO: make this a little smarter by using the USES global lists?
         - Apply floor area assumptions
      - Adjust build-out targets for each parcel based on existing + pipeline floor area
      - Blend TOD build out capacity with non-TOD build-out capacity
      - Subtract existing floor area from build-out capacity to estimate change capacity
      - Run allocation by segment
      - Populate attributes valuable for story telling and visualization
        - Buildout activity (EXPI + ALLOC)
        - EXPI, ALLOC and BUILDOUT activity sum by parcel
        - FAR value by Activity for each phase (EXPI, ALLOC, BUILDOUT)
        - weighted station area FAR for Dashboard indicator
      - Generate Segment and TAZ level summaries of JOBS and HOUSING Units (EMP, RES)
        - append summaries to segment and taz
        - generate difference between RP buildout and COG buildout numbers
"""

# %% IMPORTS

import arcpy
from pathlib import Path
import sys

sys.path.append(Path(__file__).parent)
from suitability import generate_suitability
from walksheds import generate_walksheds
from existing_sqft import sqFtByLu
from allocation import allocate_df, allocate_dict
from os import path
from tod.TOD import (
    createTODTemplatesGDB,
    applyTODTemplates,
    adjustTargetsBasedOnExisting2,
)
from tod.HandyGP import extendTableDf, dfToArcpyTable
import pandas as pd
import numpy as np

# %% WORKSPACES AND SCENARIO NAMES.

project_dir = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3"
source_gdb = str(Path(project_dir, "LCBRT_data.gdb"))
scenarios_ws = str(Path(project_dir, "scenarios"))
scenarios = ["WE_Sum", "WE_Fair"]
arcpy.env.overwriteOutput = True

# %% GLOBAL SETTINGS/SPECS
USE_NET = False
TECH = "BRT"
SHARE_THRESHOLD = 0.5

# Use groupings
RES = ["SF", "MF"]
NRES = ["Ret", "Ind", "Off"]
HOTEL = ["Hot"]
UNTRACKED = ["Oth"]
USES = RES + NRES + HOTEL + UNTRACKED

# Suitability weightings
weights = {
    "in_DO": 0.6,
    "is_vacant": 0.15,
    "in_TOD": 0.05,
    "in_walkshed": 0.1,
    "dev_size": 0.1,
}

activity_sf_factors = {
    "SF": 1800,
    "MF": 1200,
    "Ret": 500,
    "Ind": 800,
    "Off": 400,
    "Hot": 500,
}


# %% HELPER FUNCTIONS AND CLASSES
class LicenseError(Exception):
    pass


def genFieldList(suffix, measure="SF", include_untracked=True):
    """
    Generates a list of fields based on use groupings with the form:
    `{UseGroup}_SF_{suffix}`, recording the square footage (SF) for each
    use grouping for a time frame indicated by the suffix.
    """
    global USES, UNTRACKED
    if include_untracked:
        return ["{}_{}_{}".format(use, measure, suffix) for use in USES]
    else:
        return [
            "{}_{}_{}".format(use, measure, suffix)
            for use in USES
            if use not in UNTRACKED
        ]


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
            # TODO: smarter error
        out_dict[k] = "{}_SF_{}".format(v, suffix)
    return out_dict


def makeTargetFieldsDict(tgt_fields):
    """
    Create a dictionary that facilitates conversion of activity targets to floor area
    targets based on tod typology embellishments. Assumed well-named fields in the
    embellishments table.

    dictionary structure: {target field: (activity_field, share_field, sqft_field)}
    """
    global RES, NRES, HOTEL
    out_dict = {}
    for fld in tgt_fields:
        use, suffix = fld.split("_SF_")
        if use in RES:
            act_field = "RES"
        elif use in NRES:
            act_field = "JOB"
        elif use in HOTEL:
            act_field = "HOTEL"
        else:
            # This is an untracked ause
            continue
        share_field = "shr_{}".format(use)
        sqft_field = "{}_sqft".format(use)
        out_dict[fld] = (act_field, share_field, sqft_field)
    return out_dict


# %% INPUT DATA SETS
# Parcels
parcels = "parcels"
parcels = str(Path(source_gdb, parcels))
id_field = "ParclID"
lu_field = "LandUse"
par_est_fld_ref = {
    "Commercial/Retail": "Ret",
    "Industrial/Manufacturing": "Ind",
    "Institutional": "Off",
    "Multifamily": "MF",
    "Office": "Off",
    "Single-family": "SF",
    "Hospitality": "Hot",
    "Other": "Oth",
}
par_bld_sqft_field = "BldSqFt"
par_sqft_field = "Sq_Feet"
is_do_field = "DO_Site"
do_prop_field = "DOSProp"
acres_field = "Area_AC"
seg_id_field = "seg_num"
in_pipe_field = "in_pipe"
excl_lu = ["Recreation/Cultural", "Single-family", "Transportation", "Utilities"]
basecap_sqft = "EXP_Sqft"
basecap_lu = "Exp_LU"

# New/pipeline features
newpipe_fc = "pipeline_with_pid"
newpipe_fc = str(Path(source_gdb, newpipe_fc))
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
    "Student New": "Oth",
    "Single Family": "SF",
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
    "Student Pipeline": "Oth",
    "Single Family": "SF",
}
new_dev_wc = arcpy.AddFieldDelimiters(newpipe_fc, newpipe_lu) + "LIKE '%New'"
pipe_wc = arcpy.AddFieldDelimiters(newpipe_fc, newpipe_lu) + "LIKE '%Pipeline'"

# Stations
stations = "stations_LCRT_BRT_scenarios_20200814"
st_type_emb_tbl = str(Path(project_dir, "tables", "tod_type_shares.csv"))

# Network
walk_net = str(Path(source_gdb, "network", "walk_network_ND"))
imp_field = "Length"
cost = "1320"
restrictions = None

# TAZ
taz = str(Path(source_gdb, "TAZ_LCRT_SBF08122020v2"))
tid = "Big_TAZ"

# Control variables
control_tbl = str(Path(project_dir, "tables\control_totals.csv"))
control_fields = ["Ind", "Ret", "MF", "SF", "Off", "Hot"]
control_seg_attr = "segment"

# %% DERIVED INPUTS/SPECS
par_est_fields = genFieldList(suffix="Par")  # Parcel estimates of existing floor area
new_dev_fields = genFieldList(
    suffix="New"
)  # New dev pts estimates of existing floor area
ex_lu_fields = genFieldList(
    suffix="Ex"
)  # Estimates of existing floor are (parcel-based + new-dev)
pipe_fields = genFieldList(suffix="Pipe")  # Pipeline floor area
expi_fields = genFieldList(suffix="ExPi")  # Existing + pipeline floor area
tgt_sf_fields = genFieldList(
    suffix="Tgt", include_untracked=False
)  # Target floor area (from TOD template application)
tgt_sf_field_dict = makeTargetFieldsDict(
    tgt_sf_fields
)  # Dictionary for conversion of TOD template activities to floor area
adj_fields = genFieldList(
    suffix="Adj", include_untracked=False
)  # Adjusted floor area targets (TOD templates adjusted based on expi)
basecap_fields = genFieldList(
    suffix="BCap", include_untracked=False
)  # Build-out capacity for non-TOD parcels (from expected LU and FAR)
totcap_fields = genFieldList(
    suffix="TotCap", include_untracked=False
)  # Total capacity, blended from TOD and non-TOD
chgcap_fields = genFieldList(
    suffix="ChgCap", include_untracked=False
)  # Capacity for change (total capacity minus existing)

# allocation fields
alloc_fields = genFieldList(
    suffix="Alloc", include_untracked=False
)  # allocated sqft in at buildout based on suitability, capacity for change and control sqft anticipated
# buildout fields
build_fields = genFieldList(suffix="Build", include_untracked=False)

# FAR conversions for AGOL
far_expi_fields = genFieldList(
    suffix="ExPi", measure="FAR", include_untracked=False
)  # FAR for existing and pipeline
far_alloc_fields = genFieldList(
    suffix="Alloc", measure="FAR", include_untracked=False
)  # FAR allocated
far_build_fields = genFieldList(
    suffix="build", measure="FAR", include_untracked=False
)  # FAR available overall (TOD/non-TOD)

# %% PROCESS
try:
    if arcpy.CheckExtension("Network") == "Available":
        arcpy.CheckOutExtension("Network")
    else:
        raise LicenseError

    # Setup working environments for each scenario
    arcpy.env.workspace = str(source_gdb)
    scenarios_sr = arcpy.Describe(parcels).spatialReference

    # create scenario folder if not already there
    if not arcpy.Exists(scenarios_ws):
        pth, name = path.split(scenarios_ws)
        arcpy.CreateFolder_management(out_folder_path=pth, out_name=name)
    # Run each scenario
    for scenario in scenarios:
        # Create the scenario workspace folder if needed
        print("---Scenario: {}---".format(scenario))
        scen_ws = path.join(scenarios_ws, scenario)
        scen_gdb = path.join(scen_ws, "{}_scenario.gdb".format(scenario))
        if not arcpy.Exists(scen_ws):
            arcpy.CreateFolder_management(
                out_folder_path=scenarios_ws, out_name=scenario
            )

        # Drop scenario gdb for a clean run
        #  (NumPyArrayToTable cannot overwrite existing tables)
        if arcpy.Exists(scen_gdb):
            print("Deleting existing scenario db for new run...")
            arcpy.Delete_management(scen_gdb)

        # Create the scenario gdb
        print("Creating scenario gdb...")
        scen_gdb = createTODTemplatesGDB(
            in_folder=scen_ws,
            gdb_name="{}_scenario.gdb".format(scenario),
            sr=scenarios_sr,
        )

        # Check if sqft embellishments have been added already
        #  (most of this is currently superfluous since we drop and recreate the gdb
        #   with each run)
        print("Extending station types table with embellishments...")
        st_type_tbl = str(Path(scen_gdb, "station_area_types"))
        type_emb = pd.read_csv(st_type_emb_tbl)
        type_emb_arr = np.array(
            np.rec.fromrecords(
                recList=type_emb.values, names=type_emb.dtypes.index.tolist()
            )
        )
        # Add embellishsments
        arcpy.da.ExtendTable(
            in_table=st_type_tbl,
            table_match_field="stn_type",
            in_array=type_emb_arr,
            array_match_field="stn_type",
        )

        # Import scenario stations into the new GDB
        print("Pushing scenario stations to gdb...")
        stations_wc = arcpy.AddFieldDelimiters(stations, scenario) + " <> 'NA'"
        stations_fl = arcpy.MakeFeatureLayer_management(
            in_features=stations, out_layer="stat_scenario", where_clause=stations_wc
        )

        # Assume stations source has the template fields already populated (stn_type, stn_name, stn_order)
        arcpy.Append_management(
            inputs=stations_fl,
            target=str(Path(scen_gdb, "stations")),
            schema_type="NO_TEST",
        )
        """ TODO: modify TOD.py to generate customized tables 
            (ie _todTemplatesFromConfig() ...insert csv as templates for stn_types and gradients)
            existing strategy is to modify the defaults to fit LCRT needs
        """
        # Build walkshed for suitability calculations
        print("Generating walksheds...")
        walk_shed = generate_walksheds(
            stations=stations_fl,
            walk_net=walk_net,
            imp_field=imp_field,
            cost=cost,
            out_gdb=scen_gdb,
            stations_wc=None,
        )

        # generate suitability table and tack on the tot_suit to parcel data
        print("Evaluating suitability...")
        suit_fc, suit_table = generate_suitability(
            in_suit_fc=parcels,
            id_field=id_field,
            is_do_field=is_do_field,
            do_prop_field=do_prop_field,
            acres_field=acres_field,
            seg_id_field=seg_id_field,
            lu_field=lu_field,
            pipe_field=in_pipe_field,
            stations=stations_fl,
            station_buffers=walk_shed,
            weights=weights,
            out_gdb=scen_gdb,
            excl_lu=excl_lu,
            stations_wc=None,
        )

        # Estimate existing, pipeline development
        #  -- Parcel-based estimates
        print(
            "Appending existing activity data to parcel features based on parcel attributes"
        )
        _par_est_fld_ref = makeFieldRefDict(par_est_fld_ref, "Par")
        sqFtByLu(
            in_fc=suit_fc,
            sqft_field=par_bld_sqft_field,
            lu_field=lu_field,
            lu_field_ref=_par_est_fld_ref,
            where_clause=None,
        )

        # -- From New Dev features
        print("...Estimating new activity")
        newpipe = arcpy.FeatureClassToFeatureClass_conversion(
            newpipe_fc, scen_gdb, "newpipe"
        )
        _new_dev_fld_ref = makeFieldRefDict(new_dev_fld_ref, "New")
        sqFtByLu(
            in_fc=newpipe,
            sqft_field=newpipe_sqft,
            lu_field=newpipe_lu,
            lu_field_ref=_new_dev_fld_ref,
            where_clause=new_dev_wc,
        )

        # -- Pipeline dev
        print("...Estimating pipeline development")
        _pipe_fld_ref = makeFieldRefDict(pipe_fld_ref, "Pipe")
        sqFtByLu(
            in_fc=newpipe,
            sqft_field=newpipe_sqft,
            lu_field=newpipe_lu,
            lu_field_ref=_pipe_fld_ref,
            where_clause=pipe_wc,
        )

        # -- Sum to parcels
        print("...Summarizing new and pipeline data to parcel level")
        newpipe_fields = [newpipe_par_field] + new_dev_fields + pipe_fields
        newpipe_df = pd.DataFrame(
            arcpy.da.TableToNumPyArray(
                in_table=newpipe, field_names=newpipe_fields, null_value=0
            )
        )
        newpipe_sum = newpipe_df.groupby(newpipe_par_field).sum().reset_index()
        # -- Extend table
        print("...Adding new and pipeline data to parcels")
        extendTableDf(
            in_table=suit_fc,
            table_match_field=id_field,
            df=newpipe_sum,
            df_match_field=newpipe_par_field,
            append_only=False,
        )

        # -- Calculate fields
        print("...Calculating existing (parcel-based + new development)")
        for ex_lu_field, par_est_field, new_dev_field in zip(
            ex_lu_fields, par_est_fields, new_dev_fields
        ):
            arcpy.AddField_management(suit_fc, ex_lu_field, "LONG")
            with arcpy.da.UpdateCursor(
                suit_fc, [par_est_field, new_dev_field, ex_lu_field]
            ) as c:
                for r in c:
                    par_val, new_dev_val, ex_lu_val = r
                    if new_dev_val:
                        r[-1] = new_dev_val
                    else:
                        r[-1] = par_val
                    c.updateRow(r)

        print("...Calculating existing + pipeline")
        for ex_lu_field, pipe_field, expi_field in zip(
            ex_lu_fields, pipe_fields, expi_fields
        ):
            arcpy.AddField_management(suit_fc, expi_field, "LONG")
            with arcpy.da.UpdateCursor(
                suit_fc, [ex_lu_field, pipe_field, expi_field]
            ) as c:
                for r in c:
                    ex_val, pipe_val, expi_val = r
                    if ex_val is None:
                        ex_val = 0
                    if pipe_val is None:
                        pipe_val = 0
                    r[-1] = ex_val + pipe_val
                    c.updateRow(r)

        # Apply TOD templates
        print("Applying TOD templates...")
        if USE_NET:
            # Net-based run:
            applyTODTemplates(
                in_gdb=scen_gdb,
                fishnet_fc=suit_fc,
                fishnet_id=id_field,
                technology_name=TECH,
                fishnet_suitability_field="tot_suit",
                fishnet_where_clause="",
                network_dataset=walk_net,
                impedance_attribute=imp_field,
                restrictions=restrictions,
                preset_stations_field=None,
                weight_by_area=True,
                share_threshold=SHARE_THRESHOLD,
            )
            dev_area_tbl = path.join(scen_gdb, "dev_area_activities_net_suit")
        else:
            # Simple buffer-based run:
            applyTODTemplates(
                in_gdb=scen_gdb,
                fishnet_fc=suit_fc,
                fishnet_id=id_field,
                technology_name=TECH,
                fishnet_suitability_field="tot_suit",
                fishnet_where_clause="",
                preset_stations_field=None,
                weight_by_area=True,
                share_threshold=SHARE_THRESHOLD,
            )
            dev_area_tbl = path.join(scen_gdb, "dev_area_activities_suit")

        # Adjust dev_area_activities_net_suit  activity values to SQFT
        print(
            "Converting activity targets to Sq Ft targets from station type embellishments..."
        )

        for tgt_sf_field in tgt_sf_fields:
            arcpy.AddField_management(dev_area_tbl, tgt_sf_field, "LONG")
            arcpy.CalculateField_management(dev_area_tbl, tgt_sf_field, 0)

        # -- Dump reference tables: stations, station_types, parcels
        stations_df = pd.DataFrame(
            arcpy.da.TableToNumPyArray(stations, ["stn_name", "stn_type"])
        )
        stn_type_fields = ["stn_type"] + [
            fld for k in tgt_sf_fields for fld in tgt_sf_field_dict[k][-2:]
        ]
        stn_types_df = pd.DataFrame(
            arcpy.da.TableToNumPyArray(
                in_table=st_type_tbl, field_names=stn_type_fields
            )
        )
        append_fields = [id_field, "stn_name"] + expi_fields
        parcels_df = pd.DataFrame(
            arcpy.da.TableToNumPyArray(
                in_table=suit_fc, field_names=append_fields, null_value=0.0
            )
        )

        # -- Update dev_area_tbl to include more specific activity type sqft
        tgt_act_fields = list({tgt_sf_field_dict[k][0] for k in tgt_sf_fields})
        dev_area_fields = [id_field] + tgt_sf_fields + tgt_act_fields
        with arcpy.da.UpdateCursor(dev_area_tbl, dev_area_fields) as c:
            for r in c:
                parcel_id = r[0]
                stn_name = parcels_df[parcels_df[id_field] == parcel_id][
                    "stn_name"
                ].values[0]
                stn_type = " - ".join(
                    [
                        stations_df[stations_df["stn_name"] == stn_name][
                            "stn_type"
                        ].values[0],
                        TECH,
                    ]
                )
                stn_type_data = stn_types_df[stn_types_df["stn_type"] == stn_type]
                for tgt_sf_field in tgt_sf_fields:
                    tgt_act_field, share_field, sqft_field = tgt_sf_field_dict[
                        tgt_sf_field
                    ]
                    tgt_idx = dev_area_fields.index(tgt_act_field)
                    update_idx = dev_area_fields.index(tgt_sf_field)
                    tgt_val = r[tgt_idx]
                    if tgt_val > 0:
                        share = stn_type_data[share_field].values[0]
                        sqft = stn_type_data[sqft_field].values[0]
                        estimate = tgt_val * share * sqft
                        r[update_idx] = estimate
                        c.updateRow(r)

        # -- Tack on existing + pipeline square footage fields to the dev_area_tbl
        extendTableDf(
            in_table=dev_area_tbl,
            table_match_field=id_field,
            df=parcels_df,
            df_match_field=id_field,
            append_only=False,
        )

        # Adjust build-out targets based on existing and pipeline development
        print("Adjusting build-out targets based on existing and pipeline development")
        adj_tgt_tbl = dev_area_tbl + "_adj"
        tgt_suffix = tgt_sf_fields[0].split("_SF_")[-1]
        expi_suffix = expi_fields[0].split("_SF_")[-1]
        expi_refs = [f.replace(tgt_suffix, expi_suffix) for f in tgt_sf_fields]
        adjustTargetsBasedOnExisting2(
            dev_areas_table=dev_area_tbl,
            id_field=id_field,
            station_area_field="stn_name",
            existing_fields=expi_refs,
            target_fields=tgt_sf_fields,
            out_fields=adj_fields,
            out_table=adj_tgt_tbl,
            where_clause=None,
        )

        print("Blending TOD and baseline capacity estimates")
        # "Pivot out" the baseline expected floor area for all parcels
        print("...Pivoting baseline development capacity")
        bcap_suffix = basecap_fields[0].split("_SF_")[-1]
        _bcap_fld_ref = makeFieldRefDict(par_est_fld_ref, bcap_suffix)
        bcap_wc = arcpy.AddFieldDelimiters(suit_fc, in_pipe_field) + " <> 1"
        sqFtByLu(
            in_fc=suit_fc,
            sqft_field=basecap_sqft,
            lu_field=basecap_lu,
            lu_field_ref=_bcap_fld_ref,
            where_clause=bcap_wc,
        )
        # -- Dump basecaps to df
        bcap_df_fields = [id_field] + basecap_fields
        bcap_df = pd.DataFrame(
            arcpy.da.TableToNumPyArray(
                in_table=suit_fc, field_names=bcap_df_fields, null_value=0.0
            )
        )
        # -- Dump adjusted TOD caps to df
        print("...masking baseline capacity with TOD capacity")
        adj_df_fields = [id_field] + adj_fields
        adj_df = pd.DataFrame(
            arcpy.da.TableToNumPyArray(in_table=adj_tgt_tbl, field_names=adj_df_fields)
        )
        # -- Merge and update TOD and base cap
        cap_df = bcap_df.merge(adj_df, how="left", on=id_field)
        for tcap, bcap, acap in zip(totcap_fields, basecap_fields, adj_fields):
            acap_filter = cap_df[acap] is not None
            cap_df[tcap] = np.select(
                [acap_filter, ~acap_filter],
                [cap_df[acap], cap_df[bcap]],
                default=np.nan,
            )
        # -- export full capacity estimates
        print("...exporting blended capacity to 'capacity' table")
        capacity_table = path.join(scen_gdb, "capacity")
        dfToArcpyTable(cap_df, capacity_table)

        print("Calculating change capacity")
        # Get existing activity (ex_lu_fields)
        ex_array_fields = [id_field] + ex_lu_fields
        exist_array = arcpy.da.TableToNumPyArray(
            suit_fc, ex_array_fields, null_value=0.0
        )
        # Extend capacity table
        arcpy.da.ExtendTable(capacity_table, id_field, exist_array, id_field)
        # Add fields and update
        for ccap_field, tcap_field, ex_lu_field in zip(
            chgcap_fields, totcap_fields, ex_lu_fields
        ):
            arcpy.AddField_management(capacity_table, ccap_field, "LONG")
            with arcpy.da.UpdateCursor(
                capacity_table, [ccap_field, tcap_field, ex_lu_field]
            ) as c:
                for r in c:
                    ccap, tcap, ex = r
                    if tcap is None:
                        r[0] = 0
                    elif ex is None:
                        r[0] = tcap
                    else:
                        if tcap - ex < 0:
                            r[0] = 0
                        else:
                            r[0] = tcap - ex
                    c.updateRow(r)
        # Dump tot-capacity fields into suitabiltiy fc for FAR calcs
        tcap_fields = [id_field] + totcap_fields + chgcap_fields
        cap_array = arcpy.da.TableToNumPyArray(
            capacity_table, tcap_fields, null_value=0.0
        )
        arcpy.da.ExtendTable(suit_fc, id_field, cap_array, id_field)

        # Run allocation
        print(
            "Allocating square footage based on change capacity and segment level control totals"
        )
        pipe_fields_noOther = pipe_fields[:-1]
        p_flds = (
            [id_field, seg_id_field, "tot_suit"] + chgcap_fields + pipe_fields_noOther
        )
        pdf = pd.DataFrame(
            arcpy.da.TableToNumPyArray(
                in_table=suit_fc, field_names=p_flds, null_value=0.0
            )
        ).set_index(keys=id_field)

        """ read control table to df """
        control_fields = ["Ind", "Ret", "MF", "SF", "Off", "Hot"]
        control_seg_attr = "segment"
        demand_phase = "group"
        ctl_df = pd.read_csv(
            control_tbl, usecols=control_fields + [control_seg_attr, demand_phase]
        ).set_index(control_seg_attr)
        ctl_df = ctl_df[ctl_df[demand_phase] == "net"].drop(demand_phase, axis=1)

        """ remove activity sqft already absorbed by pipeline development """
        pipeline_df = pdf[[seg_id_field] + pipe_fields_noOther]
        pipeline_by_seg = pipeline_df.groupby(seg_id_field).sum()
        for col in ctl_df.columns:
            idx = ctl_df.columns.get_loc(col)
            ctl_df[col] = np.where(
                (ctl_df[col] != 0), ctl_df[col] - pipeline_by_seg.iloc[:, idx], 0
            )
            ctl_df[col] = np.where((ctl_df[col] < 0), 0, ctl_df[col])

        """ run allocation """
        ctl_dict = ctl_df.T.to_dict()
        allocation_df = allocate_dict(
            suit_df=pdf,
            suit_id_field=id_field,
            suit_field="tot_suit",
            suit_df_seg_field=seg_id_field,
            suit_cap_fields=chgcap_fields,
            control_dict=ctl_dict,
        )

        # write out to parcels
        extendTableDf(
            in_table=suit_fc,
            table_match_field=id_field,
            df=allocation_df,
            df_match_field=id_field,
        )

        # populate buildout totals for each activity
        print("Calculating buildout sqft totals...")
        for (expi_field, alloc_field, build_field) in zip(
            expi_fields, alloc_fields, build_fields
        ):
            arcpy.AddField_management(suit_fc, build_field, "LONG")
            with arcpy.da.UpdateCursor(
                suit_fc, [expi_field, alloc_field, build_field]
            ) as cur:
                for row in cur:
                    act_list = [val for val in row if val is not None]
                    row[2] = sum(act_list)
                    cur.updateRow(row)

        # populate expi, alloc, and buildout parcel sum
        print("Calculating summary square footage for developement phases..")
        sum_sf_fields = ["ExPi_SF_sum", "Alloc_SF_sum", "Build_SF_sum"]
        activity_fields = [expi_fields, alloc_fields, build_fields]
        for summ, activities in zip(sum_sf_fields, activity_fields):
            arcpy.AddField_management(
                in_table=suit_fc, field_name=summ, field_type="LONG"
            )
            print("\tAdding {} for each parcel...".format(summ))
            with arcpy.da.UpdateCursor(
                in_table=suit_fc, field_names=[summ] + activities
            ) as cur:
                for row in cur:
                    act_list = [val for val in row[1:] if val is not None]
                    row[0] = sum(act_list)
                    cur.updateRow(row)

        # populate FAR by activity for visualization and summaries
        # far = activity_sqft/parcel_sqft
        print("Calculating FAR for each phase...")
        FAR_phases = [
            [alloc_fields, far_alloc_fields],
            [expi_fields, far_expi_fields],
            [build_fields, far_build_fields],
        ]
        for phase in FAR_phases:
            for act_sqft_field, act_far_field in zip(phase[0], phase[1]):
                arcpy.AddField_management(
                    in_table=suit_fc, field_name=act_far_field, field_type="DOUBLE"
                )
                with arcpy.da.UpdateCursor(
                    in_table=suit_fc,
                    field_names=[act_sqft_field, act_far_field, par_sqft_field],
                ) as c:
                    for r in c:
                        act_sqft, act_far, par_psqft = r
                        if act_sqft is None:
                            act_sqft = 0
                        r[1] = act_sqft / par_psqft
                        c.updateRow(r)

        # create station area weighted FAR values for Indicator summaries
        # create buildout summary sum_SF_build, activ_SF_build, wstat_FAR_build
        print("Calculating weighted FAR for each station area parcels...")
        station_sum_fields = ["Wstat_ExPi_far", "Wstat_Alloc_far", "Wstat_Build_far"]
        for field in station_sum_fields:
            arcpy.AddField_management(
                in_table=suit_fc, field_name=field, field_type="DOUBLE"
            )
        station_names = set(
            row[0] for row in arcpy.da.SearchCursor(suit_fc, "stn_name")
        )
        for station in station_names:
            if station is not None:
                suit_fl = arcpy.MakeFeatureLayer_management(
                    in_features=suit_fc,
                    out_layer="suit_fl",
                    where_clause="stn_name = '{}'".format(station),
                )
                land_areas = arcpy.da.TableToNumPyArray(
                    suit_fl, "SHAPE@AREA", skip_nulls=True
                )
                land_area = land_areas["SHAPE@AREA"].sum()
                with arcpy.da.UpdateCursor(
                    suit_fl,
                    ["SHAPE@AREA"]
                    + station_sum_fields
                    + expi_fields[:-1]
                    + alloc_fields
                    + build_fields,
                ) as cur:
                    for row in cur:
                        p_area, expi_far, alloc_far, build_far, ep_sf, ep_mf, ep_ret, ep_ind, ep_off, ep_hot, a_sf, a_mf, a_ret, a_ind, a_off, a_hot, b_sf, b_mf, b_ret, b_ind, b_off, b_hot = (
                            row
                        )
                        area_share = p_area / land_area  # land area share for station
                        ep_sqft_sum = (
                            ep_sf + ep_mf + ep_ret + ep_ind + ep_off + ep_hot
                        )  # sum of activity sqft
                        a_sqft_sum = (
                            a_sf + a_mf + a_ret + a_ind + a_off + a_hot
                        )  # sum of activity sqft
                        b_sqft_sum = (
                            b_sf + b_mf + b_ret + b_ind + b_off + b_hot
                        )  # sum of activity sqft
                        row[1] = (
                            ep_sqft_sum / p_area
                        ) * area_share  # sum of activity sqft/par_sqft [expi]
                        row[2] = (
                            a_sqft_sum / p_area
                        ) * area_share  # sum of activity sqft/par_sqft [alloc]
                        row[3] = (
                            b_sqft_sum / p_area
                        ) * area_share  # sum of activity sqft/par_sqft [buildout]
                        cur.updateRow(row)
                arcpy.Delete_management(suit_fl)

        # create Corridor Segment and TAZ summaries with conversion to RES and JOBS
        print("Generating Segment and TAZ summary tables...")
        taz = arcpy.FeatureClassToFeatureClass_conversion(
            in_features=taz, out_path=scen_gdb, out_name="taz"
        )
        p_fields = [id_field, "seg_num"] + expi_fields + alloc_fields + build_fields
        t_fields = [tid, "Share", "LCRT_H40", "LCRT_E40"]
        pwTAZ = arcpy.SpatialJoin_analysis(
            target_features=suit_fc,
            join_features=taz,
            out_feature_class="in_memory\parcels_wTAZ",
            match_option="INTERSECT",
        )
        p_df = pd.DataFrame(
            arcpy.da.TableToNumPyArray(
                in_table=pwTAZ, field_names=p_fields + t_fields, null_value=0.0
            )
        ).set_index(id_field)

        # segment summary
        seg_summaries = p_df.groupby(seg_id_field).sum()
        seg_summaries.drop(tid, axis=1, inplace=True)
        seg_summaries["RES_build"] = (
            seg_summaries[build_fields[0]] / activity_sf_factors["SF"]
        ) + (seg_summaries[build_fields[1]] / activity_sf_factors["MF"])
        seg_summaries["JOBS_build"] = (
            (seg_summaries[build_fields[2]] / activity_sf_factors["Ret"])
            + (seg_summaries[build_fields[3]] / activity_sf_factors["Ind"])
            + (seg_summaries[build_fields[4]] / activity_sf_factors["Off"])
        )  # + (seg_summaries[build_fields[5]] / activity_sf_factors["Hot"])
        seg_summaries.reset_index(inplace=True)

        # taz summary
        taz_summaries = p_df.groupby(tid).sum()
        taz_summaries.drop("seg_num", axis=1, inplace=True)

        taz_summaries["RES_build"] = (
            taz_summaries[build_fields[0]] / activity_sf_factors["SF"]
        ) + (taz_summaries[build_fields[1]] / activity_sf_factors["MF"])
        taz_summaries["JOBS_build"] = (
            (taz_summaries[build_fields[2]] / activity_sf_factors["Ret"])
            + (taz_summaries[build_fields[3]] / activity_sf_factors["Ind"])
            + (taz_summaries[build_fields[4]] / activity_sf_factors["Off"])
        )  # + (taz_summaries[buildout_flds[5]] / shares['Hot'])
        taz_summaries.reset_index(inplace=True)

        # write out tables
        taz_summaries.to_csv(path.join(scen_ws, "taz_summary.csv"))
        seg_summaries.to_csv(path.join(scen_ws, "seg_summary.csv"))

        # create DIFF between OUR RES/JOBS for TAZ to COG RES/JOBS for TAZ
        taz_sum_simple = taz_summaries[t_fields + ["RES_build", "JOBS_build"]]
        extendTableDf(
            in_table=taz,
            table_match_field=tid,
            df=taz_sum_simple,
            df_match_field=tid,
            append_only=False,
        )
        # update RES and JOBS to reflect proportion of full TAZ
        arcpy.CalculateField_management(
            in_table=taz,
            field="RES_build",
            expression="!RES_build! * !Share!",
            expression_type="PYTHON_9.3",
        )
        arcpy.CalculateField_management(
            in_table=taz,
            field="JOBS_build",
            expression="!JOBS_build! * !Share!",
            expression_type="PYTHON_9.3",
        )
        # calculate difference from current CoG estimates
        arcpy.AddField_management(
            in_table=taz, field_name="RES_diff", field_type="DOUBLE"
        )
        arcpy.AddField_management(
            in_table=taz, field_name="JOBS_diff", field_type="DOUBLE"
        )
        arcpy.CalculateField_management(
            in_table=taz,
            field="RES_diff",
            expression="!RES_build! - !LCRT_H40!",
            expression_type="PYTHON_9.3",
        )
        arcpy.CalculateField_management(
            in_table=taz,
            field="JOBS_diff",
            expression="!JOBS_build! - !LCRT_E40!",
            expression_type="PYTHON_9.3",
        )
        print("DONE!\n")


except LicenseError:
    arcpy.AddWarning("Network Analyst not available to generate walksheds")
except Exception as e:
    arcpy.AddMessage(e)
    raise

# %%
