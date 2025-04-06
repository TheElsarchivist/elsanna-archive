from ebooklib import epub
from bs4 import BeautifulSoup
import os
import re

# Generate list of paths for all epubs in directory
def getFiles(path, extension):
    files = []
    for (dir_path, dir_names, file_names) in os.walk(path):
        files.extend([(dir_path + "\\" + file) for file in file_names if file[-len(extension):] == extension])
    return(files)


# Remove class attributes from a bs4 html object
def CleanSoup(content):
    for tag in content.find_all(): 
        for val in list(tag.attrs):
            if val == "class":
                del tag.attrs[val]
            # DELETE
            if val == "id":
                del tag.attrs[val]
        if tag.name == "h2":
            tag.name = "h3"
        if tag.name == "h1":
            tag.name = "h3"
    return content


# Import an epub, extract and return it's metadata and chapters
def pullEPUB(file):

    # Define metadata dictionary
    metadata = {
        "ID": "",
        "Title": "",
        "StoryURL": "",
        "Author": "",
        "AuthorURL": "",
        "Series": "",
        "SeriesURL": "",
        "Category": "",
        "Genre": "",
        "Language": "",
        "LanguageID": "",
        "Characters": "",
        "Pairings": "",
        "Relationships": "",
        "Status": "",
        "Published": "",
        "Updated": "",
        "Packaged": "",
        "Rating": "",
        "Warnings": "",
        "Chapters": "",
        "Words": "",
        "Publisher": "",
        "Summary": "",
        "Comments": "",
        "Kudos": "",

    }

    # Extract metadata from first page
    book = epub.read_epub(file)
    chapters = []
    titles = []
    chapterCount = len(book.toc)
    metadata["LanguageID"] = book.metadata["http://purl.org/dc/elements/1.1/"]["language"][0][0]
    rawMetadata = BeautifulSoup(book.get_item_with_id(book.spine[0][0]).get_content(), "html.parser")
    content = rawMetadata.getText().split("\n")
    content = [line for line in content if line != ""]
    links = [node.get("href") for node in rawMetadata.find_all("a")]

    if "fanfiction.net" in book.metadata["http://purl.org/dc/elements/1.1/"]["publisher"][0][0]:
        
        # Special handling for title and author
        metadata["StoryURL"], metadata["AuthorURL"] = links
        metadata["ID"] = metadata["StoryURL"].split("/s/")[1].split("/")[0]
        metadata["Title"], metadata["Author"] = content[0].rsplit(" by ", 1)
        content.pop(0)

        # Ensure standardisation in url formatting
        if len(metadata["StoryURL"].split("/")) == 7:
            metadata["StoryURL"] = metadata["StoryURL"].rsplit("/", 2)[0]
        if metadata["StoryURL"][-3:] == "/1/":
            metadata["StoryURL"] = metadata["StoryURL"][:-3]
        if len(metadata["AuthorURL"].split("/")) == 6:
            metadata["AuthorURL"] = metadata["AuthorURL"].rsplit("/", 1)[0]

        # Read metadata into dictionary
        while(len(content) > 0):
            temp = content.pop(0).split(": ", 1)    
            metadata[temp[0]] = temp[1]
            
            # Handling for multiple line summaries
            if temp[0] == "Summary":
                while(len(content) > 0):
                    metadata[temp[0]] = "</p><p>".join((metadata[temp[0]], content.pop(0)))
            metadata["Summary"] = "<p>" + metadata["Summary"] + "</p>"
        
        # Consolidate relationship and pairings metadata
        metadata["Relationships"] = metadata["Pairings"]
    
    if "archiveofourown" in book.metadata["http://purl.org/dc/elements/1.1/"]["publisher"][0][0]:
        
        # Special handling for series
        # Need to add proper handling for multiple series
        if "/series/" in links[-1]:
            metadata["SeriesURL"] =links.pop(-1)

        # Special handling for title and author
        if (len(links) > 2):
            metadata["StoryURL"] = links[0]
            metadata["AuthorURL"] = links[1:]
            metadata["AuthorURL"] = [link for link in metadata["AuthorURL"] if "https://archiveofourown.org/users/" in link]
        else:
            metadata["StoryURL"], metadata["AuthorURL"] = links
        metadata["ID"] = metadata["StoryURL"].split("/works/")[1].split("/")[0]
        metadata["Title"], metadata["Author"] = content[0].rsplit(" by ", 1)
        content.pop(0)

        # Read metadata into dictionary
        while(len(content) > 0):
            temp = content.pop(0).split(": ", 1)    
            metadata[temp[0]] = temp[1]
            
            # Handling for multiple line summaries
            if temp[0] == "Summary":
                if(len(content) > 0):
                    metadata[temp[0]] = content.pop(0)
                while(len(content) > 0):
                    metadata[temp[0]] = "</p><p>".join((metadata[temp[0]], content.pop(0)))
            metadata["Summary"] = "<p>" + metadata["Summary"] + "</p>"
    
    if "wattpad" in book.metadata["http://purl.org/dc/elements/1.1/"]["publisher"][0][0]:
    
        # Special handling for title and author
        metadata["StoryURL"], metadata["AuthorURL"] = links
        metadata["ID"] = metadata["StoryURL"].split("/story/")[1].split("/")[0]
        metadata["Title"], metadata["Author"] = content[0].rsplit(" by ", 1)
        content.pop(0)

        # Read metadata into dictionary
        while(len(content) > 0):
            temp = content.pop(0).split(": ", 1)    
            metadata[temp[0]] = temp[1]
            
            # Handling for multiple line summaries
            if temp[0] == "Summary":
                while(len(content) > 0):
                    line = content.pop(0)
                    if "Language: " in line:
                        content = []
                    else:
                        metadata[temp[0]] = "</p><p>".join((metadata[temp[0]], line))
            metadata["Summary"] = "<p>" + metadata["Summary"] + "</p>"


    # Pull chapter html
    for i in range(1, chapterCount):
        titles.append(book.toc[i].title.split(". ")[-1])
        chapters.append(CleanSoup(BeautifulSoup(book.get_item_with_id(book.spine[i][0]).get_content(), "html.parser")))
        h3_tag = chapters[i - 1].find("h3")
        h3_tag.string = titles[i - 1]
        h3_tag.attrs["style"]= "text-align: center;"


    # Remove unimportant metadata entries
    del metadata["Pairings"]
    del metadata["Packaged"]
    del metadata["Comments"]
    del metadata["Kudos"]

    # Simplify dates, publisher, and wordcount
    metadata["Published"] = metadata["Published"].split(" ")[0]
    metadata["Updated"] = metadata["Updated"].split(" ")[0]
    metadata["Publisher"] = metadata["Publisher"].replace("www.", "")
    metadata["Words"] = metadata["Words"].replace(",", "")

    return((metadata, titles, chapters))


