library("httr")
library("rvest")
library("tidyverse")

url <- paste0("https://official.nba.com/",
              "2018-19-nba-officiating-last-two-minute-reports/")

links <- read_html(url) %>% 
  html_nodes("#main a+ a , strong+ a") %>%
  html_attr("href")

tail(links)

table(tools::file_ext(links))

local_dir     <- "0-data/L2M/2018-19"
data_source   <- paste0(local_dir, "/raw")
if (!file.exists(local_dir)) dir.create(local_dir, recursive = T)
if (!file.exists(data_source)) dir.create(data_source, recursive = T)

links_pdf <- links[grepl(pattern = "*.pdf", links)]

files  <- paste(data_source, basename(links_pdf), sep = "/")


pdf_games <- map(links_pdf,  function(x) {
  file_x <- paste(data_source, basename(x), sep = "/")
  if (!file.exists(file_x)) {
    Sys.sleep(runif(1, 3, 5))
    tryCatch(download.file(x, file_x, method = "libcurl"),
             warning = function(w) {
               "bad"
             })
  } else "exists"
})

links[1] %>% 
  read_html() %>% 
  html_table()

library("splashr")

splash_active() 
l2m_raw <- render_html(url = links[1], wait = 7)

l2m_site <- l2m_raw  %>% 
  html_table(fill = T) %>% 
  .[[1]]
glimpse(tail(l2m_site))

temp <- raw_text[[1]] %>% 
  str_split("\n") %>% 
  unlist() %>% 
  str_trim()

begin <- grep("@", temp)
if (length(begin) > 1) {
  begin <- begin[1]
  game_details = temp[begin]
  } else if (length(begin) == 1) {
    game_details = temp[begin]
        } else if (length(begin) == 0) { 
      begin = 1
      game_details = NA
    }

done  <- grep("Event Assessments", temp)
if (length(done) == 0) {
  done = length(temp) + 1
  }

temp_info <- temp[(begin):(done - 1)]
head(temp_info)

plays <- temp_info[c(grep("^Period", temp_info),
                     grep("^Q", temp_info))]

play_data <- read_table(plays, col_names = FALSE,
                        col_types = cols(.default = "c"))

glimpse(play_data)

names(play_data) <- c("period", "time", "call_type", "committing",
                      "disadvantaged", "decision", "decision2")
play_data <- play_data %>% 
  mutate(decision = ifelse(is.na(decision) | decision == "",
                           decision2, decision)) %>% 
  select(period, time, call_type, committing, disadvantaged, decision)
glimpse(play_data)

temp_com <- str_remove(temp_info[grep("^Comment", temp_info)], "Comment:")
comment  <- data.frame(comments = str_trim(temp_com))
comments <- bind_rows(data.frame(comments = NA), comment)

results <- bind_cols(play_data, comments)
glimpse(results)