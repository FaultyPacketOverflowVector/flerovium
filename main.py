import sys
import os
import traceback
import time
import logging
import subprocess
import asyncio
import aiofiles
import colorlog
import httpx
import winreg
import ujson as json
import vdf
from typing import Any
from pathlib import Path
from colorama import init, Fore, Back, Style
init()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
lock = asyncio.Lock()
client = httpx.AsyncClient(trust_env=True)
DEFAULT_CONFIG = {'Github_Personal_Token': '', 'Custom_Steam_Path': '', 'QA1': 'Friendly Reminder: You can find your Github Personal Token in the developer options at the bottom of the Github settings. For details, see the tutorial.', 'Tutorial': 'Coming Soon!'}
LOG_FORMAT = '%(log_color)s%(message)s'
LOG_COLORS = {'INFO': 'purple', 'WARNING': 'yellow', 'ERROR': 'red', 'CRITICAL': 'red'}

def init_log(level=logging.DEBUG) -> logging.Logger:
    """Initialize logging module """  # inserted
    logger = logging.getLogger('Flerovium')
    logger.setLevel(level)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    fmt = colorlog.ColoredFormatter(LOG_FORMAT, log_colors=LOG_COLORS)
    stream_handler.setFormatter(fmt)
    if not logger.handlers:
        logger.addHandler(stream_handler)
    return logger
log = init_log()

def init():
    """Output initialization information """  # inserted
    banner_lines = ['______  _      _____ ______  _____  _   _  _____  _   _ ___  ___', '|  ___|| |    |  ___|| ___ \\|  _  || | | ||_   _|| | | ||  \\/  |', '| |_   | |    | |__  | |_/ /| | | || | | |  | |  | | | || .  . |', '|  _|  | |    |  __| |    / | | | || | | |  | |  | | | || |\\/| |', '| |    | |____| |___ | |\\ \\ \\ \\_/ /\\ \\_/ / _| |_ | |_| || |  | |', '\\_|    \\_____\\/____/ \\_| \\_| \\___/  \\___/  \\___/  \\___/ \\_|  |_/']
    for line in banner_lines:
        log.info(line)
    log.info('Author: Clubby')
    log.warning('This project is licensed under the GNU General Public License v3. Please do not use it for commercial purposes.')
    log.info('Version: 2.0')
    log.info('Project Github Repository: https://github.com/Clubby999/flerovium')
    log.info('Official website: Coming Soon!')
    log.warning('This project is free. If you have paid for this, you got scammed!')
    log.info('')
    log.info('App ID can be viewed on SteamDB, SteamUI, or Steam store link page.')

def stack_error(exception: Exception) -> str:
    """Handle error stack """  # inserted
    stack_trace = traceback.format_exception(type(exception), exception, exception.__traceback__)
    return ''.join(stack_trace)

async def gen_config_file():
    """Generate configuration file """  # inserted
    try:
        async with aiofiles.open('./config.json', mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False, escape_forward_slashes=False))
    except KeyboardInterrupt:
        log.info('The program has exited')

async def load_config():
    """Load configuration file """  # inserted
    if not os.path.exists('./config.json'):
        await gen_config_file()
        os.system('pause')
        sys.exit()
    try:
        async with aiofiles.open('./config.json', mode='r', encoding='utf-8') as f:
            config = json.loads(await f.read())
            return config
    except KeyboardInterrupt:
        log.info('The program has exited')
config = asyncio.run(load_config())

async def check_github_api_rate_limit(headers):
    """Check Github request count """  # inserted
    log.info('You have configured the Github Token') if headers is not None else None
    url = 'https://api.github.com/rate_limit'
    try:
        r = await client.get(url, headers=headers)
            r_json = r.json()
            if r.status_code == 200:
                rate_limit = r_json.get('rate', {})
                remaining_requests = rate_limit.get('remaining', 0)
                reset_time = rate_limit.get('reset', 0)
                reset_time_formatted = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reset_time))
                log.info(f'Remaining request count: {remaining_requests}')
                if remaining_requests == 0:
                    log.warning(f'The GitHub API request count has been exhausted. It will reset at {reset_time_formatted}. It is recommended to generate one and fill it in the configuration file.')
                return
    except KeyboardInterrupt:
        log.info('The program has exited')

