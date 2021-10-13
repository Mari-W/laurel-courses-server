from datetime import datetime
from dataclasses import dataclass
from typing import Union


@dataclass
class CreateCourseOption:
    display_name: str
    website: str
    joinable: bool
    owner: str


@dataclass
class AddTutorOption:
    description: str
    # is placed automatically
    name: str = ""


@dataclass
class CreateExerciseOption:
    creator: str
    start: datetime
    end: datetime
    points: Union[float, int]
    # placed automatically
    course_name: str = ""
