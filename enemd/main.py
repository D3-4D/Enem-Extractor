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
from urllib3 import disable_warnings, exceptions
from contextlib import nullcontext
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup, Tag
from os import path, cpu_count
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4


try:
    assert __name__ != "__main__"
    from tkinter.filedialog import askdirectory as AskDir
except Exception:
    AskDir = lambda: input("Input Directory: ")


Parser = ArgumentParser()

FilterG = Parser.add_argument_group("Settings")

# Global
FilterG.add_argument("--Debug", type=int)
FilterG.add_argument("--Retry", type=str)

# Extraction
FilterG.add_argument("--Mode", type=int)
FilterG.add_argument("--Type", type=int)
FilterG.add_argument("--Link", nargs="*", default=None)
FilterG.add_argument("--Tab", nargs="*", default=None)
FilterG.add_argument("--Title", nargs="*", default=None)
FilterG.add_argument("--Year", nargs="*", type=int, default=None)
FilterG.add_argument("--LooseEx", type=bool)
FilterG.add_argument("--ThreadedEx", type=bool)

#Download
FilterG.add_argument("--ThreadedDw", type=bool)
FilterG.add_argument("--Replace", type=bool)

Parsed = Parser.parse_args()

Settings = {
    # Global
    "Debug": Parsed.Debug if Parsed.Debug is not None else 3,                       # 0: Off, 1: Minimal, 2: Basic, 3: Verbose
    "Retry": Parsed.Retry,                                                          # Retry file path (specific execution mode, ignores most flags)

    # Extraction
    "Mode": Parsed.Mode if Parsed.Mode is not None else 2,                          # 0: Exam, 1: Answers, 2: Both, 3: Both strict             
    "Type": Parsed.Type if Parsed.Type is not None else 0,                          # 0: Inclusive, 1: Exclusive (filter type. Applies to InLink, InTab, InTitle and Year)
    "InLink": Parsed.Link if Parsed.Link is not None else [],                       # Raw link
    "InTab": Parsed.Tab if Parsed.Tab is not None else [],                          # Title rows
    "InTitle": Parsed.Title if Parsed.Title is not None else [],                    # Link rows
    "Year": Parsed.Year if Parsed.Year is not None else [],                         # Specific year (int)
    "LooseEx": Parsed.LooseEx if Parsed.LooseEx is not None else True,              # Makes endpoint extraction sparse and opportunistic (unrequiring of all endpoints)
    "ThreadedEx": Parsed.ThreadedEx if Parsed.ThreadedEx is not None else True,    # Splits extraction with threading

    #Download
    "ThreadedDw": Parsed.ThreadedDw if Parsed.ThreadedDw is not None else True,    # Splits downloads with threading
    "Replace": Parsed.Replace if Parsed.Replace is not None else True              # Override already downloaded files
}


try:
    assert Settings["Debug"] != 0
    from tqdm import tqdm
except Exception:
    tqdm = None

try:
    assert Settings["Debug"] != 0
    from colorama import Fore, init, Style
except Exception:
    class _Empty:
        def __getattr__(self, *args, **kwargs):
            return ""
    Fore = _Empty()
    Style = _Empty()
    init = lambda **kwargs: None

if Settings["Retry"]:
    if not path.isfile(Settings["Retry"]):
        raise SystemError(f"{Fore.RED}Retry path is invalid.{Style.RESET_ALL}")
    
    try:
        with open(Settings["Retry"], "r", encoding="utf-8") as f:
            Settings["Retry"] = jload(f)
    except BaseException:
        raise SystemError(f"{Fore.RED}Retry file is not valid JSON or corrupted.{Style.RESET_ALL}")
    
    if not isinstance(Settings["Retry"], dict):
        raise SystemError(f"{Fore.RED}Retry file is corrupted.{Style.RESET_ALL}")

del FilterG, Parsed, Parser


Session = S()

Session.verify = False # Domain utilized is legitimate, verification only adds overhead and is prone to certification errors
disable_warnings(exceptions.InsecureRequestWarning)

Adapt = HTTPAdapter(max_retries=Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
))

Session.mount("http://", Adapt)
Session.mount("https://", Adapt)

del Adapt, disable_warnings, exceptions


init() # Colorama

ErrLogsFile = path.join(path.dirname(path.abspath(__file__)), "ErrorLogs.json")
ErrorLogs = {}


