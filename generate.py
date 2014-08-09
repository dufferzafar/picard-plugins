#!/usr/bin/env python

import os
import re
import sys
import json

import zipfile
import zlib

from hashlib import md5
from subprocess import call

re_name = re.compile(r'PLUGIN_NAME = (?:_\(u|u|)((?:\"\"\"|\'\'\'|\"|\'))(.*)\1')
re_author = re.compile(r'PLUGIN_AUTHOR = (?:_\(u|u|)((?:\"\"\"|\'\'\'|\"|\'))(.*)\1')
re_ver = re.compile(r'PLUGIN_VERSION = (?:_\(u|u|)((?:\"\"\"|\'\'\'|\"|\'))(.*?)\1')
re_api = re.compile(r'PLUGIN_API_VERSIONS = \[((?:\"\"\"|\'\'\'|\"|\'))(.*?)\1\]')

# Descriptions are spread out in multiple lines so these will be handled separately
re_desc_start = re.compile(r'PLUGIN_DESCRIPTION = (?:_\(u|u|)(.*)')
re_desc_end = re.compile(r'PLUGIN_(.*)')
re_desc = re.compile(r'PLUGIN_DESCRIPTION = (?:_\(u|u|)((?:\"\"\"|\'\'\'|\"|\'))(.*?)\1', re.DOTALL)


def get_data(filepath):
    """
    Extract usable information from plugin files.
    """
    data = {}
    desc_lines = []
    desc_flag = False

    with open(filepath) as f:
        for line in f:
            if 'name' not in data:
                name = re.match(re_name, line)
                if name:
                    data['name'] = name.group(2)

            if 'author' not in data:
                author = re.match(re_author, line)
                if author:
                    data['author'] = author.group(2)

            if 'description' not in data:
                if re.match(re_desc_start, line):
                    desc_flag = True
                elif re.match(re_desc_end, line):
                    desc_flag = False
                    desc = re.match(re_desc, re.sub(r'[\\\n]', '', "".join(desc_lines)))
                    if desc:
                        data['description'] = desc.group(2)

                if desc_flag:
                    desc_lines.append(line)

            if 'version' not in data:
                ver = re.match(re_ver, line)
                if ver:
                    data['version'] = ver.group(2)

            if 'api_version' not in data:
                apiver = re.match(re_api, line)
                if apiver:
                    data['api_version'] = apiver.group(2)

    return data


def build_json():
    """
    Traverse the plugins directory to generate json data.
    """

    # Read the existing data
    if os.path.isfile(plugin_file):
        plugins = json.load(open(plugin_file, "r"))["plugins"]
    else:
        plugins = {}

    # All top level directories in plugin_dir are plugins
    for dirname in os.walk(plugin_dir).next()[1]:

        files = {}
        data = {}

        if dirname in [".git"]:
            continue

        dirpath = os.path.join(plugin_dir, dirname)
        for root, dirs, filenames in os.walk(dirpath):
            for filename in filenames:
                ext = os.path.splitext(filename)[1]

                if ext not in [".pyc"]:
                    file_path = os.path.join(root, filename)
                    md5Hash = md5(open(file_path, "rb").read()).hexdigest()
                    files[file_path.split(os.path.join(dirpath, ''))[1]] = md5Hash

                if not data:
                    data = get_data(os.path.join(plugin_dir, dirname, filename))

        if dirname in plugins:
            print("Updated: " + dirname)
            if data:
                for key, value in data.items():
                    plugins[dirname][key] = value
            plugins[dirname]["files"] = files
        else:
            print("Added: " + dirname)
            data['files'] = files
            data['downloads'] = 0
            plugins[dirname] = data

    json.dump({"plugins": plugins}, open(plugin_file, "w"),
              sort_keys=True, indent=2)


def zip_files():
    """
    Zip up plugin folders
    """

    for dirname in os.walk(plugin_dir).next()[1]:
        archive_path = os.path.join(plugin_dir, dirname)
        archive = zipfile.ZipFile(archive_path + ".zip", "w")

        dirpath = os.path.join(plugin_dir, dirname)
        for root, dirs, filenames in os.walk(dirpath):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                archive.write(file_path,
                              file_path.split(os.path.join(dirpath, ''))[1],
                              compress_type=zipfile.ZIP_DEFLATED)

        print("Created: " + dirname + ".zip")


# The file that contains json data
plugin_file = "plugins.json"

# The directory which contains plugin files
plugin_dir = "plugins"

if __name__ == '__main__':
    if 1 in sys.argv:
        if sys.argv[1] == "pull":
            call(["git", "pull", "-q"])
        elif sys.argv[1] == "json":
            build_json()
        elif sys.argv[1] == "zip":
            zip_files()
    else:
        # call(["git", "pull", "-q"])
        build_json()
        zip_files()