async def checkcn() -> bool:
    try:
        req = await client.get('https://mips.kugou.com/check/iscn?&format=json')
            body = req.json()
            scn = bool(body['flag'])
            if not scn:
                log.info('Automatically switching back to the official Github download CDN.')
                os.environ['IS_CN'] = 'no'
            return False
    except KeyboardInterrupt:
        log.info('The program has exited')
    return None

async def depotkey_merge(config_path: Path, depots_config: dict) -> bool:
    if not config_path.exists():
        async with lock:
            log.error('Steam default configuration does not exist, possibly not logged in.')
    return False

async def get(sha: str, path: str, repo: str):
    if os.environ.get('IS_CN') == 'yes':
        url_list = [f'https://jsdelivr.pai233.top/gh/{repo}@{sha}/{path}', f'https://cdn.jsdmirror.com/gh/{repo}@{sha}/{path}', f'https://raw.gitmirror.com/{repo}/{sha}/{path}', f'https://raw.dgithub.xyz/{repo}/{sha}/{path}', f'https://gh.akass.cn/{repo}/{sha}/{path}']
    retry = 3
    if retry > 0:
        for url in url_list:
            try:
                r = await client.get(url, timeout=30)
                    if r.status_code == 200:
                        return r.read()
        else:  # inserted
            retry -= 1
            log.warning(f'Retry remaining: {retry} - {path}')
    log.error(f'Maximum retry limit exceeded: {path}')
    raise Exception(f'Unable to download: {path}')
        except KeyboardInterrupt:
            log.info('The program has exited')
            continue
        except httpx.ConnectError as e:
            log.error(f'Failed to retrieve: {path} - Connection error: {str(e)}')
            continue
        except httpx.ConnectTimeout as e:
            log.error(f'Connection timed out: {url} - Error: {str(e)}')
            continue

async def get_manifest(sha: str, path: str, steam_path: Path, repo: str) -> list:
    collected_depots = []
    depot_cache_path = steam_path / 'depotcache'
    try:
        depot_cache_path.mkdir(exist_ok=True)
        if path.endswith('.manifest'):
            save_path = depot_cache_path / path
            if save_path.exists():
                log.warning(f'Manifest already exists: {save_path}')
                return collected_depots
            break
    except KeyboardInterrupt:
        log.info('The program has exited')

def get_steam_path() -> Path:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\Valve\\Steam')
        steam_path = Path(winreg.QueryValueEx(key, 'SteamPath')[0])
        custom_steam_path = config.get('Custom_Steam_Path', '').strip()
        return Path(custom_steam_path) if custom_steam_path else None
    except KeyboardInterrupt:
        log.info('The program has exited')
steam_path = get_steam_path()
isGreenLuma = any(((steam_path / dll).exists() for dll in ['GreenLuma_2024_x86.dll', 'GreenLuma_2024_x64.dll', 'User32.dll']))
isSteamTools = (steam_path / 'config' / 'stUI').is_dir()
directory = Path(steam_path) / 'config' / 'stplug-in'
temp_path = Path('./temp')
setup_url = 'https://steamtools.net/res/SteamtoolsSetup.exe'
setup_file = temp_path / 'SteamtoolsSetup.exe'

async def download_setup_file() -> None:
    log.info('Starting download of SteamTools installation program...')
    try:
        r = await client.get(setup_url, timeout=30)
            if r.status_code == 200:
                async with aiofiles.open(setup_file, mode='wb') as f:
                    await f.write(r.read())
            else:  # inserted
                return None
    except KeyboardInterrupt:
        log.info('The program has exited')

