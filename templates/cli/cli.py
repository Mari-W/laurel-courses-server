#!/usr/bin/env python3
"""
Author: Marius Weidner <weidner@cs.uni-freiburg.de>
"""
import json
import os.path
import re
import subprocess
import sys
from argparse import ArgumentParser
from dataclasses import dataclass, field
from getpass import getpass
from shutil import rmtree

# ensure requests is installed (why is this still not STL?)
try:
    import requests
except ImportError:
    print("This cli depends on the commonly used 'requests' library.")
    print("Unfortunately 'requests' is not installed in this environment.")
    if str(input("> install 'requests'? [Y/n]: ")) != "n":
        try:
            __process = subprocess.run("python3 -m pip install requests", stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       shell=True)

            if __process.returncode != 0:
                raise Exception(__process.stderr)

            print("Installed 'requests'.")
            os.execv(sys.argv[0], sys.argv)
        except Exception as install_exception:
            print(f"Failed to install 'requests': {install_exception}")
            print("Please manually install 'requests'")
    else:
        print("Well then.. have fun cloning all repos alone!!")
        exit(1)

# ---------------------------------------------------------------------------------------------------------------------

# RENDERED

# before downloading this script these values are getting inserted server side

# ---------------------------------------------------------------------------------------------------------------------

VERSION = "{{version}}"
COURSE = "{{course}}"

AUTH_URL = "{{auth_url}}"
AUTH_COOKIE = "{{auth_cookie}}"

CLI_API_URL = "{{cli_url}}"
GIT_SSH = "{{git_ssh}}"


# ---------------------------------------------------------------------------------------------------------------------

# STORE

# file based dictionary for saving your authentication token

# ---------------------------------------------------------------------------------------------------------------------


@dataclass
class Store:
    __body: dict = field(default_factory=lambda: {})
    __file: str = ".cli.store.json"

    def __post_init__(self):
        if os.path.isfile(self.__file):
            with open(self.__file, "r", encoding="utf-8") as f:
                self.__body = json.load(f)
        else:
            with open(self.__file, "w", encoding="utf-8") as f:
                f.write("{}")
                self.__body = {}

    def __getitem__(self, item):
        # actually this is kinda ambiguous, as this returns None if key not found and
        # does not throw a ValueError, like a normal dict
        # tho, controversial option, this should be the default behaviour :angry:
        return self.__body.get(item)

    def __setitem__(self, key, value):
        self.__body[key] = value
        with open(self.__file, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.__body))


# ---------------------------------------------------------------------------------------------------------------------

# API

# logs into the system, can be used to interact with all services needed

# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Session:
    __session: requests.Session = field(default_factory=lambda: requests.Session())
    __username: str = None

    def __post_init__(self):
        if AUTH_COOKIE not in self.__session.cookies:
            self.__session.cookies.set(AUTH_COOKIE, store["AUTH_COOKIE"])

        r = self.__session.get(f"{AUTH_URL}/auth/me")

        if r.status_code != 200:
            print("Authentication required.")
            print("Please log in using your university id.")

            if AUTH_COOKIE in self.__session.cookies:
                self.__session.cookies.pop(AUTH_COOKIE)

            username = str(input("> Username: ")).strip()
            password = str(getpass("> Password: ")).strip()

            r = self.__session.post(f"{AUTH_URL}/auth/login?silent=true",
                                    json={"username": username, "password": password})

            if r.status_code != 200:
                if r.status_code == 401:
                    print("Invalid credentials.")
                    return self.__post_init__()
                else:
                    print("Login failed.")
                    print(f"API responded: {r.status_code}: {r.text}")
                    print("Please contact server administrator")
                    exit(1)
            else:
                store["AUTH_COOKIE"] = self.__session.cookies.get(AUTH_COOKIE)
                print("Login successful.")
                return self.__post_init__()
        else:
            self.__username = json.loads(r.text)["username"]

    @property
    def username(self):
        return self.__username

    def get(self, url):
        try:
            return self.__session.get(url)
        except requests.RequestException as e:
            print(f"{url} seems to be offline.")
            print(f"Server responded with: {e}")
            print("Please contact server administrator")
            exit(1)


# ---------------------------------------------------------------------------------------------------------------------

# UPDATER

# requests updated from courses server, applies them if there is one

# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Updater:
    @staticmethod
    def __post_init__():
        r = session.get(f"{CLI_API_URL}/version")
        if r.status_code != 200:
            print("Failed to get current CLI version.")
            print("Please contact server administrator.")
            return
        if r.text != VERSION:
            print("Detected CLI update.")
            if str(input("> Update CLI? [Y/n]: ")) != "n":
                r = session.get(f"{CLI_API_URL}/{COURSE}/cli.py")
                if r.status_code != 200:
                    print("Failed to get CLI update.")
                    print(f"API responded: {r.status_code}: {r.text}")
                    print("Please contact server administrator.")
                    return
                # inplace update, python magic
                with open(__file__, "w", encoding="utf-8") as file:
                    file.write(r.text)
                print("Update successful.")
                # restart with same arguments, as applied on this script call
                os.execv(sys.argv[0], sys.argv)


