
####################################
### read and process tool matrix ###
####################################

read_matrix <- function(matrix_file){
  
  matrix_tibble <- read_tsv(matrix_file, skip = 2) %>%
    
    select(`Tool / workflow name`,
           toolID,
           biotoolsID,
           `include?`,
           on_galaxy_australia,
           `Primary purpose (EDAM, if available)`,
           `Galaxy toolshed name / search term`,
           `Info URL`,
           `bio.containers link`, 
           `bio.tools link`,
           `GitHub link`) %>%
    
    rename(galaxy_search_term = `Galaxy toolshed name / search term`,
           biocontainers_link = `bio.containers link`, 
           biotools_link = `bio.tools link`,
           `BioCommons Documentation` = `GitHub link`) %>%
    
    #see https://community.rstudio.com/t/which-tidyverse-is-the-equivalent-to-search-replace-from-spreadsheets/3548/7
    #mutate_if(is.character, str_replace_all, pattern = '^\\?$', replacement = 'unknown') %>%
    #mutate_if(is.character, str_replace_all, pattern = '^[Yy]$', replacement = '&#9679;') %>%
    #mutate_if(is.character, str_replace_all, pattern = '^[Nn]ot [Aa]pplicable$', replacement = "") %>%
    #mutate_if(is.character, str_replace_all, pattern = '^n/a( .+)?$', replacement = "") %>%
    #mutate_if(is.character, str_replace_all, pattern = '^NA$', replacement = "") %>%
    #mutate_if(is.character, str_replace_all, pattern = '[Ss]oon', replacement = "install requested") %>%
    mutate(source_bc = "BioCommons matrix")
  
  return(matrix_tibble)
  
  }

##################################
### join and process tool lists###
##################################

join_and_process_tools <- function(matrix_data, gadi_data, zeus_data, magnus_data, qris_data, galaxy_data){
  
  COMPLETE_tibble <- matrix_data %>%
    full_join(qris_data, by = "toolID") %>%
    full_join(gadi_data, by = "toolID") %>%
    full_join(zeus_data, by = "toolID") %>%
    full_join(magnus_data, by = "toolID") %>%
    left_join(galaxy_data, by = "toolID", keep = TRUE) %>%
    rename(toolID = toolID.x) %>%
    # as earlier functions arrange by the key `toolID`
    arrange(`Tool / workflow name`) %>%
    filter(`include?` == "y" | is.na(`include?`)) %>%
    #see post by Max @ https://stackoverflow.com/a/55708065
    mutate(`Tool / workflow name` = coalesce(`Tool / workflow name`, toolID)) %>%
    arrange(`Tool / workflow name`) %>%
    
    #https://www.sitepoint.com/use-unicode-create-bullet-points-trademarks-arrows/
    #see post by SLaks @ https://stackoverflow.com/a/4521389
    #https://www.w3schools.com/jsref/prop_anchor_text.asp
    #https://www.w3schools.com/jsref/tryit.asp?filename=tryjsref_anchor_text2
    ###example
    #<p><a href="url">&#x25cf;</a></p>
    
    mutate(
      `Galaxy Australia` = case_when(grepl("^y$", on_galaxy_australia) ~ "Yes"),
      `Available in Galaxy toolshed` = case_when(
        !is.na(galaxy_search_term) ~
          #see post by Hao @ https://stackoverflow.com/a/48512819
          #see post by jrdnmdhl @ https://stackoverflow.com/a/30901774
          paste0("<a href='https://toolshed.g2.bx.psu.edu/repository/browse_repositories?f-free-text-search=", galaxy_search_term, "'  target='_blank'  rel='noopener noreferrer'>", galaxy_search_term, "</a>"))
      #paste("[", galaxy_search_term, "](https://toolshed.g2.bx.psu.edu/repository/browse_repositories?f-free-text-search=", 
      #      galaxy_search_term, "&sort=name)", sep = ""))
    ) %>%
  
    #see post by Akrun @ https://stackoverflow.com/a/43696252
    #question url https://stackoverflow.com/questions/43696227/mutate-with-case-when-and-contains
    mutate(
      `Tool / workflow name` = case_when(
        grepl("https?://", `Info URL`) ~ paste0("<a href='", `Info URL`, "' target='_blank'  rel='noopener noreferrer'>", `Tool / workflow name`, "</a>"),
        grepl("", `Info URL`) | is.na(`Info URL`) ~ `Tool / workflow name`),
    
      `bio.tools` = case_when(grepl("https?://", biotools_link) ~ paste0("<a href='", biotools_link, "' target='_blank'  rel='noopener noreferrer'>&#9679;</a>")),
      
      `BioCommons Documentation` = case_when(grepl("https?://", `BioCommons Documentation`) ~ paste0("<a href='", `BioCommons Documentation`, "' target='_blank'  rel='noopener noreferrer'>&#9679;</a>")),
    
      `BioContainers` = case_when(grepl("https?://", biocontainers_link) ~ paste0("<a href='", biocontainers_link, "' target='_blank'  rel='noopener noreferrer'>&#9679;</a>"))
      )
  
  write_tsv(COMPLETE_tibble, "../../external_GitHub_inputs/complete_processed_tool_matrix.tsv")
  
  return(COMPLETE_tibble)
  
  }

