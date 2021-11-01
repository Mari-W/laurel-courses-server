import base64
import time
from dataclasses import dataclass

from gitea_api import Configuration, ApiClient, AdminApi, RepositoryApi, OrganizationApi, CreateOrgOption, \
    CreateRepoOption, CreateTeamOption, UserApi, GenerateRepoOption, AddCollaboratorOption, \
    CreateUserOption, EditRepoOption, TransferRepoOption, UserSettingsOptions, EditUserOption, CreateFileOptions, \
    Identity, DeleteFileOptions
from gitea_api.rest import ApiException

from server.env import Env
from server.exercises.options import CreateCourseOption, AddTutorOption, CreateExerciseOption

gitea_exercises_configuration = Configuration()
gitea_exercises_configuration.host = Env.get("GITEA_LOCAL_URL") + "/api/v1"
gitea_exercises_configuration.username = Env.get("GITEA_USERNAME")
gitea_exercises_configuration.password = Env.get("GITEA_PASSWORD")
gitea_exercises_api_client = ApiClient(gitea_exercises_configuration)


@dataclass
class GiteaExercises:
    admin_api = AdminApi(gitea_exercises_api_client)
    repo_api = RepositoryApi(gitea_exercises_api_client)
    org_api = OrganizationApi(gitea_exercises_api_client)
    user_api = UserApi(gitea_exercises_api_client)

    # course
    def add_course(self, course: str, options: CreateCourseOption):
        # create organization
        self.admin_api.admin_create_org(username=options.owner, body=CreateOrgOption(
            description="",
            full_name=options.display_name,
            website=options.website,
            visibility="public" if options.joinable else "private",
            repo_admin_change_team_access=False,
            username=course,
        ))

        # create template repo that student repositories will be based on
        self.org_api.create_org_repo(org=course, body=CreateRepoOption(
            auto_init=True,
            private=True,
            default_branch="master",
            description=f"Template repository for {options.display_name}. "
                        f"This repository is the base repository for all student repositories in this course. "
                        f"Changes (like creating an exercise) are also applied here.",
            name="template",
            template=True,
        ))
        self.org_api.create_org_repo(org=course, body=CreateRepoOption(
            auto_init=True,
            private=True,
            default_branch="master",
            description=f"Space for tutors.",
            name="tutors",
        ))

        # create tutors team
        self.org_api.org_create_team(org=course, body=CreateTeamOption(
            name="Tutors",
            description="Amazing people grading exercises in exchange for money they definitely need.",
            permission="write",
            units=["repo.code"],
            includes_all_repositories=True
        ))

        # create students team
        self.org_api.org_create_team(org=course, body=CreateTeamOption(
            name="Students",
            description="Awesome people trying their best.",
            permission="write",
            units=["repo.code"],
        ))

    def remove_course(self, course: str):
        # restrict access to all repos
        self.restrict_access(course)
        # move all repos to archive (with unique name)
        self.ensure_archive_exists()
        # ignore if it does not exist
        try:
            for repo in self.org_api.org_list_repos(org=course):
                self.archive_repo(course, repo.name, ensure_archive_exists=False)

            # delete organization
            self.org_api.org_delete(org=course)
        except ApiException as e:
            if e.status != 404:
                raise e

    def restrict_access(self, course: str):
        for repo in self.org_api.org_list_repos(org=course):
            try:
                self.repo_api.repo_delete_collaborator(owner=repo.owner.login, repo=repo.name, collaborator=repo.name)
            except ApiException as e:
                # ignore if their is no such user, as e.g in template
                if e.status != 422:
                    raise e

    def permit_access(self, course: str):
        for repo in self.org_api.org_list_repos(org=course):
            try:
                self.repo_api.repo_add_collaborator(owner=repo.owner.login, repo=repo.name, collaborator=repo.name)
            except ApiException as e:
                # ignore if their is no such user, as e.g in template
                if e.status != 422:
                    raise e

    # student
    def add_student(self, course: str, student: str):
        # add to students team
        self.org_api.org_add_team_member(id=self.team_id(course, "Students"), username=student)

        # create repository based on template
        self.repo_api.generate_repo(template_owner=course, template_repo="template", body=GenerateRepoOption(
            avatar=True,
            description=f"",
            git_content=True,
            git_hooks=True,
            name=student,
            owner=course,
            private=True,
            topics=False,
            labels=False,
            webhooks=False
        ))

        # add student as collaborator to his own repo
        self.repo_api.repo_add_collaborator(owner=course, repo=student, collaborator=student,
                                            body=AddCollaboratorOption(
                                                permission="write"
                                            ))

    def remove_student(self, course: str, student: str):
        try:
            # remove access from repo
            self.repo_api.repo_delete_collaborator(owner=course, repo=student, collaborator=student)
            # move repo to archive
            self.archive_repo(course, student)
            # remove from students team
            self.org_api.org_remove_team_member(id=self.team_id(course, "Students"), username=student)
        except ApiException as e:
            # if repo did not exist, dont care
            if e != 422:
                raise e

    # tutor
    def add_tutor(self, course: str, tutor: str, options: AddTutorOption):
        self.org_api.org_add_team_member(id=self.team_id(course, "Tutors"), username=tutor)
        # make info public for tutors students
        self.sudo(tutor, lambda: self.user_api.update_user_settings(body=UserSettingsOptions(
            description=options.description,
            full_name=options.name,
            hide_activity=False,
            hide_email=False,
        )))

    def remove_tutor(self, course: str, tutor: str):
        try:
            self.org_api.org_remove_team_member(id=self.team_id(course, "Tutors"), username=tutor)
        except ApiException as e:
            # if they are not in the team dont care
            if e.status != 404:
                raise e

    # exercise
    def add_exercise(self, course: str, exercise: str, students: list, options: CreateExerciseOption):
        for student in students + ["template"]:
            try:
                self.repo_api.repo_create_file(owner=course, repo=student, filepath=f"{exercise}/README.md",
                                               body=CreateFileOptions(
                                                   author=Identity(name=options.course_name,
                                                                   email="laurel@informatik.uni-freiburg.de"),
                                                   committer=Identity(name=options.course_name,
                                                                      email="laurel@informatik.uni-freiburg.de"),
                                                   message=f"Published '{exercise}'",
                                                   content=base64.b64encode(f"# {exercise} (?? / {str(options.points)})"
                                                                            .encode("utf-8")).decode("utf-8")
                                               ))
                self.repo_api.repo_create_file(owner=course, repo=student, filepath=f"{exercise}/NOTES.md",
                                               body=CreateFileOptions(
                                                   author=Identity(name=options.course_name,
                                                                   email="laurel@informatik.uni-freiburg.de"),
                                                   committer=Identity(name=options.course_name,
                                                                      email="laurel@informatik.uni-freiburg.de"),
                                                   message=f"Published '{exercise}'",
                                                   content=base64.b64encode(
                                                       f"# Notes\n\nZeitbedarf: X.X h\n\n## Erfahrungen\nYOUR TEXT HERE"
                                                           .encode("utf-8")).decode("utf-8")
                                               ))
            except ApiException as e:
                # file existed why so ever, is okay
                if e.status != 422 and e.status != 403:
                    raise e

    def delete_exercise(self, course: str, display_name: str, exercise: str, students: list):
        for student in students + ["template"]:
            try:
                readme = self.repo_api.repo_get_contents(owner=course, repo=student,
                                                         filepath=f"{exercise}/README.md")
                self.repo_api.repo_delete_file(owner=course, repo=student,
                                               filepath=exercise + "/README.md",
                                               body=DeleteFileOptions(
                                                   author=Identity(name=display_name,
                                                                   email="laurel@informatik.uni-freiburg.de"),
                                                   committer=Identity(name=display_name,
                                                                      email="laurel@informatik.uni-freiburg.de"),
                                                   sha=readme.sha,
                                                   message=f"Deleted '{exercise}'",
                                               ))
                notes = self.repo_api.repo_get_contents(owner=course, repo=student,
                                                        filepath=f"{exercise}/NOTES.md")
                self.repo_api.repo_delete_file(owner=course, repo=student,
                                               filepath=exercise + "/NOTES.md",
                                               body=DeleteFileOptions(
                                                   author=Identity(name=display_name,
                                                                   email="laurel@informatik.uni-freiburg.de"),
                                                   committer=Identity(name=display_name,
                                                                      email="laurel@informatik.uni-freiburg.de"),
                                                   sha=notes.sha,
                                                   message=f"Deleted '{exercise}'",
                                               ))
            except ApiException as e:
                # did not exist
                if e.status != 404 and e.status != 403 and e.status != 400:
                    raise e

    def get_readme(self, course: str, exercise: str, student: str):
        try:
            file = self.repo_api.repo_get_contents(owner=course, repo=student, filepath=f"{exercise}/README.md")
            try:
                return base64.b64decode(file.content.encode("utf-8")).decode("utf-8")
            except UnicodeDecodeError:
                return None
        except ApiException as e:
            if e.status != 404:
                raise e
        return None

    def get_notes(self, course: str, exercise: str, student: str):
        try:
            file = self.repo_api.repo_get_contents(owner=course, repo=student, filepath=f"{exercise}/NOTES.md")
            try:
                return base64.b64decode(file.content.encode("utf-8")).decode("utf-8")
            except UnicodeDecodeError:
                return None
        except ApiException as e:
            if e.status != 404:
                raise e
        return None

    # archive
    def archive_repo(self, owner: str, repo: str, ensure_archive_exists=True):
        if ensure_archive_exists:
            self.ensure_archive_exists()
        self.repo_api.repo_edit(owner=owner, repo=repo, body=EditRepoOption(
            archived=True,
            name=f"{owner}-{repo}-{str(int(time.time()))}"
        ))
        self.repo_api.repo_transfer(owner=owner, repo=repo, body=TransferRepoOption(
            new_owner="archive"
        ))

    def ensure_archive_exists(self):
        if not self.user_exists("archive"):
            self.admin_api.admin_create_user(body=CreateUserOption(
                username="archive",
                login_name="archive",
                email="archive@courses.server.email",
                full_name="Archive",
                visibility="private",
                password=Env.get("GITEA_PASSWORD"),
                must_change_password=False
            ))

    # util
    @staticmethod
    def sudo(user: str, f):
        gitea_exercises_configuration.api_key["Sudo"] = user
        r = f()
        gitea_exercises_configuration.api_key["Sudo"] = None
        return r

    def make_admin(self, user):
        if self.exists_no_admin(user["sub"]):
            self.admin_api.admin_edit_user(username=user["sub"], body=EditUserOption(
                admin=True,
                login_name=user["sub"],
                full_name=user["name"],
                source_id=0
            ))

    def is_admin(self, user: str):
        try:
            return self.user_api.user_get(user).is_admin
        except ApiException:
            return False

    def exists_no_admin(self, user: str):
        try:
            return not self.user_api.user_get(user).is_admin
        except ApiException:
            return False

    def user_exists(self, user: str):
        try:
            self.user_api.user_get(user)
            return True
        except ApiException:
            return False

    def get_all_users(self):
        return list(map(lambda user: user.login, self.admin_api.admin_get_all_users()))

    def team_id(self, course: str, team: str):
        q = list(filter(lambda t: t.name == team, self.org_api.org_list_teams(course)))
        if q:
            return q[0].id
        else:
            return None


gitea_exercises = GiteaExercises()
