# Copyright 2010 New Relic, Inc.
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

import pytest

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import record_exception
from newrelic.api.transaction import current_transaction

from newrelic.common.object_names import callable_name

from testing_support.fixtures import (
    validate_transaction_errors,
    override_application_settings,
    validate_error_event_sample_data,
    validate_transaction_metrics,
)


_runtime_error_name = callable_name(RuntimeError)
_error_message = "Test error message."

# Settings presets

# Error classes settings
expected_runtime_error_settings = {
    "error_collector.expected_classes": _runtime_error_name
}
ignore_runtime_error_settings = {
    "error_collector.ignore_errors": _runtime_error_name
}  # TODO Change this to the new setting
combined_runtime_error_settings = {}
combined_runtime_error_settings.update(expected_runtime_error_settings)
combined_runtime_error_settings.update(ignore_runtime_error_settings)

# Status code settings
expected_status_code_error_settings = {"error_collector.expected_status_codes": "429"}
ignore_status_code_error_settings = {"error_collector.ignore_status_codes": "429"}
combined_status_code_error_settings = {}
combined_status_code_error_settings.update(expected_runtime_error_settings)
combined_status_code_error_settings.update(ignore_runtime_error_settings)

_test_record_exception = [(_runtime_error_name, _error_message)]
_intrinsic_attributes = {
    "error.class": _runtime_error_name,
    "error.message": _error_message,
    "error.expected": False,
    "transactionName": "OtherTransaction/Function/test",
}
_metrics_normal = [
    ("Errors/all", 1),
    ("Errors/OtherTransaction/Function/test", 1),
    ("Errors/allOther", 1),
]

parameter_matrix = [
    ({}, False, False),
    (ignore_runtime_error_settings, False, True),
    # (expected_runtime_error_settings, True, False),  # TODO Enable this test after implementing logic
    (combined_runtime_error_settings, False, True),
]
override_expected_matrix = (False, None)  # TODO Add true once functionality is in place


def exercise(override_expected=None):
    try:
        raise RuntimeError(_error_message)
    except RuntimeError:
        # TODO Switch to notice_error and pass expected=override_expected
        record_exception()


@pytest.mark.parametrize("settings,expected,ignore", parameter_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
def test_classes_error_events(settings, expected, ignore, override_expected):
    expected = override_expected or expected

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0
    errors = _test_record_exception if not ignore else []

    @override_application_settings(settings)
    @validate_transaction_errors(errors=errors)
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @background_task(name="test")
    def _test():
        exercise()

    _test()


@pytest.mark.parametrize("settings,expected,ignore", parameter_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
def test_classes_exception_metrics(settings, expected, ignore, override_expected):
    expected = override_expected or expected
    metrics = _metrics_normal if not (expected or ignore) else []

    @override_application_settings(settings)
    @validate_transaction_metrics("test", background_task=True, rollup_metrics=metrics)
    @background_task(name="test")
    def _test():
        exercise()

    _test()