########################################
### read and process qriscloud tools ###
########################################

read_qris <- function(qriscloud_file){
  
  qris_tibble <- read_tsv(qriscloud_file, col_names = FALSE)
  
  fix_qris <- qris_tibble %>%
    filter(grepl("/[A-Za-z0-9]+/", X1)) %>%
    #  mutate(X1 = str_replace(X1, pattern = "^[A-Za-z0-9]+/", "")) 
    mutate(X1 = case_when(grepl("/[A-Za-z0-9]+/", X1) ~ str_replace(X1, pattern = "/{1}", "-")))
  
  qris_final <- fix_qris %>%
    bind_rows(qris_tibble) %>%
    arrange(X1) %>%
    filter(!grepl("/[A-Za-z0-9]+/", X1)) %>%
    #see post by aosmith @ https://community.rstudio.com/t/tidyr-separate-at-first-whitespace/26269/3  
    #separate(X1, c("toolID", "version"), sep = "/") %>%
    mutate(toolID = str_extract(X1, "^[^/]+"),
           version = str_extract(X1, "[^/]+$")) %>%
    select(toolID, version) %>%
    #see post by G. Grothendieck @ https://stackoverflow.com/a/56810604
    #see post by Damian @ https://stackoverflow.com/a/45200648
    mutate(toolID = tolower(toolID)) %>%
    group_by(toolID) %>%
    summarize(qris_cloud = toString(version)) %>%
    ungroup() %>%
    #see post by Chris @ https://stackoverflow.com/a/33191810
    mutate(qris_cloud = str_replace_all(qris_cloud, pattern = ", " , "<br />"))
  
  return(qris_final)
  
}

##################################
### read and process hpc tools ###
##################################

read_hpc <- function(hpc_file){
  
  hpc_tibble <- read_tsv(hpc_file) %>%
    #see post by aosmith @ https://community.rstudio.com/t/tidyr-separate-at-first-whitespace/26269/3  
    separate(1, c("toolID", "version"), sep = "/", extra = "merge") %>%
    arrange(toolID) %>%
    filter(!grepl("[A-Za-z]+ [0-9]+", toolID)) %>%
    #see post by G. Grothendieck @ https://stackoverflow.com/a/56810604
    #see post by Damian @ https://stackoverflow.com/a/45200648
    mutate(toolID = tolower(toolID)) %>%
    group_by(toolID) %>%
    summarize(version = toString(version)) %>%
    ungroup() %>%
    #see post by Chris @ https://stackoverflow.com/a/33191810
    mutate(version = str_replace_all(version, pattern = ", " , "<br />"))
  
  return(hpc_tibble)
  
}

read_gadi <- function(gadi_file){
  
  gadi_tibble <- read_csv(gadi_file, col_names = c("toolID", "version")) %>%
    arrange(toolID) %>%
    #see post by G. Grothendieck @ https://stackoverflow.com/a/56810604
    #see post by Damian @ https://stackoverflow.com/a/45200648
    mutate(toolID = tolower(toolID)) %>%
    group_by(toolID) %>%
    summarize(version = toString(version)) %>%
    ungroup() %>%
    #see post by Chris @ https://stackoverflow.com/a/33191810
    mutate(version = str_replace_all(version, pattern = ", " , "<br />"))
  
  return(gadi_tibble)
  
}

###################################
### parse Galaxy Australia yaml ###
###################################

parse_GA_yaml <- function(AU_files){
  
  AU_tools <- tibble()
  
  for (i in 1:length(AU_files)){
    
    temp_data_AU <- read_yaml(AU_files[i])
    filename_AU <- unlist(strsplit(AU_files[i], "/"))[5]
    
    for (j in 1:length(temp_data_AU$tools)){
      AU <- temp_data_AU$tools[[j]]
      #example: https://toolshed.g2.bx.psu.edu/view/iuc/abricate/b734db305578
      rev_AU <- str_split(AU$revisions, ",")
      latest_revision <- rev_AU[[length(rev_AU)]]
      
      temp_AU <- tibble(
        toolID = AU$name,
        owner = AU$owner,
        revision = latest_revision,
        label = AU$tool_panel_section_label,
        yaml = filename_AU
      )
      AU_tools <- bind_rows(AU_tools, temp_AU)
    }
    
  }
  return(AU_tools)
}

