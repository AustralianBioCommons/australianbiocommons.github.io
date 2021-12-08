library(rmarkdown)
rmarkdown::render("./rmarkdowns/index.rmd", output_file = "../output/index.html")
rmarkdown::render("./rmarkdowns/2_1_workflows.Rmd", output_file = "../output/2_1_workflows.html")
rmarkdown::render("./rmarkdowns/2_tools.Rmd", output_file = "../output/2_tools.html")
rmarkdown::render("./rmarkdowns/5_attributions.Rmd", output_file = "../output/5_attributions.html")

