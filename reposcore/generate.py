# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Main python script for calculating OSS Criticality Score."""

import argparse
import csv
import os
import sys
import time

from . import run

LANGUAGE_SEARCH_MAP = {
    'c': ['C'],
    'c#': ['C#'],
    'c++': ['C++'],
    'go': ['Go'],
    'java': ['Java', 'Groovy', 'Kotlin', 'Scala'],
    'js': ['Javascript', 'Typescript', 'CoffeeScript'],
    'php': ['PHP'],
    'python': ['Python'],
    'ruby': ['Ruby'],
    'rust': ['Rust'],
    'shell': ['Shell'],
}
IGNORED_KEYWORDS = ['course', 'docs', 'interview', 'tutorial']

def get_github_repo_urls(sample_size, languages):
    urls = []
    if (languages):
        for lang in languages:
            lang = lang.lower()
            for github_lang in LANGUAGE_SEARCH_MAP.get(lang, lang):
                urls = get_github_repo_urls_for_language(urls, sample_size, github_lang)
    else:
        urls = get_github_repo_urls_for_language(urls, sample_size)

    return urls

def get_github_repo_urls_for_language(urls, sample_size, github_lang=None):
    """Return repository urls given a language list and sample size."""
    samples_processed = 1
    last_stars_processed = None
    while samples_processed <= sample_size:

        query = 'archived:false'
        if github_lang:
            query += f' language:{github_lang}'

        if last_stars_processed:
            # +100 to avoid any races with star updates.
            query += f' stars:<{last_stars_processed+100}'
        print(f'Running query: {query}')
        token_obj = run.get_github_auth_token()
        new_result = False
        repo = None
        for repo in token_obj.search_repositories(query=query,
                                                    sort='stars',
                                                    order='desc'):
            # Forced sleep to avoid hitting rate limit.
            time.sleep(0.1)
            repo_url = repo.html_url
            if repo_url in urls:
                # Github search can return duplicates, so skip if analyzed.
                continue
            if any(k in repo_url.lower() for k in IGNORED_KEYWORDS):
                # Ignore uninteresting repositories.
                continue
            urls.append(repo_url)
            new_result = True
            print(f'Found repository'
                    f'({samples_processed}): {repo_url}')
            samples_processed += 1
            if samples_processed > sample_size:
                break
        if not new_result:
            break
        last_stars_processed = repo.stargazers_count

    return urls


def main():
    parser = argparse.ArgumentParser(
        description=
        'Generate a sorted criticality score list for particular language(s).')
    parser.add_argument("--language",
                        nargs='+',
                        default=[],
                        required=False,
                        choices=LANGUAGE_SEARCH_MAP.keys(),
                        help="List of languages to use.")
    parser.add_argument("--output-dir",
                        type=str,
                        required=True,
                        help="Directory to place the output in.")
    parser.add_argument("--count",
                        type=int,
                        default=200,
                        help="Number of projects in result.")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5000,
        help="Number of projects to analyze (in descending order of stars).")

    args = parser.parse_args()

    # GitHub search can return incomplete results in a query, so try it multiple
    # times to avoid missing urls.
    repo_urls = set()
    for rnd in range(1, 4):
        print(f'Finding repos (round {rnd}):')
        repo_urls.update(get_github_repo_urls(args.sample_size, args.language))

    csv_writer = csv.writer(sys.stdout)
    header = None
    stats = []
    for repo_url in repo_urls:
        output = None
        for _ in range(3):
            try:
                repo = run.get_repository(repo_url)
                output = run.get_repository_stats(repo)
                break
            except Exception as exp:
                print(
                    f'Exception occurred when reading repo: {repo_url}\n{exp}')
        if not output:
            continue
        if not header:
            header = output.keys()
            csv_writer.writerow(header)
        csv_writer.writerow(output.values())
        stats.append(output)

    languages = '_'.join(args.language) if args.language else 'all'
    languages = languages.replace('+', 'plus').replace('c#', 'csharp')
    output_filename = os.path.join(args.output_dir,
                                   f'{languages}_top_{args.count}.csv')
    with open(output_filename, 'w') as file_handle:
        csv_writer = csv.writer(file_handle)
        csv_writer.writerow(header)
        for i in sorted(stats,
                        key=lambda i: i['criticality_score'],
                        reverse=True)[:args.count]:
            csv_writer.writerow(i.values())
    print(f'Wrote results: {output_filename}')


if __name__ == "__main__":
    main()