# Generate a new epup using metadata and chapter content
def writeEpub(metadata, titles, chapters):

    # Instantiate book
    bookContent = []
    book = epub.EpubBook()
    book.toc = []
    book.spine = []
    book.set_identifier(metadata["ID"])
    book.set_title(metadata["Title"])
    book.set_language(metadata["LanguageID"])
    if "," in metadata["Author"]:
        authors = metadata["Author"].split(", ")
        for author in authors:
            book.add_author(author)
    else:
        book.add_author(metadata["Author"])

    # Prepare directory for saving book
    path = "C:/Archive/" + metadata["Publisher"].split(".")[0] + "/" + "".join([c for c in metadata["Author"].split(",")[0] if re.match(r'\w', c)])
    if not os.path.exists(path):
        os.makedirs(path)
    path = path + "/" + metadata["ID"] + "_" + "".join([c for c in metadata["Title"] if re.match(r'\w', c)]) + ".epub"
    

    # Add metadata
    book.add_metadata("DC", "date", metadata["Published"])
    book.add_metadata("DC", "modified", metadata["Updated"])
    book.add_metadata("DC", "description", metadata["Summary"][3:-4].replace("</p><p>", " "))
    book.add_metadata("DC", "publisher", metadata["Publisher"])
    book.add_metadata("DC", "source", metadata["StoryURL"])
    tags = ", ".join((metadata["Category"], metadata["Genre"], metadata["Characters"], metadata["Relationships"]))
    for tag in tags.split(", "):
        book.add_metadata("DC", "subject", tag)

    # Construct title page
    titleHTML = []
    titleHTML.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    titleHTML.append("<html xmlns=\"http://www.w3.org/1999/xhtml\">")
    titleHTML.append("<head>")
    titleHTML.append("<title>" + metadata["Title"] + " by " + metadata["Author"] + "</title>")
    titleHTML.append("<link href=\"stylesheet.css\" type=\"text/css\" rel=\"stylesheet\"/>")
    titleHTML.append("</head>")
    titleHTML.append("<body>")

    # Handling for multiple authors
    if type(metadata["AuthorURL"]) is list:
        authorTags = []
        names = metadata["Author"].split(", ")
        for i in range(len(metadata["Author"].split(", "))):
            authorTags.append("<a href=\"" + metadata["AuthorURL"][i] + "\">" + names[i] + "</a>")
        titleHTML.append("<h3 style=\"text-align: center;\"><a href=\"" + metadata["StoryURL"] + "\">" + metadata["Title"] + "</a> by " + ", ".join(authorTags) + "</h3>")
    else: 
        titleHTML.append("<h3 style=\"text-align: center;\"><a href=\"" + metadata["StoryURL"] + "\">" + metadata["Title"] + "</a> by " + "<a href=\"" + metadata["AuthorURL"] + "\">" + metadata["Author"] + "</a>" + "</h3>")

    titleHTML.append("<div>")

    # URL handling for series
    if metadata["Series"]:
        titleHTML.append("<b>Series:</b> " + " <a class=\"serieslink\" href=\"" + metadata["SeriesURL"] + "\">" + metadata["Series"] + "</a><br />")
        del metadata["Series"]
        del metadata["SeriesURL"]
    
    # Delete redundant metadata
    del metadata["ID"]
    del metadata["Title"]
    del metadata["Author"]
    del metadata["StoryURL"]
    del metadata["AuthorURL"]
    del metadata["LanguageID"]
    metadata = {k:v for k,v in metadata.items() if v!=""}

    # Iteratively add metadata
    for key, value in metadata.items():
        titleHTML.append("<b>" + key + ":</b> " + value + "<br/>")

    titleHTML.append("</div>")
    titleHTML.append("</body>")
    titleHTML.append("</html>")

    # Format title page for epub and add to book
    titlePage = BeautifulSoup("\n".join(titleHTML), "html.parser")
    bookContent.append(epub.EpubHtml(title = "Title Page", file_name = "titlepage.xhtml", lang = book.language))
    bookContent[0].content = titlePage.prettify().encode('utf-8')
    book.toc.append(epub.Link("titlepage.xhtml", "Title Page", "titlepage"))
    book.spine.append(bookContent[0])

    # Iterate through chapters and format them for epub
    for i in range(len(chapters)):
        filename = "chapter" + str(i + 1).zfill(3) + ".xhtml"
        bookContent.append(epub.EpubHtml(title = titles[i], file_name = filename, lang = book.language))
        bookContent[i + 1].content = chapters[i].prettify().encode('utf-8')
        book.toc.append(epub.Link(filename, titles[i], filename[:-6]))
        book.spine.append(bookContent[i + 1])
    
    # Add chapters to book
    for item in bookContent:
        book.add_item(item)

    # Add default NCX toc
    book.add_item(epub.EpubNcx())

    # define CSS style
    style = "BODY {color: white;}"
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style,
    )

    # add CSS file
    book.add_item(nav_css)

    # Generate book
    epub.write_epub(path, book, {})

    return(path)