if not Settings["Retry"] or Settings["Retry"].get("modular"):
    def Extract_Endpoints(Years:range|int|None=None, PageMode:bool|None=False)->dict|None:
        if Settings["Debug"] > 0:
            print(f"{Fore.BLUE}Extracting api endpoints...{Style.RESET_ALL}")

        MainEndpoint = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/"
        MaxRange = range(1998, datetime.now().year + 1)

        def GetYearPage(Year:int, dbidx:int|str=""):
            ret = MainEndpoint+f"{Year}"

            if Settings["Debug"] > 1:
                print(f"{dbidx}{Fore.LIGHTBLUE_EX}Requesting year page: {Year}{f"({ret})" if Settings["Debug"] == 3 else ""}{Style.RESET_ALL}")
            
            try:
                get = Session.get(ret, timeout=1)

                if (200 <= get.status_code < 300):
                    if Settings["Debug"] == 3:
                        print(f"{dbidx}{Fore.GREEN}SUCCESS{Style.RESET_ALL}")

                    return get
                else:
                    if Settings["Debug"] == 3:
                        print(f"{dbidx}{Fore.GREEN}FAIL: Error code {get.status_code}{Style.RESET_ALL}")

                    return None
            except Exception as e:
                if Settings["Debug"] > 0:
                    print(f"{dbidx}{Fore.RED}FAIL: {e if Settings["Debug"] > 1 else ""}{Style.RESET_ALL}")

                return None

        if not Years:
            Years = MaxRange
        elif isinstance(Years, int):
            if PageMode:
                return GetYearPage(Years)
            else:
                Years = range(Years, Years+1)
        
        assert Years.start >= MaxRange.start and Years.stop <= MaxRange.stop

        Links = {}
    
        def ParsePage(year:int, dbidx:int|str=""):
            assert year

            dbidx = f"[{dbidx}]" if Settings["ThreadedEx"] else ""

            if Settings["Debug"] > 1:
                print(f"{dbidx}{Fore.LIGHTBLUE_EX}Processing year {year}.{Style.RESET_ALL}")
            
            if Settings["Year"] and (Settings["Type"] == 1) == (year in Settings["Year"]):
                if Settings["Debug"] > 1:
                    print(f"{dbidx}{Fore.LIGHTYELLOW_EX}Skipping due to {"exclusive" if Settings["Type"] == 1 else "inclusive"} year filter.{Style.RESET_ALL}")
                
                return
  
            _tempresp = GetYearPage(year, dbidx)
            if _tempresp:
                Page = BeautifulSoup(_tempresp.text, "html.parser").select_one("div.list-download__row") or BeautifulSoup(_tempresp.text, "html.parser").find(id="parent-fieldname-text")
            else:
                Page = None

            del _tempresp

            if not Page:
                if Settings["LooseEx"]:
                    if Settings["Debug"] > 0:
                        print(f"{dbidx}{Fore.LIGHTYELLOW_EX}Could not find content for this year's page. Proceeding anyway.{Style.RESET_ALL}")
                        
                    return
                else:
                    raise SystemError("Could not find content for this year's page.")

            
            Tab = "Undefined"
            Title = "Undefined"

            for Item in Page.children:
                Type = Item.name

                if Type is None: #not isinstance(Item, Tag):??
                    continue


                if "h" in Type: # Extract tabs
                    Tab = Item.get_text(strip=True).replace("/", "-")

                    if Settings["Debug"] == 3:
                        print(f"{dbidx}{Fore.CYAN}[TAB] {Tab}{Style.RESET_ALL}")
                elif Type == "p" or Type == "div": # Extract titles
                    if Type == "div": # Temporary(?) measure for 2022 and 2023 formatting. 
                        Item = Item.find("p")
                    
                    Title = Item.get_text(strip=True).replace("/", "-")

                    if Settings["Debug"] == 3:
                        print(f"{dbidx}{Fore.CYAN}[TITLE] {Title}{Style.RESET_ALL}")
                elif Type == "ul":  # Extract urls

                    Break = False

                    for Filter in Settings["InTab"]:
                        if (Filter in Tab) == (Settings["Type"] == 1):
                            if Settings["Debug"] > 1:
                                print(f"{dbidx}{Fore.LIGHTYELLOW_EX}Skipping due to {"exclusive" if Settings["Type"] == 1 else "inclusive"} tab filter.{Style.RESET_ALL}")
                                Break = True

                            break

                    for Filter in Settings["InTitle"]:
                        if (Filter in Title) == (Settings["Type"] == 1):
                            if Settings["Debug"] > 1:
                                print(f"{Fore.MAGENTA}{dbidx}{Style.RESET_ALL}{Fore.LIGHTYELLOW_EX}Skipping due to {"exclusive" if Settings["Type"] == 1 else "inclusive"} title filter.{Style.RESET_ALL}")
                                Break = True

                            break
                    
                    if Break:
                        continue

                    Exam = Item.find('a', string='Prova') if Settings["Mode"] != 1 else None
                    Answers = Item.find('a', string='Gabarito') if Settings["Mode"] != 0 else None

                    # Temporary measures for the 2017 href typos
                    if Exam and Exam.has_attr("href"):
                        Exam["href"] = Exam["href"].replace("http//", "")
                        
                        if Settings["Debug"] == 3:
                            print(f"{dbidx}{Fore.LIGHTCYAN_EX}Exam: {Exam["href"]}{Style.RESET_ALL}")
                    if Answers and Answers.has_attr("href"):
                        Answers["href"] = Answers["href"].replace("http//", "")

                        if Settings["Debug"] == 3:
                            print(f"{dbidx}{Fore.LIGHTCYAN_EX}Answers: {Answers["href"]}{Style.RESET_ALL}")

                    if Settings["Mode"] == 3 and not (Exam and Answers):
                        if Settings["Debug"] == 3:
                            print(f"{dbidx}{Fore.LIGHTYELLOW_EX}Skipping due to exclusive operation mode.{Style.RESET_ALL}")
                        continue

                    Links[str(year)] = Links.get(str(year)) or {}

                    Links[str(year)][Tab] = Links[str(year)].get(Tab) or {}

                    Links[str(year)][Tab][Title] = {
                        "Exam": Exam["href"] if Exam else None,
                        "Answers": Answers["href"] if Answers else None
                    }

        if Settings["ThreadedEx"]:
            with ThreadPoolExecutor(max_workers=min(int(cpu_count()/1.5), 32) or 2) as exe:
                work = {exe.submit(ParsePage, year, dbidx=idx): idx for idx, year in enumerate(Years)}
                for fu in as_completed(work):
                    try:
                        fu.result()
                        if Settings["Debug"] > 3:
                            print(f"{Fore.MAGENTA}{work[fu]}{Style.RESET_ALL}{Fore.GREEN}DONE!{Style.RESET_ALL}")
                    except Exception as e:
                        if Settings["Debug"] > 3:
                            print(f"{Fore.MAGENTA}{work[fu]}{Style.RESET_ALL}{Fore.GREEN}FAIL: {e}{Style.RESET_ALL}")
        else:
            for year in Years:
                ParsePage(year)


        if Settings["Debug"] > 0:
            print(f"{Fore.GREEN}DONE!{Style.RESET_ALL}")

        return Links

    if Settings["Debug"] > 0:
        print(f"{Fore.LIGHTBLUE_EX}Checking endpoint availability...{Style.RESET_ALL}")

    _test = Extract_Endpoints(1998, True)
    if not _test:
        raise SystemError("Request failed. Verify packages for version mismatch or file corruption.")
    if not (200 <= _test.status_code < 300):
        raise SystemError(f"{Fore.RED}Request failed. Verify computer clock synchronization, network connectivity or firewall settings. (Error code: {_test.status_code}).{Style.RESET_ALL}")
    elif Settings["Debug"] > 0:
        print(f"{Fore.GREEN}PASS{Style.RESET_ALL}")

    del _test

