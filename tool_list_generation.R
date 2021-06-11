

###########################
### external .R sources ###
###########################
#see https://stackoverflow.com/questions/13548266/define-all-functions-in-one-r-file-call-them-from-another-r-file-how-if-pos
source("functions.R")

###########################
### 1. load matrix data ###
###########################
biocommons_tool_matrix <- read_matrix("../external_GitHub_inputs/Matrix of Availability of Bioinformatics Tools across BioCommons - deployment version - Bioinformatics Software Availability.tsv")

###########################
### 2. load galaxy data ###
###########################
galaxy <- parse_GA_yaml(list.files("../external_GitHub_inputs/usegalaxy.org.au/", full.names = TRUE))

##############################
### 3. load QRIScloud data ###
##############################
qris <- read_qris("../external_GitHub_inputs/qriscloud.txt") %>%
  rename(`QRIScloud / UQ-RCC (Flashlite, Awoonga, Tinaroo)` = qris_cloud) %>%
  #see https://community.rstudio.com/t/which-tidyverse-is-the-equivalent-to-search-replace-from-spreadsheets/3548/7
  mutate_if(is.character, str_replace_all, pattern = 'genomeanalysistk', replacement = 'gatk') %>%
  mutate_if(is.character, str_replace_all, pattern = '^pacbio$', replacement = 'smrtlink') %>%
  mutate_if(is.character, str_replace_all, pattern = '^soapdenovo$', replacement = 'soapdenovo2')

#########################  
### 4. load Gadi data ###
#########################
gadi <- read_gadi("../external_GitHub_inputs/keys/key1.hdr") %>%
  rename(`NCI (Gadi)` = version)

###########################
### 5. load Pawsey data ###
###########################
zeus <- read_hpc("../external_GitHub_inputs/zeus.txt") %>%
  rename(`Pawsey (Zeus)` = version) %>%
  #see https://community.rstudio.com/t/which-tidyverse-is-the-equivalent-to-search-replace-from-spreadsheets/3548/7
  mutate_if(is.character, str_replace_all, pattern = 'wgs', replacement = 'celera') %>%
  mutate_if(is.character, str_replace_all, pattern = 'trinityrnaseq', replacement = 'trinity')

magnus <- read_hpc("../external_GitHub_inputs/magnus.txt") %>%
  rename(`Pawsey (Magnus)` = version)

#############################################################
### 6. Access bio.tools API using biotoolsIDs from matrix ###
#############################################################

tool_list_for_biotools <- biocommons_tool_matrix %>%
  filter(!is.na(biotoolsID)) %>%
  #see https://stackoverflow.com/a/44542659
  pull(biotoolsID)

#biocommons_tool_matrix %>%
#  filter(is.na(biotoolsID)) %>%
#  select(toolID) %>%
#  write_tsv(paste0("./", today(), "matrix_tools_NOT_in_biotools.txt"))

## Access bio.tools API
## Access the bio.tools API using the list of biotoolsIDs of interest to the Australian BioCommons
#see https://cran.r-project.org/web/packages/httr/vignettes/quickstart.html
#see https://biotools.readthedocs.io/en/latest/api_reference.html
#see https://cran.r-project.org/web/packages/urltools/vignettes/urltools.html
#See https://cran.r-project.org/web/packages/tidyjson/vignettes/introduction-to-tidyjson.html

biotools <- access_biotools_api_biotoolsID(tool_list_for_biotools)# %>%
  #write_tsv("./biotools_api_metadata.tsv")

#biotools <- read_tsv("./biotools_api_metadata.tsv")

###############################################
### 7. Merge bio.tools metadata with matrix ###
###############################################

biotools <- biotools %>%
  select(accessibility:owner, homepage:additionDate, license, maturity, terms) %>%
  # to remove duplicate biotoolsIDs
  distinct()

merge <- biocommons_tool_matrix %>%
  left_join(biotools, by = "biotoolsID") %>%
  #as_tibble() %>%
  select(`Tool / workflow name`:biotoolsID, `include?`, description, terms, license, on_galaxy_australia:galaxy_search_term, `Info URL`, homepage)

##########################
### 8. join tool lists ###
##########################

complete_join <- join_tool_and_install_metadata(matrix_data = merge, 
                                                gadi_data  = gadi, 
                                                zeus_data = zeus, 
                                                magnus_data = magnus, 
                                                qris_data = qris, 
                                                galaxy_data = galaxy)
############################
### 9. process tool list ###
############################

complete_processed <- process_tool_and_install_metadata(complete_join)

complete_processed %>%
  #filter(is.na(biotoolsID)) %>%
  write_tsv(paste0("../external_GitHub_inputs/", today(), "_processed_tool_matrix.tsv"))

###other links
#see https://stackoverflow.com/a/56683740
#see https://stackoverflow.com/questions/43696227/mutate-with-case-when-and-contains

#########################################
### 10. final processing / formatting ###
#########################################

installs <- complete_processed %>%
  select(`Tool / workflow name`:toolID, description, `Topic (EDAM, if available)`, `BioContainers link`,`bio.tools link`, 
         license, `Galaxy Australia`, `Available in Galaxy toolshed`, `NCI (Gadi)`, `Pawsey (Zeus)`, `Pawsey (Magnus)`,
         `QRIScloud / UQ-RCC (Flashlite, Awoonga, Tinaroo)`) %>%
  #see https://tidyr.tidyverse.org/reference/replace_na.html
  replace_na(list(description = "",
                  `Pawsey (Zeus)` = "",
                  `Pawsey (Magnus)` = "",
                  `QRIScloud / UQ-RCC (Flashlite, Awoonga, Tinaroo)` = "",
                  `NCI (Gadi)` = "",
                  `Topic (EDAM, if available)` = "",
                  `bio.tools link` = "",
                  `BioContainers link` = "",
                  `Available in Galaxy toolshed` = ""
  )) %>%
  rename(`Tool identifier (module name / bio.tools ID / placeholder)` = toolID,
         Description = description,
         License = license)
