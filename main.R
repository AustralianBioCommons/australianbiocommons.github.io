library(rmarkdown)
rmarkdown::render("./rmarkdowns/index.rmd", output_file = "../docs/index.html")
rmarkdown::render("./rmarkdowns/2_1_workflows.Rmd", output_file = "../docs/2_1_workflows.html")
rmarkdown::render("./rmarkdowns/2_tools.Rmd", output_file = "../docs/2_tools.html")
rmarkdown::render("./rmarkdowns/5_attributions.Rmd", output_file = "../docs/5_attributions.html")

