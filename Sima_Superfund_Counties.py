#-------------------------------------------------------------------------------
# A Tool for Determining the Economic and Ecologic Vulnerability of US Counties
# Created by Andy Sima on May 7th, 2020
# 
# A GEOG380 Project for Dr. Kashem at
# the University of Illinois Urbana-Champaign
#
# Please see the downloadable ArcMap tool for further documentation.
#
# Description: This tool takes data from the American Community Survey (ACS),
# cleans it, joins it with the shapefile contained in that same dataset, and
# compares counties based on a variety of available demographic factors
# as well as the location of US EPA Priority Superfund Sites, or sites severaly
# contaminated by hazardous materials 
#
# Data: By default, this code is written to utilize the ACS 2017 data,
# available as ACS_2017_5YR_COUNTY.gdb and the metadata also available there.
# (https://www2.census.gov/geo/tiger/TIGER_DP/2017ACS/)
#
# However, the code is also compatible with more current ACS county surveys.
# Should you want to use the ACS Tracts data, it should also be compatible;
# though this may require tweaking the "Join Data" parameters and some GEOIDs.
# This code was developed with poverty data (table X17) in mind, though
# customization options are included.  Some example codes are given in tool help.
#
# The Superfund site data used for development are the SuperfundSites.gdb
# (https://catalog.data.gov/dataset/superfund-sites1e8f4/resource/c848a1a6-259d-4b59-8b27-3242c895bfc4)
# (ftp://ftp.coast.noaa.gov/pub/MSP/SuperfundSites.zip)
# This data only contains the 1200+ sites connected to the National Priorities
# List, which are the most severely contaminated sites as determined by the EPA.
# This code should work fine with a shapefile containing all 40,000
# true superfund sites, if you have one.
# Though using multiple files would require tweaking and/or batch processing. 
#
# Coordinate Systems: Both files specified in the above documentation should
# download in the GCS_North_American_1983 geographic coordinate system,
# therefore not needing projection or changing systems.  Should they
# download in another coordinate system, I would recommend converting
# them outside this tool.
#
# Potential Additions: Beneficial additions that could be made to this program
# include the option of entering a unique expression for calculating the new
# field.  However, this would require knowledge of SQL expressions, instead of
# just simple math.  To alter the program to accept SQL expression, replace the
# operand parameter with an SQL parameter, and change the "Calculat Field" parts
# to just take that variable as-is.  An example expression would be, then:
# ([code1]/[code2])*100
# written just like that as a parameter, to get non-decimal percentages.
# This leaves the possibility of having more than 3 fields as part of the
# evaluation, though this would require manually adding more parameters.
#
# A different use for this could be the inclusion of
# the margin-of-error numbers that come with the ACS data.
#
# Another possible add-on would be the inclusion
# of a ranking system that takes into account the severity of superfund sites;
# this would be especially useful if a file with all 40,000 superfund sites
# was to be used.
#
#------------------------------------------------------------------------------

"""
Parameters:
0 - workspace - the filepath to the location where your shapefiles will be saved(workspace)
1 - SFsites - the filepath to the GEODATABASE containing superfund or other hazardous sites(feature class)
2 - county - the filepath to the GEODATABASE with the polygons and tables of US counties(feature class)
3 - table - the demographic file (i.e. X17_POVERTY) to be joined to county(table)
4 - code1 - the ACS code for the numerator (i.e. population impoverished)(str)
5 - code2 - the ACS code for the denominator (i.e. total population)(str)(optional)
6 - code3 - the ACS code for a third field(str)(optional)
7 - operand - the term for evaluating the EVAL field(i.e. / for two terms divide, + to add terms)(str)(optional)
8 - compare - the term for comparing the fields (i.e. > for above threshold, < for below)(str)
9 - value - the threshold (i.e. percentage) for how to classify counties(i.e. 25.0% impoverished)(str)
10 - search - the distance (with units) to search for nearby superfund sites(str)
"""

#Initialization
import arcpy
from arcpy import env
arcpy.overwriteOutput = True

workspace = arcpy.GetParameterAsText(0)
SFsites = arcpy.GetParameterAsText(1)
county = arcpy.GetParameterAsText(2)
table = arcpy.GetParameterAsText(3)
code1 = arcpy.GetParameterAsText(4)
code2 = arcpy.GetParameterAsText(5)
code3 = arcpy.GetParameterAsText(6)
operand = arcpy.GetParameterAsText(7)
compare = arcpy.GetParameterAsText(8)
value = arcpy.GetParameterAsText(9)
search = arcpy.GetParameterAsText(10)

env.workspace = workspace

#cleaning the ACS data
arcpy.AddField_management(table, "GEOID_TRUE","TEXT")
cursor = arcpy.da.UpdateCursor(table, ["GEOID","GEOID_TRUE"])
for row in cursor:
    row[1] = row[0][7:]
    cursor.updateRow(row)

del row
del cursor

#Adding a Field to hold the Calculations
arcpy.AddField_management(county, "EVAL", "FLOAT", 5, 2)

#Joining Data from ACS to County
if code2 and code3:
    arcpy.JoinField_management(county, "GEOID", table, "GEOID_TRUE",[code1,code2,code3])
elif code2:
    arcpy.JoinField_management(county, "GEOID", table, "GEOID_TRUE",[code1,code2])
elif code3:
    raise Exception("Please don't skip code2!")
else:
    arcpy.JoinField_management(county, "GEOID", table, "GEOID_TRUE",[code1])

#Determining the Percentage
if code2 and code3:
    arcpy.CalculateField_management(county, "EVAL", '[' + code1 + ']' + operand + '[' + code2 + ']' + operand + '[' + code3 + ']')
elif code2:
    arcpy.CalculateField_management(county, "EVAL", '[' + code1 + ']' + operand + '[' + code2 + ']')
elif code3:
    raise Exception("Please don't skip code2!")
else:
    arcpy.CalculateField_management(county, "EVAL", '[' + code1 + ']')

#Selecting Counties Above the Percent Threshold
arcpy.Select_analysis(county, "Threshold_Counties.shp", 'EVAL ' + compare + ' ' + value)

#Making Layers to work with SelectLayerByLocation
arcpy.MakeFeatureLayer_management("Threshold_Counties.shp","threshold_lyr")

#Selecting Counties with Superfund Sites
arcpy.SelectLayerByLocation_management("threshold_lyr", "WITHIN_A_DISTANCE", SFsites, search)
arcpy.CopyFeatures_management("threshold_lyr","Counties_with_Superfund")

#Making Layers
arcpy.MakeFeatureLayer_management(SFsites,"SF_lyr")

#Selecting Superfund Sites near counties
arcpy.SelectLayerByLocation_management("SF_lyr", "WITHIN_A_DISTANCE", "Threshold_Counties.shp", search)
arcpy.CopyFeatures_management("SF_lyr","Superfund_near_Counties")


