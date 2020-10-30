import arcpy
import pandas as pd
import numpy as np

taz_file = r"C:\Users\V_RPG\Desktop\parceldata\RenPlan_TAZ_withSBFProjections.shp"
taz_fields = ['ID', 'LCRT', "LCRT_H20", "LCRT_H40", "LCRT_E20", "LCRT_E40", "RES_2040", "JOBS_2040"]

oid = arcpy.Describe(taz_file).OIDFieldName
fields = [oid] + taz_fields
data = [row for row in arcpy.da.SearchCursor(taz_file, fields)]
taz_df = pd.DataFrame(data, columns=fields)
taz_df = taz_df.set_index(oid, drop=True)

res_jobs_unique = taz_df[['ID', 'LCRT', "RES_2040", "JOBS_2040"]].drop_duplicates().set_index(keys='ID')
lcbrt_unique = taz_df.groupby('ID')["LCRT_H20", "LCRT_H40", "LCRT_E20", "LCRT_E40"].sum()

taz_df = lcbrt_unique.merge(res_jobs_unique, on='ID')

# analyze changes
taz_df['JOBS_CHANGE'] = taz_df["LCRT_E40"] - taz_df["LCRT_E20"]
taz_df['RES_CHANGE'] = taz_df["LCRT_H40"] - taz_df["LCRT_H20"]
taz_df['JOB_GROWTH'] = np.where(taz_df['JOBS_CHANGE'] > 0, 1, 0)
taz_df['RES_GROWTH'] = np.where(taz_df['RES_CHANGE'] > 0, 1, 0)

# determine off the top factors
# 2020 sums
cor_sum_jobs_2020 = taz_df.loc[taz_df['LCRT'] == 1, 'LCRT_E20'].sum()
cor_sum_jobs_2040 = taz_df.loc[taz_df['LCRT'] == 1, 'LCRT_E40'].sum()
cor_sum_jobs_growing = taz_df.loc[(taz_df['LCRT'] == 1) and (taz_df['JOB_GROWTH'] == 1) ].sum()
cor_sum_jobs_notgrowing = taz_df.loc[(taz_df['LCRT'] == 1) and (taz_df['JOB_GROWTH'] == 0)].sum()
nocor_sum_res_2020 = taz_df.loc[taz_df['LCRT'] == 0, 'LCRT_E20'].sum()
nocor_sum_res_2040 = taz_df.loc[taz_df['LCRT'] == 0, 'LCRT_E40'].sum()
nocor_sum_res_growing = taz_df.loc[(taz_df['LCRT'] == 1) and (taz_df['RES_GROWTH'] == 1),].sum()
nocor_sum_res_notgrowing = taz_df.loc[(taz_df['LCRT'] == 1) and (taz_df['RES_GROWTH'] == 0)].sum()
print('Read in')