# Writes a SQL statement to add a book's information to a database
def databaseWriter(path, metadata):

    if type(metadata["AuthorURL"]) is list:
        metadata["AuthorURL"] = ", ".join(metadata["AuthorURL"])

    if metadata["Summary"] != "":
        metadata["Summary"] = metadata["Summary"].replace("<p>", "").replace("</p>", " ")[:-1]

    for k,v in metadata.items():
        metadata[k] = v.replace("'", "''")
        if v == "":
            metadata[k] = "NULL"

    lead = "REPLACE INTO \"" + metadata["Publisher"].split(".")[-2] + "\" VALUES ('"
    content = "','".join((metadata["ID"], 
                          path[10:], 
                          metadata["Title"], 
                          metadata["StoryURL"], 
                          metadata["Author"], 
                          metadata["AuthorURL"], 
                          metadata["Series"], 
                          metadata["SeriesURL"], 
                          metadata["Category"], 
                          metadata["Genre"], 
                          metadata["Characters"], 
                          metadata["Relationships"], 
                          metadata["Language"], 
                          metadata["LanguageID"], 
                          metadata["Status"], 
                          metadata["Published"], 
                          metadata["Updated"], 
                          metadata["Rating"], 
                          metadata["Warnings"], 
                          metadata["Chapters"], 
                          metadata["Words"], 
                          metadata["Publisher"], 
                          metadata["Summary"]))
    end = "');\n"

    return("".join((lead, content, end)).replace("'NULL'", "NULL"))


