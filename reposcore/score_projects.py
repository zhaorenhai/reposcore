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


def main():
    parser = argparse.ArgumentParser(
        description=
        'Generate a sorted criticality score list for input projects .')
    parser.add_argument("--projects_list",
                        type=open,
                        required=True,
                        help="File name of projects url list.")
    parser.add_argument("--result_file",
                        type=str,
                        required=True,
                        help="Result file name.")

    args = parser.parse_args()

    repo_urls = set()
    repo_urls.update(args.projects_list.read().splitlines())

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

    with open(args.result_file, 'w') as file_handle:
        csv_writer = csv.writer(file_handle)
        csv_writer.writerow(header)
        for i in sorted(stats,
                        key=lambda i: i['criticality_score'],
                        reverse=True):
            csv_writer.writerow(i.values())
    print(f'Wrote results: {args.result_file}')


if __name__ == "__main__":
    main()