# ---------------------------------------------------------------------------------------------------------------------

# GIT

# bundles a few git commands

# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Git:

    @staticmethod
    def __exec(command):
        # combines stderr and stdout
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                 encoding="utf-8")
        if process.returncode != 0:
            print(f"Failed to execute {command}: {process.stdout}")
            print(f"Please make sure you have access to all repositories by adding SSH key to Gitea.")
            print(f"Also run this command again to make sure all repositories have this command applied.")
            print(f"Before rerunning the command you can commit all changes by running ./cli.py -c 'Commit changes'")
            exit(1)
        return process.stdout

    def pull(self):
        for student in course.students:
            if not os.path.isdir(f"{COURSE}/{student}"):
                self.__exec(f"git clone {GIT_SSH}/{COURSE}/{student}.git {COURSE}/{student}")
            else:
                self.__exec(f"git -C {COURSE}/{student} pull --rebase --autostash")

    def commit(self, commit_message):
        for student in course.students:
            work_dir = f"-C {COURSE}/{student}"
            # only add readmes
            self.__exec(f"cd {COURSE}/{student} && git add */README.md")
            # commit changes (if there are any)
            self.__exec(f'git {work_dir} diff-index --quiet HEAD || git {work_dir} commit -m "{commit_message}"')

    def push(self):
        # make sure to call commit before this or changes are lost
        for student in course.students:
            work_dir = f"-C {COURSE}/{student}"
            # reset to student changes (if he pushed while you corrected exercises)
            self.__exec(f"git {work_dir} reset --hard")
            # pull updates & re-apply changes
            self.__exec(f"git {work_dir} pull --rebase")
            # push changes
            self.__exec(f"git {work_dir} push")

    @property
    def modified(self):
        # returns all modified files in all repos as path
        modified = []
        for student in course.students:
            stdout = self.__exec(f"git -C {COURSE}/{student} --no-pager diff --name-only master remotes/origin/HEAD")
            modified.extend([f"{COURSE}/{student}/{path.strip()}" for path in stdout.split("\n") if path])
        return modified


# ---------------------------------------------------------------------------------------------------------------------

# COURSE

# uses courses server api to get all information needed to have a painless experience

# ---------------------------------------------------------------------------------------------------------------------


