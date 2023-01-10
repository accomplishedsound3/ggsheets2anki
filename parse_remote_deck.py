import re

import bs4
import requests
from bs4 import BeautifulSoup

from .libs.org_to_anki import config
from .libs.org_to_anki.build_deck_from_org_lines import build_deck_from_org_lines


# Should get the remote deck and return an Anki Deck
def getRemoteDeck(url):
    # Get remote page
    # TODO Validate url before getting data
    pageType = _determinePageType(url)
    deck = None
    if pageType == "html":
        data = _download(url)
        orgData = _parseHtmlPageToAnkiDeck(data)
        deck = orgData["deck"]

    elif pageType == "sheet":
        data = _download(url)
        orgData = _parseHtmlPageToAnkiDeck(data)
        deck = orgData["deck"]
    else:
        raise Exception("url is not a Google doc or sheet file")

    return orgData


def _determinePageType(url):

    # TODO use url to determine page types
    sheetString = "/spreadsheets/"
    documentString = "/document/"
    if (documentString in url):
        return "html"
    elif (sheetString in url):
        return "sheet"
    else:
        return None


def _parseHtmlPageToAnkiDeck(data):

    orgData = _generateOrgListFromHtmlPage(data)
    deckName = orgData["deckName"]
    data = orgData["data"]
    orgData["deck"] = build_deck_from_org_lines(data, deckName)

    # Ensure images are lazy loaded to reduce load
    config.lazyLoadImages = True

    return orgData


def _generateOrgListFromHtmlPage(data):

    imageTemplate = " [image={}]"
    soup = BeautifulSoup(data, 'html.parser')
    deckName = soup.find("div", {"id":"doc-title"})
    contents = soup.find_all("table", {"class":"waffle"})

    deckName = list(header.children)[0].text
    sheetsSoup = soup.find("ul", {"id":"sheet-menu"})
    sheets = {}
    sheetsName=[]
    for sheet in sheetsSoup.children:
        #print(sheet)
        if sheet.name == "li" and len(list(sheet.children))>0 :
            key = list(sheet.children)[0].text
            sheets[key]={}
            sheetsName.append(key)
    contents = soup.find_all("table", {"class":"waffle"})
    # Try and get CSS
    """ """
    cssData = soup.find_all("style")
    cssStyles = {}
    for css in cssData:
        cssData = soup.find_all("style")[0]
        styleSection = _getCssStyles(cssData)
        cssStyles.update(styleSection)
    """ """

    orgFormattedFile = []

    for table, tableName in zip(contents, sheetsName):
        for tbody in table.children:
            if tbody.name == "tbody":
                header = True
                fields = []
                for row in tbody.children:
                    j = 0
                    for item in row.children:
                        # print(item)
                        if item.name == "td" and header == True:
                            fields.append(item.text)
                            sheets[tableName][item.text] = []
                        elif item.name == "td" and header == False:
                            # print("p")
                            sheets[tableName][fields[j]].append(item.text)
                            j += 1
                            lineText = item.text
                            if len(lineText) > 0:
                                orgFormattedFile.append(lineText)

                            # Item class is in the format of s## where # is a number
                            itemText = []

                            textSpans = item.find_all("span")
                            lineOfText = ""
                            for span in textSpans:
                                lineOfText += _extractSpanWithStyles(
                                    span, cssStyles)
                                # Check for images and take first
                            images = item.find_all("img")
                            if len(images) >= 1:
                                imageText = imageTemplate.format(
                                    images[0]["src"])
                                lineOfText += imageText
                                itemText.append(lineOfText)

                        else:
                            pass
                            # print("Unknown line type: {}".format(item.name))
                    header = False

    return {"deckName": deckName, "data": orgFormattedFile, "sheets": sheets}


def _getCssStyles(cssData):

    # Google docs used the following class for lists $c1
    cSectionRegexPattern = "\.s\d{1,2}\{[^\}]+}"
    cssSections = re.findall(cSectionRegexPattern, cssData.text)

    cssStyles = {}
    # for each c section extract critical data
    regexValuePattern = ":[^;^}\s]+[;}]"
    startSectionRegex = "[;{]"
    for section in cssSections:
        name = re.findall("s[\d]+", section)[0]
        color = re.findall("{}{}{}".format(
            startSectionRegex, "color", regexValuePattern), section)
        fontStyle = re.findall("{}{}{}".format(
            startSectionRegex, "font-style", regexValuePattern), section)
        fontWeight = re.findall("{}{}{}".format(
            startSectionRegex, "font-weight", regexValuePattern), section)
        textDecoration = re.findall("{}{}{}".format(
            startSectionRegex, "text-decoration", regexValuePattern), section)

        # Ignore default values
        if (len(color) > 0 and "color:#000000" in color[0]):
            color = []
        if (len(fontWeight) > 0 and "font-weight:400" in fontWeight[0]):
            fontWeight = []
        if (len(fontStyle) > 0 and "font-style:normal" in fontStyle[0]):
            fontStyle = []
        if (len(textDecoration) > 0 and "text-decoration:none" in textDecoration[0]):
            textDecoration = []

        d = [color, fontStyle, fontWeight, textDecoration]

        styleValues = []
        for i in d:
            if len(i) > 0:
                cleanedStyle = i[0][1:-1]
                styleValues.append(cleanedStyle)
        cssStyles[name] = styleValues

    return cssStyles

