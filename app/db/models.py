"""PostgreSQL 모델 stub (SQLAlchemy). Day5에 진척도 연결."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# TODO(Day5): 아래 테이블 구현
# users        : id, username, grade(4~6), semester
# problems     : id, unit, difficulty, problem, answer, solution_steps, hint_by_level
# attempts     : id, user_id, problem_id, hints_used, solved, created_at
# unit_mastery : user_id, unit, problems_attempted, avg_hints_used, mastery_level, updated_at
