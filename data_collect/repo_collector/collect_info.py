import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import subprocess
import requests
import time
from datetime import datetime, timedelta
from utils.llm import chat
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()


def fetch_repos_by_day(**kwargs):
    github_key = os.getenv('GITHUB_KEY')
    url = 'https://api.github.com/search/repositories'
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {github_key}',
    }

    current_date = kwargs.get("start_date")
    all_repos = []
    while current_date <= kwargs.get("end_date"):
        day_after = current_date + timedelta(days=kwargs.get("time_range"))
        page = 1

        while True:
            params = {
                'q': f'language:{kwargs.get("language")} created:{current_date.strftime("%Y-%m-%d")}..{day_after.strftime("%Y-%m-%d")} {kwargs.get("kw")} in:description,readme stars:>{kwargs.get("star")} NOT native in:name,description,readme NOT learn in:name,description,readme NOT tutorial in:name,description,readme NOT example in:name,description,readme NOT demo in:name,description,readme',
                'sort': 'stars',
                'order': 'desc',
                'per_page': kwargs.get("per_page"),
                'page': page,
            }

            print(
                f"Fetching repositories created on {current_date.strftime('%Y-%m-%d')}, page {page} ...")
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                repos = response.json()['items']
                if not repos:
                    break
                print(f"Found {len(repos)} repositories")
                # with open(kwargs.get("output_file_name"), 'a', encoding='utf-8') as file:
                #     for repo in repos:
                #         file.write(json.dumps(repo) + '\n')
                all_repos.extend(repos)
                if len(repos) < kwargs.get("per_page"):
                    break
                page += 1
            else:
                print(f"Error: {response.status_code}")
                print(response.json())
                break
            # Sleep to avoid hitting the rate limit
            time.sleep(kwargs.get("sleep_time"))
        current_date += timedelta(days=kwargs.get("time_range"))
        # Sleep to avoid hitting the rate limit
        time.sleep(kwargs.get("sleep_time"))

    return all_repos


def download_repo(repo, output_repo_path):
    print('downloading: ', repo['full_name'])
    output_file_path = os.path.join(
        output_repo_path, repo['full_name'].replace('/', '_'))
    # print(f"git clone {repo['clone_url']} {output_file_path}")

    try:
        subprocess.run(["git", "clone", repo['clone_url'],
                       output_file_path], check=True)
        print(f"Repository cloned into: {output_file_path}")
        return 1
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        return 0