########
# MAIN #
########


sql = []
books = []
sourcePath = "C:\\FF Lib\\Temp\\"
# Read files to list and pull their content.
files = getFiles(sourcePath, ".epub")
for file in files:
    books.append(pullEPUB(file))

# Generate new epubs and database entries
for book in books:
    path = writeEpub(book[0].copy(), book[1].copy(), book[2].copy())
    sql.append(databaseWriter(path, book[0].copy()))

# Write SQL statment for updating database
f = open("C:/Archive/newEntries.sql", "w", encoding="utf-8")
f.writelines(sql)
f.close()

print("done")











# SQL statement for creating the database
"""
BEGIN TRANSACTION;
CREATE DATABASE elsannaDB;
CREATE TABLE IF NOT EXISTS "fanfiction" (
	"ID"	TEXT,
	"Path"	TEXT,
	"Title"	TEXT,
	"StoryURL"	TEXT,
	"Author"	TEXT,
	"AuthorURL"	TEXT,
	"Series"	TEXT,
	"SeriesURL"	TEXT,
	"Category"	TEXT,
	"Genre"	TEXT,
	"Characters"	TEXT,
	"Relationships"	TEXT,
	"Language"	TEXT,
	"LanguageID"	TEXT,
	"Status"	TEXT,
	"Published"	DATE,
	"Updated"	DATE,
	"Rating"	TEXT,
	"Warnings"	TEXT,
	"Chapters"	INT,
	"Words"	INT,
	"Publisher"	TEXT,
	"Summary"	TEXT,
	PRIMARY KEY (ID)
);
CREATE TABLE IF NOT EXISTS "archiveofourown" (
	"ID"	TEXT,
	"Path"	TEXT,
	"Title"	TEXT,
	"StoryURL"	TEXT,
	"Author"	TEXT,
	"AuthorURL"	TEXT,
	"Series"	TEXT,
	"SeriesURL"	TEXT,
	"Category"	TEXT,
	"Genre"	TEXT,
	"Characters"	TEXT,
	"Relationships"	TEXT,
	"Language"	TEXT,
	"LanguageID"	TEXT,
	"Status"	TEXT,
	"Published"	DATE,
	"Updated"	DATE,
	"Rating"	TEXT,
	"Warnings"	TEXT,
	"Chapters"	INT,
	"Words"	INT,
	"Publisher"	TEXT,
	"Summary"	TEXT,
	PRIMARY KEY (ID)
);
CREATE TABLE IF NOT EXISTS "wattpad" (
	"ID"	TEXT,
	"Path"	TEXT,
	"Title"	TEXT,
	"StoryURL"	TEXT,
	"Author"	TEXT,
	"AuthorURL"	TEXT,
	"Series"	TEXT,
	"SeriesURL"	TEXT,
	"Category"	TEXT,
	"Genre"	TEXT,
	"Characters"	TEXT,
	"Relationships"	TEXT,
	"Language"	TEXT,
	"LanguageID"	TEXT,
	"Status"	TEXT,
	"Published"	DATE,
	"Updated"	DATE,
	"Rating"	TEXT,
	"Warnings"	TEXT,
	"Chapters"	INT,
	"Words"	INT,
	"Publisher"	TEXT,
	"Summary"	TEXT,
	PRIMARY KEY (ID)
);
CREATE TABLE IF NOT EXISTS "fictionpress" (
	"ID"	TEXT,
	"Path"	TEXT,
	"Title"	TEXT,
	"StoryURL"	TEXT,
	"Author"	TEXT,
	"AuthorURL"	TEXT,
	"Series"	TEXT,
	"SeriesURL"	TEXT,
	"Category"	TEXT,
	"Genre"	TEXT,
	"Characters"	TEXT,
	"Relationships"	TEXT,
	"Language"	TEXT,
	"LanguageID"	TEXT,
	"Status"	TEXT,
	"Published"	DATE,
	"Updated"	DATE,
	"Rating"	TEXT,
	"Warnings"	TEXT,
	"Chapters"	INT,
	"Words"	INT,
	"Publisher"	TEXT,
	"Summary"	TEXT,
	PRIMARY KEY (ID)
);
"""