@dataclass
class Course:
    __students: list = None
    __finished_exercises: list = None
    __logs: dict = field(default_factory=lambda: {})

    def __repr__(self):
        return f"Logged in as: {session.username}\n" \
               f"Course: {COURSE}\n" \
               f"Students: {', '.join(self.students)}\n" \
               f"Finished exercises: {', '.join(self.finished_exercises)}"

    @property
    def students(self):
        if self.__students is None:
            r = session.get(f"{CLI_API_URL}/{COURSE}/students")
            if r.status_code != 200:
                print(f"Could not obtain your assigned students.")
                print(f"API responded: {r.status_code}: {r.text}")
                print("Please contact server administrator.")
                exit(1)
            self.__students = json.loads(r.text)
        return self.__students

    @property
    def finished_exercises(self):
        if self.__finished_exercises is None:
            r = session.get(f"{CLI_API_URL}/{COURSE}/finished_exercises")
            if r.status_code != 200:
                print(f"Could not obtain the currently finished exercises.")
                print(f"API responded: {r.status_code}: {r.text}")
                print("Please contact server administrator.")
                exit(1)
            self.__finished_exercises = json.loads(r.text)
        return self.__finished_exercises

    def pull(self):
        # remove all repos of people you are not tutoring anymore (if there are any)
        self.clean()
        # pull rebase all changes
        git.pull()
        # insert 0P for people with no files in the exercise directory
        self.grade_no_submission()
        # append build logs to all readmes
        self.append_builds()

        print("Done.")

    def push(self, commit_message: str):
        # commit changes
        git.commit(commit_message)
        # validate no student was forgot to grade
        self.validate_readmes()
        # push changes (with reset and pull rebase)
        git.push()

        print("Done.")

    @staticmethod
    def commit(commit_message: str):
        git.commit(commit_message)

    def clean(self):
        obsolete_repositories = []
        if not os.path.isdir(COURSE):
            return
        for repository in next(os.walk(COURSE))[1]:
            if repository not in self.students and repository != COURSE:
                obsolete_repositories += [repository]
        if obsolete_repositories:
            print("Found repositories of students you are not assigned to (anymore).")
            print(f"Students: {','.join(obsolete_repositories)}")
            if str(input(f"> Delete all? [Y/n]")) != "n":
                for repository in obsolete_repositories:
                    rmtree(f"{COURSE}/{repository}")

    def get_build(self, student: str, exercise: str):
        if self.__logs.get((student, exercise)) is None:
            r = session.get(f"{CLI_API_URL}/{COURSE}/logs/{student}/{exercise}")
            if r.status_code == 404:
                self.__logs[(student, exercise)] = None
            elif r.status_code != 200:
                print(f"Could not obtain build latest log for {exercise} of {student}.")
                print(f"API responded: {r.status_code}: {r.text}")
                print("Please contact server administrator.")
                exit(1)
            else:
                build = json.loads(r.text)
                self.__logs[(student, exercise)] = {
                    "failure": build["failure"],
                    "logs": json.loads(build["logs"])
                }
        return self.__logs[(student, exercise)]

    def append_builds(self):
        for student in self.students:
            for exercise in self.finished_exercises:
                readme_path = f"{COURSE}/{student}/{exercise}/README.md"
                if os.path.isfile(readme_path):
                    with open(readme_path, "r", encoding="utf-8") as readme:
                        if any(["## Build" in line for line in readme.readlines()]):
                            continue
                    with open(readme_path, "a", encoding="utf-8") as readme:
                        build = self.get_build(student, exercise)
                        if not build:
                            readme.write("\n")
                            readme.write(f"## Build ⚫ (not found)")
                            continue
                        readme.write("\n")
                        readme.write(f"## Build {'🔴 (failure)' if build['failure'] else '🟢 (success)'}")
                        for step in build["logs"]:
                            readme.write("\n")
                            readme.write(f"### {step['name']} {'🔴 (failure)' if step['failure'] else '🟢 (success)'}")
                            readme.write("\n")
                            readme.write("```bash")
                            readme.write("\n")
                            readme.write("\n".join([log for log in step["logs"] if log]))
                            readme.write("\n")
                            readme.write("```")

    def grade_no_submission(self):
        for student in self.students:
            for exercise in self.finished_exercises:
                exercise_path = f"{COURSE}/{student}/{exercise}"
                if os.path.isdir(exercise_path):
                    files = next(os.walk(f"{COURSE}/{student}/{exercise}"))[2]
                    if files == ["README.md"] or files == ["README.md", "NOTES.md"] or files == ["NOTES.md", "README.md"]:
                        with open(f"{exercise_path}/README.md", "r", encoding="utf-8") as readme:
                            first_line = readme.readline()
                            matches = re.findall(r"\?\? */ *(\d+[,.]?\d*)", first_line)
                            if matches:
                                with open(f"{exercise_path}/README.md", "w", encoding="utf-8") as readme:
                                    first_line = first_line.replace("??", "0")
                                    readme.write(f"{first_line}\n")
                                    readme.write("No submission.\n")
                                    readme.write("This exercise was graded as 'no submission' automatically.\n")
                                    readme.write("If you believe this is an error, contact your tutor.\n")

    def validate_readmes(self):
        for path in git.modified:
            elements = path.split("/")
            if len(elements) != 4 or elements[-1].lower() != "readme.md" \
                    or elements[2] not in self.finished_exercises:
                continue

            with open(path, "r", encoding="utf-8") as readme:
                matches = re.findall(r"(\d+[,.]?\d*) */ *(\d+[,.]?\d*)", readme.readline())
                if len(matches) == 0:
                    print(f"Found no valid point schema in {path}")
                    print(f"Make sure the first line contains this: (XX/XX) where XX are floats exactly once.")
                if len(matches) > 1:
                    print(f"Found multiple valid point schema in {path}")
                    print(f"Make sure the first line contains this: (XX/XX) where XX are floats exactly once.")


# ---------------------------------------------------------------------------------------------------------------------

# ARGS

# parses and executes command line arguments

# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Args:
    __args = None

    def __post_init__(self):
        parser = ArgumentParser(description=f"CLI for {COURSE}.",
                                epilog="To invalidate your session, delete the '.cli.store.json' in this directory.")
        # d for down, u for up (why do they need to start with p, both)
        parser.add_argument("-d", "--pull", help="pull / clone all your student's repositories", action="store_true")
        parser.add_argument("-u", "--push",
                            help="push all your student's repositories, you need to specify the commit message "
                                 "(used when there are uncommitted changes)",
                            type=str)
        parser.add_argument("--commit",
                            help="commit all your student's repositories, you need to specify the commit message "
                                 "(use this when something fails while pulling, so that you can run pull again"
                                 "normally push will take care of committing)",
                            type=str)
        parser.add_argument("-i", "--info", action="store_true")

        self.__args = parser.parse_args()

    def apply(self):
        if self.__args.info:
            print(repr(course))
        elif self.__args.pull:
            course.pull()
        elif self.__args.commit:
            course.commit(self.__args.commit)
        elif self.__args.push:
            course.push(self.__args.push)
        else:
            print("No valid argument passed.")
            print("Use --help for help.")

        exit(0)


if __name__ == '__main__':
    # order matters here as global objects get created, most of the time used by objects below them

    # parse arguments
    args = Args()

    # create cli store where authentication token is stored
    store = Store()

    # session which will ensure you are authorized after it's creation
    session = Session()  # uses: store

    # run updater
    Updater()  # uses: session

    # git command line wrapper
    git = Git()

    # actual logic and communicating with courses server
    course = Course()  # uses: session, git

    # apply arguments
    args.apply()  # uses course
