###########################
### external .R sources ###
###########################
#see https://stackoverflow.com/questions/13548266/define-all-functions-in-one-r-file-call-them-from-another-r-file-how-if-pos
source("functions.R")

#################
### libraries ###
#################
library(knitr)
library(markdown)

###############################################
### retrieve workflowhub entries and format ###
###############################################

#see https://cran.r-project.org/web/packages/httr/vignettes/quickstart.html
#see https://cran.r-project.org/web/packages/urltools/vignettes/urltools.html
#see https://cran.r-project.org/web/packages/tidyjson/vignettes/introduction-to-tidyjson.html
#see https://rdrr.io/cran/tidyjson/f/vignettes/introduction-to-tidyjson.Rmd
#search_term <- 'https://workflowhub.eu/ga4gh/trs/v2/tools'
#example link <- "https://workflowhub.eu/workflows/114.json"

search_space <- 'https://workflowhub.eu/programmes/8/workflows.json'

formatted <- find_workflows(search_space) %>%
  select(Title, Tags, Description, License, `Workflow Class`, Teams, links.self) %>%
  arrange(Title) %>%
  mutate(Title = paste0("<a href='https://workflowhub.eu", links.self, "' target='_blank'  rel='noopener noreferrer'>", Title, "</a>")) %>%
  select(-links.self) %>%
  #see https://stackoverflow.com/a/63927848
  mutate(Description = str_replace_all(Description, "\n","<br />")) %>%
  #regex attribution - Tracy Chew (Sydney Informatics Hub, University of Sydney)
  mutate(Description = gsub("[\r\n]", "", Description)) %>%
  mutate(Description = str_remove_all(Description, "<img.+>"))

#see https://community.rstudio.com/t/rendering-markdown-text/11588/4
#see also markdownToHTML documentation
workflow_descriptions <- tibble()
for (i in 1:nrow(formatted)){
  temp <- formatted$Description[i]
  workflow <- tibble(workflow_descriptions = markdownToHTML(text = temp, fragment.only = TRUE))
  workflow_descriptions <- bind_rows(workflow_descriptions, workflow)
}

workflows_final <- bind_cols(formatted, workflow_descriptions) %>%
  select(-Description) %>%
  select(Title, Tags, `Workflow descriptions` = workflow_descriptions,
         License:Teams) %>%
  mutate(infrastructure_temp = str_extract(`Workflow descriptions`, "Infrastructure_deployment_metadata: ([A-Za-z ]+ \\([A-Za-z]+\\))")) %>%
  #see https://tidyr.tidyverse.org/reference/separate.html
  separate(infrastructure_temp, into = c("temp", "Successful infrastructure deployment(s)"), sep = ": ") %>%
  select(-temp) %>%
  #see https://stackoverflow.com/a/63927848
  mutate(`Workflow descriptions` = str_extract(`Workflow descriptions`, "^.{10,300}")) %>%
  mutate(`Workflow descriptions` = paste0(`Workflow descriptions`, " ...")) %>%
  mutate(`Workflow descriptions` = str_replace_all(`Workflow descriptions`, "<h1>",""))
