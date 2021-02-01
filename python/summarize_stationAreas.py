# %% Imports
import arcpy
import os
import pandas as pd

# %% factors
activity_sf_factors = {
    "SF": 1800,
    "MF": 1200,
    "Ret": 720,
    "Ind": 2342,
    "Off": 206,
    "Hot": 700,
}

unit_to_hh_factors = {
    "SF": 0.95,
    "MF": 0.93
}

# Use groupings
RES = ["SF", "MF"]
NRES = ["Ret", "Ind", "Off"]
HOTEL = ["Hot"]
UNTRACKED = ["Oth"]
USES = RES + NRES + HOTEL + UNTRACKED


# %% functions
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


# %% variable setup
# fields of interest
id_field = "ParclID"
station_name = 'stn_name'
ex_lu_fields = genFieldList(suffix="Ex", include_untracked=False)
pipe_fields = genFieldList(suffix="Pipe", include_untracked=False)
alloc_fields = genFieldList(suffix="Alloc", include_untracked=False)
future_fields = genFieldList(suffix="Fut", include_untracked=False)

# %% read in data
scen_path = r'K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\WE_Sum'
gdb = 'WE_Sum_scenario.gdb'
parcels = os.path.join(scen_path, gdb, 'parcels_bldSqft_update_1202')

p_fields = [id_field, station_name] + ex_lu_fields + pipe_fields + alloc_fields + future_fields

pdf = pd.DataFrame(
    arcpy.da.TableToNumPyArray(
        in_table=parcels, field_names=p_fields, null_value=0.0
    )
).set_index(id_field)

# %% summarize data at station area
station_summaries = pdf.groupby(station_name).sum()

# summary of Households by phase
station_summaries["HH_EX"] = (
        ((station_summaries[ex_lu_fields[0]] / activity_sf_factors["SF"]) * unit_to_hh_factors["SF"]) +
        ((station_summaries[ex_lu_fields[1]] / activity_sf_factors["MF"]) * unit_to_hh_factors["MF"])
).astype(int)
station_summaries["HH_PIPE"] = (
        ((station_summaries[pipe_fields[0]] / activity_sf_factors["SF"]) * unit_to_hh_factors["SF"]) +
        ((station_summaries[pipe_fields[1]] / activity_sf_factors["MF"]) * unit_to_hh_factors["MF"])
).astype(int)
station_summaries["HH_ALLOC"] = (
        ((station_summaries[alloc_fields[0]] / activity_sf_factors["SF"]) * unit_to_hh_factors["SF"]) +
        ((station_summaries[alloc_fields[1]] / activity_sf_factors["MF"]) * unit_to_hh_factors["MF"])
).astype(int)
station_summaries["HH_2040"] = (station_summaries['HH_PIPE'] +
                                station_summaries['HH_ALLOC'] +
                                station_summaries['HH_EX'])
# summary of jobs by phase
station_summaries["JOBS_EX"] = (
        (station_summaries[ex_lu_fields[2]] / activity_sf_factors["Ret"]) +
        (station_summaries[ex_lu_fields[3]] / activity_sf_factors["Ind"]) +
        (station_summaries[ex_lu_fields[4]] / activity_sf_factors["Off"]) +
        (station_summaries[ex_lu_fields[5]] / activity_sf_factors["Hot"])).astype(int)
station_summaries["JOBS_PIPE"] = (
        (station_summaries[pipe_fields[2]] / activity_sf_factors["Ret"]) +
        (station_summaries[pipe_fields[3]] / activity_sf_factors["Ind"]) +
        (station_summaries[pipe_fields[4]] / activity_sf_factors["Off"]) +
        (station_summaries[pipe_fields[5]] / activity_sf_factors["Hot"])).astype(int)
station_summaries["JOBS_ALLOC"] = (
        (station_summaries[alloc_fields[2]] / activity_sf_factors["Ret"]) +
        (station_summaries[alloc_fields[3]] / activity_sf_factors["Ind"]) +
        (station_summaries[alloc_fields[4]] / activity_sf_factors["Off"]) +
        (station_summaries[alloc_fields[5]] / activity_sf_factors["Hot"])).astype(int)
station_summaries["JOBS_2040"] = (station_summaries['JOBS_PIPE'] +
                                  station_summaries['JOBS_ALLOC'] +
                                  station_summaries['JOBS_EX'])
# reset index to stn_name
station_summaries.reset_index(inplace=True)

# drop summary of parcels outside station areas
station_summaries.drop(index=0, inplace=True)

# %% write to csv
station_summaries.to_csv(os.path.join(scen_path, 'station_area_summaries.csv'))
