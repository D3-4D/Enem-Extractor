# Copyright 2025 D3-4D

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from json import dump, load as jload
from requests import Session as S
from argparse import ArgumentParser
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup, Tag
from os import path as pathlib, makedirs
from datetime import datetime

try:
    from tqdm import tqdm
except BaseException:
    tqdm = None

try:
    from colorama import Fore, init, Style
except BaseException:
    class _Empty:
        def __getattr__(self):
            return ""
    Fore = _Empty()
    init = lambda **kwargs: None

if __name__ == "__main__":
    try:
        from tkinter.filedialog import askdirectory as AskDir
    except BaseException:
        AskDir = lambda: input("Input Directory: ")
else:
    AskDir = lambda: input("Input Directory: ")

def Download(Directory:str|None=None, Filters:list|None=None, Replacement:bool|None=None):
    ErrLogsFile = pathlib.join(pathlib.dirname(pathlib.abspath(__file__)), "ErrorLogs.json")

    Session = S()

    Adapt = HTTPAdapter(max_retries=Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    ))

    Session.mount("http://", Adapt)
    Session.mount("https://", Adapt)

    del Adapt

    init(autoreset=True)

    Parser = ArgumentParser()

    FilterG = Parser.add_argument_group("Filter Options")
    FilterG.add_argument("--Retry")
    FilterG.add_argument("--Replace", action="store_true")
    FilterG.add_argument("--Type", type=int)
    FilterG.add_argument("--Mode", type=int)
    FilterG.add_argument("--Link", nargs="*", default=None)
    FilterG.add_argument("--Tab", nargs="*", default=None)
    FilterG.add_argument("--Title", nargs="*", default=None)
    FilterG.add_argument("--Year", nargs="*", type=int, default=None)

    Settings = Parser.parse_args()

    Replace = Replacement if Replacement is not None else Settings.Replace

    _Filters = Filters if Filters is not None else {
        "Type": Settings.Type if Settings.Type is not None else 0,           # 0: None, 1: Inclusive, 2: Exclusive
        "Mode": Settings.Mode if Settings.Mode is not None else 2,           # 0: Exam, 1: Answers, 2: Both, 3: Both strict
        "Retry": Settings.Retry,                                             # Retry file path (exclusive execution mode)
        "Inlink": Settings.Link if Settings.Link is not None else [],        # Raw link
        "InTab": Settings.Tab if Settings.Tab is not None else [],           # Title rows
        "InTitle": Settings.Title if Settings.Title is not None else [],     # Link rows
        "Year": Settings.Year if Settings.Year is not None else []           # Specific year (int)
    }

    del FilterG, Settings, Parser

    if _Filters["Retry"]:
        if not pathlib.isfile(_Filters["Retry"]):
            raise SystemExit(f"{Fore.RED}Retry path is invalid.{Style.RESET_ALL}")
        
        try:
            with open(_Filters["Retry"], "r", encoding="utf-8") as f:
                _Filters["Retry"] = jload(f)
        except BaseException:
            raise SystemExit(f"{Fore.RED}Retry file is not valid JSON or corrupted.{Style.RESET_ALL}")
        
        if not isinstance(_Filters["Retry"], dict):
            raise SystemExit(f"{Fore.RED}Retry file is corrupted.{Style.RESET_ALL}")

    MainEndpoint = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/"

    def GetYearPage(Year:int):
        print(f"{Fore.BLUE}Requesting year page: {Year}{Style.RESET_ALL}")
        return Session.get(MainEndpoint+f"/{Year}")

    RangeMin = 1998
    RangeMax = datetime.now().year

    print(f"{Fore.LIGHTBLUE_EX}Checking endpoint availability...{Style.RESET_ALL}")
    if not (200 <= GetYearPage(RangeMax).status_code < 300):
        RangeMax -= 1
        if not (200 <= GetYearPage(RangeMax).status_code < 300):
            raise SystemExit(f"{Fore.RED}Request failed, verify computer clock synchronization or network connectivity.{Style.RESET_ALL}")

    DownloadDirectory = Directory if Directory is not None else AskDir()

    if not DownloadDirectory or not pathlib.exists(DownloadDirectory):
        raise SystemExit(f"{Fore.RED}Invalid path.{Style.RESET_ALL}")

    print(f"{Fore.LIGHTBLUE_EX}Saving files to: {DownloadDirectory}{Style.RESET_ALL}")

    ErrorLogs = {}
    if _Filters["Retry"]:
        for Year, List in _Filters["Retry"].items():
            for Data in List:
                print(f"{Fore.BLUE}\n=== Processing year {Year} ==={Style.RESET_ALL}")
                print(f"{Fore.LIGHTBLUE_EX}Retrying download from Error: {Data[2]}")

                Item = Data[0]

                Path = Data[1]
                makedirs(pathlib.dirname(Path), exist_ok=True)
                Title = pathlib.basename(pathlib.dirname(Path))
                try:
                    print(f"{Fore.GREEN}Downloading {Item[1]} → {Title}{Style.RESET_ALL}")
                    R = Session.get(Item[0], stream=True) 

                    File = Path

                    if not (200 <= R.status_code < 300):
                        print(f"{Fore.LIGHTRED_EX}{Item[1]} download failed.")
                        if not str(Year) in ErrorLogs:
                            ErrorLogs[str(Year)] = []
                        ErrorLogs[str(Year)].append([Item, File, R.status_code])
                        continue
                    
                    Total = int(R.headers.get("Content-Length", 0))
                    if tqdm:
                        with open(File, "wb") as f, tqdm(
                            total=Total,
                            unit="B",
                            unit_scale=True,
                            desc=f"{Item[1]} {Year}"
                        ) as Bar:
                            for Chunk in R.iter_content(16384):
                                if Chunk:
                                    f.write(Chunk)
                                    Bar.update(len(Chunk))
                    else:
                        with open(File, "wb") as f:
                            for Chunk in R.iter_content(16384):
                                if Chunk:
                                    f.write(Chunk)
                except BaseException as E:
                    print(f"{Fore.LIGHTRED_EX}Temporarily unable to download {Item[1]} - {Title}. Error: {repr(E)}{Style.RESET_ALL}")
                    if not str(Year) in ErrorLogs:
                        ErrorLogs[str(Year)] = []
                    ErrorLogs[str(Year)].append([Item, File, repr(E)])
    else:
        for Year in (range(RangeMin, RangeMax+1) if _Filters["Type"] != 1 else _Filters["Year"]):
            print(f"{Fore.BLUE}\n=== Processing year {Year} ==={Style.RESET_ALL}")

            if _Filters["Type"] == 2 and Year in _Filters["Year"]:
                print(Fore.LIGHTYELLOW_EX + f"Skipping {Year} due to filter.{Style.RESET_ALL}")
                continue
            
            Response = GetYearPage(int(Year))
            # list-download__row is a temporary measure for supporting the unusual 2003 structure
            Page = BeautifulSoup(Response.text, "html.parser").select_one("div.list-download__row") or BeautifulSoup(Response.text, "html.parser").find(id="parent-fieldname-text")

            if not Page:
                print(f"{Fore.LIGHTRED_EX}Could not find content for this year.{Style.RESET_ALL}")
                continue

            # The older exams are not properly formatted within their interface. Uncategorized directories will be named "Undefined"
            Tab = "Undefined"
            Title = "Undefined"

            for Item in Page.children:
                if not isinstance(Item, Tag):
                    continue

                Type = Item.name

                if "h" in Type: # Extract tabs
                    Tab = Item.get_text(strip=True).replace("/", "-")
                    print(f"{Fore.CYAN}[TAB] {Tab}{Style.RESET_ALL}")

                elif Type == "p" or Type == "div": # Extract titles
                    if Type == "div": # Temporary(?) measure for 2022 and 2023 formatting. 
                        Item = Item.find("p")
                    Title = Item.get_text(strip=True).replace("/", "-")
                    print(f"{Fore.CYAN}[TITLE] {Title}{Style.RESET_ALL}")

                elif Type == "ul":  # Extract urls
                    Exam = Item.find('a', string='Prova') if _Filters["Mode"] != 1 else None
                    Answers = Item.find('a', string='Gabarito') if _Filters["Mode"] != 0 else None

                    # Temporary measures for the 2017 href typos (retards...)
                    if Exam and Exam.has_attr("href"):
                        Exam["href"] = Exam["href"].replace("http//", "")
                        print(f"{Fore.LIGHTCYAN_EX}Exam: {Exam["href"]}{Style.RESET_ALL}")
                    if Answers and Answers.has_attr("href"):
                        Answers["href"] = Answers["href"].replace("http//", "")
                        print(f"{Fore.LIGHTCYAN_EX}Answers: {Answers["href"]}{Style.RESET_ALL}")

                    if _Filters["Mode"] == 3 and not (Exam and Answers):
                        continue

                    # Apply _Filters
                    if _Filters["Type"] != 0:
                        for LinkF in _Filters["Inlink"]:
                            if Exam and (LinkF in Exam["href"]) == (_Filters["Type"] == 2):
                                Exam = None
                                print(Fore.LIGHTYELLOW_EX + f"Skipping {Title} Exam due to filter.{Style.RESET_ALL}")

                            if Answers and (LinkF in Answers["href"]) == (_Filters["Type"] == 2):
                                Answers = None
                                print(Fore.LIGHTYELLOW_EX + f"Skipping {Title} Answers due to filter.{Style.RESET_ALL}")

                        for TitleF in _Filters["InTitle"]:
                            if (TitleF in Title) == (_Filters["Type"] == 2):
                                print(Fore.LIGHTYELLOW_EX + f"Skipping {Title} due to filter.{Style.RESET_ALL}")
                                Exam = None
                                Answers = None

                        for TabF in _Filters["InTab"]:
                            if (TabF in Tab) == (_Filters["Type"] == 2):
                                print(Fore.LIGHTYELLOW_EX + f"Skipping {Title} due to filter.{Style.RESET_ALL}")
                                Exam = None
                                Answers = None

                    Path = pathlib.join(DownloadDirectory, str(Year), Tab, Title)
                    makedirs(Path, exist_ok=True)

                    # Downloads
                    _Download = [[Exam and Exam["href"], "Exam"], [Answers and Answers["href"], "Answers"]]

                    for Item in _Download:
                        if not Item[0]:
                            print(f"{Fore.LIGHTBLUE_EX}Excluding {Item[1]}.{Style.RESET_ALL}")
                        else:
                            try:
                                R = Session.get(Item[0], stream=True) 

                                File = pathlib.join(Path, f"{Item[1]}.pdf")

                                if not (200 <= R.status_code < 300):
                                    print(f"{Fore.LIGHTRED_EX}{Item[1]} download failed.")
                                    if not str(Year) in ErrorLogs:
                                        ErrorLogs[str(Year)] = []
                                    ErrorLogs[str(Year)].extend([Item, File, R.status_code])
                                    continue
                                elif pathlib.exists(File) and not Replace:
                                    print(f"{Fore.LIGHTYELLOW_EX}Skipping existing file: {File}{Style.RESET_ALL}")
                                    continue
                                
                                print(f"{Fore.GREEN}Downloading {Item[1]} → {Title}{Style.RESET_ALL}")
                                Total = int(R.headers.get("Content-Length", 0))
                                if tqdm:
                                    with open(File, "wb") as f, tqdm(
                                        total=Total,
                                        unit="B",
                                        unit_scale=True,
                                        desc=f"{Item[1]} {Year}"
                                    ) as Bar:
                                        for Chunk in R.iter_content(16384):
                                            if Chunk:
                                                f.write(Chunk)
                                                Bar.update(len(Chunk))
                                else:
                                    with open(File, "wb") as f:
                                        for Chunk in R.iter_content(16384):
                                            if Chunk:
                                                f.write(Chunk)
                            except BaseException as E:
                                print(f"{Fore.LIGHTRED_EX}Temporarily unable to download {Item[1]} - {Title}. Error: {repr(E)}{Style.RESET_ALL}")
                                if not str(Year) in ErrorLogs:
                                    ErrorLogs[str(Year)] = []
                                ErrorLogs[str(Year)].append([Item, File, repr(E)])
        with open(ErrLogsFile, "w", encoding="utf-8") as f:
            dump(ErrorLogs, f, indent=1)

if __name__ == "__main__":
    Download()