async def migrate(st_use: bool) -> None:
    try:
        if st_use:
            log.info('Detected that you are using SteamTools, attempting to migrate old files.')
            if directory.exists():
                for file in directory.iterdir():
                    if file.is_file() and file.name.startswith('Flerovium_unlock_'):
                        pass  # postinserted
                    else:  # inserted
                        new_filename = file.name[len('Flerovium_unlock_'):]
                        try:
                            file.rename(directory / new_filename)
                            log.info(f'Renamed: {file.name} -> {new_filename}')
            return None
            subprocess.run(str(setup_file), check=True)
            for file in temp_path.iterdir():
                file.unlink()
            temp_path.rmdir()
        else:  # inserted
            return None
        except Exception as e:
            log.error(f'Rename failed {file.name} -> {new_filename}: {e}')
    except KeyboardInterrupt:
        log.info('The program has exited')

async def stool_add(depot_data: list, app_id: str) -> bool:
    lua_filename = f'{app_id}.lua'
    lua_filepath = steam_path / 'config' / 'stplug-in' / lua_filename
    async with lock:
        log.info(f'SteamTools unlock file generation: {lua_filepath}')
        try:
            async with aiofiles.open(lua_filepath, mode='w', encoding='utf-8') as lua_file:
                await lua_file.write(f'addappid({app_id}, 1, \"None\")\n')
                for depot_id, depot_key in depot_data:
                    await lua_file.write(f'addappid({depot_id}, 1, \"{depot_key}\")\n')
    except KeyboardInterrupt:
        log.info('The program has exited')

async def greenluma_add(depot_id_list: list) -> bool:
    app_list_path = steam_path / 'AppList'
    try:
        app_list_path.mkdir(parents=True, exist_ok=True)
        for file in app_list_path.glob('*.txt'):
            file.unlink(missing_ok=True)
        depot_dict = {int(i.stem): int(i.read_text(encoding='utf-8').strip()) for i in app_list_path.iterdir() if i.is_file() and i.stem.isdecimal() and (i.suffix == '.txt')}
            for depot_id in map(int, depot_id_list):
                if depot_id not in depot_dict.values():
                    pass  # postinserted
                else:  # inserted
                    index = max(depot_dict.keys(), default=(-1)) + 1
                    if index in depot_dict:
                        index += 1
                    (app_list_path / f'{index}.txt').write_text(str(depot_id), encoding='utf-8')
                    depot_dict[index] = depot_id
            else:  # inserted
                return True
    except Exception as e:
        print(f'Error during processing: {e}')
        return False

async def fetch_branch_info(url, headers) -> str | None:
    try:
        r = await client.get(url, headers=headers)
            return r.json()
    except KeyboardInterrupt:
        log.info('The program has exited')

async def get_latest_repo_info(repos: list, app_id: str, headers) -> Any | None:
    latest_date = None
    selected_repo = None
    for repo in repos:
        url = f'https://api.github.com/repos/{repo}/branches/{app_id}'
        r_json = await fetch_branch_info(url, headers)
        if r_json and 'commit' in r_json:
            pass  # postinserted
        else:  # inserted
            date = r_json['commit']['commit']['author']['date']
            if latest_date is None or date > latest_date:
                pass  # postinserted
            else:  # inserted
                latest_date = date
                selected_repo = repo
    return (selected_repo, latest_date)

async def main(app_id: str, repos: list) -> bool:
    app_id_list = list(filter(str.isdecimal, app_id.strip().split('-')))
    if not app_id_list:
        log.error('Invalid App ID.')
    return False
if __name__ == '__main__':
    init()
    try:
        repos = ['Clubby999/ManifestHub', 'Clubby999/ManifestAutoUpdate2', 'Clubby999/ManifestAutoUpdate']
        app_id = input(f'{Fore.RED}{Back.BLACK}{Style.BRIGHT}Please enter the game AppID: {Style.RESET_ALL}').strip()
        asyncio.run(main(app_id, repos))
    except KeyboardInterrupt:
        log.info('The program has exited')