def _extract_css_styles(style_item: bs4.element.Tag):

    # Google docs uses c1, c2, ... classes for styling
    css_section_re = "\.c\d+\{[\w\W]+?}"
    html_str = style_item.decode_contents()
    css_sections = re.findall(css_section_re, html_str)

    result = {}

    # for each c section extract critical data
    data_re = ":[^;^}\s]+[;}]"
    section_start_re = "[;{]"
    for section in css_sections:
        name = re.findall("c[\d]+", section)[0]
        color = re.findall("{}{}{}".format(
            section_start_re, "color", data_re), section)
        font_style = re.findall(
            "{}{}{}".format(section_start_re, "font-style", data_re), section
        )
        font_weight = re.findall(
            "{}{}{}".format(section_start_re, "font-weight", data_re),
            section,
        )
        text_decoration = re.findall(
            "{}{}{}".format(section_start_re, "text-decoration", data_re),
            section,
        )
        vertical_align = re.findall(
            "{}{}{}".format(section_start_re, "vertical-align", data_re),
            section,
        )

        # Ignore default values
        if len(color) > 0 and "color:#000000" in color[-1]:
            color = []
        if len(font_weight) > 0 and "font-weight:400" in font_weight[-1]:
            font_weight = []
        if len(font_style) > 0 and "font-style:normal" in font_style[-1]:
            font_style = []
        if len(text_decoration) > 0 and "text-decoration:none" in text_decoration[-1]:
            text_decoration = []
        if len(vertical_align) > 0 and "vertical-align:baseline" in vertical_align[-1]:
            vertical_align = []

        style_rules = [color, font_style, font_weight,
                       text_decoration, vertical_align]
        style_values = []
        for style_rule in style_rules:
            if len(style_rule) > 0:
                cleaned_style = style_rule[-1][1:-1]
                style_values.append(cleaned_style)

        result[name] = style_values

    return result
    
def _extractSpanWithStyles(soupSpan, cssStyles):

    text = soupSpan.text
    classes = soupSpan.attrs.get("class")

    if classes == None:
        return text

    relevantStyles = []
    for clazz in classes:
        if cssStyles.get(clazz) != None:
            for style in cssStyles.get(clazz):
                relevantStyles.append(style)

    if len(relevantStyles) > 0:
        styleAttributes = ""
        for i in relevantStyles:
            styleAttributes += i + ";"
        styledText = '<span style="{}">{}</span>'.format(styleAttributes, text)
        return styledText
    else:
        return text


def substitute_cloze_aliases(html):
    result = html
    cloze_idx = 1
    alias_re = "\$(\d*)\$(.+?)\$\$"
    while m := re.search(alias_re, result):
        number, text = m.groups()
        cur_idx = number if number else cloze_idx
        result = re.sub(
            alias_re, f"{{{{c{cur_idx}::{text.strip()}}}}}", result, count=1
        )
        cloze_idx += 1
    return result


def _clean_up(item):
    parent = item.parent
    item.decompose()
    if not parent.contents:
        _clean_up(parent)


### Special cases ###


def _startOfMultiLineComment(item):

    # Get span text
    if item.name == "p":
        line = ""
        sections = item.find_all("span")
        for span in sections:
            line += span.text
        if "#multilinecommentstart" == line.replace(" ", "").lower():
            return True
    return False


def _endOfMultiLineComment(item):

    # Get span text
    if item.name == "p":
        line = ""
        sections = item.find_all("span")
        for span in sections:
            line += span.text
        if "#multilinecommentend" == line.replace(" ", "").lower():
            return True
    return False


def _apply_styles(item, cssStyles, depth=0):
    if not hasattr(item, "attrs"):
        return

    classes = item.attrs.get("class", None)
    if classes is None:
        return

    for class_ in classes:
        for style in cssStyles.get(class_, []):
            item["style"] = item.get("style", "") + style + "; "
    item.attrs.pop("class", None)

    for child in item.children:
        _apply_styles(child, cssStyles, depth=depth + 1)

    # text in tables gets wrapped into p tags by default which should be removed
    if depth == 1 and item.name == "p" and len(list(item.children)) == 1:
        item.replace_with(list(item.children)[0])

    if item.name == "span" and len(item.attrs) == 0:
        item.unwrap()

    return item


def _download(url):

    response = requests.get(url)
    if response.status_code == 200:
        data = response.content
    else:
        raise Exception("Failed to get url: {}".format(response.status_code))

    data = data.decode("utf-8")
    data = data.replace("\xa0", " ")
    return data