import os

from dagster_dbt import DbtCliResource

DBT_PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "dbt_project")
DBT_PROJECT_DIR = os.path.abspath(DBT_PROJECT_DIR)

dbt_resource = DbtCliResource(project_dir=DBT_PROJECT_DIR, profiles_dir=DBT_PROJECT_DIR)
