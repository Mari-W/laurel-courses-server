import re
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from flask import request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from server.database import database
from server.error_handling import try_except, send_error
from server.exercises.models import CourseEntity, StudentEntity, TutorEntity, TutorStudentEntity, ExerciseEntity, \
    StudentExerciseEntity
from server.exercises.options import CreateCourseOption, AddTutorOption, CreateExerciseOption
from server.integration.auth_server import auth
from server.integration.gitea_exercises import gitea_exercises
from server.integration.rocket_chat import rocket


@dataclass
class Course:
    name: str
    semester: str

    # general
    def create(self, options: CreateCourseOption) -> Optional[str]:
        if not self.exists_strict:
            if try_except(lambda: rocket.add_course(str(self), options),
                          lambda: rocket.remove_course(str(self))):
                if try_except(lambda: gitea_exercises.add_course(str(self), options),
                              lambda: [gitea_exercises.remove_course(str(self)), rocket.remove_course(str(self))]):
                    with database as db:
                        db += CourseEntity(
                            name=self.name,
                            semester=self.semester,
                            owner=options.owner,
                            display_name=options.display_name,
                            website=options.website,
                            restricted=False,
                            open=options.joinable
                        )
                else:
                    return f"failed creating {str(self)} in gitea"
            else:
                return f"failed creating {str(self)} in rocket"
        else:
            return f"course {str(self)} already exists"

    def delete(self):
        if self.exists:
            if try_except(lambda: rocket.remove_course(str(self))):
                if try_except(lambda: gitea_exercises.remove_course(str(self))):
                    with database:
                        CourseEntity.query.delete_by(name=self.name, semester=self.semester)
                        StudentEntity.query.delete_by(course=str(self))
                        TutorEntity.query.delete_by(course=str(self))
                        TutorStudentEntity.query.delete_by(course=str(self))
                        ExerciseEntity.query.delete_by(course=str(self))
                        StudentExerciseEntity.query.delete_by(course=str(self))
            else:
                return f"failed to remove {str(self)} in rocket"
        else:
            return f"failed to remove {str(self)} in gitea"

    def restrict_student_access(self):
        if try_except(lambda: gitea_exercises.restrict_access(str(self))):
            with database:
                self.entity.restricted = True

    def permit_student_access(self):
        if try_except(lambda: gitea_exercises.permit_access(str(self))):
            with database:
                self.entity.restricted = False

    def close(self):
        with database:
            self.entity.open = False

    def open(self):
        with database:
            self.entity.open = True

    @property
    def is_open(self):
        return self.exists and self.entity.open

    @property
    def is_restricted(self):
        return self.exists and self.entity.restricted

    def get_role(self, username: str, is_admin=False):
        if self.has_student(username):
            return "student"
        elif self.has_tutor(username):
            return "tutor"
        elif self.entity.owner == username:
            return "owner"
        elif is_admin or auth.is_admin(username):
            return "admin"

    # students
    def add_student(self, student: str) -> Optional[str]:
        info = auth.get_user_info(student)
        if info:
            role = self.get_role(student, is_admin=info["role"] == "admin")
            if role is None:
                if try_except(lambda: rocket.add_student(str(self), student),
                              lambda: rocket.remove_student(str(self), student)):
                    if try_except(lambda: gitea_exercises.add_student(str(self), student),
                                  lambda: [gitea_exercises.remove_student(str(self), student),
                                           rocket.remove_student(str(self), student)]):
                        # if try_except(lambda: drone.activate(str(self), student),
                        #               lambda: [gitea_exercises.remove_student(str(self), student),
                        #                        rocket.remove_student(str(self), student), drone.sync()]):
                        # safe method
                        self.assign_tutor(student)
                        try:
                            with database as db:
                                db += StudentEntity(
                                    course=str(self),
                                    username=student,
                                    name=info["name"],
                                    email=info["email"],
                                    matrikelnummer=info["matrikelnummer"]
                                )
                        except IntegrityError as e:
                            # if student entity exist dont care
                            send_error(e)
                            pass
                        # else:
                        #     return f"failed to activate {student} in drone"
                    else:
                        return f"failed to create {student}'s repo in gitea"
                else:
                    return f"failed to add student in rocket"
            else:
                return f"failed to add {student}, is {role}"
        else:
            return f"failed to retrieve information about {student} from auth server"

    def remove_student(self, student) -> Optional[str]:
        if self.has_student(student):
            if try_except(lambda: rocket.remove_student(str(self), student)):
                if try_except(lambda: gitea_exercises.remove_student(str(self), student),
                              lambda: rocket.add_student(str(self), student)):
                    self.unassign_tutor(student)
                    with database:
                        StudentEntity.query.delete_by(course=str(self), username=student)
                        StudentExerciseEntity.query.delete_by(course=str(self), student=student)
                else:
                    return f"failed to remove {student} in gitea"
            else:
                return f"failed to remove {student} in rocket"
        else:
            return f"failed to remove {student}, not a student"

    def has_student(self, student: str):
        return StudentEntity.query.exists(course=str(self), username=student)

    @property
    def students(self):
        return StudentEntity.query.many(course=str(self))

    @property
    def student_names(self):
        return [student.username for student in StudentEntity.query.many(course=str(self))]

    # tutors
    def has_tutor(self, tutor: str):
        return TutorEntity.query.exists(course=str(self), username=tutor)

    def add_tutor(self, tutor: str, options: AddTutorOption) -> Optional[str]:
        role = self.get_role(tutor)
        if role is None:
            info = auth.get_user_info(tutor)
            if info:
                options.name = info["name"]
                if try_except(lambda: rocket.add_tutor(str(self), tutor, options.name),
                              lambda: rocket.remove_tutor(str(self), tutor)):
                    if try_except(lambda: gitea_exercises.add_tutor(str(self), tutor, options),
                                  lambda: [gitea_exercises.remove_tutor(str(self), tutor),
                                           rocket.remove_tutor(str(self), tutor)]):
                        try:
                            with database as db:
                                db += TutorEntity(
                                    course=str(self),
                                    username=tutor,
                                    name=options.name,
                                    description=options.description,
                                    email=info["email"]
                                )
                        except IntegrityError as e:
                            # if he somehow exists
                            send_error(e)
                            pass
                        # first ever tutor, assign all students
                        if len(self.tutors) == 1:
                            for student in self.students:
                                try:
                                    with database as db:
                                        db += TutorStudentEntity(tutor=tutor, student=student.username,
                                                                 course=str(self))
                                except IntegrityError as e:
                                    # student already had tutor
                                    send_error(e)
                                    pass
                    else:
                        return f"failed to add {tutor} in gitea"
                else:
                    return f"failed to add {tutor} in rocket"
            else:
                return f"failed to retrieve information about {tutor} from auth server"
        else:
            return f"failed to add {tutor}, is {role}"

    def remove_tutor(self, tutor: str) -> Optional[str]:
        if self.has_tutor(tutor):
            if try_except(lambda: rocket.remove_tutor(str(self), tutor)):
                if try_except(lambda: gitea_exercises.remove_tutor(str(self), tutor),
                              lambda: rocket.add_tutor(str(self), tutor, tutor)):
                    with database:
                        TutorEntity.query.delete_by(course=str(self), username=tutor)
                    students = self.get_tutor_student_names(tutor)
                    with database:
                        TutorStudentEntity.query.delete_by(course=str(self), tutor=tutor)
                    for student in students:
                        self.assign_tutor(student)
                else:
                    return f"failed to remove {tutor} in gitea"
            else:
                return f"failed to remove {tutor} in rocket"
        else:
            return f"failed to remove {tutor}, not a tutor"

    def assign_tutor(self, student: str):
        if not student.startswith("test"):
            tutors = self.tutor_names

            # will be assigned on first tutor join
            if not tutors:
                return

            distribution = self.tutor_students_count

            for tutor in tutors:
                if tutor not in distribution.keys():
                    distribution[tutor] = 0

            with database as db:
                try:
                    db += TutorStudentEntity(tutor=min(distribution, key=distribution.get), student=student,
                                             course=str(self))
                except IntegrityError as e:
                    # student already got some tutor
                    send_error(e)
                    pass

    def unassign_tutor(self, student: str):
        with database:
            TutorStudentEntity.query.delete_by(student=student, course=str(self))

    def edit_tutors(self, upd):
        for tutor, student_list in upd.items():
            if not student_list:
                continue
            for student in student_list:
                r = TutorStudentEntity.query.one(student=student, course=str(self))
                # if student had no tutor till now, why so ever, add him
                if not r:
                    with database as db:
                        db += TutorStudentEntity(student=student, course=str(self), tutor=tutor)
                # tutor changed, update tutor
                elif r.tutor != tutor:
                    with database:
                        r.tutor = tutor

    def get_tutor(self, tutor: str):
        return TutorEntity.query.one(course=str(self), username=tutor)

    @property
    def tutors(self):
        return TutorEntity.query.many(course=str(self))

    @property
    def tutor_names(self):
        return [tutor.username for tutor in TutorEntity.query.many(course=str(self))]

    def get_tutor_students(self, tutor: str):
        return TutorStudentEntity.query.many(course=str(self), tutor=tutor)

    def get_tutor_student_names(self, tutor: str):
        return [r.student for r in self.get_tutor_students(tutor)]

    def get_student_tutor(self, student: str):
        r = TutorStudentEntity.query.one(course=str(self), student=student)
        if not r:
            return None
        else:
            return TutorEntity.query.one(course=str(self), username=r.tutor)

    def get_student_tutor_name(self, student: str):
        r = TutorStudentEntity.query.one(course=str(self), student=student)
        if not r:
            return None
        else:
            return r.tutor

    @property
    def tutor_students_count(self):
        return dict(database.session.query(TutorStudentEntity.tutor, func.count(TutorStudentEntity.tutor)).filter_by(
            course=str(self)).group_by(TutorStudentEntity.tutor).all())

    # exercises

    def add_exercise(self, exercise: str, options: CreateExerciseOption) -> Optional[str]:
        if not self.has_exercise(exercise):
            options.course_name = self.entity.display_name
            if " " not in exercise:
                if options.start <= options.end:
                    if try_except(lambda: rocket.add_exercise(str(self), exercise),
                                  lambda: rocket.remove_exercise(str(self), exercise)):
                        if try_except(
                                lambda: gitea_exercises.add_exercise(str(self), exercise, self.student_names, options),
                                lambda: [
                                    gitea_exercises.delete_exercise(str(self), options.course_name, exercise,
                                                                    self.student_names),
                                    rocket.remove_exercise(str(self), exercise)]):
                            # has to work, has_exercise checks integrity
                            with database as db:
                                db += ExerciseEntity(
                                    course=str(self),
                                    creator=options.creator,
                                    name=exercise,
                                    start=options.start,
                                    end=options.end,
                                    points=options.points
                                )
                        else:
                            return f"could not create {exercise} in gitea"
                    else:
                        return f"could not create {exercise} in rocket"
                else:
                    return f"{exercise} starts after it ends"
            else:
                return f"{exercise} has spaces in it. uncool bro."
        else:
            return f"exercise with name {exercise} already exists"

    def delete_exercise(self, exercise: str) -> Optional[str]:
        if self.has_exercise(exercise):
            if try_except(lambda: rocket.remove_exercise(str(self), exercise)):
                if try_except(lambda: gitea_exercises.delete_exercise(str(self), self.entity.display_name, exercise,
                                                                      self.student_names),
                              lambda: rocket.add_exercise(str(self), exercise)):
                    with database:
                        ExerciseEntity.query.delete_by(course=str(self), name=exercise)
                        StudentExerciseEntity.query.delete_by(course=str(self), exercise=exercise)
                else:
                    return f"could not delete {exercise} in gitea"
            else:
                return f"could not delete {exercise} in rocket"
        else:
            return f"exercise with name {exercise} does not exists"

    def update_start_date(self, exercise: str, date: datetime):
        with database:
            self.get_exercise(exercise).start = date

    def update_end_date(self, exercise: str, date: datetime):
        with database:
            self.get_exercise(exercise).end = date

    def update_points(self, exercise: str, points: float):
        with database:
            self.get_exercise(exercise).points = points

    @property
    def exercises(self):
        return ExerciseEntity.query.many(course=str(self))

    def get_exercise(self, exercise: str):
        return ExerciseEntity.query.one(course=str(self), name=exercise)

    def has_exercise(self, exercise: str):
        return ExerciseEntity.query.exists(course=str(self), name=exercise)

    @property
    def student_exercises(self):
        return StudentExerciseEntity.query.many(course=str(self))

    def get_student_exercises(self, student: str):
        return StudentExerciseEntity.query.many(course=str(self), student=student)

    def get_student_exercises_by_exercise(self, exercise: str):
        return StudentExerciseEntity.query.many(course=str(self), exercise=exercise)

    def get_student_exercise(self, exercise: str, student: str):
        return StudentExerciseEntity.query.one(course=str(self), student=student, exercise=exercise)

    @property
    def pending_exercises(self):
        now = datetime.now()
        return [exercise for exercise in self.exercises if exercise.start <= now < exercise.end]

    @property
    def finished_exercises(self):
        now = datetime.now()
        return [exercise for exercise in self.exercises if exercise.end < now]

    def get_students_with_points(self, points: int, exercise: str, student_exercises=None):
        if not student_exercises:
            student_exercises = self.get_student_exercises_by_exercise(exercise)
        return len(
            [student_exercise for student_exercise in student_exercises if round(student_exercise.points) == points]
        )

    def get_student_exercises_stats(self, student: str, include_ungraded: bool = False, return_exercises=False,
                                    exercises=None):
        # ugly code but less db queries ;)
        res = dict()
        if exercises is None:
            exercises = self.exercises
        student_exercises = self.get_student_exercises(student)

        def _find_student_exercise(exercise):
            m = [student_exercise for student_exercise in student_exercises if
                 student_exercise.exercise == exercise.name]
            return m[0] if m else None

        total = 0
        max_total = 0

        res["exercises"] = {}

        for exercise, student_exercise in [(exercise, _find_student_exercise(exercise)) for exercise in exercises]:
            if student_exercise:
                total += student_exercise.points
                max_total += exercise.points
                res["exercises"][exercise.name] = {
                    "points": student_exercise.points,
                    "max_points": exercise.points,
                    "tutor": student_exercise.tutor
                }
            elif include_ungraded:
                max_total += exercise.points
                res["exercises"][exercise.name] = {
                    "points": 0,
                    "max_points": exercise.points,
                    "tutor": None
                }

        res["total"] = total
        res["max_total"] = max_total
        res["percentage"] = round((total / max_total) * 100, 1) if max_total != 0 else 0.0
        # for efficiency in courses/exercises route
        if return_exercises:
            return exercises, res

        return res

    def get_time_spent(self, exercise: str):
        res = {}
        for student in self.student_names:
            notes = gitea_exercises.get_notes(str(self), exercise, student)
            matches = re.findall(r"Zeitbedarf: (\d+[,.]?\d*) h", notes)
            if len(matches) != 1:
                continue
            match = matches[0]
            try:
                spent = float(match)
            except ValueError:
                continue
            spent = round(spent)
            if spent in res:
                res[spent] += 1
            else:
                res[spent] = 1
        return res

    def get_points(self, exercise: str, student: str):
        ex = self.get_student_exercise(exercise, student)
        if not ex:
            return None
        else:
            return ex.points

    def set_points(self, exercise: str, student: str, tutor: str, points: float):
        ex = self.get_student_exercise(exercise, student)
        if ex:
            with database:
                ex.tutor = tutor
                ex.points = points
        else:
            with database as db:
                db += StudentExerciseEntity(
                    course=str(self),
                    exercise=exercise,
                    student=student,
                    tutor=tutor,
                    points=points
                )

    # util

    def __str__(self):
        return f"{self.semester}-{self.name}"

    def __hash__(self):
        return int.from_bytes(str(self).encode(), 'little')

    @property
    def dict(self):
        return self.entity.to_dict()

    @property
    def entity(self):
        return CourseEntity.query.one(name=self.name, semester=self.semester)

    @property
    def exists(self):
        return CourseEntity.query.exists(name=self.name, semester=self.semester)

    @property
    def exists_strict(self):
        cs = list(filter(lambda
                             course: course.name.lower() == self.name.lower() and course.semester.lower() == self.semester.lower(),
                         CourseEntity.query.all()))
        return True if cs else False

    @property
    def is_valid(self):
        if " " in self.name:
            return False

        if len(self.semester) != 6:
            return False

        if not (self.semester[4:6] == "SS" or self.semester[4:6] == "WS"):
            return False
        return True

    @staticmethod
    def all_courses():
        return [course for course in [Course(course.name, course.semester) for course in CourseEntity.query.all()] if
                course.is_valid]

    @staticmethod
    def from_req():
        # check if login attempt is via json data
        data = request.get_json(silent=True)

        # check if user logged in via form data
        if not data:
            data = request.form

        if not data["course"]:
            return None

        return Course.from_str(data["course"])

    @staticmethod
    def from_str(s: str) -> Optional["Course"]:
        if len(s) >= 6 and "-" in s:
            s = s.split("-")
            semester = s[0]
            name = "-".join(s[1:])

            c = Course(semester=semester, name=name)
            if c.exists and c.is_valid:
                return c
            else:
                cs = list(filter(
                    lambda course: course.name.lower() == name.lower() and course.semester.lower() == semester.lower(),
                    CourseEntity.query.all()))
                if not cs:
                    return None
                c = Course(semester=cs[0].semester, name=cs[0].name)
                if c.is_valid and c.exists:
                    return c
        return None
