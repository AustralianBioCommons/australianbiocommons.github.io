
####################################
### read and process tool matrix ###
####################################

read_matrix <- function(matrix_file){
  
  matrix_tibble <- read_tsv(matrix_file, skip = 2) %>%
    
    select(`Tool / workflow name`, toolID, biotoolsID, `include?`, on_galaxy_australia, `Primary purpose (EDAM, if available)`,
           `Galaxy toolshed name / search term`, `Info URL`) %>%
    rename(galaxy_search_term = `Galaxy toolshed name / search term`)
  
  return(matrix_tibble)
  
}

##########################################################
### Access bio.tools API using biotoolsIDs from matrix ###
##########################################################
#see https://cran.r-project.org/web/packages/httr/vignettes/quickstart.html
#see https://biotools.readthedocs.io/en/latest/api_reference.html
#see https://cran.r-project.org/web/packages/urltools/vignettes/urltools.html
#See https://cran.r-project.org/web/packages/tidyjson/vignettes/introduction-to-tidyjson.html

access_biotools_api_biotoolsID <- function(biotoolsID_vector){
  
  biotools <- tibble()
  
  # example https://bio.tools/api/t/?biotoolsID=%22signalp%22
  biotools_URL <- "https://bio.tools/api/t/?biotoolsID="
  
  for (i in 1:length(biotoolsID_vector)){
    
    biotoolsID <- biotoolsID_vector[i]
    
    #see https://www.rdocumentation.org/packages/utils/versions/3.6.2/topics/URLencode
    #see https://cran.r-project.org/web/packages/urltools/vignettes/urltools.html
    response <- GET(URLencode(paste0(biotools_URL, '"', biotoolsID, '"')))
    data <- content(response, as = "text")
    
    #see also https://stackoverflow.com/a/62630236
    #see also https://stackoverflow.com/a/44448208
    
    tool_data <- data %>%
      enter_object(list) %>% 
      gather_array(column.name = "tool_index") %>%
      spread_all %>%
      #see https://datacarpentry.org/r-socialsci/05-json/index.html
      as_tibble()
    
    if(nrow(tool_data) >= 1){
      
      topics <- data %>%
        enter_object(list) %>% 
        gather_array(column.name = "tool_index") %>%
        enter_object() %>%
        gather_object() %>%
        json_types() %>%
        filter(name == "topic") %>%
        enter_object
      
      if(nrow(topics) >= 1){
        
        topics_temp <- topics %>% 
          gather_array(column.name = "topic_index") %>%
          spread_all
        
        topics_string <- topics_temp %>%
          as_tibble() %>%
          select(tool_index, term) %>%
          #see post by G. Grothendieck @ https://stackoverflow.com/a/56810604
          #see post by Damian @ https://stackoverflow.com/a/45200648
          group_by(tool_index) %>%
          summarize(terms = toString(term)) %>%
          ungroup()
        
        tool_data_terms <- tool_data %>%
          full_join(topics_string, by = "tool_index")
        
        biotools <- bind_rows(biotools, tool_data_terms)
        
      } else {
        
        tool_data_terms <- tool_data %>%
          mutate(terms = "No term available") 
        
        biotools <- bind_rows(biotools, tool_data_terms)
        
      }
      
    } else {}
    
  }
  
  return(biotools)
  
} 

########################################################
### join tool metadata with facility module installs ###
########################################################

join_tool_and_install_metadata <- function(matrix_data, gadi_data, zeus_data, magnus_data, qris_data, galaxy_data){
  
  complete_join <- matrix_data %>%
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
    arrange(`Tool / workflow name`)
  
  return(complete_join)
  
}

#https://www.sitepoint.com/use-unicode-create-bullet-points-trademarks-arrows/
#see post by SLaks @ https://stackoverflow.com/a/4521389
#https://www.w3schools.com/jsref/prop_anchor_text.asp
#https://www.w3schools.com/jsref/tryit.asp?filename=tryjsref_anchor_text2
###example
#<p><a href="url">&#x25cf;</a></p>

############################################################
### integrate bio.tools fields homepage/URL, and topics) ###
############################################################

