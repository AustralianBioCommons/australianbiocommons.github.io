import toolfinder
from toolfinder import *
import pandas as pd

if __name__ == "__main__":
    mytooldb = toolfinder.ToolDB("external/tool_matrix_2021_11_15.xlsx")
    mytooldb.add_provider(ToolMatrixDataProvider("external/tool_matrix_2021_11_15.xlsx"))
    mytooldb.add_provider(ZeusDataProvider("external/zeus.txt"))
    mytooldb.add_provider(MagnusDataProvider("external/magnus.txt"))
    mytooldb.add_provider(QriscloudDataProvider("external/qriscloud.txt"))
    mytooldb.add_provider(GadiDataProvider("./external/gadi.key.hdr"))
    gdp = GalaxyDataProvider(mytooldb)
    mytooldb.add_provider(gdp)
    mytooldb.add_provider(BiotoolsDataProvider("external/tool_matrix_2021_11_15.xlsx", mytooldb))

    print("The following Galaxy Australia bio.tools IDs were not matched to the tool matrix sheet:")
    for id in gdp.get_unmatched_galaxy_biotools_ids():
        print(id)
