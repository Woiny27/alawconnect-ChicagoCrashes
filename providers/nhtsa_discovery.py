from typing import Any, Dict, List

import requests

from providers.base import Provider


class NHTSADiscoveryModule(Provider):
    """Fetch valid crash case IDs from NHTSA CrashAPI."""

    def __init__(self) -> None:
        self.base_url = "https://crashviewer.nhtsa.dot.gov/CrashAPI"

    def fetch(self, state_code: int, year: int) -> List[str]:
        """Provider-compatible wrapper around case ID discovery."""
        return self.get_valid_case_ids(state_code=state_code, year=year)

    def get_valid_case_ids(self, state_code: int, year: int) -> List[str]:
        """
        Fetch real case IDs from NHTSA CrashAPI.

        Args:
            state_code: Numeric state code (for example, 1 for Alabama).
            year: Year to query.

        Returns:
            A list of case IDs using `CaseNumber` when available,
            otherwise `StateCase`.
        """
        endpoint = f"{self.base_url}/crashes/GetCaseList"
        params = {
            "states": state_code,
            "fromYear": year,
            "toYear": year,
            "minNumOfVehicles": 1,
            "format": "json",
        }

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        return self._extract_case_ids(data)

    def get_case_details(self, state_case: str, case_year: int, state_code: int) -> Dict[str, Any]:
        """
        Fetch details for a specific NHTSA crash case.

        Args:
            state_case: The state case number (for example, "10003").
            case_year: Case year.
            state_code: Numeric state code (for example, 1 for Alabama).

        Returns:
            Raw JSON payload from NHTSA CrashAPI GetCaseDetails.
        """
        endpoint = f"{self.base_url}/crashes/GetCaseDetails"
        params = {
            "stateCase": state_case,
            "caseYear": case_year,
            "state": state_code,
            "format": "json",
        }

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_crashes_by_person(
        self,
        age: int,
        sex: int,
        seat_pos: int,
        injury_severity: int,
        from_case_year: int,
        to_case_year: int,
        state_code: int,
        include_occupants: bool = True,
        include_non_occupants: bool = True,
    ) -> Dict[str, Any]:
        """
        Query crashes by person-level filters via NHTSA CrashAPI.

        Args:
            age: Person age.
            sex: Sex code expected by NHTSA API.
            seat_pos: Seat position code.
            injury_severity: Injury severity code.
            from_case_year: Start case year (inclusive).
            to_case_year: End case year (inclusive).
            state_code: Numeric state code.
            include_occupants: Include occupant records.
            include_non_occupants: Include non-occupant records.

        Returns:
            Raw JSON payload from NHTSA CrashAPI GetCrashesByPerson.
        """
        endpoint = f"{self.base_url}/crashes/GetCrashesByPerson"
        params = {
            "age": age,
            "sex": sex,
            "seatPos": seat_pos,
            "injurySeverity": injury_severity,
            "fromCaseYear": from_case_year,
            "toCaseYear": to_case_year,
            "state": state_code,
            "includeOccupants": str(include_occupants).lower(),
            "includeNonOccupants": str(include_non_occupants).lower(),
            "format": "json",
        }

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_crashes_by_location(
        self,
        from_case_year: int,
        to_case_year: int,
        state_code: int,
        county_code: int,
    ) -> Dict[str, Any]:
        """
        Query crashes by state/county and case-year range.

        Args:
            from_case_year: Start case year (inclusive).
            to_case_year: End case year (inclusive).
            state_code: Numeric state code.
            county_code: Numeric county code.

        Returns:
            Raw JSON payload from NHTSA CrashAPI GetCrashesByLocation.
        """
        endpoint = f"{self.base_url}/crashes/GetCrashesByLocation"
        params = {
            "fromCaseYear": from_case_year,
            "toCaseYear": to_case_year,
            "state": state_code,
            "county": county_code,
            "format": "json",
        }

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_variables(self, data_year: int) -> Dict[str, Any]:
        """
        Fetch variable definitions for a given FARS data year.

        Args:
            data_year: Data year used by the definitions endpoint.

        Returns:
            Raw JSON payload from NHTSA CrashAPI GetVariables.
        """
        endpoint = f"{self.base_url}/definitions/GetVariables"
        params = {
            "dataYear": data_year,
            "format": "json",
        }

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_variable_attributes(self, variable: str, case_year: int) -> Dict[str, Any]:
        """
        Fetch allowed attributes/values for a specific variable in a case year.

        Args:
            variable: Variable name (for example, "make").
            case_year: Case year used by the definitions endpoint.

        Returns:
            Raw JSON payload from NHTSA CrashAPI GetVariableAttributes.
        """
        endpoint = f"{self.base_url}/definitions/GetVariableAttributes"
        params = {
            "variable": variable,
            "caseYear": case_year,
            "format": "json",
        }

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_variable_attributes_for_model(
        self,
        variable: str,
        case_year: int,
        make: int,
    ) -> Dict[str, Any]:
        """
        Fetch model-scoped attributes/values for a specific variable.

        Args:
            variable: Variable name (for example, "model").
            case_year: Case year used by the definitions endpoint.
            make: Numeric make code expected by the API.

        Returns:
            Raw JSON payload from NHTSA CrashAPI GetVariableAttributesForModel.
        """
        endpoint = f"{self.base_url}/definitions/GetVariableAttributesForModel"
        params = {
            "variable": variable,
            "caseYear": case_year,
            "make": make,
            "format": "json",
        }

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_variable_attributes_for_body_type(
        self,
        variable: str,
        make: int,
        model: int,
    ) -> Dict[str, Any]:
        """
        Fetch body-type-scoped attributes/values for a specific variable.

        Args:
            variable: Variable name (for example, "bodytype").
            make: Numeric make code expected by the API.
            model: Numeric model code expected by the API.

        Returns:
            Raw JSON payload from NHTSA CrashAPI GetVariableAttributesForbodyType.
        """
        endpoint = f"{self.base_url}/definitions/GetVariableAttributesForbodyType"
        params = {
            "variable": variable,
            "make": make,
            "model": model,
            "format": "json",
        }

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_fars_data(
        self,
        dataset: str,
        from_year: int,
        to_year: int,
        state_code: int,
        output_format: str = "csv",
    ) -> Any:
        """
        Fetch FARS data for a dataset, year range, and state.

        Args:
            dataset: FARS dataset name (for example, "Accident").
            from_year: Start year (inclusive).
            to_year: End year (inclusive).
            state_code: Numeric state code.
            output_format: Response format ("csv" or "json").

        Returns:
            CSV text when format is csv; parsed JSON when format is json.
        """
        endpoint = f"{self.base_url}/FARSData/GetFARSData"
        params = {
            "dataset": dataset,
            "FromYear": from_year,
            "ToYear": to_year,
            "State": state_code,
            "format": output_format,
        }

        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()

        if output_format.lower() == "csv":
            return response.text

        return response.json()

    @staticmethod
    def _extract_case_ids(data: Dict[str, Any]) -> List[str]:
        """Safely parse the API response and collect valid case identifiers."""
        results = data.get("Results", [])
        if not results:
            return []

        # In observed payloads, Results can be a list of case dicts, but some
        # responses wrap the list as the first element.
        case_rows: List[Dict[str, Any]] = []
        first = results[0]

        if isinstance(first, list):
            case_rows = [row for row in first if isinstance(row, dict)]
        elif isinstance(first, dict):
            case_rows = [row for row in results if isinstance(row, dict)]

        case_ids: List[str] = []
        for row in case_rows:
            raw_id = row.get("CaseNumber") or row.get("StateCase")
            if raw_id is None:
                continue

            case_id = str(raw_id).strip()
            if case_id:
                case_ids.append(case_id)

        return case_ids