def Download(Endpoints: dict, Directory:str|None):
    assert Endpoints and Directory

    if Settings["Debug"] > 0:
        print(f"{Fore.BLUE}Starting downloads.{Style.RESET_ALL}")
        if Settings["Debug"] > 1:
            print(f"{Fore.LIGHTBLUE_EX}Saving files to: {Directory}{Style.RESET_ALL}")

    ParsedEndpoints = {}
    FilesCount = 0

    for Year, Module in Endpoints.items():
        if not isinstance(Module, dict):
            ParsedEndpoints = Endpoints # Retry mode bypass
            FilesCount = len(Endpoints.keys())
            break
        for Tab, Exams in Module.items():
            for Name, Exam in Exams.items():
                if Exam:
                    _temp = [Exam["Exam"] if Exam["Exam"] else False, Exam["Answers"] if Exam["Answers"] else False]
                    ParsedEndpoints[path.join(Directory, Year, Tab, Name)] = _temp
                    
                    FilesCount += sum(bool(x) for x in _temp)

    def D(Dir:str, Batch:list, Bar=None, dbidx:int|str|None=None):
        # add debugging for no tqdm later, make retry use partial files range
        dbidx = f"[{dbidx}]" if Settings["ThreadedDw"] else ""

        IterSize = pow(2, 14)

        for i in range(0, 2):
            try:
                if Batch[i]:
                    File = Session.get(Batch[i], stream=True, timeout=3)
                    
                    Targ_Path = Path(Dir)
                    Targ_Path.mkdir(parents=True, exist_ok=True)

                    with tqdm(
                        total=int(File.headers.get("Content-Length", 0)),
                        unit_scale=True,
                        unit="B",
                        leave=False,
                        desc=f"{dbidx}{f"{Fore.LIGHTCYAN_EX}[EXAM]" if i == 0 else f"{Fore.LIGHTBLUE_EX}[ANSWERS]"}{Style.RESET_ALL}{Dir if Settings["Debug"] > 1 else ""}"
                    ) if tqdm else nullcontext() as TempBar:
                        Targ_Path = Path(path.join(Targ_Path, "exam.pdf" if i == 0 else "answers.pdf"))

                        if Targ_Path.is_file() and not Settings["Replace"]:
                            if Settings["Debug"] > 0:
                                TempBar.set_description(f"{dbidx}{Fore.LIGHTYELLOW_EX}Skipping due to replacement restriction settings.{Style.RESET_ALL}")
                            TempBar.leave = True
                            TempBar.total = TempBar.n
                        else:
                            ByteProgress = 0
                            _temp = IterSize
                            
                            for Attempt in range(6):
                                try:
                                    if Attempt > 0:
                                        File.close()
                                        File = Session.get(Batch[i], stream=True, timeout=1, headers={"Range": f"bytes={ByteProgress}-"})
                                    
                                    File.raw.decode_content = True
                                    
                                    with open(Targ_Path, "ab" if ByteProgress > 0 else "wb") as f:
                                        while True:
                                            chunk = File.raw.read(_temp)
                                            if not chunk:
                                                break
                                            f.write(chunk)
                                            ByteProgress += len(chunk)
                                            if tqdm:
                                                TempBar.update(len(chunk))
                                    break
                                except Exception as e:
                                    if _temp > 32:
                                        _temp = 32
                                    if Attempt == 5:
                                        raise e
                                
                                del __temp
                            CurrDownlads += 1
                            if Bar:
                                TempBar.refresh()
                                TempBar.close()

                                Bar.update(1)
                        
                        File.close()
            except Exception as e:
                ErrorLogs[Dir] = Batch

                if Bar:
                    Bar.update(1)
    with tqdm(
        total=FilesCount,
        unit="files",
        desc=f"Downloading Files"
    ) if tqdm else nullcontext() as Bar:
        if Settings["ThreadedDw"]:
            with ThreadPoolExecutor(max_workers=min(int(cpu_count()/1.4), 32) or 2) as exe:
                work = {
                    exe.submit(D, Dir, Batch, Bar if tqdm else None, idx): idx 
                    for idx, (Dir, Batch) in enumerate(ParsedEndpoints.items())
                }

                for fu in as_completed(work):
                    try:
                        fu.result()
                        if Settings["Debug"] > 3:
                            print(f"{Fore.MAGENTA}{work[fu]}{Style.RESET_ALL}{Fore.GREEN}DONE!{Style.RESET_ALL}")
                    except Exception as e:
                        if Settings["Debug"] > 3:
                            print(f"{Fore.MAGENTA}{work[fu]}{Style.RESET_ALL}{Fore.GREEN}FAIL: {e}{Style.RESET_ALL}")
        else:
            for idx, (Dir, Batch) in enumerate(ParsedEndpoints.items()):
                D(Dir, Batch, Bar if tqdm else None, idx)
           

if __name__ == "__main__":
    Download(Endpoints=Settings["Retry"] if Settings["Retry"] else Extract_Endpoints(), Directory=AskDir())

    with open(ErrLogsFile, "w", encoding="utf-8") as f:
        dump(ErrorLogs, f, indent=1)
