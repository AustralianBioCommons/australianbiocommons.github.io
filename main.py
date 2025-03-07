from finders import *

##########################################
### Create TOOL and WORKFLOW databases ###
##########################################

if __name__ == "__main__":
    mytooldb = toolfinder.ToolDB("./external/Matrix_of_Availability_of_Bioinformatics_Tools_across_BioCommons__deployment_version.xlsx")
    mytooldb.add_provider(ToolMatrixDataProvider("./external/Matrix_of_Availability_of_Bioinformatics_Tools_across_BioCommons__deployment_version.xlsx"))
    mytooldb.add_provider(SetonixDataProvider("./external/setonix.txt"))
    mytooldb.add_provider(QriscloudDataProvider("external/bunya-modules-07March2025.txt"))
    mytooldb.add_provider(GadiDataProvider("./external/gadi.key.hdr"))
    mytooldb.add_provider(if89DataProvider("./external/bioapps_token.txt"))
    gdp = GalaxyDataProvider(mytooldb, "external/galaxy_tools_curation - DATA.csv")
    mytooldb.add_provider(gdp)
    mytooldb.add_provider(BiotoolsDataProvider("./external/Matrix_of_Availability_of_Bioinformatics_Tools_across_BioCommons__deployment_version.xlsx", mytooldb))
    mytooldb.add_provider(BiocontainersDataProvider("./external/Matrix_of_Availability_of_Bioinformatics_Tools_across_BioCommons__deployment_version.xlsx", mytooldb))

    #print("The following Galaxy Australia bio.tools IDs were not matched to the tool matrix sheet:")
    unresolved_gdp, unmatched_gdp = mytooldb.get_unmatched_ids(gdp)
    #print(unresolved_gdp)

    myworkflowdb = WorkflowDB()
    myworkflowdb.add_provider(WorkflowHubSpaceDataProvider())

    ###########################################
    ### Create TOOL and WORKFLOW yaml files ###
    ###########################################

    mytooldb.get_formatted_yaml()
    myworkflowdb.get_formatted_yaml()

    #####################################################
    ### Create TOOL and WORKFLOW tables in csv format ###
    ################# from ToolFinder v1 ################
    #####################################################

    #mytooldb.get_formatted_table().to_csv("./temp/toolfinder_input.csv", index = None)
    #myworkflowdb.get_formatted_table().to_csv("./temp/workflowfinder_input.csv", index = None)

###########################################
### REPORTING SECTION FOR MISSING TOOLS ###
###########################################

    print("#############################################")
    print("########### MISSING TOOL REPORT #############")
    print("#############################################")
    print("")

    #print("########## UNRESOLVED GALAXY TOOL IDs ##########")
    #for tool in unresolved_gdp:
    #    print(unresolved_gdp[tool]['id'])
    #print("########## UNRESOLVED GALAXY TOOL IDs + biotools IDs ##########")
    #for tool in unresolved_gdp:
    #    if "xrefs" in tool:
    #        for item in tool["xrefs"]:
    #            if item["reftype"] == "bio.tools":
    #                biotools_id = item["value"]
    #                print(unresolved_gdp[tool]['id'] + biotools_id)
    #print("########## UNMATCHED GALAXY TOOL IDs ##########")
    #print(unmatched_gdp)
    #print("####################################################")

    print("")

    for dataprovider in mytooldb.dataprovider:
        unresolved, unmatched = mytooldb.get_unmatched_ids(dataprovider)
        #print(dataprovider.__class__)
        print("")
        print("########## UNRESOLVED ", dataprovider, " TOOL IDs ##########")
        for tool in unresolved:
            print(tool)
        print("")
        print("########## UNMATCHED ", dataprovider, " TOOL IDs ##########")
        for tool in unmatched:
            print(tool)
        print("")

    print("")
    print("#############################################")
    print("################ END REPORT #################")
    print("#############################################")