def download_package_json(repo):
    github_key = os.getenv('GITHUB_KEY')
    url = f"https://api.github.com/repos/{repo}/contents/package.json"
    headers = {"Authorization": f"token {github_key}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        content = response.json()
        package_json_content = base64.b64decode(
            content['content']).decode('utf-8')
        return json.loads(package_json_content)
    else:
        print(
            f"Failed to download package.json for {repo}: {response.status_code}")
        return None


def judge_dependencies(package_json):
    if 'dependencies' in package_json:
        if 'dependencies' in package_json and 'react' in package_json['dependencies']:
            return True
        elif 'devDependencies' in package_json and 'react' in package_json['devDependencies']:
            return True
        else:
            return False
    return False


def judge_scripts(package_json):
    if 'scripts' in package_json:
        # judge whether there is a start script
        for key in package_json['scripts']:
            if key == 'start' and 'node' not in package_json['scripts']['start']:
                return True
    return False


def judge_react(repo):
    package_json = download_package_json(repo)
    if package_json:
        return judge_dependencies(package_json) and judge_scripts(package_json)
    else:
        print(f"Failed to download package.json for {repo}")
        return False


def rule_based_filter(repo, target):
    if repo['name'].lower() == target:
        return False

    if not judge_react(repo['full_name']):
        return False

    return True


def distill_repo_info(repo_json):
    # copy the repo_json and remove the fields includes name, node_id, owner, and all those end with _url
    repo = repo_json.copy()
    for key in list(repo.keys()):
        if key.endswith('_url') or key in ['id', 'node_id', 'owner', 'url', 'created_at', 'updated_at', 'pushed_at', 'homepage', 'stargazers_count', 'watchers_count', 'has_issues', 'forks_count', 'open_issues_count', 'allow_forking', 'forks', 'open_issues', 'watchers', 'default_branch']:
            repo.pop(key)
    return repo


def filter_repo_llm(repo_json):
    prompt = '''
Evaluate the given JSON object detailing a GitHub repository to determine if it is a web application (such as a website or web app, not some browser extension,toolkit, or similar) and if it can be segmented for individual rendering. This evaluation is for creating training data for a multimodal language model that translates images into frontend code, specifically using frameworks like React or Vue. Analyze the repository based on the name, description, and other fields provided. Your response should be a single word: "yes" if the repository meets the criteria for being both a web application and suitable for segmented rendering, or "no" if it does not. Respond with only this word.

Target Repository Information:
'''
    repo_json = distill_repo_info(repo_json)
    # print(f"repo_json: {repo_json}")

    prompt += json.dumps(repo_json, indent=4)
    result = chat(prompt)
    print(f'result: {result}')

    result_blocks = result.lower().split(' ')
    if 'yes' in result_blocks:
        return 'yes'
    elif 'no' in result_blocks:
        return 'no'
    else:
        print(f"Error: {result}")
        return None


def filtering(repo, target):
    print(f"Processing {repo['full_name']}")

    if not rule_based_filter(repo, target):
        return None

    llm_suggest = filter_repo_llm(repo)

    if llm_suggest == 'yes':
        tmp_repo = {
            'name': repo['name'],
            'full_name': repo['full_name'],
            'description': repo['description'],
            'language': repo['language'],
            'clone_url': repo['clone_url'],
        }
        return tmp_repo
    else:
        return None


def filter_repo(repo_infos, target):
    print(f"Found {len(repo_infos)} repositories")
    filtered_repos = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for repo_info in repo_infos:
            futures.append(executor.submit(
                filtering, repo_info, target))
        for future in as_completed(futures):
            filtered_repo = future.result()
            if filtered_repo:
                filtered_repos.append(filtered_repo)

    return filtered_repos


def clone_repo(repo_infos, output_repo_path):
    print(f"Found {len(repo_infos)} repositories")

    downloaded_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for repo_info in repo_infos:
            futures.append(executor.submit(
                download_repo, repo_info, output_repo_path))
        for future in as_completed(futures):
            downloaded_count += future.result()
    return downloaded_count




def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', type=str, default='JavaScript')
    parser.add_argument('--start_date', type=str, default='2016-06-01')
    parser.add_argument('--end_date', type=str, default='2025-01-20')
    parser.add_argument('--per_page', type=int, default=100)
    parser.add_argument('--sleep_time', type=int, default=3)
    parser.add_argument('--star', type=int, default=5)
    parser.add_argument('--time_range', type=int, default=30)
    parser.add_argument('--kw', type=str, default='react')
    parser.add_argument('--output_repo_path', type=str, default='data/original_repo')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    language = args.language
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    per_page = args.per_page
    sleep_time = args.sleep_time
    star = args.star
    time_range = args.time_range
    kw = args.kw
    output_repo_path = args.output_repo_path
    if not os.path.exists(output_repo_path):
        os.makedirs(output_repo_path)

    repo_infos = fetch_repos_by_day(language=language, start_date=start_date, end_date=end_date,
                                    per_page=per_page, sleep_time=sleep_time, star=star, time_range=time_range, kw=kw)
    print(f'found {len(repo_infos)} repos with query schema')

    filtered_repos = filter_repo(repo_infos, 'react')
    print(f'found {len(filtered_repos)} repos after filtering')

    downloaded_count = clone_repo(filtered_repos, output_repo_path)
    print(f"Downloaded {downloaded_count} repositories")
