import toolfinder
from toolfinder import *
import pandas as pd

if __name__ == "__main__":
    db = toolfinder.ToolDB("external/tool_matrix_2021_11_15.xlsx")
    db.add_provider(ToolMatrixDataProvider("external/tool_matrix_2021_11_15.xlsx"))
    db.add_provider(ZeusDataProvider("external/zeus.txt"))
    db.add_provider(MagnusDataProvider("external/magnus.txt"))
    db.add_provider(QriscloudDataProvider("external/qriscloud.txt"))
