###########################
### external .R sources ###
###########################
#see https://stackoverflow.com/questions/13548266/define-all-functions-in-one-r-file-call-them-from-another-r-file-how-if-pos
source("functions.R")

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
  mutate(Description = str_extract(gsub("[\r]", "", Description), "^.{10,300}")) %>%
  mutate(Description = str_remove_all(Description, "<img.+>")) %>%
  mutate(Description = paste0(Description, " ..."))
