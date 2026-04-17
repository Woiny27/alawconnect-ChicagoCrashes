import pytest

from core.pipeline import run_pipeline


def test_run_pipeline_applies_steps_in_order():
    def step1(data):
        return data + ["step1"]

    def step2(data):
        return data + ["step2"]

    steps = [step1, step2]
    result = run_pipeline(steps, data=[])

    assert result == ["step1", "step2"]


def test_run_pipeline_passes_none_initial_data():
    def step(data):
        return ["initialized"] if data is None else data

    result = run_pipeline([step])

    assert result == ["initialized"]
