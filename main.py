from finders import *

if __name__ == "__main__":
    mytooldb = toolfinder.ToolDB("external/tool_matrix_2021_11_15.xlsx")
    mytooldb.add_provider(ToolMatrixDataProvider("external/tool_matrix_2021_11_15.xlsx"))
    #mytooldb.add_provider(ZeusDataProvider("external/zeus.txt"))
    #mytooldb.add_provider(MagnusDataProvider("external/magnus.txt"))
    mytooldb.add_provider(SetonixDataProvider("external/setonix.txt"))
    mytooldb.add_provider(QriscloudDataProvider("external/qriscloud.txt"))
    mytooldb.add_provider(GadiDataProvider("./external/gadi.key.hdr"))
    mytooldb.add_provider(if89DataProvider("./external/bioapps_token.txt"))
    gdp = GalaxyDataProvider(mytooldb, "./external/galaxy_tools_curation - DATA.csv")
    mytooldb.add_provider(gdp)
    mytooldb.add_provider(BiotoolsDataProvider("external/tool_matrix_2021_11_15.xlsx", mytooldb))

    print("The following Galaxy Australia bio.tools IDs were not matched to the tool matrix sheet:")
    unresolved_gdp, unmatched_gdp = mytooldb.get_unmatched_ids(gdp)
    print(unresolved_gdp)
    print(unmatched_gdp)

    for dataprovider in mytooldb.dataprovider:
        unresolved, unmatched = mytooldb.get_unmatched_ids(dataprovider)
        print(dataprovider.__class__)
        print(unresolved)
        print(unmatched)

    mytooldb.get_formatted_table().to_csv("./temp/toolfinder_input.csv", index = None)

    myworkflowdb = WorkflowDB()
    myworkflowdb.add_provider(WorkflowHubSpaceDataProvider())

    myworkflowdb.get_formatted_table().to_csv("./temp/workflowfinder_input.csv", index = None)