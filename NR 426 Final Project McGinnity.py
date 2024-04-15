## NR 426 Final Project
## Eileen McGinnity, Spring 2024
## Script to create two watersheds along Mail Creek Ditch in Southern Fort Collins, CO, starting from DEM data and a boundary polygon of Larimer County, CO.

# import packages
import arcpy, arcpy.sa, os, sys

######## ONLY CHANGE THIS PATH #########
arcpy.env.workspace = r"C:\Users\mcgin\Documents\Grad School\Spring 2024\NR 426-7 - Programming for GIS\NR 426\Final Project\NR 426 Final Project McGinnity\data"
    # setting workspace - change this to local "data" file containing the DEMs and a subfolder for the Larimer County boundary (all included in provided zip file)
########################################

# overwrite true
arcpy.env.overwriteOutput = True

print("\n***Script Starting***\n")

# checking if the workspace path is set correctly (exits if wrong)
if not arcpy.Exists(arcpy.env.workspace):
    sys.exit("Workspace is not set correctly or does not exist.")

# import data & assigning constant variables
print("Pre-delineation setup:")
print("\tImporting Aster GDEMs for study area...")
dem1 = "ASTGTMV003_N40W105_dem.tif"
dem2 = "ASTGTMV003_N40W106_dem.tif"

print("\tImporting Larimer County boundary polygon...")
county = "GIS_BoundariesSHP\BoundaryBOCC.shp"
county_path = os.path.join(arcpy.env.workspace, county)

print("\tSetting stream outlet points...")
outlet1_coords = [(-104.9430134, 40.4831938)]
outlet2_coords = [(-105.0325449, 40.4855403)]

print("\tSetting additional constant variables...")
wsh1 = "Watershed1.shp"
wsh2 = "Watershed2.shp"
outlet1_fc = "outlet1fc.shp"
outlet2_fc = "outlet2fc.shp"
dems_merged = "DEMmerge"
mergeclip = "MergeClip"
filledraster_out = "fillraster"
flowdirection_out = "flowdir"
flowaccumulation_out = "flowacc"
countypro = "County_84"

# functions
print("\tCreating function for building pyramids and calculating statistics...")
def pyramidsstats():
    arcpy.BuildPyramidsandStatistics_management(arcpy.env.workspace)
    # creating function for building pyramids and calculating statistics
    # (this is not a necessary step, but seems to make loading data faster in my experience)

# creating spatial reference (WGS84)
print("\tSetting spatial reference (WGS84)...")
spatial_reference = arcpy.SpatialReference(4326)

print ("\tChecking workspace and data accuracy...")
# checking if the imported data is present in the workspace (exits if not found)
if arcpy.Exists(dem1) and arcpy.Exists(dem2) and arcpy.Exists(county_path):
    print("\t\tWorkspace correct and required data have been successfully found.")
else:
    sys.exit("Workspace is set correctly, but required data are not present.")


print("\nStarting watershed delineation steps:")
try: # catching errors for all processes below
    # 1: Reprojecting the Larimer County boundary from NAD83 to WGS84
    print("\tProjecting Larimer County boundary polygon...") # NAD83 to WGS84
    county_split = county_path.split(".")[0] # removing .shp
    arcpy.Project_management(county_split, countypro, spatial_reference)

    # 2: Calculating statistics for the DEMs
    print("\tCalculating statistics for imported DEMs...")
    dem1stat = arcpy.CalculateStatistics_management(dem1)
    dem2stat = arcpy.CalculateStatistics_management(dem2)

    # 3: Merging DEMs together
    print("\tMerging DEMs...")
    arcpy.MosaicToNewRaster_management([dem1stat, dem2stat],
                                       arcpy.env.workspace, dems_merged, spatial_reference,"16_BIT_UNSIGNED", None, 1, "LAST", "FIRST")

    # 4: Clipping the DEM to the boundary of Larimer County
    print("\tClipping DEM to Larimer County boundary polygon...")
    arcpy.Clip_management(dems_merged,"-106.19544002409 40.2577895760696 -104.943052820597 40.9984405695312", mergeclip, countypro,"-32768")

    # 5: Filling the sinks in the raster
    print("\tFilling raster...")
    filled_raster = arcpy.sa.Fill(mergeclip)
    filled_raster.save(filledraster_out)
    pyramidsstats()

    # 6: Determining the direction of the stream flow
    print("\tDetermining flow direction...")
    flowdirection = arcpy.sa.FlowDirection(filled_raster)
    flowdirection.save(flowdirection_out)
    pyramidsstats()

    # 7: Calculating the accumulated flows into each downslope cell
    print("\tCalculating accumulated flows...")
    flowaccumulation = arcpy.sa.FlowAccumulation(flowdirection)
    flowaccumulation.save(flowaccumulation_out)
    pyramidsstats()

    # 8: Creating a feature class for the stream outlet points/pour points based on DD coordinate points.
    print("\tCreating feature classes for outlet points...")
    arcpy.CreateFeatureclass_management(arcpy.env.workspace, outlet1_fc, "POINT", "", "", "", spatial_reference)

    # inserting coordinates into fc
    with arcpy.da.InsertCursor(outlet1_fc, ['SHAPE@XY']) as cursor:
        for coordinate in outlet1_coords:
            cursor.insertRow([coordinate])

    arcpy.CreateFeatureclass_management(arcpy.env.workspace, outlet2_fc, "POINT", "", "", "", spatial_reference)

    with arcpy.da.InsertCursor(outlet2_fc, ['SHAPE@XY']) as cursor:
        for coordinate in outlet2_coords:
            cursor.insertRow([coordinate])

    # 9: Creating feature classes for the watershed boundaries.
    print("\tCreating feature classes for watershed boundaries...")
    arcpy.CreateFeatureclass_management(arcpy.env.workspace, wsh1, "POLYGON", "", "", "", spatial_reference)

    arcpy.CreateFeatureclass_management(arcpy.env.workspace, wsh2, "POLYGON", "", "", "", spatial_reference)

    # 10: Creating the watershed boundaries and converting them into polygons.
    print("\tCreating the watershed boundaries...")
    arcpy.RasterToPolygon_conversion(arcpy.sa.Watershed(flowdirection, outlet1_fc), wsh1)
    arcpy.RasterToPolygon_conversion(arcpy.sa.Watershed(flowdirection, outlet2_fc), wsh2)
    print(f"\t\tSuccessfully created watershed polygon boundaries.\n\nOutput can be found in: {arcpy.env.workspace}")

#printing any possible errors
except arcpy.ExecuteError:
    print(arcpy.GetMessages(2))
except Exception as e:
    print(e)


print("\n***Script Complete***")