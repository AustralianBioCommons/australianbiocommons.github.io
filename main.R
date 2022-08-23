library(rmarkdown)
library(DT)
library(tidyverse)
library(lubridate)

# index page
rmarkdown::render("./rmarkdowns/index.rmd", output_file = "../docs/index.html")

# toolfinder
rmarkdown::render("./rmarkdowns/2_tools.Rmd", output_file = "../docs/2_tools.html")

# workflowfinder
rmarkdown::render("./rmarkdowns/2_1_workflows.Rmd", output_file = "../docs/2_1_workflows.html")

# attributions
rmarkdown::render("./rmarkdowns/5_attributions.Rmd", output_file = "../docs/5_attributions.html")