process_tool_and_install_metadata <- function(joined_tool_and_install_data){
  
  complete_tibble <- joined_tool_and_install_data %>%
    mutate(
      `Galaxy Australia` = case_when(grepl("^[Yy]e?s?$", on_galaxy_australia) ~ "Yes"),
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
        is.na(homepage) & grepl("https?://", `Info URL`) ~ paste0("<a href='", `Info URL`, "' target='_blank'  rel='noopener noreferrer'>", `Tool / workflow name`, "</a>"),
        grepl("https?://", homepage) ~ paste0("<a href='", homepage, "' target='_blank'  rel='noopener noreferrer'>", `Tool / workflow name`, "</a>"),
        grepl("", `Info URL`) | is.na(`Info URL`) | is.na(homepage) ~ `Tool / workflow name`),
      
      `bio.tools link` = case_when(!is.na(biotoolsID) ~ paste0("<a href='https://bio.tools/", biotoolsID, "' target='_blank'  rel='noopener noreferrer'>", biotoolsID, "</a>")),
      
      #example https://biocontainers.pro/tools/canu
      `BioContainers link` = case_when(!is.na(biotoolsID) ~ paste0("<a href='https://biocontainers.pro/tools/", biotoolsID, "' target='_blank'  rel='noopener noreferrer'>", biotoolsID, "</a>")),
      
      `Topic (EDAM, if available)` = case_when(
        !is.na(terms) ~ terms,
        is.na(terms) & !is.na(`Primary purpose (EDAM, if available)`) ~ `Primary purpose (EDAM, if available)`
      )
    )
  
  write_tsv(complete_tibble, "../../external_GitHub_inputs/complete_processed_tool_matrix.tsv")
  
  return(complete_tibble)
  
  }

########################################
### read and process qriscloud tools ###
########################################

read_qris <- function(qriscloud_file){
  
  qris_tibble <- read_tsv(qriscloud_file, col_names = FALSE)
  
  fix_qris <- qris_tibble %>%
    #see https://stackoverflow.com/a/28860172
    filter(grepl("/[A-Za-z0-9]+/", X1)) %>%
    #  mutate(X1 = str_replace(X1, pattern = "^[A-Za-z0-9]+/", "")) 
    mutate(X1 = case_when(grepl("/[A-Za-z0-9]+/", X1) ~ str_replace(X1, pattern = "/{1}", "-")))
  
  qris_final <- fix_qris %>%
    bind_rows(qris_tibble) %>%
    arrange(X1) %>%
    #see https://stackoverflow.com/a/28860172
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

read_gadi <- function(key_location){
  
  #see https://stackoverflow.com/questions/12193779/how-to-write-trycatch-in-r
  #see also https://stackoverflow.com/a/12195574
  gadi_tibble <- tryCatch(
    
    {
      
      key <- read_file(key_location) %>% str_extract(" .+$") %>% str_trim(side = "left")
      response <- GET("http://gadi-test-apps.nci.org.au:5000/dump", add_headers(Authorization = key))
      
      #see https://stackoverflow.com/a/46147957
      if(file.exists("../../external_GitHub_inputs/gadi.csv")){
        
        #see https://stackoverflow.com/a/28771203
        #see also ?file.info in base R
        if(difftime(Sys.time(), file.info("../../external_GitHub_inputs/gadi.csv")$mtime, units = "days") > 7){
          
          if(response$status_code == 200){
            
            gadi_tibble_temp <- content(response, "text") %>%
              read_csv(col_names = c("toolID", "version"))
            
            #see https://cran.r-project.org/web/packages/uuid/uuid.pdf
            uuid_file_name <- paste0("../../external_GitHub_inputs/", UUIDgenerate(), ".csv")
            write_csv(gadi_tibble_temp, uuid_file_name)
            file.rename(uuid_file_name, "../../external_GitHub_inputs/gadi.csv")
            
          } else {
            
            print("Response status is not equal to 200. Using existing Gadi *.csv file!")  
            gadi_tibble_temp <- read_csv("../../external_GitHub_inputs/gadi.csv")
            
          }
          
        } else {
          
          print("File does not need to be replaced yet. Using existing Gadi *.csv file!")  
          gadi_tibble_temp <- read_csv("../../external_GitHub_inputs/gadi.csv")
          
        }
        
      } else if (!file.exists("../../external_GitHub_inputs/gadi.csv")){
        
        if (response$status_code == 200){
          
          gadi_tibble_temp <- content(response, "text") %>%
            read_csv(col_names = c("toolID", "version"))
          
          #see https://cran.r-project.org/web/packages/uuid/uuid.pdf
          uuid_file_name <- paste0("../../external_GitHub_inputs/", UUIDgenerate(), ".csv")
          write_csv(gadi_tibble_temp, uuid_file_name)
          file.rename(uuid_file_name, "../../external_GitHub_inputs/gadi.csv")
          
        } else {
          
          print("Response status is not equal to 200. Please try again!")  
          
        }
      }
      
    },
    
    error=function(error) {
      print("Error occurred: existing Gadi *.csv file being used!")
      print(error)
      gadi_tibble_temp <- read_csv("../../external_GitHub_inputs/gadi.csv")
    },
    
    warning=function(warning) {
      print("Warning occurred: existing Gadi *.csv file being used!")
      print(warning)
      gadi_tibble_temp <- read_csv("../../external_GitHub_inputs/gadi.csv")
    },
    
    finally={
      
      gadi_tibble <- gadi_tibble_temp %>%
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
    
  )
  
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

