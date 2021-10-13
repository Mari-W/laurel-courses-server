from sqlalchemy import UniqueConstraint, Column, Integer, String, Boolean, Text, DateTime, Float

from server.database import database


class CourseEntity(database.Model):
    __tablename__ = 'course'

    __table_args__ = (UniqueConstraint('name', 'semester', name='_course_uc'),)

    id = Column(Integer, primary_key=True)

    name = Column(String(122), nullable=False)
    semester = Column(String(6), nullable=False)
    owner = Column(String(64), nullable=False)
    display_name = Column(String(256))
    website = Column(String(256))
    # students can access repos
    restricted = Column(Boolean, nullable=False, default=False)
    # students can join
    open = Column(Boolean, nullable=False, default=False)

    @property
    def uid(self):
        return self.semester + "-" + self.name


class TutorEntity(database.Model):
    __tablename__ = 'tutor'

    __table_args__ = (UniqueConstraint('course', 'username', name='_tutor_uc'),)

    id = Column(Integer, primary_key=True)

    course = Column(String(128), nullable=False)
    username = Column(String(64), nullable=False)
    email = Column(String(128), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text)


class StudentEntity(database.Model):
    __tablename__ = 'student'

    __table_args__ = (UniqueConstraint('course', 'username', name='_student_uc'),)

    id = Column(Integer, primary_key=True)

    course = Column(String(128), nullable=False)
    username = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False)
    matrikelnummer = Column(Integer, nullable=True)


class TutorStudentEntity(database.Model):
    __tablename__ = 'tutor_student'

    __table_args__ = (UniqueConstraint('course', 'student', name='_student_tutor_uc'),)

    id = Column(Integer, primary_key=True)

    student = Column(String(64), nullable=False)
    tutor = Column(String(64), nullable=False)
    course = Column(String(128), nullable=False)


class ExerciseEntity(database.Model):
    __tablename__ = 'exercise'

    __table_args__ = (UniqueConstraint('course', 'name', name='_exercise_uc'),)

    id = Column(Integer, primary_key=True)

    course = Column(String(128), nullable=False)
    creator = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)

    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)

    points = Column(Float, nullable=True)


class StudentExerciseEntity(database.Model):
    __tablename__ = 'student_exercise'

    __table_args__ = (UniqueConstraint('course', 'student', 'exercise', name='_student_exercise_uc'),)

    id = Column(Integer, primary_key=True)

    course = Column(String(128), nullable=False)
    exercise = Column(String(128), nullable=False)

    student = Column(String(64), nullable=False)
    tutor = Column(String(64), nullable=False)

    points = Column(Float, nullable=True)
